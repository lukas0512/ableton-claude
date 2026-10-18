"""listen(path): hear a track the way a producer would, and say it in words.

grid -> stems -> drums, bass, chords, arrangement, mix balance -> report + MIDI.
Results are cached per file (knowledge/ear/<id>/), so a reference is heard once.
"""
import json
import os
import re

import numpy as np

from .. import references as R
from ..storage import DATA_DIR, serialized_analysis
from . import EAR_VERSION, arrangement, bass, drums, grid, harmony, midi, perception, stems

CACHE_DIR = os.path.join(DATA_DIR, "knowledge", "ear")
GM = {"kick": 36, "clap": 39, "hats": 42, "open": 46}


def _dir(fid):
    d = os.path.join(CACHE_DIR, fid)
    os.makedirs(d, exist_ok=True)
    return d


@serialized_analysis
def listen(path, bpm_hint=None, use_cache=True, log=None):
    if bpm_hint is not None and (not np.isfinite(bpm_hint) or not 20 <= bpm_hint <= 400):
        raise ValueError("bpm_hint must be finite and between 20 and 400")
    fid = R._file_id(path)
    rep_path = os.path.join(CACHE_DIR, fid, "report.json")
    if use_cache and os.path.exists(rep_path):
        rep = json.load(open(rep_path))
        if rep.get("ear_version") == EAR_VERSION and rep.get("bpm_hint") == bpm_hint:
            return rep
    say = log or (lambda *a: None)
    x, sr = R.load_audio(path)
    say("grid")
    g = grid.analyze(x, sr, bpm_hint)
    say("stems")
    st = stems.separate(x, sr)
    say("drums")
    d = drums.transcribe(st["drums"], sr, g)
    say("bass")
    b = bass.transcribe(st["bass"], sr, g, kick_hits=d["kick"].get("hits"))
    say("harmony")
    h = harmony.analyze(st["other"], sr, g, b["notes"])
    if h["tonic_pc"] is not None:
        b.update(bass.stats(b["notes"], g, d["kick"].get("hits"), h["tonic_pc"]))
    say("arrangement")
    arr = arrangement.analyze(x, sr, st, g, d)
    mix = stem_mix(st, sr, g, arr)
    rep = {"ear_version": EAR_VERSION, "bpm_hint": bpm_hint, "file": os.path.basename(path), "id": fid,
           "duration_s": round(len(x) / sr, 1), "grid": g, "key": h["key"],
           "arrangement": {k: v for k, v in arr.items() if k != "stem_levels_db"},
           "drums": _drums_summary(d, arr, g), "bass": _bass_summary(b), "harmony": h, "mix": mix}
    rep["reliability"] = reliability(rep)
    say("section perception (bass character and break/drop contrast)")
    rep["perception"] = perception.analyze(x, sr, st, g, arr, b["notes"])
    rep["summary"] = summarize(rep)
    rep["summary"].extend(rep["reliability"]["warnings"])
    out = _dir(fid)
    midi.write(os.path.join(out, "heard.mid"), _midi_parts(d, b, h, g), g["bpm"])
    with open(rep_path, "w") as f:
        json.dump(R.analysis._plain(rep), f, indent=1)
    return json.load(open(rep_path))


# --------------------------------------------------------------------------- pieces

def _main_bars(arr):
    """Bars of the fullest sections (drop/groove) - where a track shows its main groove."""
    secs = [s for s in arr["sections"] if s["label"] in ("drop", "groove")]
    if not secs:
        secs = arr["sections"]
    if not secs:
        return []
    top = max(len(s["elements"]) for s in secs)
    return sorted({b for s in secs if len(s["elements"]) == top for b in range(s["start_bar"] - 1, s["end_bar"])})


def _drums_summary(d, arr, g):
    main = _main_bars(arr)
    out = {"main_patterns": drums.section_patterns(d, main)}
    for name, r in d.items():
        out[name] = {k: r.get(k) for k in ("hits_per_bar", "swing_pct", "late_ms_offbeat_vs_onbeat",
                                          "timing_spread_ms", "template")}
        out[name]["patterns"] = r.get("patterns", {})
    per_sec = []
    for s in arr["sections"]:
        bars = list(range(s["start_bar"] - 1, s["end_bar"]))
        per_sec.append({"section": "%s %d-%d" % (s["label"], s["start_bar"], s["end_bar"]),
                        "patterns": drums.section_patterns(d, bars)})
    out["by_section"] = per_sec
    return out


def _bass_summary(b):
    out = {k: v for k, v in b.items() if k != "notes"}
    out["notes"] = b["notes"]
    rh = bass.bar_rhythms(b["notes"])
    common = {}
    for r in rh.values():
        common[r] = common.get(r, 0) + 1
    out["common_rhythms"] = sorted(common.items(), key=lambda kv: -kv[1])[:5]
    return out


def stem_mix(st, sr, g, arr):
    """Level and width of each stem in the fullest sections, relative to the drums."""
    bars = _main_bars(arr)
    if not bars:
        return {}
    out = {}
    for k, s in st.items():
        mid_power, side_power, count, weighted_hz, magnitude = 0., 0., 0, 0., 0.
        for bar in bars:
            a = max(0, int(grid.bar_start(g, bar) * sr))
            b = min(len(s), int(grid.bar_start(g, bar + 1) * sr))
            seg = s[a:b]
            if not len(seg):
                continue
            mid = seg.mean(axis=1) if seg.ndim == 2 else seg
            side = (seg[:, 0] - seg[:, 1]) / 2 if seg.ndim == 2 and seg.shape[1] == 2 else np.zeros_like(mid)
            mid_power += float(np.dot(mid, mid))
            side_power += float(np.dot(side, side))
            count += len(mid)
            spec = np.abs(np.fft.rfft(mid * np.hanning(len(mid))))
            f = np.fft.rfftfreq(len(mid), 1.0 / sr)
            weighted_hz += float((f * spec).sum())
            magnitude += float(spec.sum())
        if not count:
            continue
        lv = 20 * np.log10(np.sqrt(mid_power / count) + 1e-9)
        wd = 10 * np.log10((side_power / count + 1e-12) / (mid_power / count + 1e-12))
        cen = weighted_hz / (magnitude + 1e-12)
        out[k] = {"level_db": round(float(lv), 1), "width_db": round(float(wd), 1), "centroid_hz": round(cen)}
    ref = out.get("drums", {}).get("level_db", 0.0)
    for k in out:
        out[k]["vs_drums_db"] = round(out[k]["level_db"] - ref, 1)
    return out


def reliability(rep):
    """Expose evidence limits; key_confidence is a correlation margin, not a probability."""
    warnings = ["Separated stems can contain bleed; inferred notes/chords need audition."]
    fit_ms = rep["grid"].get("fit_ms")
    if fit_ms is None or not np.isfinite(fit_ms) or fit_ms > 25:
        warnings.append("Beat-grid fit is uncertain: verify downbeat and half/double tempo before warping.")
    margin = rep["harmony"].get("key_confidence")
    key_usable = bool(rep.get("key")) and margin is not None and np.isfinite(margin) and margin >= 0.05
    if not key_usable:
        warnings.append("Key is ambiguous: verify against the isolated bass/hook before transposing or reharmonising.")
    return {"key_usable_for_transpose": bool(key_usable), "key_margin": margin,
            "key_margin_kind": "top-two key correlation difference; heuristic threshold 0.05",
            "grid_fit_ms": fit_ms, "warnings": warnings}


def _midi_parts(d, b, h, g):
    beat = g["period"]
    parts = []
    dr = []
    for name, r in d.items():
        for x in r.get("hits", []):
            pitch = GM["open"] if x.get("open") else GM[name]
            start = x["bar"] * 4 + x["step"] / 4.0 + x["offset_ms"] / 1000.0 / beat
            dr.append([pitch, round(max(0.0, start), 4), 0.1, int(np.clip(110 + x["rel_db"] * 3, 20, 127))])
    parts.append(("drums (heard)", 9, dr))
    parts.append(("bass (heard)", 1, bass.to_midi_notes(b["notes"], g)))
    ch = []
    for s in h["segments"]:
        if s["root"] is None:
            continue
        iv = harmony.QUALITIES[s["quality"]][0]
        base = 48 + (s["root"] - 48) % 12
        for i in iv:
            p = base + i
            while p > 72:
                p -= 12
            ch.append([p, s["start_beat"], s["beats"] * 0.98, 80])
    parts.append(("chords (heard)", 2, ch))
    return parts


# --------------------------------------------------------------------------- words

def _parse_chord(label):
    m = re.match(r"^([A-G][b#]?)(.*?)(?:/([A-G][b#]?))?$", label.split()[0])
    if not m:
        return None
    return harmony.NAMES.index(m.group(1)) if m.group(1) in harmony.NAMES else None, m.group(2), m.group(3)


def roman_cycle(cycle, tonic, mode):
    out = []
    for lab in cycle.split(" | "):
        p = _parse_chord(lab)
        if not p or p[0] is None or p[1] not in harmony.QUALITIES:
            out.append(lab)
            continue
        rn = harmony.roman(p[0], p[1], tonic, mode)
        out.append(rn + ("/" + p[2] if p[2] else ""))
    return " | ".join(out)


def form(sections):
    """Consecutive sections with the same name merged: [(label, start_bar, end_bar)]."""
    out = []
    for x in sections:
        if out and out[-1][0] == x["label"]:
            out[-1] = (x["label"], out[-1][1], x["end_bar"])
        else:
            out.append((x["label"], x["start_bar"], x["end_bar"]))
    return out


def summarize(rep):
    g, arr, dr, bs, h, mix = rep["grid"], rep["arrangement"], rep["drums"], rep["bass"], rep["harmony"], rep["mix"]
    s = []
    mins, secs = divmod(int(rep["duration_s"]), 60)
    s.append("%.1f BPM, %s, %d bars (%d:%02d). The beat grid fits the detected beats within %.0f ms."
             % (g["bpm"], rep["key"] or "key unclear", g["n_bars"], mins, secs, g["fit_ms"]))
    s.append("Form: " + ", ".join("%s %d-%d" % f for f in form(arr["sections"])) + ".")
    fb = arr["first_bar"]
    order = sorted((v, k) for k, v in fb.items() if v)
    s.append("Entries: " + ", ".join("%s at bar %d" % (k, v) for v, k in order) + ".")
    breaks = [x for x in arr["sections"] if x["label"] == "break"]
    for x in breaks:
        s.append("Break %d-%d keeps %s and drops to %.1f LUFS." % (x["start_bar"], x["end_bar"],
                 ", ".join(x["elements"]) or "almost nothing", x["lufs"]))
    mp = dr.get("main_patterns", {})
    words = []
    for name, label in (("kick", "kick"), ("clap", "clap/perc"), ("hats", "hats")):
        if name in mp:
            p = mp[name]["pattern"]
            desc = drums.describe_pattern(p)
            words.append("%s %s%s" % (label, p, (" (" + "; ".join(desc) + ")") if desc else ""))
    if words:
        s.append("Main groove, 16 steps per bar: " + " | ".join(words) + ".")
    hs = dr.get("hats", {})
    if hs.get("swing_pct"):
        s.append("Hats swing %.0f%% (off-beat 16ths %.0f ms behind the on-beats), timing spread %.0f ms."
                 % (hs["swing_pct"], hs.get("late_ms_offbeat_vs_onbeat") or 0, hs.get("timing_spread_ms") or 0))
    if bs.get("notes_per_bar"):
        deg = bs.get("degrees") or {}
        top = ", ".join("%s %d%%" % (k, round(v * 100)) for k, v in list(deg.items())[:3])
        rh = bs["common_rhythms"][0][0] if bs.get("common_rhythms") else ""
        s.append("Bass: register %s (range %s-%s), %s notes per bar, degrees %s; typical bar %s; "
                 "%d%% of notes off the beat%s; median length %.1f 16ths."
                 % (bs["register"], bs["range"][0], bs["range"][1], bs["notes_per_bar"], top or "-", rh,
                    round(100 * bs.get("offbeat_share", 0)),
                    (", %d%% together with the kick" % round(100 * bs["with_kick_share"])) if "with_kick_share" in bs else "",
                    bs.get("median_len_steps", 0)))
    if h.get("loops"):
        cyc, n = h["loops"][0]
        rn = roman_cycle(cyc, h["tonic_pc"], h["mode"]) if h.get("tonic_pc") is not None else cyc
        s.append("Harmony: most repeated cycle %s (%s), heard %d times; %.2f chord changes per 8 bars; qualities %s."
                 % (cyc, rn, n, h["changes_per_8_bars"], ", ".join(list(h["qualities"])[:4])))
    if mix:
        s.append("Balance in the fullest sections (vs drums): " + ", ".join(
            "%s %+.1f dB" % (k, v["vs_drums_db"]) for k, v in mix.items() if k != "drums") +
            "; width (side vs mid): " + ", ".join("%s %.0f dB" % (k, v["width_db"]) for k, v in mix.items()) + ".")
    return s
