"""HOUSE (a friend's 128 BPM sketch, C minor): groove and arrangement pass, v1 2026-11-10.

What the sketch was (measured on its render): kick/clap/hats as ~1900 one-shot audio clips, no
swing, hats only on the "&"; the bass a drum loop converted to MIDI (pitches 36/38/42 = C, D, F#:
a tritone over the synth's Cm9), only its first bar looping, 44 % of its notes with the kick,
13.6 dB under the drums; a 24-bar break at -30 LUFS (13 LU under the groove); 131 bars, no outro.

What stays (his aesthetic): his kick, clap and two hats (now in Simplers), his Drift bass patch,
his Cm9 synth loop, his three spoken vocals, his percussion loop and FX, 128 BPM.

What changes: one pocket (57.5 % swing baked into every 16th part, accents, ghosts, pockets and
phrase-end fills), a bass riff in C minor written in the holes of the kick (0 % with it) and of
the synth's stabs (0/4/7/10/13), and a club form of 184 bars with two drops.

v2 (same day, his notes on v1: "esse hat tá muito fora do groove da música... o baixo ficou bem
legal, encaixar mais no synth pra os 2 fazerem a mesma harmonia, um talento na mix, uma preenchida
e call response"):
- the hat: his synth and percussion loops play their odd 16ths (the stab on step 7 and 13) straight,
  so a hat swung 17.6 ms late flammed on the stab every bar. One pocket now: the loops' odd-step
  hits are moved onto the same swing with warp markers; the 16th hat sits 5 dB lower with a flatter
  accent map (it was as loud as the off-beat hat).
- harmony: each bar of the loop is Gm (stabs on 1 and 2) then Cm/G (from the "a" of 2). The bass
  keeps its rhythm and now plays G under the Gm stabs and walks to C (G G Bb C Eb C).
- fill: the synth far and dark under the groove from bar 33; a crash on the drops.
- call and response: his own Cm stab an octave up answers on beat 4 of every 2nd bar into a
  ping-pong 3/16 delay (drop 1's second half, drop 2); his half-bar vocal chop answers the calls.
- mix: high-passes per element, one plate (1.4 s) for voices/clap/synth, a DRUMS bus with a Glue,
  a True Peak limiter on the master.

Run: cd mcp_server && uv run python ../scripts/build_house_amigo.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client  # noqa: E402

C = client.call
BPM = 128.0
SWING_PCT = 57.5
SW = (SWING_PCT - 50.0) / 100.0 * 0.5        # off-16th delay in beats (0.0375 = 17.6 ms)
MS = BPM / 60000.0                             # beats per millisecond
SRC = "/Users/lukasgalhardo/Downloads/house/HOUSE Project/Samples/Imported/"
SYNTH_WAV = SRC + "Marian Vol.2 - Synth Loop 18 Gmin.wav"
PERC_WAV = SRC + "Classmatic - Classmatic - Sample Pack Vol. 02 - 243 cl_percussion_loop_24.wav"
CALL_WAV = SRC + "Marian Vol.2 - Vocal 14.wav"
HOOK_WAV = SRC + "Marian Vol.2 - Vocal 11 - C#min.wav"
TALK_WAV = SRC + "Marian Vol.2 - Vocal 1.wav"
FX_WAV = SRC + "NoZzo FX 15.wav"

# the form: (name for the locator, first bar, bar after the last)
SECTIONS = [
    ("INTRO A - drums, DJ", 1, 17), ("INTRO B - bass enters", 17, 33), ("GROOVE - the call", 33, 49),
    ("BREAK 1 - synth hint", 49, 57), ("BUILD 1 - synth opens", 57, 65),
    ("DROP 1 - synth + bass talk", 65, 97), ("MAIN BREAK - voices", 97, 113),
    ("BUILD 2", 113, 121), ("DROP 2 - everything", 121, 153),
    ("OUTRO A - layers leave", 153, 169), ("OUTRO B - drums, DJ", 169, 185),
]
END = 185
BREATHS = (64, 120)                            # the last 2 beats of these bars are empty
DROPS = ((65, 97), (121, 153))
RNG = random.Random(11)


def log(*a):
    print(*a, flush=True)


def in_(bar, spans):
    return any(a <= bar < b for a, b in spans)


def pos(step):
    """16th step of a bar in beats, the off-16ths late by the swing."""
    return step * 0.25 + (SW if step % 2 else 0.0)


def jit(ms=2.5):
    return RNG.uniform(-ms, ms) * MS


def vel(v, spread=5):
    return float(max(1, min(127, v + RNG.randint(-spread, spread))))


# --------------------------------------------------------------------------- drums
KICK_BARS = ((1, 49), (65, 97), (121, 185))
KICK_EXITS = {16: (0, 4), 32: (0, 8), 48: (0, 4), 80: (0, 4, 8), 96: (0, 4, 8), 136: (0, 4, 8)}


def kick(bar):
    if not in_(bar, KICK_BARS):
        return []
    return [[60, s * 0.25, 0.5, 127.0] for s in KICK_EXITS.get(bar, (0, 4, 8, 12))]


def kick_hp(bar):
    """The build's kick, high-passed on its channel: quarters, 8ths, 16ths, then the breath."""
    plan = {57: (4, 56, 66), 58: (4, 66, 76), 59: (4, 76, 86), 60: (4, 86, 96),
            61: (4, 96, 104), 62: (4, 104, 110), 63: (2, 104, 116), 64: (1, 108, 124),
            113: (4, 50, 60), 114: (4, 60, 70), 115: (4, 70, 80), 116: (4, 80, 90),
            117: (4, 90, 100), 118: (4, 100, 108), 119: (2, 104, 116), 120: (1, 108, 124)}
    if bar not in plan:
        return []
    every, v0, v1 = plan[bar]
    steps = [s for s in range(0, 16, every) if not (bar in BREATHS and s >= 8)]
    return [[60, pos(s), 0.2, float(round(v0 + (v1 - v0) * i / max(1, len(steps) - 1)))]
            for i, s in enumerate(steps)]


def clap(bar):
    if bar < 9 or bar >= 181:
        return []
    late = 5 * MS
    out = []
    back = (12,) if 97 <= bar < 105 else (4, 12)          # half-time in the main break's first half
    for s in back:
        if bar in BREATHS and s >= 8:
            continue
        out.append([60, s * 0.25 + late, 0.3, vel(120, 3)])
    if bar < 17 or in_(bar, ((49, 53), (97, 105))) or bar in BREATHS:
        return out
    ghosts = {2: ((15, 44),), 3: ((7, 38),), 0: ((11, 50), (15, 58))}.get(bar % 4, ())
    if bar % 8 == 0:
        ghosts = ((11, 50), (14, 66), (15, 82))              # a two-note pickup, not a roll
    for s, v in ghosts:
        out.append([60, pos(s) + late + jit(), 0.2, vel(v, 4)])
    return out


def hat_off(bar):
    if bar < 5 or bar >= 181 or 97 <= bar < 105:
        return []
    out = []
    for s, v in ((2, 104), (6, 96), (10, 108), (14, 98)):
        if bar in BREATHS and s >= 8:
            continue
        out.append([60, s * 0.25 + jit(1.5), 0.24, vel(v, 4)])
    return out


def hat_16(bar):
    """v3 ("o midi dele, a forma que está desenhado, não está no mesmo groove e swing da música"):
    v1-v2 played beat + e + a and skipped the "&", with a loud "a", pockets and 32nd flutters: a
    lopsided gallop against the stabs. Now one continuous 16th line like the references' (the "&"
    the accent, e/a ~7 dB under it, the on-beats ghosted under the kick), nothing dropped."""
    if bar < 13 or bar >= 173 or 49 <= bar < 53:
        return []
    lift = 8 if in_(bar, (DROPS[1],)) else 0
    out = []
    for s in range(16):
        if bar in BREATHS and s >= 8:
            break
        v = {0: 46, 1: 58, 2: 84, 3: 66}[s % 4] + lift
        if bar % 4 == 0 and s == 15:
            v += 14                                          # a small push into the next phrase
        out.append([60, pos(s) + jit(1.2), 0.12, vel(v, 4)])
    return out


# --------------------------------------------------------------------------- bass
# Live's C1 = MIDI 36: the Drift's saw sounds C2 (65 Hz), above the kick's 50 Hz body.
Cn, D, Eb, F, G, Bb_, G_ = 36, 38, 39, 41, 43, 34, 31
# (step, pitch, 16ths long, velocity): every note off the kick (0/4/8/12) and in the gaps of the
# synth's stabs (0/4/7/10/13 and 0/4/7/10/14). The loop is Gm on beats 1-2 and Cm from the "a" of
# 2: the bass plays G (49 Hz, the kick's own pitch) under the Gm stabs and walks up to C.
RIFF_A = [(2, G_, 2.0, 112), (6, G_, 1.5, 104), (9, Bb_, 1.5, 98), (11, Cn, 1.0, 110), (14, Eb, 1.0, 100), (15, Cn, 0.8, 106)]
RIFF_B = [(2, G_, 2.0, 112), (6, G_, 1.5, 104), (9, F, 1.5, 98), (11, Eb, 1.0, 108), (13, Cn, 1.5, 102), (15, D, 0.8, 104)]
RIFF_T = [(2, G_, 2.0, 112), (6, G_, 1.5, 104), (9, Bb_, 1.5, 98), (11, Cn, 1.0, 104), (13, D, 1.5, 106), (15, F, 0.8, 108)]
RIFF_SPARSE = [(2, G_, 2.0, 112), (11, Cn, 1.0, 106)]
BASS_FULL = ((17, 49), (65, 97), (121, 169))
BASS_LOW = ((49, 57), (105, 113))                         # under a break: quieter, darker
BASS_SPARSE = ((97, 105),)
BASS_BUILD = ((57, 65), (113, 121))                       # the riff high-passed: the sub is the drop's


def bass(bar):
    if in_(bar, BASS_SPARSE):
        cell, scale = RIFF_SPARSE, 0.62
    elif in_(bar, BASS_LOW):
        cell, scale = None, 0.55
    elif in_(bar, BASS_FULL + BASS_BUILD):
        cell, scale = None, 1.0
    else:
        return []
    if cell is None:
        cell = RIFF_T if bar % 8 == 0 else (RIFF_A if bar % 2 else RIFF_B)
    out = []
    for s, p, ln, v in cell:
        if bar in (48, 96) + BREATHS and s >= 8:             # the bass leaves with the kick
            continue
        out.append([p, pos(s) + jit(1.5), ln * 0.25 * 0.88, vel(v * scale, 3)])
    return out


def crash(bar):
    v = {33: 78, 65: 112, 97: 84, 121: 118, 153: 80}.get(bar)
    return [[49, 0.0, 2.0, float(v)]] if v else []


MIDI_PARTS = {"CRASH": crash, "KICK": kick, "KICK HP": kick_hp, "CLAP": clap, "HAT OFF": hat_off, "HAT 16": hat_16,
              "BASS": bass}
PART_NAMES = {"CRASH": "crash on the section", "KICK": "kick 4x4", "KICK HP": "build kick (high-passed)", "CLAP": "clap 2+4 + ghosts",
              "HAT OFF": "off-beat hat", "HAT 16": "16th motor (swing 57.5)", "BASS": "bass riff Cm"}


def midi_clips(track, gen, envelope=None):
    """One clip per section, named by the section; `envelope(name, a, b)` -> envelope specs."""
    n = 0
    for name, a, b in SECTIONS:
        notes = []
        for bar in range(a, b):
            for p, t, ln, v in gen(bar):
                notes.append([p, round((bar - a) * 4 + max(0.0, t), 4), round(ln, 4), v])
        if not notes:
            continue
        args = {"track": track, "bar": a, "length": (b - a) * 4, "notes": notes,
                "name": "%s | %s" % (PART_NAMES[track], name.split(" - ")[0])}
        env = envelope(name, a, b) if envelope else None
        if env:
            args["envelopes"] = env
        r = C("create_midi_clip", args)
        if r.get("envelopes_lost"):
            log("  !! envelopes lost on", track, name, r.get("envelopes_lost"))
        n += len(notes)
    return n


def bass_envelope(name, a, b):
    """Drift's filters per section: his 310 Hz low-pass in the grooves, darker under the breaks;
    its high-pass at 220 Hz through the builds (the riff without its sub). Every clip holds both."""
    lp = "170 Hz" if in_(a, BASS_LOW + BASS_SPARSE) else "310 Hz"
    hp = "220 Hz" if in_(a, BASS_BUILD) else "10.0 Hz"
    n = (b - a) * 4
    return [{"param": "LP Freq", "device": "Drift", "unit": "display", "points": [[0, lp], [n, lp]], "resolution": 4.0},
            {"param": "HP Freq", "device": "Drift", "unit": "display", "points": [[0, hp], [n, hp]], "resolution": 4.0}]


# --------------------------------------------------------------------------- audio
def hz(v):
    return "%.0f Hz" % v if v < 1000 else "%.2f kHz" % (v / 1000.0)


def at(points, x):
    """Geometric interpolation of (bar offset, Hz) points."""
    for (x0, v0), (x1, v1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            f = (x - x0) / float(x1 - x0)
            return v0 * (v1 / v0) ** f
    return points[-1][1] if x > points[-1][0] else points[0][1]


def swing_loop(track, at_beat, file_beats, file_s, odd_steps):
    """Move a straight loop's odd-16th hits onto the set's swing: each hit's body (from just before
    its attack to 1.5 steps after) shifts late as a block; the stretch falls in the gaps around it.
    odd_steps: per bar of the file, the odd steps that carry a hit."""
    sw16 = SW * 4.0
    spb = file_s / file_beats
    m = [[0.0, 0.0]]
    for bar in range(int(file_beats // 4)):
        for k in odd_steps[bar % len(odd_steps)]:
            x = bar * 16 + k
            for s16, d in ((x - 1.6, 0.0), (x - 0.6, sw16), (x + 1.5, sw16), (x + 2.5, 0.0)):
                if s16 + d < file_beats * 4 - 0.1:
                    m.append([(s16 + d) / 4.0, s16 / 4.0 * spb])
    m.append([float(file_beats), file_s])
    C("set_warp_markers", {"track": track, "clip": {"at": at_beat}, "markers": m})


SYNTH_ODD = [(7, 13), (7,)]                                # stabs 0/4/7/10/13 | 0/4/7/10/14
PERC_ODD = [(7,)]                                          # hits (0)/2/4/7/10


def build_synth():
    """His Cm9 loop (4 bars), disclosed in stages: a dark hint in break 1, opening through the
    build, open in the drops, half-open under the main break, closing in the outro. The filter
    is a clip envelope, so every 4-bar clip carries its own stretch of the curve."""
    t = "SYNTH"
    plan = [
        (33, 16, [(0, 420), (16, 750)], "synth | far, under the groove", None),
        (49, 8, [(0, 750), (8, 1100)], "synth | hint (dark)", None),
        (57, 8, [(0, 1100), (7.5, 7000), (8, 7000)], "synth | opening", 254.0),
        (65, 32, None, "synth | drop 1", None),
        (97, 16, [(0, 2500), (8, 1200), (16, 1600)], "synth | under the voices", None),
        (113, 8, [(0, 1600), (7.5, 9000), (8, 9000)], "synth | opening 2", 478.0),
        (121, 32, None, "synth | drop 2", None),
        (153, 8, [(0, 8000), (8, 450)], "synth | closing", None),
    ]
    for bar, bars, pts, name, stop in plan:
        chunks = range(0, bars, 4) if pts else (0,)
        for k in chunks:
            if pts:
                xs = sorted({k, k + 4} | {x for x, _ in pts if k < x < k + 4})
                env = [[(x - k) * 4.0, hz(at(pts, x))] for x in xs]
            else:
                env = [[0.0, "12.0 kHz"], [16.0, "12.0 kHz"]]
            r = C("create_audio_clip", {
                "gain_db": 3.0 if "opening" in name else 0.0,
                "track": t, "path": SYNTH_WAV, "beat": (bar + k - 1) * 4.0, "beats": 16, "warp": True,
                "warp_mode": "beats", "name": name, "length": 16.0,
                "envelopes": [{"param": "Frequency", "device": "Auto Filter", "unit": "display",
                               "points": env, "resolution": 0.5}]})
            swing_loop(t, (bar + k - 1) * 4.0, 16, 7.38463, SYNTH_ODD)
        if not pts:
            C("fill_range", {"track": t, "src_start_bar": bar, "src_end_bar": bar + 4,
                             "start_bar": bar + 4, "end_bar": bar + bars})
        if stop:
            C("trim_clip", {"track": t, "clip": {"at": (bar + bars - 5) * 4.0}, "end_beat": stop})


def build_perc():
    for bar, bars in ((25, 24), (53, 11.5), (73, 24), (97, 22.5), (121, 32), (153, 16)):
        start = (bar - 1) * 4.0
        C("create_audio_clip", {"track": "PERC LOOP", "path": PERC_WAV, "beat": start, "beats": 8,
                                "warp": True, "warp_mode": "beats", "name": "perc loop",
                                "length": 8.0})
        swing_loop("PERC LOOP", start, 8, 3.69231, PERC_ODD)
        info = C("get_track", {"track": "PERC LOOP", "max_clips": 400})
        here = [c for c in info["clips"] if abs(c["start"] - start) < 1e-3][0]
        end_bar = bar + bars
        if here["end"] < (end_bar - 1) * 4.0 - 1e-3:
            C("fill_range", {"track": "PERC LOOP", "src_start_bar": bar, "src_end_bar": bar + 2,
                             "start_bar": bar + 2, "end_bar": end_bar})


def piece(track, path, bar, src_beat, beats, name, warp_mode="complex_pro", gain_db=None):
    """`beats` of a 32-beat vocal file from `src_beat`, at `bar` (fractional bars allowed)."""
    start = (bar - 1) * 4.0
    args = {"track": track, "path": path, "beat": start, "beats": 32, "warp": True,
            "warp_mode": warp_mode, "name": name}
    if gain_db is not None:
        args["gain_db"] = gain_db
    C("create_audio_clip", args)
    C("set_clip", {"track": track, "clip": {"at": start}, "looping": True, "start_marker": src_beat,
                   "loop_start": src_beat, "loop_end": 32.0})
    if beats < 32.0 - 1e-6:                               # the clip keeps the file's 32 beats until cut
        C("trim_clip", {"track": track, "clip": {"at": start}, "end_beat": start + beats})


def build_voices():
    # VOX CALL (Vocal 14): a pick-up in the 2nd half of a bar landing on the next downbeat.
    # A = file bars 1-2, B = file bars 5-6. Never the same call twice in a row.
    for bar, src, nm in ((32, 0, "call A -> groove"), (40, 16, "call B"), (56, 0, "call A -> build"),
                         (136, 16, "call B (kick hole)"), (144, 0, "call A")):
        piece("VOX CALL", CALL_WAV, bar, src, 8, nm)
    # VOX HOOK (Vocal 11): four 2-bar cells (pick-up, landing); cell 4's 2nd bar is a full line.
    hook = [(64, 0, 8, "hook 1 a cappella -> DROP 1"), (72, 0, 16, "hook 1+2"), (78, 24, 8, "hook 4 (full line)"),
            (88, 16, 8, "hook 3"), (94, 24, 8, "hook 4 -> break"),
            (104, 0, 32, "hook, whole, in the break"),
            (120, 0, 8, "hook 1 a cappella -> DROP 2"), (128, 0, 16, "hook 1+2"), (134, 24, 8, "hook 4"),
            (146, 16, 8, "hook 3"), (150, 24, 8, "hook 4 -> outro")]
    for bar, src, beats, nm in hook:
        piece("VOX HOOK", HOOK_WAV, bar, src, beats, nm)
    # VOX TALK (Vocal 1): the 4-bar line opens the main break; his half-bar chop drives build 2
    # and, two beats after a call or hook lands, answers it (call and response between the voices).
    talk = [(97, 0, 14, "talk | line"), (101, 0, 14, "talk | line again"),
            (137, 0, 14, "talk | ad-lib under drop 2")]
    talk += [(b, 16, beats, "talk | chop (his) builds") for b, beats in
             ((117, 2), (118, 2), (119, 2), (119.5, 2), (120, 1.5))]
    talk += [(b + 0.5, 16, 2, "talk | answers the call") for b in (33, 41, 73, 75, 89, 129, 131, 147)]
    for bar, src, beats, nm in sorted(talk):
        piece("VOX TALK", TALK_WAV, bar, src, beats, nm)


def build_answer():
    """His own Cm stab (the loop's step 10), an octave up and short, on beat 4 of every 2nd bar:
    the one place where neither the loop nor the bass plays. Its 3/16 ping-pong echoes fall on
    steps 15, 2 and 5, between the stabs. Enters with drop 1's second half; all of drop 2."""
    t = "SYNTH ANSWER"
    bars = [b for b in list(range(82, 96, 2)) + list(range(122, 152, 2))]
    first = None
    for b in bars:
        dest = (b - 1) * 4.0 + 3.0 - 0.125               # its soft attack starts half a step early
        if first is None:
            C("create_audio_clip", {"track": t, "path": SYNTH_WAV, "beat": dest, "beats": 16, "warp": True,
                                    "warp_mode": "complex_pro", "pitch": 12, "name": "answer (his stab, 8va)"})
            C("set_clip", {"track": t, "clip": {"at": dest}, "looping": True, "start_marker": 2.375,
                           "loop_start": 2.375, "loop_end": 16.0})
            C("trim_clip", {"track": t, "clip": {"at": dest}, "end_beat": dest + 0.7})
            first = dest
        else:
            C("duplicate_clip", {"track": t, "clip": {"at": first}, "beat": dest})


def build_fx():
    for bar in (16, 48, 96, 152):
        start = (bar - 1) * 4.0
        C("create_audio_clip", {"track": "FX", "path": FX_WAV, "beat": start, "beats": 16,
                                "warp": True, "warp_mode": "beats", "name": "fx (his) into the turn"})


# --------------------------------------------------------------------------- set-up
def setp(track, device, param, v):
    args = {"track": track, "device": device, "param": param}
    if isinstance(v, float):
        args["value"] = v
    elif v[:1].isdigit() or v[:1] in "+-.":
        args["display"] = v
    else:
        args["item"] = v
    r = C("set_param", args)
    return r.get("display")


def setup():
    # Simpler's Vol < Vel adds level at high velocities (+16 dB at 100 %, +8 at 50 %, measured
    # soloed): the Volume takes it back so nothing leaves the instrument above ~-6 dBFS
    for t, vol, vv in (("KICK", "-6.0 dB", "0.0 %"), ("KICK HP", "-22.0 dB", "100 %"),
                       ("CLAP", "-24.0 dB", "80 %"), ("HAT OFF", "-12.0 dB", "50 %"),
                       ("HAT 16", "-18.0 dB", "100 %")):
        setp(t, 0, "Volume", vol)
        setp(t, 0, "Vol < Vel", vv)
    for p, v in (("1 Filter On A", 1.0), ("1 Filter Type A", "High Pass 48dB"), ("1 Frequency A", "180 Hz")):
        log("  KICK HP eq", p, setp("KICK HP", "EQ Eight", p, v))
    # the sub an octave under the saw sat at 32.7 Hz, under what a club system plays: same octave
    log("  bass Osc 2 Oct ->", setp("BASS", "Drift", "Osc 2 Oct", "0"))
    # his patch was a pluck (sustain 34 %, peak 14 dB over its body) sitting 15 LU under the kick:
    # hold the body for the note's length and let his Saturator shave the attack instead of a fader
    for dev, p, v in (("Drift", "Env 1 Sustain", "70 %"), ("Saturator", "Drive", "12.0 dB"),
                      ("Saturator", "Output", "-8.0 dB")):
        log("  bass", p, setp("BASS", dev, p, v))
    # his compressor was pointed at the old kick with its sidechain off: key it from the new one
    C("set_device_input", {"track": "BASS", "device": "Compressor-1", "source": "KICK", "channel": "Post FX"})
    for p, v in (("S/C On", 1.0), ("S/C EQ On", 0.0), ("Threshold", "-16.0 dB"), ("Ratio", 0.8333),
                 ("Attack", "0.10 ms"), ("Release", "110 ms")):
        log("  bass comp", p, setp("BASS", "Compressor-1", p, v))
    for p, v in (("Filter Type", "Low-pass"), ("Frequency", "12.0 kHz")):
        log("  synth filter", p, setp("SYNTH", "Auto Filter", p, v))
    # set from the soloed pass over drop bars 73-81 (LU against the kick, which peaks at -10 dBFS):
    # clap -9, hats -15/-16, bass -3, synth -12, hook voice -10
    faders = {"KICK": -4.0, "KICK HP": -9.0, "CLAP": -4.5, "HAT OFF": -6.0, "HAT 16": -4.0,
              "BASS": -2.0, "SYNTH": -14.0, "PERC LOOP": -12.0, "VOX CALL": -7.5, "VOX HOOK": -11.0,
              "VOX TALK": -13.0, "FX": -22.0}
    # v3 soloed: HAT OFF read -11 LU and the perc loop and clap peaked over the kick (-9.3 / -9.5
    # against -10.1 dBFS): nothing peaks above the kick
    faders.update({"HAT 16": -9.5, "SYNTH ANSWER": -12.0, "CRASH": -14.0, "HAT OFF": -8.0,
                   "SYNTH": -12.5, "BASS": -3.5, "KICK HP": -2.0, "PERC LOOP": -15.5, "CLAP": -6.0})
    pans = {"HAT OFF": -0.12, "HAT 16": 0.15, "PERC LOOP": 0.2, "SYNTH ANSWER": -0.25}
    for t, db in faders.items():
        C("set_track", {"track": t, "volume_db": db, "pan": pans.get(t, 0.0)})
    mix()


def devs(track):
    return [d["name"] for d in C("get_track", {"track": track, "clips": False})["devices"]]


# high-pass per element: (slope, Hz). Nothing here is a bass part; the synth's lowest note is G3.
HP = {"SYNTH": ("High Pass 12dB", "120 Hz"), "SYNTH ANSWER": ("High Pass 48dB", "350 Hz"),
      "VOX CALL": ("High Pass 12dB", "120 Hz"), "VOX HOOK": ("High Pass 12dB", "120 Hz"),
      "VOX TALK": ("High Pass 12dB", "120 Hz"), "PERC LOOP": ("High Pass 12dB", "200 Hz"),
      "HAT OFF": ("High Pass 12dB", "300 Hz"), "HAT 16": ("High Pass 12dB", "400 Hz"),
      "CLAP": ("High Pass 12dB", "150 Hz"), "CRASH": ("High Pass 12dB", "300 Hz")}
# sends in dB: (A plate, B ping-pong delay)
SENDS = {"CLAP": (-24.0, None), "HAT OFF": (-30.0, None), "CRASH": (-16.0, None), "SYNTH": (-24.0, None),
         "SYNTH ANSWER": (-14.0, -8.0), "VOX CALL": (-16.0, -24.0), "VOX HOOK": (-16.0, -24.0),
         "VOX TALK": (-16.0, -24.0)}                      # one space for every voice
DRUM_BUS = ["CLAP", "HAT OFF", "HAT 16", "PERC LOOP", "CRASH"]
ROOM = {"CLAP": -20.0, "HAT OFF": -21.0, "HAT 16": -22.0, "PERC LOOP": -20.0, "CRASH": -20.0}
MUSIC_BUS = ["SYNTH", "SYNTH ANSWER"]
ROOM_REVERB = "audio_effects/Reverb"


def mix():
    for t, (slope, f) in HP.items():
        if "EQ Eight" not in devs(t):
            C("load_device", {"track": t, "query": "EQ Eight", "roots": ["audio_effects"]})
        setp(t, "EQ Eight", "1 Filter On A", 1.0)
        setp(t, "EQ Eight", "1 Filter Type A", slope)
        log("  hp %-12s %s" % (t, setp(t, "EQ Eight", "1 Frequency A", f)))
    for t, (a, b) in SENDS.items():
        C("set_send", {"track": t, "send": 0, "db": a})
        if b is not None:
            C("set_send", {"track": t, "send": 1, "db": b})
    # his returns: the 2.5 s reverb becomes the one short plate; the delay a filtered 3/16 ping-pong
    log("  plate", setp("return:0", 0, "Decay Time", "1.40 s"))
    for p, v in (("Ping Pong", "On"), ("Filter On", "On"), ("Feedback", "42 %")):
        log("  delay", p, setp("return:1", 0, p, v))
    for t in DRUM_BUS:
        C("set_track_output", {"track": t, "dest": "DRUMS"})
    # v2 check: the top of the mix was 8 dB short of the references (dull hat samples): air on the
    # drum bus and presence on the synth, in the elements, not on the master
    for t, f, g in (("DRUMS", "7.00 kHz", "5.0 dB"), ("SYNTH", "2.50 kHz", "3.0 dB")):
        setp(t, "EQ Eight", "4 Filter On A", 1.0)
        setp(t, "EQ Eight", "4 Filter Type A", "High Shelf")
        setp(t, "EQ Eight", "4 Frequency A", f)
        log("  shelf %-6s %s" % (t, setp(t, "EQ Eight", "4 Gain A", g)))
    # "colar mais a bateria": his DRUMS recipe (Glue 2:1 10 ms, soft-sine saturation in parallel)
    # and one short room for every drum. Glue's Attack/Release are steps (raw 5 = 10 ms, 6 = Auto)
    for p, v in (("Ratio", "2"), ("Attack", 5.0), ("Release", 6.0), ("Range", "4.00 dB"),
                 ("Threshold", "-22.0 dB"), ("Output", "1.5 dB")):
        log("  glue", p, setp("DRUMS", "Glue Compressor", p, v))
    if "Saturator" not in devs("DRUMS"):
        C("load_device", {"track": "DRUMS", "query": "Saturator", "roots": ["audio_effects"]})
    for p, v in (("Type", "Soft Sine"), ("Drive", "2.0 dB"), ("Dry/Wet", "35 %")):
        log("  drums sat", p, setp("DRUMS", "Saturator", p, v))
    if len(C("get_song")["returns"]) < 3:
        C("create_return", {"name": "Room"})
        C("load_device", {"track": "return:2", "path": ROOM_REVERB})   # the query finds Hybrid Reverb first
    for p, v in (("Decay Time", "800 ms"), ("Dry/Wet", "100 %"), ("Predelay", "8.00 ms")):
        log("  room", p, setp("return:2", 0, p, v))
    for t, db in ROOM.items():
        C("set_send", {"track": t, "send": 2, "db": db})
    # "trabalhar a música em conjunto": the synths on one bus that breathes with the kick (~3 dB)
    if "MUSIC" not in [t["name"] for t in C("get_song")["tracks"]]:
        i = [t["name"] for t in C("get_song")["tracks"]].index("SYNTH ANSWER") + 1
        C("create_track", {"kind": "audio", "name": "MUSIC", "index": i})
        C("set_track_input", {"track": "MUSIC", "source": "No Input"})
        C("set_track", {"track": "MUSIC", "monitoring": "in", "volume_db": 0.0})
    if "Compressor" not in devs("MUSIC"):
        C("load_device", {"track": "MUSIC", "query": "Compressor", "roots": ["audio_effects"]})
    C("set_device_input", {"track": "MUSIC", "device": "Compressor", "source": "KICK", "channel": "Post FX"})
    for p, v in (("S/C On", 1.0), ("S/C EQ On", 0.0), ("Ratio", 0.6667), ("Threshold", "-11.0 dB"),
                 ("Attack", "1.00 ms"), ("Release", "90.0 ms")):
        log("  music duck", p, setp("MUSIC", "Compressor", p, v))
    for t in MUSIC_BUS:
        C("set_track_output", {"track": t, "dest": "MUSIC"})
    for p, v in (("Mode", "True Peak"), ("Ceiling", "-1.0 dB"), ("Input Gain", "6.0 dB")):
        log("  master limiter", p, setp("master", "Limiter", p, v))


def clear():
    for t in list(MIDI_PARTS) + ["SYNTH", "SYNTH ANSWER", "PERC LOOP", "VOX CALL", "VOX HOOK", "VOX TALK", "FX"]:
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": 400})


def cues():
    C("clear_cues")
    for name, a, _ in SECTIONS:
        C("set_cue", {"name": name, "bar": a})


def main(only=None):
    C("transport", {"action": "stop"})
    if only in (None, "setup"):
        setup()
    if only and only.startswith("midi:"):                    # one MIDI part again, e.g. midi:BASS
        t = only[5:]
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": 400})
        log("  %-8s %d notes" % (t, midi_clips(t, MIDI_PARTS[t], bass_envelope if t == "BASS" else None)))
    if only in (None, "clips"):
        clear()
        for t, gen in MIDI_PARTS.items():
            n = midi_clips(t, gen, bass_envelope if t == "BASS" else None)
            log("  %-8s %d notes" % (t, n))
        build_synth()
        log("  synth placed")
        build_perc()
        log("  perc placed")
        build_answer()
        log("  answers placed")
    if only in (None, "clips", "voices"):
        for t in ("VOX CALL", "VOX HOOK", "VOX TALK", "FX"):
            C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": 400})
        build_voices()
        log("  voices placed")
        build_fx()
        cues()
    song = C("get_song")
    for t in song["tracks"]:
        log("  %-10s vol %6.1f clips %3d bars %s" % (t["name"], t["vol_db"], t["clips_active"], t.get("bars")))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
