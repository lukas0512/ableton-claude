"""Mix pass for the example track, driven by the reference fingerprint comparison.

The 25 deep house references are ~11 dB wider in the mids and ~19 dB wider up top than
the first mix, because every rhythm stem and the stab were bounced mono. A mono source
cannot be widened with a width control, so space comes from placement and ambience:

- the dialogue becomes spatial: call left, response right (stab/synth, bells/e-piano)
- hats and percussion spread across the stereo field
- a plate reverb return (low end kept out) for the pads, keys, stabs and vocals
- a swung 808 maracas layer: the references carry ~16 hat hits per bar and more swing
- warmth: -2 dB around 5.5 kHz, where the references are softer

Run with Live open on the project. Idempotent where Live allows (re-runs reuse the return
and the shaker track).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client  # noqa: E402
from ableton_claude.music import groove  # noqa: E402

C = client.call
RET = "Plate"            # Live shows returns as "<letter>-<name>", e.g. "B-Plate"
SHAKER = "Claude Shaker"
PANS = {"20 Stab Rhytm": -0.32, "16 Synth resp": 0.32,
        "Claude Call (Bells)": -0.38, "Claude Response (EP)": 0.35,
        "7 Open H. Main": -0.22, "11-ODH_123_Groove_Perc": 0.28,
        "10-Open Hat Shaker": -0.35, "9 Closed Hat": 0.12, "18 Guitar": 0.30,
        "32-oss_ip1": -0.25}
SENDS_B = {"20 Stab Rhytm": -13, "16 Synth resp": -13, "Claude Pad": -11,
           "Claude Call (Bells)": -11, "Claude Response (EP)": -15,
           "19 Rhodes Reverse": -14, "29 Vox Shot Cm": -12, "30-ny_vox124_yagota": -12,
           "31-SAM_FELDT": -12, "6 Clap": -20, "18 Guitar": -18}
SHAKER_RANGES = [(17, 65), (73, 97), (129, 177)]


def log(*a):
    print(*a, flush=True)


def main():
    def find_return():
        for i, r in enumerate(C("get_song")["returns"]):
            if r["name"].endswith(RET):
                return i, r
        return None, None

    idx, ret = find_return()
    if idx is None:
        C("create_return", {"name": RET})
        idx, ret = find_return()
    rv = "return:%d" % idx
    if "Reverb" not in ret["devices"]:
        C("load_device", {"track": rv, "path": "audio_effects/Reverb"})
    for param, kw in (("Dry/Wet", {"display": 100}), ("Decay Time", {"display": "2.2 s"}),
                      ("Predelay", {"display": "22 ms"}), ("In Lo Cut On", {"value": 1}),
                      ("In Hi Cut On", {"value": 1}), ("Input Freq", {"display": 1200}),
                      ("Stereo Image", {"display": 110})):
        r = C("set_param", dict(track=rv, device="Reverb", param=param, **kw))
        log("   reverb %-14s %s" % (param, r["display"]))
    C("set_track", {"track": rv, "volume_db": -6})
    send_b = idx

    log("pans:")
    for tr, p in PANS.items():
        log("   %-24s %+.2f" % (tr, C("set_track", {"track": tr, "pan": p})["pan"]))
    log("sends to %s:" % RET)
    for tr, db in SENDS_B.items():
        C("set_send", {"track": tr, "send": send_b, "db": db})
        log("   %-24s %d dB" % (tr, db))

    names = [t["name"] for t in C("get_song")["tracks"]]
    if SHAKER not in names:
        C("create_track", {"kind": "midi", "name": SHAKER})
        C("load_device", {"track": SHAKER, "path": "drums/Drum Hits/Shaker/808 Maracas.flac"})
    C("set_track", {"track": SHAKER, "volume_db": -20, "pan": 0.40})
    C("delete_clips_in_range", {"track": SHAKER, "start_bar": 1, "end_bar": 400})
    for k, (a, b) in enumerate(SHAKER_RANGES):
        notes = groove.steps_to_notes(groove.DEEP_HOUSE["shaker"], 60, bars=b - a, swing=58.0,
                                      humanize=0.004, seed=20 + k, vel_scale=0.85,
                                      length=0.08)
        C("create_midi_clip", {"track": SHAKER, "bar": a, "length": (b - a) * 4,
                               "notes": notes, "name": "maracas 58% swing"})
    log("shaker: %s" % SHAKER_RANGES)

    for param, kw in (("4 Filter On A", {"value": 1}), ("4 Filter Type A", {"item": "Bell"}),
                      ("4 Frequency A", {"display": 5500}), ("4 Gain A", {"display": -2.0}),
                      ("4 Q A", {"display": 1.0})):
        C("set_param", dict(track="master", device="EQ Eight", param=param, **kw))
    log("master EQ: bell -2 dB at 5.5 kHz")
    # second validation: mids still narrow, maracas too noisy, panning cost ~0.4 LU
    C("set_param", {"track": "master", "device": "Pro-L 2", "param": "Gain", "display": 11.3})


if __name__ == "__main__":
    main()
