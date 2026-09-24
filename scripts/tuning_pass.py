"""Tuning after the release and timbre passes, from short test renders (bars 97-145)
measured against the 25 deep house references. Idempotent: run it on the recovered set
and it lands on the final values.

What each round found:
- bass body: Dynamic Tube (drive 6, bias 40 %) only compressed the bass (-6 dB
  fundamental, no harmonics). Roar's Half/Full Wave Rectifier made the right harmonics
  soloed but added infrasonic thumps (+8 dB at 5-20 Hz) that made the limiter pump the
  kick. Kept: Roar Tube Preamp in parallel (-11 dB 2nd+3rd, references -9.9..-5.3) with
  a 30 Hz high-pass after it, fader back so kick-over-bass sits at the references'
  median (6.5 dB).
- the tambourine's low end is its attack: high-passing it at 3 kHz left the jingle,
  which peaks tens of ms later and read as a dragging 79 % swing.
- the clap needed room it can be heard in (45 % wet, 1.2 s) to reach the references'
  tail; the dry clap fell 19 dB in 20 ms.
- the breakdown pad (Analog Soft Pad) has almost nothing at 2-6 kHz, 57 dB under its
  low-mids; ten library pads were auditioned on the same chords and Celestial Pad came
  closest to the references' breakdown timbre (691 Hz centroid, 13.5 dB warmth).
- the build dipped then ramped into bar 128: one more call/response pair over the held
  C7sus4 keeps the dialogue going, and the transition effects came down again.
- swing: measured against the hats' own on-beats (the kick-derived grid reads ~29 ms
  late), the references sit at 62.5 % (55-76); the hats and the tambourine go to 62 %,
  the swing of the song's own synth loop.
- a synthesized sub pedal (Operator sine) from bar 105: G1 under the breakdown, D2 under
  the dominant for the last 4 bars of the build, out on the last beat. It keeps some low
  end in the break (the references' bass drops 8.5 dB there, ours dropped 35) and makes
  the build a pedal point that resolves on the drop.

    tuning_pass.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
sys.path.insert(0, os.path.dirname(__file__))
from ableton_claude import client  # noqa: E402
from ableton_claude.music import groove, harmony, melody  # noqa: E402
import build_deep_house as B  # noqa: E402
import timbre_pass as TP  # noqa: E402

C = client.call
GROOVE = ("Swing Logic 16ths 62", {"timing": 100, "random": 20})
LEVELS = {"10 Bass": -10.5, "6 Clap": -16.0, "9 Closed Hat": -10.5, "10-Open Hat Shaker": -12.0,
          "Claude Shaker": -19.0, "rise": -23.0, "rise2": -23.0, "26 Uplifter": -15.0,
          "25 Reverse Crash": -14.0, "3 TOM": -22.0, "Claude Build Clap": -23.0,
          "Claude Pad": -7.0, "Claude Call (Bells)": -12.5, "Claude Response (EP)": -10.5,
          "30-ny_vox124_yagota": -15.5, "Claude Sub": -15.0}
PANS = {"10-Open Hat Shaker": -0.35}
PLATE_SENDS = {"20 Stab Rhytm": -10.0, "16 Synth resp": -10.0}
DEVICES = {  # track: [(device path, device name, [(param, kwargs), ...]), ...]
    "10 Bass": [
        ("audio_effects/Roar", "Roar", [
            ("Shaper 1 Type", {"item": "Tube Preamp"}), ("Shaper 1 Amt", {"display": 85}),
            ("Shaper 1 Bias", {"display": 0.35}), ("Drive", {"display": 6.0}),
            ("Flt 1 On", {"value": 1}), ("Flt 1 Type", {"item": "LP"}), ("Flt 1 Freq", {"display": 1500}),
            ("Comp Amt", {"display": 0}), ("Dry/Wet", {"display": 90}), ("Output", {"display": -6.0})]),
        ("audio_effects/EQ Eight", "EQ Eight", [
            ("1 Filter On A", {"value": 1}), ("1 Filter Type A", {"item": "High Pass 48dB"}),
            ("1 Frequency A", {"display": 30}), ("2 Filter On A", {"value": 0}),
            ("3 Filter On A", {"value": 0}), ("4 Filter On A", {"value": 0})])],
    "6 Clap": [("audio_effects/Reverb", "Reverb", [
        ("Decay Time", {"display": "1.2 s"}), ("Predelay", {"display": "5 ms"}), ("Dry/Wet", {"display": 45})])],
    "9 Closed Hat": [
        ("audio_effects/Reverb", "Reverb", [
            ("Decay Time", {"display": "0.5 s"}), ("Predelay", {"display": "3 ms"}), ("Dry/Wet", {"display": 25})]),
        ("audio_effects/EQ Eight", "EQ Eight", [
            ("7 Filter On A", {"value": 1}), ("7 Filter Type A", {"item": "High Shelf"}),
            ("7 Frequency A", {"display": 9000}), ("7 Gain A", {"display": -6.0}), ("7 Q A", {"display": 0.7})])],
    "10-Open Hat Shaker": [("audio_effects/EQ Eight", "EQ Eight", [
        ("7 Filter On A", {"value": 1}), ("7 Filter Type A", {"item": "High Shelf"}),
        ("7 Frequency A", {"display": 9000}), ("7 Gain A", {"display": -4.0}), ("7 Q A", {"display": 0.7})])],
    "Claude Pad": [
        ("sounds/Pad/Celestial Pad.adg", "Celestial Pad", []),
        ("audio_effects/EQ Eight", "EQ Eight", [
            ("3 Filter On A", {"value": 1}), ("3 Filter Type A", {"item": "Bell"}),
            ("3 Frequency A", {"display": 300}), ("3 Gain A", {"display": -4.0}), ("3 Q A", {"display": 0.7}),
            ("7 Filter On A", {"value": 1}), ("7 Filter Type A", {"item": "High Shelf"}),
            ("7 Frequency A", {"display": 2500}), ("7 Gain A", {"display": 4.0}), ("7 Q A", {"display": 0.7})]),
        ("audio_effects/Utility", "Utility", [("Stereo Width", {"display": 45})])],
}
PAD_FILTER = {"Breakdown -> Build (IV-V)": (97, 128, [[0, 3000], [96, 7000], [128, 14000]]),
              "Break bed Gm9 (foreshadow)": (65, 32, [[0, 2500], [24, 6000], [32, 4000]])}
SHAKER_SWING = 62.0
SHAKER_VEL = {(97, 113): 0.65}
SUB = {"bar": 105, "length": 96, "name": "sub pedal G -> D",
       "notes": [[31, 0.0, 79.5, 100],      # G1 under the breakdown and the build
                 [38, 79.5, 15.5, 100]]}    # D2 from the "and" of 4 in bar 124, gone on the last beat


def log(*a):
    print(*a, flush=True)


def devices(track):
    return [d["name"] for d in C("get_track", {"track": track, "clips": False})["devices"]]


def main():
    C("set_groove", dict(name=GROOVE[0], **GROOVE[1]))
    for tr, chain in DEVICES.items():
        for path, name, params in chain:
            if name not in devices(tr):
                C("load_device", {"track": tr, "path": path})
            for p, kw in params:
                C("set_param", dict(track=tr, device=name, param=p, **kw))
        log("%-20s %s" % (tr, devices(tr)))

    names = [t["name"] for t in C("get_song")["tracks"]]
    if "Claude Sub" not in names:
        C("create_track", {"kind": "midi", "name": "Claude Sub"})
        C("load_device", {"track": "Claude Sub", "path": "instruments/Operator"})
    for p, kw in (("Ae Attack", {"display": "300 ms"}), ("Ae Release", {"display": "60 ms"}),
                  ("Volume", {"display": -24})):
        C("set_param", dict(track="Claude Sub", device="Operator", param=p, **kw))
    C("delete_clips_in_range", {"track": "Claude Sub", "start_bar": 1, "end_bar": 400})
    C("create_midi_clip", dict(track="Claude Sub", **SUB))

    for tr, db in LEVELS.items():
        C("set_track", {"track": tr, "volume_db": db})
    for tr, pan in PANS.items():
        C("set_track", {"track": tr, "pan": pan})
    plate = [i for i, r in enumerate(C("get_song")["returns"]) if r["name"].endswith("Plate")][0]
    for tr, db in PLATE_SENDS.items():
        C("set_send", {"track": tr, "send": plate, "db": db})
    C("set_param", {"track": "master", "device": "EQ Eight", "param": "5 Filter On A", "value": 0})

    for name, (bar, length, points) in PAD_FILTER.items():
        notes = C("get_notes", {"track": "Claude Pad", "clip": {"at": (bar - 1) * 4.0}})
        C("delete_clips_in_range", {"track": "Claude Pad", "start_bar": bar, "end_bar": bar + 1})
        C("create_midi_clip", {"track": "Claude Pad", "bar": bar, "length": length, "notes": notes,
                               "name": name, "envelopes": [{"device": "Auto Filter", "param": "Frequency",
                                                            "unit": "display", "points": points}]})

    C("delete_clips_in_range", {"track": "Claude Shaker", "start_bar": 1, "end_bar": 400})
    for k, (a, b, vel) in enumerate(TP.SHAKER_RANGES):
        notes = groove.steps_to_notes(groove.DEEP_HOUSE["shaker"], 60, bars=b - a, swing=SHAKER_SWING,
                                      humanize=0.03, seed=40 + k, vel_scale=SHAKER_VEL.get((a, b), vel),
                                      length=0.12)
        C("create_midi_clip", {"track": "Claude Shaker", "bar": a, "length": (b - a) * 4, "notes": notes,
                               "name": "tambourine %d%%" % SHAKER_SWING})

    # the dialogue continues into the build, over the held IV7sus4
    cr = melody.call_and_response("G", "minor_hexatonic", ["C7sus4"] * 4, phrase_bars=2, seed=B.MOTIF_SEED)
    C("delete_clips_in_range", {"track": "Claude Call (Bells)", "start_bar": 121, "end_bar": 123})
    C("delete_clips_in_range", {"track": "Claude Response (EP)", "start_bar": 123, "end_bar": 125})
    C("create_midi_clip", {"track": "Claude Call (Bells)", "bar": 121, "length": 8,
                           "notes": harmony.swing(cr["call"], B.SWING), "name": "call"})
    C("create_midi_clip", {"track": "Claude Response (EP)", "bar": 123, "length": 8,
                           "notes": harmony.swing(cr["response"], B.SWING), "name": "response"})

    # the vocal from The Call returns alone at the top of the breakdown (Bb, G, F: tones
    # of all four breakdown chords); the other two vocals carry F#/B or clash with Fadd9
    voc = C("get_track", {"track": "30-ny_vox124_yagota"})
    if not any(96 * 4 - 1 <= c["start"] < 105 * 4 for c in voc["clips"]):
        C("duplicate_range", {"track": "30-ny_vox124_yagota", "start_bar": 40, "end_bar": 49, "dest_bar": 96})
    log("done")


if __name__ == "__main__":
    main()
