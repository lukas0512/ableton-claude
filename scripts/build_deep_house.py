"""Rebuild 'Drums groove' as a 6-minute deep house track with a story.

Key G minor, 123 BPM, 184 bars (5:59). Harmony stays inside the song's own vocabulary
(G A Bb C D F: no E, no Eb): Gm7, C7sus4, Bbmaj7, Fadd9.

Story
  1  Intro       kick, perc, hats, vocal ID                      the room fills
 17  Groove      + bass (G pedal), clap, open hats               the floor locks in
 33  The Call    stab (Gm7) asks every other 2 bars - no answer  a question hangs
 49  Dialogue    synth (Bbmaj7) answers: i -> III, 2 + 2 bars    call and response
 65  Break       kick & bass out, the answer lingers, ska guitar breath
 73  Groove B    dialogue resumes, guitar, open hat shaker, vocal chop
 97  Breakdown   pad: Gm7 - Bbmaj7 - Fadd9 - C7sus4; bells ask, e-piano answers
121  Build       C7sus4 held (suspension), 909 clap roll, risers  tension
129  Drop        stab and synth trade every bar, then play together (Gm9)
161  Outro       conversation winds down, back to drums for the DJ

Run with Live open on the project (a copy). Usage: build_deep_house.py [--dry]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client  # noqa: E402
from ableton_claude.arranger import Arranger, energy  # noqa: E402
from ableton_claude.music import groove, harmony, melody, theory  # noqa: E402

C = client.call
END = 185
SWING = 58.0             # measured on the song's own tonal loops (59-63 %)
SECTIONS = [("Intro", 1), ("Groove", 17), ("The Call", 33), ("Dialogue", 49),
            ("Break", 65), ("Groove B", 73), ("Breakdown", 97), ("Build", 121),
            ("Drop", 129), ("Outro", 161)]

# library phrases: (track, source bars in the current arrangement)
SOURCES = {
    "kick": ("8 Kick", 165, 169), "tom": ("3 TOM", 167, 168),
    "bass": ("10 Bass", 165, 169), "clap": ("6 Clap", 165, 169),
    "ohm": ("7 Open H. Main", 165, 169), "hat": ("9 Closed Hat", 145, 149),
    "ohs": ("10-Open Hat Shaker", 165, 169), "perc": ("11-ODH_123_Groove_Perc", 165, 169),
    "stab": ("20 Stab Rhytm", 165, 169), "synth": ("16 Synth resp", 133, 135),
    "guitar": ("18 Guitar", 165, 169), "rhodes": ("19 Rhodes Reverse", 129, 131),
    "sweep": ("22 Sweep Down", 129, 137), "rise8": ("rise", 153, 161),
    "rise4": ("rise", 45, 49), "rise2": ("rise2", 77, 81),
    "revcrash": ("25 Reverse Crash", 16, 17), "uplift": ("26 Uplifter", 29, 33),
    "crash": ("crash", 97, 105), "vox": ("29 Vox Shot Cm", 9, 13),
    "yagota": ("30-ny_vox124_yagota", 40, 49), "sam": ("31-SAM_FELDT", 89, 97),
    "ska": ("32-oss_ip1", 81, 89),
}
# tracks emptied and left silent: muted duplicates, the frozen brass (its freeze audio
# is tied to the old arrangement), the Mini V4 pedal that used Eb
RETIRED = ["8 Shaker", "13 Stab Rhytm MIDI", "15 Synth Resp. MIDI", "20 Brass LEAD Break",
           "28-Mini V4"]


def alternate(start, end, first, span):
    """Bars [a, a+span) for every other block of `span` starting at `first`."""
    out, a = [], first
    while a < end:
        out.append((a, min(a + span, end)))
        a += 2 * span
    return out


FILLS = {
    "kick": [(1, 32), (33, 65), (73, 97), (121, 128), (129, 160), (161, 185)],
    "bass": [(17, 65), (73, 97), (129, 177)],
    "clap": [(25, 65), (73, 97), (129, 177)],
    "ohm": [(17, 65), (73, 97), (129, 177)],
    # the Break drops kick and bass but keeps hats and perc: without them it measured
    # -29 LUFS, a hole instead of a breath
    "hat": [(9, 65), (65, 73), (73, 97), (113, 128), (129, 185)],
    "ohs": [(49, 65), (81, 97), (129, 161)],
    "perc": [(1, 65), (65, 73), (73, 97), (113, 128), (129, 185)],
    # the call: stab asks, and in The Call nobody answers yet
    "stab": (alternate(33, 49, 33, 2) + alternate(49, 65, 49, 2) + alternate(73, 97, 73, 2)
             + alternate(129, 145, 129, 1) + [(145, 161)] + alternate(161, 169, 161, 2)),
    # the response: Bbmaj7 answers Gm7 (i -> III)
    "synth": (alternate(51, 65, 51, 2) + [(65, 73)] + alternate(75, 97, 75, 2)
              + alternate(130, 145, 130, 1) + [(145, 161)] + alternate(163, 169, 163, 2)),
    "guitar": [(81, 97), (137, 161)],
    "vox": [(9, 17), (169, 177)],
}
PLACES = {
    "tom": [32, 48, 64, 96, 128, 144, 160],
    # reversed rhodes (carries E natural): swells land only on Bbmaj7 (#11) or Fadd9
    # (maj7) downbeats, never on C7sus4 where E grinds against F. Clip starts +0.25 bar.
    "rhodes": [49, 63, 97, 107, 115],
    "sweep": [65, 97, 129],
    "rise4": [69], "rise8": [121], "rise2": [45, 125],
    "revcrash": [16, 32, 48, 64, 72, 96, 120, 128, 160],
    "uplift": [29, 61, 93, 125, 157],
    "crash": [17, 33, 49, 73, 129, 145, 161],
    "yagota": [40], "sam": [89], "ska": [65],
}

BREAKDOWN = ["Gm7", "Bbmaj7", "Fadd9", "C7sus4"]
NEW_TRACKS = {  # name: (browser path, volume dB, send A dB)
    "Claude Pad": ("sounds/Pad/Analog Soft Pad.adv", -13.0, -24.0),
    "Claude Call (Bells)": ("sounds/Mallets/Bells Mellow.adv", -15.0, -12.0),
    "Claude Response (EP)": ("sounds/Piano & Keys/E-Piano Rhodish.adg", -13.0, -18.0),
    "Claude Build Clap": ("drums/Drum Hits/Clap/909 Clap.flac", -12.0, None),
}
# C&R pairs: call at bar X (2 bars), response at X + 2; chords per bar
PAIRS = [(105, ["Gm7", "Gm7", "Bbmaj7", "Bbmaj7"]), (109, ["Fadd9", "Fadd9", "C7sus4", "C7sus4"]),
         (113, ["Gm7", "Gm7", "Bbmaj7", "Bbmaj7"]), (117, ["Fadd9", "Fadd9", "C7sus4", "C7sus4"]),
         (137, ["Gm7", "Bbmaj7", "Gm7", "Bbmaj7"]), (141, ["Gm7", "Bbmaj7", "Gm7", "Bbmaj7"]),
         (153, ["Gm9"] * 4), (157, ["Gm9"] * 4)]
MOTIF_SEED = 11          # one seed: the same rhythmic motif returns as the hook


def log(*a):
    print(*a, flush=True)


def build(dry=False):
    song = C("get_song")
    names = [t["name"] for t in song["tracks"]]
    log("set: %d tracks, %.0f BPM" % (len(names), song["tempo"]))
    if dry:
        return

    arr = Arranger(log=log)
    log("\n1. stash phrases in the library zone (bars 601+)")
    phrases = {k: arr.stash(*v) for k, v in SOURCES.items()}
    json.dump({k: [p.track, p.start_bar, p.end_bar] for k, p in phrases.items()},
              open("/tmp/claude-501/phrases.json", "w"))

    log("\n2. clear bars 1-600 on every track")
    tracks = sorted({p.track for p in phrases.values()} | set(RETIRED))
    for tr in tracks:
        log("   %-32s deleted %d" % (tr, arr.clear(tr)))

    log("\n3. lay out the arrangement")
    for key, ranges in FILLS.items():
        for a, b in sorted(ranges):
            arr.fill(phrases[key], a, b)
        log("   %-8s %d ranges" % (key, len(ranges)))
    for key, bars in PLACES.items():
        for bar in sorted(bars):
            arr.place(phrases[key], bar)
        log("   %-8s placed at %s" % (key, sorted(bars)))

    log("\n4. new parts from presets and generated MIDI")
    for name, (path, vol, send) in NEW_TRACKS.items():
        if name not in names:
            C("create_track", {"kind": "midi", "name": name})
            C("load_device", {"track": name, "path": path})
        C("set_track", {"track": name, "volume_db": vol})
        if send is not None and song["returns"]:
            C("set_send", {"track": name, "send": 0, "db": send})
    C("load_device", {"track": "Claude Pad", "path": "audio_effects/Auto Filter"})

    # breakdown -> build: progression three times, then C7sus4 held through the build
    # (a suspension that resolves into the drop's Gm7); the filter opens across all 32 bars
    prog = BREAKDOWN * 3
    pad, voicings = harmony.progression_notes(prog, bars_per_chord=2, low=53, high=77,
                                              voices=4, anticipate=0.5, hold_last_bars=8)
    C("create_midi_clip", {
        "track": "Claude Pad", "bar": 97, "length": 32 * 4, "notes": pad,
        "name": "Breakdown -> Build",
        "envelopes": [{"device": "Auto Filter", "param": "Frequency", "unit": "display",
                       "points": [[0, 600], [96, 3500], [128, 9000]]}]})
    gm9 = theory.voice_lead(["C7sus4", "Gm9"], low=53, high=77, voices=5)[1]
    C("create_midi_clip", {
        "track": "Claude Pad", "bar": 145, "length": 16 * 4, "name": "Drop bed Gm9",
        "notes": [[p, 0.0, 63.5, 80] for p in gm9],
        "envelopes": [{"device": "Auto Filter", "param": "Frequency", "unit": "display",
                       "points": [[0, 2500], [32, 5000], [64, 2500]]}]})
    log("   pad voicings: %s" % [[theory.note_name(p) for p in v] for v in voicings[:4]])

    for bar, chords in PAIRS:
        cr = melody.call_and_response("G", "minor_hexatonic", chords, phrase_bars=2,
                                      seed=MOTIF_SEED)
        C("create_midi_clip", {"track": "Claude Call (Bells)", "bar": bar, "length": 8,
                               "notes": harmony.swing(cr["call"], SWING), "name": "call"})
        C("create_midi_clip", {"track": "Claude Response (EP)", "bar": bar + 2, "length": 8,
                               "notes": harmony.swing(cr["response"], SWING),
                               "name": "response"})
        log("   C&R %3d %-28s call %s (ends deg %d) | resp %s (ends deg %d)"
            % (bar, "-".join(chords), " ".join(cr["call_names"]), cr["call_ends_on_degree"],
               " ".join(cr["response_names"]), cr["response_ends_on_degree"]))

    roll = groove.build_roll(bars=8, pitch=60)      # Simpler plays the sample at C3
    C("create_midi_clip", {"track": "Claude Build Clap", "bar": 121, "length": 32,
                           "notes": roll, "name": "build roll"})

    log("\n5. locators")
    C("clear_cues")
    for name, bar in SECTIONS:
        C("set_cue", {"name": name, "bar": bar})

    log("\n6. drop the library zone")
    arr.drop_library()

    # levels from the first render: the build measured louder than the drop, and sub +
    # low held 89 % of the energy
    log("\n7. levels")
    for tr, db in (("Claude Build Clap", -16), ("rise", -16), ("rise2", -15),
                   ("10 Bass", -10.5), ("9 Closed Hat", -8.5), ("7 Open H. Main", -9)):
        C("set_track", {"track": tr, "volume_db": db})
    C("set_param", {"track": "master", "device": "Pro-L 2", "param": "Output Level",
                    "display": -1.0})
    C("set_param", {"track": "master", "device": "Pro-L 2", "param": "Gain", "display": 8.0})

    parts = arr.parts + [("Claude Pad", 97, 129), ("Claude Pad", 145, 161),
                         ("Claude Build Clap", 121, 129)]
    parts += [("Claude Call (Bells)", b, b + 2) for b, _ in PAIRS]
    parts += [("Claude Response (EP)", b + 2, b + 4) for b, _ in PAIRS]
    curve = energy(parts, END - 1)
    json.dump({"parts": parts, "curve": curve, "sections": SECTIONS},
              open("/tmp/claude-501/plan.json", "w"))
    log("\nenergy per 8 bars: " + " ".join("%d:%.0f" % (1 + i * 8, sum(curve[i*8:i*8+8]) / 8)
                                           for i in range((END - 1) // 8)))


if __name__ == "__main__":
    build(dry="--dry" in sys.argv)
