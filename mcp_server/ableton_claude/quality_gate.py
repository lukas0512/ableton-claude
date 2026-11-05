"""Static checks of the open set before a version goes to the producer.

Each check is a mistake that reached him once (see briefs/taste.md and lessons.md):
render or measurement tracks left playing, clip automation overridden by a fader move,
sources driven hot into their effects, notes on empty Drum Rack pads, drum parts in
different swing pockets, voices in different spaces, an unsafe master, a form without
two drops. Nothing here renders or changes the set; `call` is the bridge's client.call.
"""
import statistics

LEFTOVER_PREFIXES = ("lvl", "spec", "cal", "chk", "gs", "bb", "vx", "pol", "claude render")
HOT_SIMPLER_DB = -6.0
STEEP_VEL_SENS = 0.6       # Simpler Vol<Vel above this ...
WIDE_VEL_RANGE = 40        # ... with a velocity spread above this
POCKET_TOLERANCE_MS = 3.0
SEND_TOLERANCE_DB = 3.0


def _finding(severity, check, track, detail, fix):
    return {"severity": severity, "check": check, "track": track, "detail": detail, "fix": fix}


def _leftovers(tracks, details):
    out = []
    for t in tracks:
        name = t["name"].strip().lower()
        files = [c.get("file") or "" for c in details[t["i"]].get("clips", [])]
        # a render track holds one or two recorded takes and nothing else; a part resampled
        # into Samples/Recorded and then arranged (many clips) is music, not a leftover
        recorded = (0 < len(files) <= 2
                    and all("/Samples/Recorded/" in f for f in files))
        if name.startswith(LEFTOVER_PREFIXES) or (recorded and not name.startswith(("ref", "archive"))):
            out.append(_finding("error", "leftover track", t["name"],
                                "a render or measurement track is still in the set"
                                + ("" if t.get("mute") else " and plays"),
                                "delete it (names lose trailing spaces in Live: match stripped)"))
    return out


def _hot_simplers(tracks, details, call):
    out = []
    for t in tracks:
        for d in details[t["i"]].get("devices", []):
            if d.get("class") != "OriginalSimpler":
                continue
            dev = call("get_device", {"track": t["i"], "device": d["i"]})
            vol = next((p["value"] for p in dev["params"] if p["name"] == "Volume"), None)
            if vol is not None and vol > HOT_SIMPLER_DB:
                out.append(_finding("warn", "gain staging", t["name"],
                                    f"Simpler volume {vol:+.1f} dB drives the chain hot",
                                    "Simpler at -12 dB, raise the fader instead"))
    return out


def _steep_velocity(tracks, details, call):
    """A Simpler at a steep Vol<Vel playing a wide velocity range: neighbouring notes jump tens of
    dB and top velocities add ~20 dB inside the channel (his "não existe", "clipando")."""
    out = []
    for t in tracks:
        for d in details[t["i"]].get("devices", []):
            if d.get("class") != "OriginalSimpler":
                continue
            dev = call("get_device", {"track": t["i"], "device": d["i"]})
            sens = next((p.get("value") for p in dev["params"] if p["name"] == "Vol < Vel"), None)
            if sens is None or sens <= STEEP_VEL_SENS:
                continue
            vels = [n[3] for n in call_notes(t, details, call)]
            if vels and max(vels) - min(vels) > WIDE_VEL_RANGE:
                out.append(_finding("warn", "gain staging", t["name"],
                                    f"Vol<Vel {sens:.0%} with velocities {min(vels):.0f}-{max(vels):.0f}: "
                                    "hits jump tens of dB and the top ones overload the channel",
                                    "Vol<Vel 35 %, a small accent under 100 (the kit's hat is 78-105)"))
    return out


def call_notes(t, details, call):
    """Each note with its velocity, every MIDI clip of the track."""
    out = []
    for c in details[t["i"]].get("clips", []):
        if c.get("type") == "midi":
            out += call("get_notes", {"track": t["i"], "clip": {"at": c["start"]}})
    return out


def _midi_notes(t, details, call):
    notes = []
    for c in details[t["i"]].get("clips", []):
        if c.get("type") == "midi":
            for n in call("get_notes", {"track": t["i"], "clip": {"at": c["start"]}}):
                notes.append((n[0], c["start"] + n[1]))
    return notes


def _empty_pads(tracks, details, notes_of, call):
    out = []
    for t in tracks:
        if t.get("kind") != "midi":
            continue
        pads = call("drum_pads", {"track": t["i"]})
        if not pads.get("device"):
            continue
        used = {p for p, _ in notes_of(t)}
        silent = sorted(used - set(pads["pads"]))
        if silent:
            out.append(_finding("error", "empty drum pad", t["name"],
                                f"notes {silent} hit pads without a sound in {pads['device']}",
                                "move the notes to the part's pad pitch"))
    return out


def off16_offset_ms(times, tempo):
    """Median offset (ms) of the notes nearest an off-beat 16th from that 16th."""
    beat_ms = 60000.0 / tempo
    devs = [(t - round(t * 4) / 4) * beat_ms for t in times if round(t * 4) % 2 == 1]
    return statistics.median(devs) if len(devs) >= 8 else None


def _pocket(tracks, notes_of, tempo):
    offs = {}
    for t in tracks:
        if t.get("kind") != "midi" or t.get("mute"):
            continue
        o = off16_offset_ms([s for _, s in notes_of(t)], tempo)
        if o is not None:
            offs[t["name"]] = o
    if len(offs) < 3:
        return []
    ref = statistics.median(offs.values())
    return [_finding("warn", "swing pocket", n,
                     f"off-16ths at {o:+.1f} ms against the set's {ref:+.1f} ms",
                     "one swing for every 16th part")
            for n, o in offs.items() if abs(o - ref) > POCKET_TOLERANCE_MS]


def _voices(tracks, details):
    vox = [t for t in tracks if "vox" in t["name"].lower() and "bus" not in t["name"].lower()
           and not t.get("mute")]
    out = []
    if len(vox) < 2:
        return out
    sends = {t["name"]: details[t["i"]].get("sends_db", []) for t in vox}
    names = list(sends)
    for n in names[1:]:
        for k, (a, b) in enumerate(zip(sends[names[0]], sends[n])):
            fa, fb = max(a, -70.0), max(b, -70.0)
            if abs(fa - fb) > SEND_TOLERANCE_DB:
                out.append(_finding("warn", "voices in different spaces", n,
                                    f"send {k}: {fb:.0f} dB against {names[0]} {fa:.0f} dB",
                                    "same bus, same plate, same sends for every voice"))
    return out


def _master(song, call):
    devs = song.get("master", {}).get("devices", [])
    if "Limiter" not in devs:
        return [_finding("warn", "master", "master", "no limiter on the master",
                         "Limiter, True Peak, ceiling -1 dBTP")]
    # the last limiter feeds the output: a soft-clip stage before a True Peak one is fine
    last = devs.count("Limiter") - 1
    lim = call("get_device", {"track": "master",
                              "device": f"Limiter#{last}" if last else "Limiter"})
    p = {x["name"]: x["display"] for x in lim["params"]}
    out = []
    if p.get("Mode") != "True Peak":
        out.append(_finding("warn", "master", "master", f"limiter mode {p.get('Mode')}",
                            "True Peak mode"))
    try:
        ceiling = float(p.get("Ceiling", "0").split()[0])
    except ValueError:
        ceiling = 0.0
    if ceiling > -0.9:
        out.append(_finding("warn", "master", "master", f"ceiling {ceiling} dB",
                            "-1.0 dB for lossy playback"))
    return out


def _form(song):
    drops = [c["name"] for c in song.get("cues", []) if "drop" in c["name"].lower()]
    if len(drops) < 2:
        return [_finding("info", "club form", "-",
                         f"{len(drops)} drop locator(s); his club form has two drops",
                         "intro A/B, groove, break 1 + build, drop 1, main break + build, "
                         "drop 2, outro A/B (briefs/taste.md)")]
    return []


def _looped_phrases(tracks, call):
    """A vocal phrase clip left looping and longer than its loop plays the phrase twice
    ("o vocal está repetindo 2x, aí perde o hook")."""
    out = []
    for t in tracks:
        if t.get("kind") != "audio" or not any(k in t["name"].upper() for k in ("VOX", "VOCAL")):
            continue
        for c in call("get_track", {"track": t["i"], "markers": True}).get("clips", []):
            if c.get("muted") or not c.get("looping"):
                continue
            span = (c.get("loop_end") or 0) - (c.get("loop_start") or 0)
            if span > 0 and c["end"] - c["start"] > span + 0.25:
                out.append(_finding("error", "phrase repeats", t["name"],
                                    f"'{c.get('name', '')}' at bar {c['start'] / 4 + 1:g} loops "
                                    f"{span:.2f} beats over {c['end'] - c['start']:.2f}",
                                    "turn looping off or trim the clip to its phrase"))
    return out


def _state(tracks, call):
    """Leftover debugging state that silently ruins a render: a soloed track (v17 of Murder
    rendered the riff alone), a device switched off on the master or a bus, and Arrangement
    automation that came from edits made while a render recorded (a master device switched
    on/off, a time parameter of many seconds)."""
    out = [_finding("error", "soloed track", t["name"], "a track is soloed: the render plays it alone",
                    "set_track(solo=False)") for t in tracks if t.get("solo")]
    buses = ["master"] + [t["name"] for t in tracks
                          if t["name"].isupper() and not t.get("mute") and
                          any(k in t["name"] for k in ("BUS", "DRUMS", "LOW END"))]
    for b in buses:
        try:
            devs = call("get_track", {"track": b}).get("devices", [])
        except Exception:
            continue
        out += [_finding("warn", "device off", b, "%s is switched off" % d["name"],
                         "switch it on, or delete it if it is not meant to play")
                for d in devs if not d.get("on", True)]
    try:
        autos = call("automated_params")
    except Exception:
        autos = []
    for a in autos:
        junk = (a["track"] == "master" and a["param"] == "Device On") or \
               (a["param"] in ("Decay Time", "Release", "Attack") and a["now"].endswith(" s")
                and float(a["now"].split()[0]) >= 5)
        if junk and a["state"] == "playing":
            out.append(_finding("error", "recorded automation", a["track"],
                                "%s %s is automated (%s): likely written while a render recorded"
                                % (a["device"], a["param"], a["now"]),
                                "override it (set the value while playing, not recording) and ask "
                                "the producer to delete the lane"))
    return out


def run(call):
    song = call("get_song")
    tracks = [t for t in song["tracks"]]
    details = {t["i"]: call("get_track", {"track": t["i"]}) for t in tracks}
    cache = {}

    def notes_of(t):
        if t["i"] not in cache:
            cache[t["i"]] = _midi_notes(t, details, call)
        return cache[t["i"]]

    findings = []
    findings += _leftovers(tracks, details)
    if call("transport_state").get("re_enable_automation_enabled"):
        findings.append(_finding("warn", "automation overridden", "-",
                                 "Re-Enable Automation is lit: some automation is overridden",
                                 "check automated_params: re-enable only if the overridden lanes are "
                                 "wanted (junk recorded during a render must stay overridden)"))
    findings += _state(tracks, call)
    findings += _hot_simplers(tracks, details, call)
    findings += _steep_velocity(tracks, details, call)
    findings += _empty_pads(tracks, details, notes_of, call)
    findings += _pocket(tracks, notes_of, song.get("tempo", 120.0))
    findings += _voices(tracks, details)
    findings += _looped_phrases(tracks, call)
    findings += _master(song, call)
    findings += _form(song)
    order = {"error": 0, "warn": 1, "info": 2}
    findings.sort(key=lambda f: order[f["severity"]])
    return {"passed": not any(f["severity"] == "error" for f in findings), "findings": findings}
