"""Timbre pass for the example track, from the element timbre comparison (timbre.py).

Against the 25 deep house references (middle half in brackets), the first mix had:
- top end too bright, too short and too loud: hits at 8.5 kHz [5.8-7.3], 24 ms long
  [44-84], 6-16 kHz at -16.9 dB of the bar [-20.7..-17.4]. The worst source was the 808
  maracas added in the first mix pass (10.2 kHz, 2 ms: the extremes of the whole Core
  Library), then the closed hat (a 4 ms tick) and the open-hat shaker (24 ms, 8.3 kHz).
  -> the maracas become the library one-shot nearest the references' hat profile
     (timbre.rank_samples over 500 shakers/hats/tambourines: Tamb Dry Tap, 6.1 kHz,
     60 ms), and it keeps playing, softly, through the breakdown; the closed hat gets a
     small room and both hats come down.
- clap loud and dry: backbeat +18.3 dB [-0.1..+13], tail 32 ms [34-240]
  -> -3 dB and a short room.
- bass nearly a sine: 2nd+3rd harmonics -15.9 dB under the fundamental [-9.9..-5.3],
  so it has weight but no body on small speakers -> Dynamic Tube with bias (the bias is
  what makes even harmonics; a symmetric clipper only adds odd ones).
- breakdown dark, muddy and wide: centroid 392 Hz [596-945], 150-500 Hz 22.9 dB over
  2-6 kHz [4.6-9.7], side -4.3 dB [-13.5..-5.4] -> the pad's filter opens from 1.5 kHz
  instead of 600 Hz, -4 dB at 300 Hz, width 65 %.

    timbre_pass.py SNAPSHOT.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
sys.path.insert(0, os.path.dirname(__file__))
from ableton_claude import client  # noqa: E402
from ableton_claude.music import groove  # noqa: E402

C = client.call
SHAKER = "Claude Shaker"
SHAKER_SAMPLE = "drums/Drum Hits/Tambourine/Tamb Dry Tap.wav"
SHAKER_RANGES = [(17, 65, 0.85), (73, 97, 0.85), (97, 113, 0.5), (113, 129, 0.7),
                 (129, 177, 0.85)]
LEVELS = {SHAKER: -21.0, "9 Closed Hat": -13.0, "10-Open Hat Shaker": -14.1, "6 Clap": -13.0}
ROOMS = {  # track: (decay, predelay, dry/wet %)
    "9 Closed Hat": ("0.5 s", "3 ms", 18),
    "6 Clap": ("0.9 s", "10 ms", 22),
}
TUBE = [("Tube Type", {"item": "B"}), ("Drive", {"display": 6.0}), ("Bias", {"display": 40}),
        ("Tone", {"display": -0.1}), ("Output", {"display": -3.0}), ("Dry/Wet", {"display": 100})]
PAD_FILTER = {"Breakdown -> Build (IV-V)": (97, [[0, 1500], [96, 4000], [128, 9000]]),
              "Break bed Gm9 (foreshadow)": (65, [[0, 1200], [24, 3500], [32, 2000]])}


def log(*a):
    print(*a, flush=True)


def device_names(track):
    return [d["name"] for d in C("get_track", {"track": track, "clips": False})["devices"]]


def ensure(track, path, name):
    if name not in device_names(track):
        C("load_device", {"track": track, "path": path})
    return name


def main(snapshot_path):
    snap = {"levels": {}, "devices": {}}
    for tr in list(LEVELS) + ["10 Bass", "Claude Pad"]:
        t = C("get_track", {"track": tr, "clips": False})
        snap["levels"][tr] = t["vol_db"]
        snap["devices"][tr] = [d["name"] for d in t["devices"]]
    pad = C("get_track", {"track": "Claude Pad"})
    snap["pad_clips"] = {c["name"]: {"start": c["start"],
                                     "notes": C("get_notes", {"track": "Claude Pad",
                                                              "clip": {"at": c["start"]}})}
                         for c in pad["clips"]}
    json.dump(snap, open(snapshot_path, "w"), indent=1, default=str)
    log("snapshot:", snapshot_path)

    # top end: the maracas become a tambourine that sits in the references' hat profile
    r = C("load_device", {"track": SHAKER, "path": SHAKER_SAMPLE})
    log("shaker sample: %s" % r["devices"])
    if len(r["devices"]) > 1:            # a second instrument was added: drop the old one
        C("delete_device", {"track": SHAKER, "device": r["devices"][0]})
    C("delete_clips_in_range", {"track": SHAKER, "start_bar": 1, "end_bar": 400})
    for k, (a, b, vel) in enumerate(SHAKER_RANGES):
        notes = groove.steps_to_notes(groove.DEEP_HOUSE["shaker"], 60, bars=b - a, swing=58.0,
                                      humanize=0.004, seed=40 + k, vel_scale=vel, length=0.12)
        C("create_midi_clip", {"track": SHAKER, "bar": a, "length": (b - a) * 4,
                               "notes": notes, "name": "tambourine 58%"})
    log("shaker clips: %s" % [(a, b) for a, b, _ in SHAKER_RANGES])

    for tr, db in LEVELS.items():
        C("set_track", {"track": tr, "volume_db": db})
        log("level %-20s %5.1f -> %5.1f dB" % (tr, snap["levels"][tr], db))
    for tr, (decay, pre, wet) in ROOMS.items():
        ensure(tr, "audio_effects/Reverb", "Reverb")
        for p, kw in (("Decay Time", {"display": decay}), ("Predelay", {"display": pre}),
                      ("Dry/Wet", {"display": wet})):
            C("set_param", dict(track=tr, device="Reverb", param=p, **kw))
        log("room on %-16s decay %s, predelay %s, %d %% wet" % (tr, decay, pre, wet))

    ensure("10 Bass", "audio_effects/Dynamic Tube", "Dynamic Tube")
    for p, kw in TUBE:
        C("set_param", dict(track="10 Bass", device="Dynamic Tube", param=p, **kw))
    log("bass: Dynamic Tube %s" % ", ".join("%s %s" % (p, list(kw.values())[0]) for p, kw in TUBE))

    # breakdown pad: brighter filter path, less 300 Hz, narrower
    for name, (bar, points) in PAD_FILTER.items():
        clip = snap["pad_clips"].get(name)
        if not clip:
            log("   pad clip %r not found, skipped" % name)
            continue
        length = {97: 128, 65: 32}[bar]
        C("delete_clips_in_range", {"track": "Claude Pad", "start_bar": bar, "end_bar": bar + 1})
        C("create_midi_clip", {"track": "Claude Pad", "bar": bar, "length": length,
                               "notes": clip["notes"], "name": name,
                               "envelopes": [{"device": "Auto Filter", "param": "Frequency",
                                              "unit": "display", "points": points}]})
        log("pad %-28s filter %s" % (name, points))
    ensure("Claude Pad", "audio_effects/EQ Eight", "EQ Eight")
    for p, kw in (("3 Filter On A", {"value": 1}), ("3 Filter Type A", {"item": "Bell"}),
                  ("3 Frequency A", {"display": 300}), ("3 Gain A", {"display": -4.0}),
                  ("3 Q A", {"display": 0.7})):
        C("set_param", dict(track="Claude Pad", device="EQ Eight", param=p, **kw))
    ensure("Claude Pad", "audio_effects/Utility", "Utility")
    util = C("get_device", {"track": "Claude Pad", "device": "Utility"})
    names = [p["name"] for p in util["params"]] if isinstance(util["params"], list) else list(util["params"])
    width = next(n for n in names if "Width" in n)
    C("set_param", {"track": "Claude Pad", "device": "Utility", "param": width, "display": 65})
    log("pad: -4 dB @ 300 Hz, %s 65 %%" % width)
    log("devices now: %s" % {tr: device_names(tr) for tr in ("10 Bass", "Claude Pad", "6 Clap",
                                                             "9 Closed Hat", SHAKER)})


if __name__ == "__main__":
    main(sys.argv[1])
