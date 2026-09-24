"""Release, groove and body pass for the example track, from the reference comparison.

What the 25 deep house references do that the first finished mix did not:

- release at the drop: the references' drop is +3.7 LU louder than the 4 bars before it
  (median; middle half +2.8..+5.1) and brings the kick back (+26 dB). Here the kick came
  back at the start of the build (bar 121), so the build start carried the jump and the
  drop arrived 1.1 LU *quieter* than the risers before it. The kick now leaves with the
  breakdown and returns on the drop, and the transition effects come down: before every
  entry (Dialogue, Drop, Outro) they peaked louder than the section they introduce, and
  the references barely ramp (build slope ~0 LU/bar).
- harmony into the drop: the build held IV7sus4 (C7sus4) over the drop's G pedal, a soft
  plagal arrival. The riser there is a tonal D->G, so the pad now turns to V7sus4 (D7sus4:
  D G A C, no F#, inside the song's hexatonic set) for the last 4 bars. D7sus4 -> Gm moves
  the bass D->G and resolves A->Bb by a half step.
- one groove: the closed hat was straight/pushed (mix swing 47 %) while the song's own
  tonal loops swing 58-63 % and the references sit at 55 % (median). One 16th swing groove
  on the hats, at the amount the generated parts already use (58 %).
- body: in the groove sections 250-500 Hz sat 2-3.6 dB under the references' median while
  5-6 kHz sat 1-2 dB over and 100 Hz above their upper quartile.

Reversible: the build's kick clips are deactivated, not deleted; the replaced pad clip's
notes and every level touched are saved to the snapshot file first.

    release_pass.py SNAPSHOT.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
sys.path.insert(0, os.path.dirname(__file__))
from ableton_claude import client  # noqa: E402
from ableton_claude.music import harmony, theory  # noqa: E402
import build_deep_house as B  # noqa: E402

C = client.call
GROOVE = "Swing Logic 16ths 62"
GROOVE_TIMING = 67.0              # 62 % swing scaled to ~58 %
GROOVED = ["9 Closed Hat", "7 Open H. Main"]
PAD_CHORDS = B.BREAKDOWN * 3 + ["D7sus4"]
PAD_BARS = [2] * 11 + [6, 4]       # ... C7sus4 held 119-125, D7sus4 125-129
# root position for the dominant: smallest-motion voice leading picks D7sus4/C, which
# keeps C in the pad's lowest voice and blurs the cadence. D4 G4 A4 C5 moves every voice
# of C7sus4 (C4 F4 G4 Bb4) up a whole step, so the lowest line runs C -> D -> (drop) G.
LAST_VOICING = [62, 67, 69, 72]
FX_LEVELS = {"26 Uplifter": -9.0, "rise2": -19.0, "rise": -19.0, "25 Reverse Crash": -4.0,
             "Claude Build Clap": -18.0}
BODY_EQ = [("5 Filter On A", {"value": 1}), ("5 Filter Type A", {"item": "Bell"}),
           ("5 Frequency A", {"display": 400}), ("5 Gain A", {"display": 1.5}),
           ("5 Q A", {"display": 0.7}),
           ("6 Filter On A", {"value": 1}), ("6 Filter Type A", {"item": "Bell"}),
           ("6 Frequency A", {"display": 100}), ("6 Gain A", {"display": -1.0}),
           ("6 Q A", {"display": 1.2})]
SHAKER_DB = -23.0


def log(*a):
    print(*a, flush=True)


def main(snapshot_path):
    snap = {"levels": {}, "eq": {}}
    for tr in list(FX_LEVELS) + ["Claude Shaker"]:
        snap["levels"][tr] = C("get_track", {"track": tr, "clips": False})["vol_db"]
    eq = C("get_device", {"track": "master", "device": "EQ Eight"})
    params = eq["params"] if isinstance(eq["params"], dict) else {p["name"]: p for p in eq["params"]}
    snap["eq"] = {k: params[k] for k, _ in BODY_EQ if k in params}
    snap["pad_notes"] = C("get_notes", {"track": "Claude Pad", "clip": {"at": 96 * 4.0}})
    snap["grooves"] = C("grooves")
    json.dump(snap, open(snapshot_path, "w"), indent=1, default=str)
    log("snapshot:", snapshot_path)

    r = C("mute_clips_in_range", {"track": "8 Kick", "muted": True, "start_bar": 121,
                                  "end_bar": 129})
    log("kick: %d build clips deactivated (returns on the drop)" % r["changed"])

    notes, voicings = harmony.progression_notes(PAD_CHORDS, low=53, high=77, voices=4,
                                                anticipate=0.5, bars=PAD_BARS)
    last_start = sum(PAD_BARS[:-1]) * 4.0 - 0.5
    last = sorted((n for n in notes if n[1] >= last_start - 1e-6), key=lambda n: n[0])
    for n, pitch in zip(last, LAST_VOICING):
        n[0] = pitch
    voicings[-1] = LAST_VOICING
    C("delete_clips_in_range", {"track": "Claude Pad", "start_bar": 97, "end_bar": 98})
    C("create_midi_clip", {
        "track": "Claude Pad", "bar": 97, "length": 32 * 4, "notes": notes,
        "name": "Breakdown -> Build (IV-V)",
        "envelopes": [{"device": "Auto Filter", "param": "Frequency", "unit": "display",
                       "points": [[0, 600], [96, 3500], [128, 9000]]}]})
    log("pad: %s" % " ".join("%s[%s]" % (c, " ".join(theory.note_name(p) for p in v))
                             for c, v in list(zip(PAD_CHORDS, voicings))[-3:]))

    g = C("set_groove", {"name": GROOVE, "timing": GROOVE_TIMING})
    log("groove: %s" % g)
    for tr in GROOVED:
        log("   %s" % C("apply_groove", {"track": tr, "groove": GROOVE}))

    for tr, db in FX_LEVELS.items():
        C("set_track", {"track": tr, "volume_db": db})
        log("fx level %-20s %5.1f -> %5.1f dB" % (tr, snap["levels"][tr], db))
    for p, kw in BODY_EQ:
        C("set_param", dict(track="master", device="EQ Eight", param=p, **kw))
    C("set_track", {"track": "Claude Shaker", "volume_db": SHAKER_DB})
    log("body: master bell +1.5 dB @400 Hz (Q 0.7), -1 dB @100 Hz; maracas %.0f dB" % SHAKER_DB)


if __name__ == "__main__":
    main(sys.argv[1])
