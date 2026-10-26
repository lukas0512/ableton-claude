"""Change journal: every change sent to Live, with what it replaced, so a change can be
reverted exactly (Live has no save API, and its undo groups API calls its own way).

A record is {"id", "time", "session", "cmd", "args", "before", "result"}.
`inverse(record)` gives the bridge commands that put the old state back, or None when the
change is not reversible here (deletes, range edits): those need Live's undo or the
user's saved copy. A revert appends {"cmd": "_reverted", "session", "ids"}, so the file
also says which kinds of change this user keeps and which they undo (`taste`).
"""
import json
import os
import time
from .storage import DATA_DIR

PATH = os.environ.get("ABLETON_CLAUDE_JOURNAL",
                      os.path.join(DATA_DIR, "journal.jsonl"))

READS = {"ping", "get_song", "get_track", "get_device", "get_notes", "browse", "grooves",
         "warp_markers", "track_routing", "device_inputs", "record_status", "api_probe",
         "reload", "batch"}

_records = []
SESSION = time.strftime("%Y%m%d-%H%M%S")    # ids restart every server start


def _next_id():
    return (_records[-1]["id"] + 1) if _records else 1


def _write(rec):
    try:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    except OSError:
        pass  # the in-memory journal still works


def record(cmd, args, result, before=None):
    """Journal one successful change. Reads are not journaled."""
    if cmd in READS:
        return None
    if isinstance(result, dict) and "before" in result:
        before = result["before"]
    rec = {"id": _next_id(), "time": time.strftime("%H:%M:%S"), "session": SESSION,
           "cmd": cmd, "args": args, "before": before, "result": result}
    _records.append(rec)
    _write(rec)
    return rec["id"]


def recent(last=20):
    return [{"id": r["id"], "time": r["time"], "cmd": r["cmd"], "args": r["args"],
             "before": r["before"], "revertible": inverse(r) is not None,
             "reverted": r.get("reverted", False)}
            for r in _records[-last:]]


def find(ids=None, last=None):
    """Records to revert, newest first: by id, or the last N not yet reverted."""
    live = [r for r in _records if not r.get("reverted")]
    if ids:
        picked = [r for r in live if r["id"] in set(ids)]
    else:
        picked = live[-(last or 1):]
    return sorted(picked, key=lambda r: r["id"], reverse=True)


def mark_reverted(rec):
    rec["reverted"] = True
    _write({"cmd": "_reverted", "session": rec.get("session", SESSION), "ids": [rec["id"]],
            "time": time.strftime("%H:%M:%S")})


def family(rec):
    """The kind of move a change was, as a producer would name it: "level",
    "EQ Eight: 4 Gain A up", "load Glue Compressor", "notes"... None for plumbing."""
    cmd, a = rec.get("cmd"), rec.get("args") or {}
    b, res = rec.get("before") or {}, rec.get("result") or {}
    if cmd == "set_track":
        for k, name in (("volume_db", "level"), ("pan", "pan"), ("mute", "mute")):
            if a.get(k) is not None:
                return name
        return None
    if cmd == "set_param":
        try:
            way = " up" if float(res["value"]) > float(b["value"]) else " down"
        except (KeyError, TypeError, ValueError):
            way = ""
        dev = str(a.get("device", "")).split("#")[0]
        return "%s: %s%s" % (dev, a.get("param"), way)
    if cmd == "set_clip":
        if a.get("gain_db") is not None:
            return "clip gain"
        if a.get("muted") is not None:
            return "clip mute"
        if a.get("detune") is not None or a.get("pitch") is not None:
            return "tuning"
        return "clip edit"
    if cmd == "load_device":
        q = a.get("query") or os.path.basename(str(a.get("path", "")))
        return "load %s" % q
    if cmd == "set_device_on":
        return "%s %s" % (str(a.get("device", "")).split("#")[0], "on" if a.get("on") else "off")
    return {"set_send": "send", "create_midi_clip": "notes", "add_notes": "notes",
            "create_audio_clip": "audio clip", "set_tempo": "tempo",
            "apply_groove": "groove", "set_groove": "groove"}.get(cmd)


def taste(path=None, min_changes=3):
    """What this user keeps and undoes, from the whole journal file: per move family,
    {family, changes, reverted, kept_pct}, most-undone first; families with fewer than
    `min_changes` changes are left out (too few to mean anything)."""
    path = path or PATH
    made, undone = {}, set()
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("cmd") == "_reverted":
                    undone.update((r.get("session"), i) for i in r.get("ids", []))
                elif r.get("session") and inverse(r) is not None:
                    fam = family(r)
                    if fam:
                        made[(r["session"], r["id"])] = fam
    except OSError:
        return []
    counts = {}
    for key, fam in made.items():
        c = counts.setdefault(fam, [0, 0])
        c[0] += 1
        c[1] += key in undone
    out = [{"family": fam, "changes": n, "reverted": r,
            "kept_pct": round(100.0 * (n - r) / n)}
           for fam, (n, r) in counts.items() if n >= min_changes]
    return sorted(out, key=lambda d: (d["kept_pct"], -d["changes"]))


def inverse(rec):
    """Bridge commands that undo `rec`, or None."""
    cmd, a, b, res = rec["cmd"], rec["args"], rec.get("before") or {}, rec.get("result") or {}
    track = a.get("track")
    if cmd == "set_param":
        return [("set_param", {"track": track, "device": a["device"], "param": a["param"],
                               "value": b["value"]})] if "value" in b else None
    if cmd == "set_send":
        return [("set_raw", {"track": track, "target": "send:%d" % int(a["send"]),
                             "value": b["raw"]})] if "raw" in b else None
    if cmd == "set_device_on":
        return [("set_device_on", {"track": track, "device": a["device"],
                                   "on": b["on"]})] if "on" in b else None
    if cmd == "set_track":
        # the change may have renamed the track: address it by its current name
        addr = res.get("name", track) if "name" in b else track
        out = []
        if "volume_raw" in b:
            out.append(("set_raw", {"track": addr, "target": "volume", "value": b["volume_raw"]}))
        if "pan_raw" in b:
            out.append(("set_raw", {"track": addr, "target": "pan", "value": b["pan_raw"]}))
        rest = {k: v for k, v in b.items() if k in ("mute", "solo", "arm", "monitoring",
                                                    "color_index", "name") and v is not None}
        if rest:
            out.append(("set_track", dict(rest, track=addr)))
        return out or None
    if cmd == "set_clip":
        if "start" not in res:
            return None
        clip = {"at": res["start"]}
        out = []
        rest = {k: v for k, v in b.items() if k != "gain_raw"}
        if rest:
            out.append(("set_clip", dict(rest, track=track, clip=clip)))
        if "gain_raw" in b:
            out.append(("set_raw", {"track": track, "target": "clip_gain", "device": clip,
                                    "value": b["gain_raw"]}))
        return out or None
    if cmd == "add_notes" and a.get("replace") and isinstance(b, dict) and "notes" in b:
        return [("add_notes", {"track": track, "clip": a["clip"], "notes": b["notes"],
                               "replace": True})]
    if cmd == "create_track" and isinstance(res, dict) and res.get("name"):
        return [("delete_track", {"track": res["name"]})]
    if cmd in ("create_midi_clip", "create_audio_clip") and isinstance(res, dict) \
            and "start" in res:
        return [("delete_clip", {"track": track, "clip": {"at": res["start"]}})]
    if cmd == "load_device" and isinstance(res, dict) and res.get("added", 0) > 0:
        n = len(res.get("devices", []))
        return [("delete_device", {"track": track, "device": i})
                for i in range(n - 1, n - 1 - res["added"], -1)]
    if cmd == "set_tempo" and isinstance(b, dict) and "bpm" in b:
        return [("set_tempo", {"bpm": b["bpm"]})]
    return None
