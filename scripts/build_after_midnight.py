"""A deep house track built from the user's sample packs, guided by the ear's principles.

Core: Loopmasters Ultimate Deep House construction kit "After Midnight" (C minor, 123 BPM,
4-bar loops that were written to fit together), placed without warping (they are already
at the song tempo). Development: a C minor organ loop from the same pack. Pad: Live's
Celestial Pad on Cm9 for the breaks and a slow i9 - VImaj9 swing through the main break.

Form follows the deep house principles measured from 22 references: a 16-bar drums-only
DJ intro, bass at bar 17, an 8-bar first break, a 16-bar main break, a 32-bar drop and a
16-bar drums-only outro. Breaks work by subtraction like the references': kick, bass and
clap leave, hats and percussion stay (73 % of reference breaks keep hats), so a break sits
~4 LU under the groove instead of falling into silence. The main break stays flat like
the references' (no rising top end): hats and tops return together at 97, the stab
leaves for the last 4 bars and comes back with kick, bass and clap on the drop, which
carries every layer and so tops the groove before the break.

Measured, not assumed: the pack's vocal chops sit ~55 cents sharp of the stab (F+43c /
F#-36c against Bb+8c / C+21c), so they are warped (Complex Pro) and detuned by VOX_DETUNE.
The kit's kick (60 Hz, short) left a -8 dB hole at 50 Hz and +6 dB at 100 Hz against the
references' 1/3-octave curve; KICK_SHOT (52.5 Hz, 128 ms, picked with find_samples) is
built into a 4-bar loop instead. The kit's hats (9.2 kHz, 20 ms) were brighter and
shorter than any reference; HAT_SHOT (6.2 kHz, 70 ms) plays every 16th with the
references' median groove (loops.from_template) at HAT_SWING, with an open hat on the
off-beat 8ths in the body of the track (the loudest steps of the references' hat
template). The kit's straight top loops are warped and swung with a pool groove so the
whole top end swings, not just the hats. Levels come from fitting each loop's band powers
to the references' curve and stem balance (bass/chords/vocals against the drums), with
the kit's own unity balance as the start: the first version sat every non-kick layer
4-14 dB under it, which is what made the breaks fall 9-12 LU.

Transitions and variation (the user's ask): a crash on every section downbeat and a
reversed one into the big ones, risers (pack FX, resampled to exactly 4 bars) into the
groove after the first break and into the drop, the kick dropping out on the last beat
before each break, snare ghost notes with the references' clap micro-timing (a busier
pattern in the drop), a one-bar vocal "call" every 4 bars before the vocal enters for
real, the organ answering in the last groove, and a iv turnaround (the stab up a fourth,
Cm -> Fm) in the two bars before the main break and before the last groove.

Re-running is safe: clips are synced to the plan (missing ones added, strays removed,
existing ones kept), devices are loaded only when missing and their parameters set.

    build_after_midnight.py
"""
import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client, knowledge, loops  # noqa: E402

C = client.call
PACKS = os.path.expanduser("~/Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs/Loopmasters - Ultimate Deep House")
KIT = os.path.join(PACKS, "WAV_LOOPS/CONSTRUCTION_KITS/6_After_Midnight_123Bpm Cmin")
HITS = os.path.join(PACKS, "SOUNDS_&_FX")
F = {
    "Clap": "WB_123_After_Midnight_Claps_SN.wav",
    "Tops 1": "WB_123_After_Midnight_Tops_1.wav",
    "Tops 2": "WB_123_After_Midnight_Tops_2.wav",
    "Perc Tops": "WB_123_After_Midnight_Perc_Tops.wav",
    "Bass": "WB_123_Cmin_After_Midnight_Bass.wav",
    "Stab": "WB_123_Cmin_After_Midnight_Stab.wav",
    "Vox Chops": "WB_123_Cmin_After_Midnight_Vox_Chops.wav",
    "FX 1": "WB_123_After_Midnight_Fx1.wav",
    "FX 2": "WB_123_After_Midnight_Fx2.wav",
}
ORGAN = os.path.join(PACKS, "WAV_LOOPS/MUSIC_LOOPS/DS2_123_Cm_Organ_03.wav")
KICK_SHOT = os.path.join(HITS, "DRUM_HITS/KICKS/HM2_Kick_001.wav")          # 55.9 Hz, 128 ms
HAT_SHOT = os.path.join(HITS, "DRUM_HITS/HATS/DSB_HH_STOMPER.wav")          # 6.2 kHz, 70 ms
OPEN_HAT = os.path.join(HITS, "DRUM_HITS/HATS/DCW_Open_Hat_07.wav")          # 5.5 kHz, 130 ms
SNARE_SHOT = os.path.join(HITS, "DRUM_HITS/SNARES/NSL_Snare_20.wav")        # 4.5 kHz, 59 ms
CRASH = os.path.join(HITS, "DRUM_HITS/CYMBALS/DGH_CRASH_004.wav")           # 5 s, 6.2 kHz
CRASH_REV = os.path.join(HITS, "DRUM_HITS/CYMBALS/MD2_CRASH_20.wav")        # 1.35 s rise
RISER = os.path.join(HITS, "FX/DCW_126_The_Rise_Fx.wav")                    # 4 bars at 126
OUT_DIR = os.path.expanduser("~/Music/Ableton/User Library/Samples/Claude/After Midnight")
BPM = 123.0
BEAT_S = 60.0 / BPM
END = 185
LOOP_BEATS = 16.0
VOX_DETUNE = -45.0
HAT_SWING = 60.0      # the median template reads 54.8 % against the references' 55-76 %
TOPS_GROOVE = "Swing 16ths 66"          # Live core groove, already in this set's pool
TOPS_GROOVE_TIMING = 50.0               # half its 66 % swing: the mix read 69 % at 100 %, 64 % at 60 %
SECTIONS = [("Intro", 1), ("Groove", 17), ("Stab", 33), ("Break", 49), ("Groove B", 57),
            ("Main Break", 89), ("Drop", 105), ("Groove C", 137), ("Outro", 153), ("DJ Outro", 169)]
PLAN = {   # track: [(start_bar, end_bar[, variant]), ...] in 4-bar loops
    "Kick":      [(1, 49), (57, 89), (105, 185)],
    "Hats":      [(1, 17, "closed"), (17, 89, "open"), (97, 169, "open"), (169, 185, "closed")],
    "Ghost":     [(17, 49, "a"), (57, 89, "a"), (105, 137, "b"), (137, 169, "a")],
    "Tops 1":    [(9, 57), (137, 169)],
    "Tops 2":    [(57, 89), (97, 137)],                # main break: hats and tops return at 97
    "Perc Tops": [(33, 57), (73, 81), (89, 153)],      # out at 81-89 so the drop tops the pre-break
    "Clap":      [(17, 49), (53, 89), (105, 169)],     # first break: back after 4 bars
    "Bass":      [(17, 49), (57, 89), (105, 169)],
    "Stab":      [(33, 57), (65, 89), (93, 101), (105, 145)],   # space before the drop; call in Groove C
    "Organ":     [(73, 89), (105, 137), (145, 153)],   # answers in the last groove
    "Vox Chops": [(49, 57), (65, 73), (89, 105), (121, 137)],
    "FX 1":      [(13, 17), (45, 49), (85, 89), (101, 105)],
    "FX 2":      [(49, 53), (89, 93), (137, 141), (181, 185)],
    "Riser":     [(53, 57), (101, 105)],
}
HITS_PLAN = {  # track: [(bar, variant)] one-shots on downbeats (reverse crash ends on it)
    "Crash": [(17, "hit"), (33, "hit"), (49, "hit"), (57, "hit"), (89, "hit"), (105, "hit"),
              (137, "hit"), (169, "hit"), (17, "rev"), (33, "rev"), (57, "rev"), (105, "rev"),
              (137, "rev")],
}
VOX_CALLS = [44, 48, 80, 84, 88, 116, 120, 156, 160, 164]   # the loop's last bar, alone
STAB_IV = [(87, 89), (135, 137)]               # Cm -> Fm turnaround; the Cm stab is cut there
KICK_DROPS = [45, 85]                          # the kick clip that loses its last beat
TOPS_SWUNG = ["Tops 1", "Tops 2", "Perc Tops"]
PAD_RANGES = [(49, 57, "Cm9"), (89, 105, None), (137, 153, "Cm9")]
MAIN_BREAK_CHORDS = ["Cm9", "Cm9", "Abmaj9", "Abmaj9"] * 2   # i9 - VImaj9, 4 bars each (refs: 0.3-0.8 changes / 8 bars)
# root position on purpose: with bass and kick out, the pad's lowest note is the bass.
# The two chords share C Eb G Bb; only the root moves (C3 -> Ab2) and D4 leaves.
VOICINGS = {"Cm9": [48, 51, 55, 58, 62], "Abmaj9": [44, 48, 51, 55, 58]}
# the open hat, crash, snare ghosts and risers of v6 put 2-6 kHz at 4.5 % (references
# 1.6-3.2) and the riser + FX filled the four bars before the drop (drop jump 1.7 LU):
# transitions sit under the drums, not on top of them
LEVELS = {"Kick": -8.0, "Clap": -6.0, "Hats": -19.5, "Ghost": -16.0, "Tops 1": -13.0,
          "Tops 2": -13.0, "Perc Tops": -5.5, "Bass": -10.5, "Stab": -4.0, "Stab iv": -4.0,
          "Organ": -5.0, "Vox Chops": -6.0, "Vox Call": -6.0, "FX 1": -18.0, "FX 2": -14.0,
          "Riser": -22.0, "Crash": -18.0, "Pad": -10.0}
PANS = {"Hats": -0.1, "Tops 1": -0.25, "Tops 2": 0.25, "Perc Tops": 0.3, "Stab": 0.1,
        "Stab iv": 0.1, "Organ": -0.1, "Ghost": 0.15}
SENDS = {  # track: [A-Reverb dB, B-Delay dB]
    "Pad": [-14.0, None], "Stab": [-16.0, -22.0], "Stab iv": [-16.0, -22.0], "Organ": [-18.0, None],
    "Vox Chops": [-16.0, -14.0], "Vox Call": [-14.0, -10.0], "Hats": [-26.0, None],
    "Clap": [-18.0, None], "Ghost": [-18.0, -20.0], "Crash": [-14.0, None]}
# v2's Drum Buss boom and bass saturation, made moot by the new kick; Dynamic Tube did not
# change this bass (its 2nd+3rd harmonics already sit 8-19 dB over the fundamental)
REMOVE = [("Kick", "Drum Buss"), ("Bass", "Saturator"), ("Bass", "Dynamic Tube")]
# (track, device, {param: number/text for the display, or an option name})
DEVICES = [
    # never above a root: a 34 Hz cut under the C1 bass and a 200 Hz one under the C3 pad
    # made the ear hear G minor (G1 took over the low end)
    ("Bass", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "25.0 Hz"}),
    ("Organ", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "100 Hz"}),
    ("Hats", "EQ Eight", {"7 Filter On A": "Off"}),     # the new hats are dark already
    ("Tops 1", "EQ Eight", {"7 Filter On A": "On", "7 Filter Type A": "High Shelf",
                            "7 Frequency A": "10.0 kHz", "7 Gain A": "-4.0 dB"}),
    ("Tops 2", "EQ Eight", {"7 Filter On A": "On", "7 Filter Type A": "High Shelf",
                            "7 Frequency A": "10.0 kHz", "7 Gain A": "-4.0 dB"}),
    # crisp: sharper attacks, not more top end (hat level and high-mid already sit at the
    # references' upper edge)
    ("Clap", "Drum Buss", {"Drive": "0 %", "Transients": "0.30", "Damping Freq": "20.0 kHz"}),
    ("Perc Tops", "Drum Buss", {"Drive": "0 %", "Transients": "0.20", "Damping Freq": "20.0 kHz"}),
    ("Ghost", "Drum Buss", {"Drive": "0 %", "Transients": "0.25", "Damping Freq": "20.0 kHz"}),
    # the low band read 12 dB wider than the references: organ and pad mono under 120 Hz
    ("Pad", "Utility", {"Stereo Width": "45 %", "Bass Mono": "On", "Bass Freq": "120 Hz"}),
    ("Organ", "Utility", {"Bass Mono": "On", "Bass Freq": "120 Hz"}),
    ("Pad", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB",
                         "1 Frequency A": "90 Hz", "7 Filter On A": "Off"}),   # keeps Ab2
    ("return:B-Delay", "Delay", {"Ping Pong": "On"}),
    ("master", "Limiter", {"Input Gain": "10.4 dB"}),
]


def log(*a):
    print(*a, flush=True)


def _is_option(v):
    return isinstance(v, str) and not (v[:1].isdigit() or v[:1] in "+-.")


def setp(track, device, param, v):
    args = {"track": track, "device": device, "param": param}
    args["item" if _is_option(v) else "display"] = v
    return C("set_param", args)


def ensure_device(track, name):
    have = [d["name"] for d in C("get_track", {"track": track, "clips": False})["devices"]]
    if name not in have:
        C("load_device", {"track": track, "query": name, "roots": ["audio_effects"]})


def _same_file(a, b):
    """Live may hand back a decomposed unicode path (the pack folder has a 'Ç')."""
    norm = lambda p: unicodedata.normalize("NFC", os.path.realpath(p))
    return norm(a) == norm(b)


def make_loops():
    """Loops the connector builds from one-shots: the kick on every beat; the hats on every
    16th with the references' measured feel (per-step micro-timing, accents and timing
    variation from the genre's ear principles), closed only or with an open hat on the
    off-beat 8ths; snare ghosts on the references' clap micro-timing; FX resampled to
    exactly 4 bars."""
    prof = knowledge.load_profile("deep house")["ear"]["drums"]
    out = lambda n: os.path.join(OUT_DIR, n)
    files = {"Kick": loops.write(out("AM_Kick_HM2_001_123bpm.wav"), loops.four_on_floor(KICK_SHOT, BPM))}
    open_hat = loops.trim_hit(OPEN_HAT, out("AM_OpenHat_DCW07_90ms.wav"), 0.09)   # refs: 44-84 ms
    hat_t = prof["hats"]["template"]
    files["Hats:closed"] = loops.write(out("AM_Hats_STOMPER_sw%d_123bpm.wav" % HAT_SWING),
                                       loops.from_template({"default": HAT_SHOT}, hat_t, BPM, seed=1,
                                                           swing_pct=HAT_SWING))
    files["Hats:open"] = loops.write(out("AM_Hats_STOMPER_open07s_sw%d_123bpm.wav" % HAT_SWING),
                                     loops.from_template({"default": HAT_SHOT, 2: open_hat, 6: open_hat,
                                                          10: open_hat, 14: open_hat}, hat_t, BPM,
                                                         seed=1, swing_pct=HAT_SWING))
    clap_t = prof["clap"]["template"]
    files["Ghost:a"] = loops.write(out("AM_Ghost_NSL20_a_123bpm.wav"),
                                   loops.from_template({"default": SNARE_SHOT}, clap_t, BPM,
                                                       steps=[7, 15], seed=2))
    files["Ghost:b"] = loops.write(out("AM_Ghost_NSL20_b_123bpm.wav"),
                                   loops.from_template({"default": SNARE_SHOT}, clap_t, BPM,
                                                       steps=[7, 10, 13, 15], seed=3))
    files["Riser"] = loops.stretch_to(RISER, out("AM_Rise_4bars_123bpm.wav"), BPM, 4)
    files["Crash:hit"] = CRASH
    files["Crash:rev"] = CRASH_REV
    return files


def path_for(files, track, variant=None):
    key = track if variant is None else "%s:%s" % (track, variant)
    if key in files:
        return files[key]
    if track == "Organ":
        return ORGAN
    return os.path.join(KIT, F[track])


def sync(track, want):
    """Arrangement clips of `track` = exactly `want`: {start_beat: (path, opts)}. Clips at
    other beats or with another file go; matching ones stay (with their trims); missing
    ones are created and shaped by opts: warp, warp_mode, detune, pitch, loop=(a, b) in
    beats of the file, length=beats (the clip is trimmed to it)."""
    clips = C("get_track", {"track": track, "max_clips": 500})["clips"]
    have = {c["start"] for c in clips if c["start"] in want and _same_file(c.get("file", ""), want[c["start"]][0])}
    for beat in sorted({c["start"] for c in clips} - have, reverse=True):
        C("delete_clip", {"track": track, "clip": {"at": beat}})
    for beat in sorted(set(want) - have):
        path, o = want[beat]
        args = {"track": track, "path": path, "beat": beat, "warp": bool(o.get("warp")), "name": track}
        for k in ("warp_mode", "detune", "pitch"):
            if k in o:
                args[k] = o[k]
        C("create_audio_clip", args)
        if o.get("warp"):                  # auto-warp can overshoot the end marker: pin the loop
            fix = {"track": track, "clip": {"at": beat}, "warping": True}
            for k in ("warp_mode", "detune", "pitch"):
                if k in o:
                    fix[k] = o[k]
            C("set_clip", fix)
            a, b = o.get("loop", (0.0, LOOP_BEATS))
            C("set_warp_markers", {"track": track, "clip": {"at": beat}, "beats": LOOP_BEATS})
            C("set_clip", {"track": track, "clip": {"at": beat}, "end_marker": b})
            C("set_clip", {"track": track, "clip": {"at": beat}, "looping": True, "loop_start": a, "loop_end": b})
        if "length" in o:
            C("trim_clip", {"track": track, "clip": {"at": beat}, "end_beat": beat + o["length"]})
    return len(set(want) - have), len({c["start"] for c in clips} - have)


def loop_wants(files, track, ranges):
    want = {}
    for r in ranges:
        a, b = r[:2]
        variant = r[2] if len(r) > 2 else None
        opts = {"warp": True, "warp_mode": "complex_pro", "detune": VOX_DETUNE} if track == "Vox Chops" else {}
        if track in TOPS_SWUNG:
            opts = {"warp": True, "warp_mode": "beats"}
        for bar in range(a, b, 4):
            want[(bar - 1) * 4.0] = (path_for(files, track, variant), opts)
    return want


def hit_wants(files, track, hits):
    want = {}
    for bar, variant in hits:
        beat = (bar - 1) * 4.0
        if variant == "rev":
            beat -= 1.35 / BEAT_S + 0.01    # the reversed crash ends just before the downbeat
        want[round(beat, 3)] = (path_for(files, track, variant), {})
    return want


def trims():
    """The kick loses its last beat before each break; the Cm stab makes room for the iv."""
    for bar in KICK_DROPS:
        beat = (bar - 1) * 4.0
        c = C("set_clip", {"track": "Kick", "clip": {"at": beat}})
        if c["end"] > beat + 15.0:
            C("trim_clip", {"track": "Kick", "clip": {"at": beat}, "end_beat": beat + 15.0})
    for a, b in STAB_IV:
        beat = (a - (a - 1) % 4 - 1) * 4.0                            # the loop that spans a
        c = C("set_clip", {"track": "Stab", "clip": {"at": beat}})
        if c["end"] > (a - 1) * 4.0:
            C("trim_clip", {"track": "Stab", "clip": {"at": beat}, "end_bar": a})


def pin_warps():
    """Every warped clip is a 16-beat loop: two warp markers make its tempo exactly 123
    (Live's auto-warp guessed 122.83 for the tops, 252 for the vocal)."""
    for t in TOPS_SWUNG + ["Vox Chops", "Vox Call", "Stab iv"]:
        for c in C("get_track", {"track": t, "max_clips": 500})["clips"]:
            if not c.get("warping"):
                C("set_clip", {"track": t, "clip": {"at": c["start"]}, "warping": True, "warp_mode": "beats"})
            C("set_warp_markers", {"track": t, "clip": {"at": c["start"]}, "beats": LOOP_BEATS})


def swing_tops():
    """Grooves only move warped clips."""
    C("set_groove", {"name": TOPS_GROOVE, "timing": TOPS_GROOVE_TIMING, "groove_amount": 1.0})
    for t in TOPS_SWUNG:
        C("apply_groove", {"track": t, "groove": TOPS_GROOVE, "start_bar": 1, "end_bar": END})


def pad_clips():
    C("delete_clips_in_range", {"track": "Pad", "start_bar": 1, "end_bar": END})
    for a, b, chord in PAD_RANGES:
        seq = [chord] if chord else MAIN_BREAK_CHORDS
        span = (b - a) * 4.0 / len(seq)
        notes = []
        for i, ch in enumerate(seq):
            start = i * span - (0.5 if i else 0.0)             # changes land on the "and" of 4
            dur = span - (0.5 if i < len(seq) - 1 else 0.0) + (0.5 if i else 0.0)
            notes += [[p, start, dur * 0.98, 84] for p in VOICINGS[ch]]
        C("create_midi_clip", {"track": "Pad", "bar": a, "length": (b - a) * 4, "notes": notes,
                               "name": chord or "Cm9 - Abmaj9"})


def mix():
    for track, device in REMOVE:
        if device in [d["name"] for d in C("get_track", {"track": track, "clips": False})["devices"]]:
            C("delete_device", {"track": track, "device": device})
    for name, db in LEVELS.items():
        C("set_track", {"track": name, "volume_db": db, "pan": PANS.get(name, 0.0)})
    for name, sends in SENDS.items():
        for i, db in enumerate(sends):
            if db is not None:
                C("set_send", {"track": name, "send": i, "db": db})
    for track, device, params in DEVICES:
        ensure_device(track, device)
        for p, v in params.items():
            got = setp(track, device, p, v)
            log("  %-15s %-10s %-16s %s" % (track, device, p, got.get("display")))


def main():
    C("set_tempo", {"bpm": BPM})
    order = list(PLAN) + list(HITS_PLAN) + ["Vox Call", "Stab iv", "Pad"]
    before = [t["name"] for t in C("get_song")["tracks"]]
    for name in order:
        if name not in before:
            C("create_track", {"kind": "midi" if name == "Pad" else "audio", "name": name})
    for name in reversed(before):                      # the blank set's empty default tracks
        if name in order:
            continue                                   # (a set must keep at least one track,
        info = C("get_track", {"track": name})         #  so ours are created first)
        if not info.get("clips") and not info.get("devices"):
            C("delete_track", {"track": name})
    files = make_loops()
    for name, ranges in PLAN.items():
        log("%-10s +%d -%d  %s" % ((name,) + sync(name, loop_wants(files, name, ranges)) + (ranges,)))
    for name, hits in HITS_PLAN.items():
        log("%-10s +%d -%d  %d hits" % ((name,) + sync(name, hit_wants(files, name, hits)) + (len(hits),)))
    vox = path_for(files, "Vox Chops")
    calls = {(bar - 1) * 4.0: (vox, {"warp": True, "warp_mode": "complex_pro", "detune": VOX_DETUNE,
                                     "loop": (12.0, 16.0), "length": 4.0}) for bar in VOX_CALLS}
    log("%-10s +%d -%d  %s" % (("Vox Call",) + sync("Vox Call", calls) + (VOX_CALLS,)))
    stab = path_for(files, "Stab")
    iv = {(a - 1) * 4.0: (stab, {"warp": True, "warp_mode": "complex_pro", "pitch": 5,
                                 "loop": (8.0, 16.0), "length": (b - a) * 4.0}) for a, b in STAB_IV}
    log("%-10s +%d -%d  %s" % (("Stab iv",) + sync("Stab iv", iv) + (STAB_IV,)))
    trims()
    pin_warps()
    swing_tops()
    if "Celestial Pad" not in [d["name"] for d in C("get_track", {"track": "Pad"})["devices"]]:
        C("load_device", {"track": "Pad", "path": "sounds/Pad/Celestial Pad.adg"})
    pad_clips()
    mix()
    song = C("get_song")
    if [(c["name"], c["bar"]) for c in song["cues"]] != [(n, float(b)) for n, b in SECTIONS]:
        if C("transport_state")["is_playing"]:          # Live refuses locator edits while playing
            log("cues not updated: Live is playing (stop it and re-run)")
        else:
            C("clear_cues")
            for name, bar in SECTIONS:
                C("set_cue", {"name": name, "bar": bar})
    log("tracks: %s" % [t["name"] for t in song["tracks"]])


if __name__ == "__main__":
    main()
