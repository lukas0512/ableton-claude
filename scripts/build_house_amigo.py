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
SOLO_BAR = 120                                 # v6: the whole track stops, the acid calls alone
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
KICK_BARS = ((9, 49), (65, 97), (121, 177))     # bars 1-8 and 177-184: the high-passed kick (DJ, energy arc)
KICK_EXITS = {16: (0, 4), 32: (0, 8), 48: (0, 4), 80: (0, 4, 8), 96: (0, 4, 8), 136: (0, 4, 8)}


def kick(bar):
    if not in_(bar, KICK_BARS):
        return []
    return [[60, s * 0.25, 0.5, 127.0] for s in KICK_EXITS.get(bar, (0, 4, 8, 12))]


def kick_hp(bar):
    """The build's kick, high-passed on its channel: quarters, 8ths, 16ths, then the breath."""
    plan = {b: (4, 118, 118) for b in list(range(1, 9)) + list(range(177, 185))}
    plan.update({57: (4, 56, 66), 58: (4, 66, 76), 59: (4, 76, 86), 60: (4, 86, 96),
            61: (4, 96, 104), 62: (4, 104, 110), 63: (2, 104, 116), 64: (1, 108, 124),
            113: (4, 50, 60), 114: (4, 60, 70), 115: (4, 70, 80), 116: (4, 80, 90),
            117: (4, 90, 100), 118: (2, 100, 112), 119: (1, 108, 124)})
    if bar not in plan or bar == SOLO_BAR:
        return []
    every, v0, v1 = plan[bar]
    steps = [s for s in range(0, 16, every) if not (bar in BREATHS and s >= 8)]
    return [[60, pos(s), 0.2, float(round(v0 + (v1 - v0) * i / max(1, len(steps) - 1)))]
            for i, s in enumerate(steps)]


def clap(bar):
    if bar < 9 or bar >= 181 or bar == SOLO_BAR:
        return []
    late = 5 * MS
    out = []
    back = (12,) if 97 <= bar < 105 else (4, 12)          # half-time in the main break's first half
    for s in back:
        if bar in BREATHS and s >= 8:
            continue
        out.append([60, s * 0.25 + late, 0.4, vel(120, 3)])
    if bar < 17 or in_(bar, ((49, 53), (97, 105))) or bar in BREATHS:
        return out
    ghosts = {2: ((15, 44),), 3: ((7, 38),), 0: ((11, 50), (15, 58))}.get(bar % 4, ())
    if bar % 8 == 0:
        ghosts = ((11, 50), (14, 66), (15, 82))              # a two-note pickup, not a roll
    for s, v in ghosts:
        out.append([60, pos(s) + late + jit(), 0.2, vel(v, 4)])
    return out


def hat_off(bar):
    if bar < 5 or bar >= 181 or 97 <= bar < 105 or bar == SOLO_BAR:
        return []
    out = []
    for s, v in ((2, 104), (6, 96), (10, 108), (14, 98)):
        if bar in BREATHS and s >= 8:
            continue
        out.append([60, s * 0.25 + jit(1.5), 0.3, vel(v, 4)])
    return out


def hat_16(bar):
    """v3 ("o midi dele, a forma que está desenhado, não está no mesmo groove e swing da música"):
    v1-v2 played beat + e + a and skipped the "&", with a loud "a", pockets and 32nd flutters: a
    lopsided gallop against the stabs. Now one continuous 16th line like the references' (the "&"
    the accent, e/a ~7 dB under it, the on-beats ghosted under the kick), nothing dropped."""
    if bar < 13 or bar >= 173 or 49 <= bar < 53 or bar == SOLO_BAR:
        return []
    lift = 8 if in_(bar, (DROPS[1],)) else 0
    out = []
    for s in range(16):
        if bar in BREATHS and s >= 8:
            break
        v = {0: 46, 1: 58, 2: 84, 3: 66}[s % 4] + lift
        if bar % 4 == 0 and s == 15:
            v += 14                                          # a small push into the next phrase
        out.append([60, pos(s) + jit(1.2), 0.2, vel(v, 4)])
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
BASS_FULL = ((17, 49), (65, 97), (121, 161))
BASS_LOW = ((49, 57), (105, 113))                         # under a break: quieter, darker
BASS_SPARSE = ((97, 105),)
BASS_BUILD = ((57, 65), (113, 121))                       # the riff high-passed: the sub is the drop's


def bass(bar):
    if bar == SOLO_BAR:
        return []
    if in_(bar, BASS_SPARSE):
        cell, scale = RIFF_SPARSE, 0.5
    elif in_(bar, BASS_LOW):
        cell, scale = None, 0.42                             # v4: the break bass sat only 3.8 dB down (refs 10-27)
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


# v4 tried his Cm stab in a Simpler as a played lead (parallel Cm/Dm/Gm chords, 3-4 hits a bar).
# He: "não colou muito no resto da track... tem que ser algo mais simples, o baixo e o outro synth já
# são bem complexos, a track tem que ser coerente". Removed. v5: one slow line of long notes over
# the two busy parts, on a clone of the bass's own Drift (same family), D - Eb - D - C - Bb over 8 bars:
# D is Gm's 5th and Cm's 9th, Eb the tension that Cm resolves. (bar of the phrase, pitch, bars long)
PAD_PHRASE = [(1, 74, 2), (3, 75, 2), (5, 74, 2), (7, 72, 1), (8, 70, 1)]
PAD_BUILD = [(1, 74, 4), (5, 77, 2), (7, 79, 2)]              # build 2: D, F, G, up into the drop
PAD_SPANS = {(81, 97): 70, (97, 113): 100, (121, 153): 88, (153, 161): 58}   # span: velocity


def pad(bar):
    if 113 <= bar < 121:
        cell, r, v = PAD_BUILD, bar - 113, 96
    else:
        span = [k for k in PAD_SPANS if k[0] <= bar < k[1]]
        if not span:
            return []
        cell, r, v = PAD_PHRASE, (bar - span[0][0]) % 8, PAD_SPANS[span[0]]
    out = []
    for b0, p, n in cell:
        if b0 - 1 == r:
            ln = n * 4.0 - 0.15
            if bar + n - 1 == SOLO_BAR:
                ln = (n - 1) * 4.0 - 0.1
            elif bar + n - 1 in BREATHS:
                ln = n * 4.0 - 2.0
            out.append([p, 0.0, ln, float(v)])
    return out


# v6 ("podia até ser um ácido, algo que entrasse na melodia, alternasse e conversasse com o synth
# que é o main da track... um detalhe complementar" and "um pré-drop no drop 2 com um synth
# característico, uma chamadinha"): one five-note acid cell, G G Bb G' G, in the gaps of the 2nd
# half of a bar (never on the stabs at 10 and 13|14). It is hinted dark in the main break, calls
# alone for one bar before drop 2 (twice, its filter opening), then answers the synth every 2nd bar.
ACID_CELL = [(8, 55, 90), (9, 55, 70), (11, 58, 100), (12, 67, 124), (15, 55, 84)]
ACID_BARS = {108: 0.75, 112: 0.8, 154: 0.8, 158: 0.7}
ACID_BARS.update({b: 1.0 for b in range(122, 153, 2)})


def acid(bar):
    if bar == SOLO_BAR:
        cells = [(s - 8, p, v) for s, p, v in ACID_CELL] + ACID_CELL
        scale = 1.0
    elif bar in ACID_BARS:
        cells, scale = ACID_CELL, ACID_BARS[bar]
    else:
        return []
    return [[p, pos(s) + jit(1.0), 0.2, vel(v * scale, 3)] for s, p, v in cells]


def acid_envelope(name, a, b):
    """Operator's filter per section (every clip holds one): dark in the break, rising through
    the solo bar, open enough to speak in the drop."""
    n = (b - a) * 4.0
    if a <= SOLO_BAR < b:
        x = (SOLO_BAR - a) * 4.0
        pts = [[0, "40.0 Hz"], [x, "40.0 Hz"], [x + 3.75, "450 Hz"], [n, "450 Hz"]]
    else:
        f = "30.0 Hz" if a < SOLO_BAR else ("90.0 Hz" if a < 153 else "45.0 Hz")
        pts = [[0, f], [n, f]]
    return [{"param": "Filter Freq", "device": 0, "unit": "display", "points": pts, "resolution": 0.25}]


MIDI_PARTS = {"ACID": acid, "PAD": pad, "PAD B": pad, "CRASH": crash, "KICK": kick, "KICK HP": kick_hp, "CLAP": clap, "HAT OFF": hat_off, "HAT 16": hat_16,
              "BASS": bass}
PART_NAMES = {"ACID": "acid cell G G Bb G' G", "PAD": "long line D-Eb-D-C-Bb", "PAD B": "long line (other timbre, muted)", "CRASH": "crash on the section", "KICK": "kick 4x4", "KICK HP": "build kick (high-passed)", "CLAP": "clap 2+4 + ghosts",
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
    lp = "200 Hz" if in_(a, BASS_LOW + BASS_SPARSE) else "420 Hz"   # v4: harmonics -12.4 dB (refs -10..-7)
    hp = "220 Hz" if in_(a, BASS_BUILD) else "10.0 Hz"
    n = (b - a) * 4
    return [{"param": "LP Freq", "device": "Drift", "unit": "display", "points": [[0, lp], [n, lp]], "resolution": 4.0},
            {"param": "HP Freq", "device": "Drift", "unit": "display", "points": [[0, hp], [n, hp]], "resolution": 4.0}]


ENVELOPES = {"BASS": bass_envelope, "ACID": acid_envelope}


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
        (33, 16, [(0, 450), (16, 1100)], "synth | far, under the groove", None),
        (49, 8, [(0, 1100), (8, 1800)], "synth | hint (dark)", None),
        (57, 8, [(0, 1800), (7.5, 8000), (8, 8000)], "synth | opening", 254.0),
        (65, 32, None, "synth | drop 1", None),
        (97, 16, [(0, 4000), (8, 2500), (16, 3000)], "synth | under the voices", None),
        (113, 8, [(0, 3000), (7.5, 10000), (8, 10000)], "synth | opening 2", 476.0),
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
                "gain_db": 2.5 if "opening" in name else 0.0,   # builds start at the break's level; +5 peaked over the kick
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
    for bar, bars in ((25, 24), (53, 11.5), (73, 24), (97, 23), (121, 32), (153, 16)):
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
            (128, 0, 16, "hook 1+2"),      # drop 2's pre-drop is the acid's, not the voice's (134, 24, 8, "hook 4"),
            (146, 16, 8, "hook 3"), (150, 24, 8, "hook 4 -> outro")]
    for bar, src, beats, nm in hook:
        piece("VOX HOOK", HOOK_WAV, bar, src, beats, nm)
    # VOX TALK (Vocal 1): the 4-bar line opens the main break; his half-bar chop drives build 2
    # and, two beats after a call or hook lands, answers it (call and response between the voices).
    talk = [(97, 0, 14, "talk | line"), (101, 0, 14, "talk | line again"),
            (137, 0, 14, "talk | ad-lib under drop 2")]
    talk += [(b, 16, beats, "talk | chop (his) builds") for b, beats in
             ((117, 2), (118, 2), (119, 2), (119.5, 2))]
    talk += [(b + 0.5, 16, 2, "talk | answers the call") for b in (33, 41, 73, 75, 89, 129, 131, 147)]
    for bar, src, beats, nm in sorted(talk):
        piece("VOX TALK", TALK_WAV, bar, src, beats, nm)


def build_answer():
    """His own Cm stab (the loop's step 10), an octave up and short, on beat 4 of every 2nd bar:
    the one place where neither the loop nor the bass plays. Its 3/16 ping-pong echoes fall on
    steps 15, 2 and 5, between the stabs. Enters with drop 1's second half; all of drop 2
    (he liked it: "gostei do synth answer")."""
    t = "SYNTH ANSWER"
    bars = list(range(82, 96, 2))                          # in drop 2 the acid is the answer
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


OWN = os.path.expanduser("~/Music/Ableton/User Library/Samples/Claude/House Amigo/")
CRASH_AIF = ("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Samples/"
             "One Shots/Drums/Cymbal/Crash 909.aif")
TWO_BARS_S = 8 * 60.0 / BPM


def make_fx():
    """FX made from the track's own sounds, printed at 128 BPM (placed unwarped):
    rev stab = his Gm stab through a 2.2 s tail, reversed, 2 bars rising to the bar line;
    rev crash = the 909 crash reversed over 2 bars; sub boom = a G1 sine falling from G2."""
    import numpy as np
    import soundfile as sf
    rng = np.random.default_rng(3)
    x, sr = sf.read(SYNTH_WAV, always_2d=True)
    spb = len(x) / sr / 16.0
    stab = x[int(3.5 / 4 * spb * sr):int(6.4 / 4 * spb * sr)].copy()
    stab[-int(0.02 * sr):] *= np.linspace(1, 0, int(0.02 * sr))[:, None]
    n = int(TWO_BARS_S * sr)
    t = np.arange(int(2.6 * sr)) / sr
    out = np.zeros((n, 2))
    for ch in range(2):
        ir = rng.standard_normal(len(t)) * np.exp(-t / 0.55)
        k = int(sr / 6000.0)                                   # darken the tail
        ir = np.convolve(ir, np.ones(k) / k, "same")
        wet = np.convolve(stab[:, ch], ir)[:n]
        out[:len(wet), ch] = wet
    out = out[::-1] * np.linspace(0.0, 1.0, n)[:, None] ** 1.5
    out[-int(0.01 * sr):] *= np.linspace(1, 0, int(0.01 * sr))[:, None]
    sf.write(OWN + "rev stab Gm 2 bars.wav", out / np.abs(out).max() * 0.5, sr, subtype="PCM_24")
    c, csr = sf.read(CRASH_AIF, always_2d=True)
    c = c[:int(TWO_BARS_S * csr)][::-1]
    pad_ = np.zeros((int(TWO_BARS_S * csr) - len(c), c.shape[1]))
    c = np.vstack([pad_, c]) * np.linspace(0.0, 1.0, int(TWO_BARS_S * csr))[:, None] ** 2
    c[-int(0.005 * csr):] *= np.linspace(1, 0, int(0.005 * csr))[:, None]
    sf.write(OWN + "rev crash 909 2 bars.wav", c / np.abs(c).max() * 0.5, csr, subtype="PCM_24")
    tb = np.arange(int(1.6 * sr)) / sr
    f = 49.0 + 49.0 * np.exp(-tb / 0.03)
    boom = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tb / 0.45)
    boom[:int(0.004 * sr)] *= np.linspace(0, 1, int(0.004 * sr))
    sf.write(OWN + "sub boom G1.wav", np.tanh(boom * 1.5) * 0.5, sr, subtype="PCM_24")


def new_tracks():
    names = [t["name"] for t in C("get_song")["tracks"]]
    if "SYNTH LEAD" in names:
        C("delete_track", {"track": "SYNTH LEAD"})           # the rejected v4 lead
    for name, src in (("PAD", "instruments/Drift"), ("PAD B", "sounds/Pad/Basic Mellow Pad.adg")):
        if name not in [t["name"] for t in C("get_song")["tracks"]]:
            i = [t["name"] for t in C("get_song")["tracks"]].index("SYNTH ANSWER") + 1
            C("create_track", {"kind": "midi", "name": name, "index": i})
            C("load_device", {"track": name, "path": src})
    # PAD: the bass's own Drift patch, re-voiced as a soft held tone (same family, another role)
    C("copy_device", {"src_track": "BASS", "src_device": "Drift", "track": "PAD", "device": 0})
    for p, v in (("LP Freq", "1.40 kHz"), ("LP Mod Amt 1", "0.0 %"), ("LP Mod Amt 2", "0.0 %"),
                 ("Env 1 Attack", "180 ms"), ("Env 1 Decay", "1.00 s"), ("Env 1 Sustain", "85 %"),
                 ("Env 1 Release", "500 ms"), ("Vel > Vol", "20 %"), ("Osc 2 Oct", "0"),
                 ("Thickness", "30 %"), ("Volume", "-6.0 dB")):
        try:
            log("  pad", p, setp("PAD", 0, p, v))
        except Exception as e:
            log("  pad:", p, str(e).splitlines()[0])
    C("set_track", {"track": "PAD B", "mute": True})          # the alternative timbre, same notes
    if "ACID" not in [t["name"] for t in C("get_song")["tracks"]]:
        i = [t["name"] for t in C("get_song")["tracks"]].index("PAD") + 1
        C("create_track", {"kind": "midi", "name": "ACID", "index": i})
        C("load_device", {"track": "ACID", "path": "sounds/Bass/Acid Bass.adv"})
    # Live's Acid Bass (Operator): velocity opens the filter (accents); a shorter squelch
    for p, v in (("Fe Decay", "320 ms"), ("Filter Res", "62 %"), ("Volume", "-12 dB")):
        try:
            log("  acid", p, setp("ACID", 0, p, v))
        except Exception as e:
            log("  acid:", p, str(e).splitlines()[0])
    for name in ("FX REV", "FX REV CRASH", "FX BOOM"):
        if name not in [t["name"] for t in C("get_song")["tracks"]]:
            i = [t["name"] for t in C("get_song")["tracks"]].index("FX") + 1
            C("create_track", {"kind": "audio", "name": name, "index": i})


def build_fx2():
    """Reverse swells into the phrase starts and the drops, a sub boom under each drop."""
    for t in ("FX REV", "FX REV CRASH", "FX BOOM"):
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": 400})
    for bar in (33, 65, 81, 97, 121, 137, 153):               # the swell ends on this bar line
        C("create_audio_clip", {"track": "FX REV", "path": OWN + "rev stab Gm 2 bars.wav", "bar": bar - 2,
                                "warp": False, "name": "rev stab (his Gm) -> %d" % bar,
                                "gain_db": 0.0 if bar in (65, 121) else -4.0})
    for bar in (65, 121):
        C("create_audio_clip", {"track": "FX REV CRASH", "path": OWN + "rev crash 909 2 bars.wav",
                                "bar": bar - 2, "warp": False, "name": "rev crash -> drop"})
        C("create_audio_clip", {"track": "FX BOOM", "path": OWN + "sub boom G1.wav", "bar": bar,
                                "warp": False, "name": "sub boom G1"})


def setup():
    make_fx()
    new_tracks()
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
    faders.update({"ACID": -15.0,                          # soloed -10.3 LU at -12: a detail sits ~-13 "PAD": -16.0, "PAD B": -16.0, "FX REV": -15.0, "FX BOOM": -11.0, "FX REV CRASH": -20.0})
    faders.update({"HAT 16": -9.5, "SYNTH ANSWER": -12.0, "CRASH": -14.0, "HAT OFF": -8.0,
                   "SYNTH": -12.5, "BASS": -3.5, "KICK HP": -2.0, "PERC LOOP": -15.5, "CLAP": -6.0})
    pans = {"HAT OFF": -0.12, "HAT 16": 0.15, "PERC LOOP": 0.2, "SYNTH ANSWER": -0.25}
    # v4 full render against dub_house_streets: kick over bass 4.0 dB (refs 5-8.5), clap backbeat
    # +13 dB (5-10.7), hats -19.8 (-18..-16.4), mids 2.6 % (3.5-4.5), high-mids 1.5 % (3.0-3.4)
    faders.update({"BASS": -5.0, "CLAP": -8.0, "HAT OFF": -6.5, "HAT 16": -8.0, "SYNTH": -10.5,
                   "VOX CALL": -6.0, "VOX HOOK": -9.5, "VOX TALK": -11.5})
    for t, db in faders.items():
        C("set_track", {"track": t, "volume_db": db, "pan": pans.get(t, 0.0)})
    mix()


def devs(track):
    return [d["name"] for d in C("get_track", {"track": track, "clips": False})["devices"]]


# high-pass per element: (slope, Hz). Nothing here is a bass part; the synth's lowest note is G3.
HP = {"SYNTH": ("High Pass 12dB", "120 Hz"), "SYNTH ANSWER": ("High Pass 48dB", "350 Hz"),
      "ACID": ("High Pass 12dB", "150 Hz"), "PAD": ("High Pass 12dB", "250 Hz"), "PAD B": ("High Pass 12dB", "250 Hz"),
      "FX REV": ("High Pass 12dB", "300 Hz"),
      "VOX CALL": ("High Pass 12dB", "120 Hz"), "VOX HOOK": ("High Pass 12dB", "120 Hz"),
      "VOX TALK": ("High Pass 12dB", "120 Hz"), "PERC LOOP": ("High Pass 12dB", "200 Hz"),
      "HAT OFF": ("High Pass 12dB", "300 Hz"), "HAT 16": ("High Pass 12dB", "400 Hz"),
      "CLAP": ("High Pass 12dB", "150 Hz"), "CRASH": ("High Pass 12dB", "300 Hz")}
# sends in dB: (A plate, B ping-pong delay)
SENDS = {"CLAP": (-24.0, None), "HAT OFF": (-30.0, None), "CRASH": (-16.0, None), "SYNTH": (-24.0, None),
         "SYNTH ANSWER": (-14.0, -8.0), "ACID": (-18.0, -14.0), "PAD": (-14.0, None), "PAD B": (-14.0, None),
         "FX REV": (-18.0, None), "VOX CALL": (-16.0, -24.0), "VOX HOOK": (-16.0, -24.0),
         "VOX TALK": (-16.0, -24.0)}                      # one space for every voice
DRUM_BUS = ["CLAP", "HAT OFF", "HAT 16", "PERC LOOP", "CRASH"]
ROOM = {"CLAP": -16.0, "HAT OFF": -21.0, "HAT 16": -22.0, "PERC LOOP": -20.0, "CRASH": -20.0}
MUSIC_BUS = ["SYNTH", "SYNTH ANSWER", "PAD", "PAD B", "ACID"]
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
    # v4: with the hat line approved, the top was still 0.6 % of the mix (references ~2.7 %): his
    # hat samples are dark (Hat 14 centres at 5 kHz), so each element gets its own shelf
    for t, f, g in (("DRUMS", "7.00 kHz", "5.0 dB"), ("SYNTH", "2.50 kHz", "3.0 dB"),
                    ("HAT OFF", "6.00 kHz", "4.0 dB"), ("HAT 16", "8.00 kHz", "3.0 dB"),
                    ("CLAP", "5.00 kHz", "2.0 dB"), ("VOX CALL", "4.00 kHz", "2.0 dB"),
                    ("VOX HOOK", "4.00 kHz", "2.0 dB"), ("VOX TALK", "4.00 kHz", "2.0 dB")):
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
    # v4: width above the bass read -13 dB side/mid (refs -8..-6): widen the music, nothing else
    if "Utility" not in devs("MUSIC"):
        C("load_device", {"track": "MUSIC", "query": "Utility", "roots": ["audio_effects"]})
    log("  music width", setp("MUSIC", "Utility", "Stereo Width", "150 %"))
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
        log("  %-8s %d notes" % (t, midi_clips(t, MIDI_PARTS[t], ENVELOPES.get(t))))
    if only == "fx2":
        build_fx2()
    if only == "answer":
        C("delete_clips_in_range", {"track": "SYNTH ANSWER", "start_bar": 1, "end_bar": 400})
        build_answer()
    if only in (None, "clips"):
        clear()
        for t, gen in MIDI_PARTS.items():
            n = midi_clips(t, gen, ENVELOPES.get(t))
            log("  %-8s %d notes" % (t, n))
        build_synth()
        log("  synth placed")
        build_perc()
        log("  perc placed")
        build_answer()
        log("  answers placed")
        build_fx2()
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
