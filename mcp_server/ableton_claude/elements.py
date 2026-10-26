"""Open a mix, a loop or a sample into one channel per element.

The producer's rule for a mix: every element alone on its own channel, so each gets its
own level, cuts and processing. A sampled loop or an original song arrives as one file;
this splits it (ear/separate.py: kick, snare, toms, hats, ride, crash, bass, music, lead
and backing vocal, and on request the lead's dry voice apart from its reverb), says what
each piece holds (ear/tagging.py: rap or speech, singing, scratch, crowd, keys...), and
lays every element on its own audio track under the source clips, with the source's
warp markers and markers, so they play exactly where the original played.

Offline functions take paths; `place` takes `call` (server._journaled), so every track
and clip it makes can be reverted.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

# element -> track label; the order is the order of the new tracks
LABELS = {
    "kick": "KICK", "snare": "SNARE", "toms": "TOMS", "hats": "HATS", "ride": "RIDE",
    "crash": "CRASH", "drums": "DRUMS", "bass": "BASS", "other": "MUSIC",
    "lead_vocal": "VOX LEAD", "lead_vocal_dry": "VOX DRY", "lead_vocal_reverb": "VOX VERB",
    "backing_vocal": "VOX BACK", "vocals": "VOX",
}
# a part replaces its parent: drums split -> no DRUMS track, and so on
PARENTS = {"drums": ("kick", "snare", "toms", "hats", "ride", "crash"),
           "vocals": ("lead_vocal", "backing_vocal"),
           "lead_vocal": ("lead_vocal_dry", "lead_vocal_reverb")}
TAGGED = ("vocals", "lead_vocal", "backing_vocal", "lead_vocal_dry", "other", "bass")
SILENT_DB = -55.0      # elements whose RMS stays under this (dBFS) are listed, not placed
BLEED_DB = 30.0        # ... or this far under the loudest element: separation leftovers
MAX_CLIPS = 64         # clips per source track placed in one call (Live main thread)


def out_dir_for(path):
    p = Path(path)
    return p.parent / ("%s elements" % p.stem)


def rms_db(path):
    x, _ = sf.read(str(path), dtype="float32", always_2d=True)
    return round(float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)), 1)


def elements_of(files):
    """The leaves of the split: parents that were split into parts drop out."""
    names = [k for k in files if not k.startswith("_")]
    drop = {p for p, parts in PARENTS.items() if p in names and any(c in names for c in parts)}
    order = list(LABELS)
    return sorted((n for n in names if n not in drop),
                  key=lambda n: order.index(n) if n in order else len(order))


def analyze(path, out_dir=None, drums=True, vocals=True, reverb=False, tag=True, log=None):
    """Split `path` and describe every element: {source, out_dir, elements: {name:
    {file, label, rms_db, silent, roles?, segments?}}, seconds, wet_dry_db?}. Writes
    elements.json next to the stems (a second call with the same options reuses it)."""
    from .ear import separate, tagging
    out_dir = Path(out_dir or out_dir_for(path))
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "elements.json"
    opts = {"drums": drums, "vocals": vocals, "reverb": reverb, "tag": tag}
    if report.exists():
        old = json.loads(report.read_text())
        if old.get("options") == opts and all(Path(e["file"]).exists()
                                              for e in old["elements"].values()):
            return dict(old, cached=True)
    files = separate.split(path, out_dir, drums=drums, vocals=vocals, reverb=reverb,
                           prefix=Path(path).stem[:40], log=log)
    els = {}
    levels = {name: rms_db(files[name]) for name in elements_of(files)}
    top = max(levels.values()) if levels else 0.0
    for name, level in levels.items():
        e = {"file": files[name], "label": LABELS.get(name, name.upper()),
             "rms_db": level, "silent": level < SILENT_DB or level < top - BLEED_DB}
        if tag and name in TAGGED and not e["silent"]:
            if log:
                log("tag %s" % name)
            t = tagging.tag_file(files[name])
            e["roles"] = t["roles"]
            e["top"] = t["top"][:5]
            e["segments"] = [s for s in t["segments"] if s["lead"] not in ("silence", "music")]
        els[name] = e
    out = {"source": str(path), "out_dir": str(out_dir), "options": opts, "elements": els,
           "seconds": files.get("_seconds")}
    if "lead_vocal_dry" in els and "lead_vocal_reverb" in els:
        out["wet_dry_db"] = round(els["lead_vocal_reverb"]["rms_db"]
                                  - els["lead_vocal_dry"]["rms_db"], 1)
    report.write_text(json.dumps(out, indent=1))
    return out


def summary(result):
    """One line per element for the producer: level and what is in it."""
    lines = []
    for name, e in result["elements"].items():
        what = ", ".join("%s %ss" % (k, v) for k, v in list((e.get("roles") or {}).items())[:3])
        lines.append("%-9s %6.1f dBFS%s%s" % (e["label"], e["rms_db"],
                                               "  (silent)" if e["silent"] else "",
                                               "  " + what if what else ""))
    if "wet_dry_db" in result:
        lines.append("lead vocal reverb %.1f dB under the dry voice" % -result["wet_dry_db"])
    return lines


def source_clips(call, track, clips=None):
    """The audio clips of `track` to split (all of them, or the given indices), grouped
    by file: {file: [clip info + warp markers]}."""
    info = call("get_track", {"track": track, "clips": True, "markers": True})
    want = None if clips is None else {int(c) for c in clips}
    by_file = {}
    for c in info.get("clips", []):
        if c.get("type") != "audio" or not c.get("file"):
            continue
        if want is not None and c["i"] not in want:
            continue
        if c.get("warping"):
            c["markers"] = call("warp_markers", {"track": track, "clip": c["i"]})["markers"]
        by_file.setdefault(c["file"], []).append(c)
    return info, by_file


def place(call, batch, track, track_index, info, by_file, results, mute_source=True):
    """One audio track per element under `track`, each source clip re-created on it with
    the element's file, the same position, warp markers, markers and loop. The source
    clips are muted (journaled: revert_changes brings everything back). `batch` runs a
    list of commands in one Live tick: every element's copy of one source clip goes in
    one batch (a round trip costs ~0.7 s on a 34-track set)."""
    names = []
    for r in results.values():
        for n, e in r["elements"].items():
            if not e["silent"] and n not in names:
                names.append(n)
    # in time order: trim_clip only cuts where nothing lies after the cut
    ordered = sorted(((src, c) for src, cl in by_file.items() for c in cl),
                     key=lambda sc: sc[1]["start"])
    if len(ordered) > MAX_CLIPS:
        raise ValueError("%d clips: place at most %d at a time (pass clips=[...])"
                         % (len(ordered), MAX_CLIPS))
    made, problems, tracks = [], [], {}
    for k, name in enumerate(names):
        label = LABELS.get(name, name.upper())
        tname = ("%s - %s" % (label, info["name"]))[:31]
        t = call("create_track", {"kind": "audio", "name": tname,
                                  "index": track_index + 1 + k})
        call("set_track", {"track": t["i"], "volume_db": info.get("vol_db") or 0.0,
                           "pan": info.get("pan", 0.0)})
        made.append(tname)
        tracks[name] = (t["i"], tname, label)
    for src, c in ordered:
        cmds, owners = [], []
        for name, (ti, tname, label) in tracks.items():
            e = results[src]["elements"].get(name)
            if not e or e["silent"]:
                continue
            new = clip_commands(ti, e["file"], c, label)
            cmds += new
            owners += [tname] * len(new)
        if not cmds:
            continue
        out = batch(cmds)
        trims = []
        for cmd, who, r in zip(cmds, owners, out):
            if not r.get("ok"):
                problems.append("%s at beat %s: %s" % (who, c["start"],
                                                       str(r.get("error")).split("\n")[0]))
            elif cmd["cmd"] == "set_clip":
                end = (r.get("result") or {}).get("end")
                if end is not None and end > c["end"] + 1e-3:
                    trims.append({"cmd": "trim_clip", "args": {
                        "track": cmd["args"]["track"], "clip": {"at": c["start"]},
                        "end_beat": c["end"]}})
                elif end is not None and end < c["end"] - 1e-3:
                    problems.append("%s at beat %s ends at %.2f, the source at %.2f"
                                    % (who, c["start"], end, c["end"]))
        for r in batch(trims) if trims else []:
            if not r.get("ok"):
                problems.append("trim at beat %s: %s" % (c["start"], r.get("error")))
    if mute_source:
        batch([{"cmd": "set_clip", "args": {"track": track, "clip": {"at": c["start"]},
                                            "muted": True}} for _, c in ordered])
    return {"tracks": made, "problems": problems}


def clip_commands(track, path, c, label):
    """The bridge commands that re-create source clip `c` with another file."""
    args = {"track": track, "path": path, "beat": c["start"], "name": label,
            "warp": bool(c.get("warping"))}
    for k in ("pitch", "detune", "gain_db") + (("warp_mode",) if c.get("warping") else ()):
        if c.get(k) is not None:
            args[k] = c[k]
    at = {"at": c["start"]}
    cmds = [{"cmd": "create_audio_clip", "args": args}]
    if c.get("warping") and c.get("markers"):
        cmds.append({"cmd": "set_warp_markers", "args": {
            "track": track, "clip": at,
            "markers": [[m["beat"], m["sample_s"]] for m in c["markers"]]}})
    cmds.append({"cmd": "set_clip", "args": {
        "track": track, "clip": at, "looping": c["looping"], "loop_start": c["loop_start"],
        "loop_end": c["loop_end"], "start_marker": c["start_marker"],
        "end_marker": c["end_marker"]}})
    return cmds
