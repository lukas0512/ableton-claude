"""Mochakk C: an original groove-first house track after the Mochakk Mixmag Lab Mocambique
set (2026-10-30). Reference = the track at 17:10 (cut alone 17:19-22:32 by reference_from_set),
direction A: C with the bass's half-step push (Db, Ab) under a C major colour; the whole set's
12 tracks studied as `mochakk_set` give the feel.

The producer's brief: "abuse do bounce, com hats percs e etc, groove, a track precisa fazer a
gente balançar e não soar robótica". What the set measures for that:
  - 126 BPM; hats swing 57 % against their own on-beats (middle half 56-59): the off-16ths
    ~17 ms late. One pocket, baked into every written part; Live's default pool groove is
    neutralised so it cannot double it.
  - a busy, quiet percussion layer with ghosts over 4x4; bass 73 % off the beat, ~4 dB under
    the drums; stabs short, off the beat, -11 dB under the drums.

Stage 1 (v3, approved bass): a 16-bar groove block. Stage 2 (his notes on v3: "gostei do baixo
mas o resto precisa fazer mais sentido, a bateria ter mais groove, as percussões no lugar delas
direitinho, nenhuma escondida, precisamos de synth ou stabs como nas referências... montar
primeiro build up e drop mais forte"):
  - percussion interlocked and tied to the track ("a bateria pode ficar menos genérica e estar
    mais encaixada com a track"): v3's congas and 909 tom hit the same 16ths (6, 7, 9, 11) and
    hid each other, on a kit pattern that ignored the bass. Now the congas (right) and the tom
    (left) play only in the bass's holes, bar by bar, so they answer it; the rim doubles the
    stab's rhythm; the clap's pickup answers the bass's Db push; the MIDI shaker only the "&".
  - more drum groove: a high-passed ghost kick on the "& of 3" (the 17:10 track's
    X...X...X.g.X...), a snare layer under the clap with ghosts.
  - the stab he picked by ear from four auditions: D (Wave Alchemy organ, B major, -22 ct,
    repitched to C), with A (the short organ, C# major) answering an octave up in the drop.
    House organ planing: call C - Db - C, answer Bb - Ab - Bb - C (bVI-bVII-I), in the bass's
    holes.
  - form so far: GROOVE 1-16, BREAK 17-24, BUILD 25-32, DROP 33-48 (the drop first, "depois
    abrir arranjo"). Breaks stay "pista" (kick out, percussion and stab stay, a low-passed bass
    ~8 dB under in the second half); the build pulses a high-passed kick (quarters, then 8ths),
    the congas thicken, the stab's filter opens, the low end leaves for the last 2 bars, the
    last 2 beats breathe; the drop lands with crash, a C sub boom, the ride and the answer organ.

v7 -> v8 balance, against the set's drop band shares: highs 8.3 % (set 2.75), 2-6 kHz 6.1 % (3.5),
mids 6.3 % (7.85), 250-500 Hz 8.1 % (4.05): hats/shaker/ride/loops -2 dB, piano +3, stab +3
(high-pass 250 Hz), keys +2.

Re-running is safe: every managed track's clips are deleted and written again.

    cd mcp_server && uv run python ../scripts/build_mochakk_c.py
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

C = client.call
BPM = 128.0                                     # v11: "128, agressiva, bem pista e bem boogie"
BEAT_S = 60.0 / BPM
END = 49                                        # first bar after the written part
SWING_PCT = 58.5                               # v9: "mais balançante", Chicago-MPC feel, inside the set's 56-59
SW = (SWING_PCT - 50.0) / 100.0 * 0.5          # off-16th delay in beats (0.035 = 16.7 ms)
SCATTER = 0.003 / BEAT_S                       # +-3 ms, beats
KIT = "user_library/Samples/Claude/Nobody Kit/"
OWN = "user_library/Samples/Claude/Mochakk C/"
OWN_DIR = os.path.expanduser("~/Music/Ableton/User Library/Samples/Claude/Mochakk C/")
GROOVE = "Swing 16ths 57"
LOOPS = os.path.expanduser("~/Music/Ableton/User Library/Samples/Claude/Nobody Kit/")
PACKS = os.path.expanduser("~/Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs/")
WA = PACKS + "Wave Alchemy - Chords and Stabs/resampled & effected/"
STAB_SRC = {"stab_organ_warm.wav": WA + "stab/wasc_stab_organ_Bmaj.wav",
            "stab_organ_short.wav": WA + "key & piano/wasc_key_sharp_organ_C#maj.wav"}
CRASH_REV = (PACKS + "The Producer School - Fiction - Indie Dance/TPS - Fiction - Project Files/Ableton Live/"
             "TPS - Fiction - Project File 02/TPS - Fiction - Project File 02 Project/Samples/Processed/Reverse/Crash 909 R.aif")
CRASH_REV_S = 1.11

GROOVE_BARS, BREAK_BARS, BUILD_BARS, DROP_BARS = (1, 17), (17, 25), (25, 33), (33, 49)
DROPS = [33]

# track: (source, fader dB, pan, room send dB, Simpler settings, sections it plays)
ALL = ("groove", "break", "build", "drop")
TRACKS = {
    "KICK":      (KIT + "SCHT_Kick1.wav", -2.3, 0.0, None, {"Vol < Vel": "0.0 %"}, ("groove", "drop")),
    "KICK HP":   (KIT + "SCHT_Kick1.wav", -9.0, 0.0, None, {"Vol < Vel": "100 %"}, ALL),
    "CLAP":      (KIT + "SCHT_Clap2.wav", -6.5, 0.0, -21.0, {"Vol < Vel": "40 %"}, ALL),
    # his v6 note: "faça groove com o snare, não com o clap; o clap pode ter groove mas pouco, o
    # snare vai sempre fazer mais, pra podermos usar ele como fills também, pra puxar a track"
    "SNARE":     (KIT + "AT_Infinite_Space_Snare_One_Shot_Resonate.wav", -8.0, 0.0, -22.0,
                  {"Vol < Vel": "100 %"}, ALL),
    "HAT 16":    (KIT + "HL_CH_CLOSED_HAT_SHOT_010.wav", -18.0, 0.0, -22.5, {"Vol < Vel": "100 %"}, ALL),
    "HAT OFF":   (KIT + "SCHT_Hat_Persona.wav", -11.0, 0.2, -21.0, {"Vol < Vel": "100 %"}, ALL),
    "HAT LIFT":  (KIT + "SCHT_Hat_Imite.wav", -13.0, -0.2, -21.0, {"Vol < Vel": "100 %"}, ("drop",)),
    "SHAKER":    (KIT + "KMRBI_AW_Shaker_One_Shot_Chuga.wav", -17.0, 0.35, -21.0, {"Vol < Vel": "100 %"}, ALL),
    "CONGAS":    ("drums/Percussion Core Kit.adg", -9.8, 0.3, -21.0, None, ALL),
    "TOM 909":   ("drums/909 Core Kit.adg", -6.0, -0.3, None, None, ("groove", "drop")),
    "RIM 909":   ("drums/909 Core Kit.adg", -4.0, -0.12, -24.0, None, ("groove", "build", "drop")),
    "RIDE":      ("drums/909 Core Kit.adg", -14.0, 0.1, -30.0, None, ("drop",)),
    "CRASH":     ("drums/909 Core Kit.adg", -10.0, 0.0, -24.0, None, ("break", "drop")),
    "BASS":      ("sounds/Bass/Electric Bass Soft.adg", -6.0, 0.0, None, None, ("groove", "drop")),
    "BASS BREAK": ("sounds/Bass/Electric Bass Soft.adg", -14.0, 0.0, None, None, ("break", "build")),
    # the stab's filter opens with velocity (Live 12.4 dropped its Auto Filter clip envelopes):
    # dark in the break, a velocity ramp through the build, open in the drop
    "STAB":      (OWN + "stab_organ_warm.wav", -11.0, -0.15, -18.0,
                  {"Vol < Vel": "60 %", "Transpose": "1 st", "Detune": "22 ct", "F On": "On",
                   "Filter Type": "Lowpass", "Filter Slope": "24 dB", "Filter Freq": "700 Hz",
                   "Filt < Vel": "100 %", "Filt < Key": "0.0 %"}, ALL),
    # the theme (his notes on v5: "falta tema, hook... pianos e stabs fortes e aparentes, com keys,
    # alguns fazem um pedalzinho distorcendo"): a piano riff in octaves, and a clav through a
    # guitar Pedal answering it
    "PIANO":     ("sounds/Piano & Keys/Grand Piano.adg", -7.0, 0.1, -16.0, None, ALL),
    # v7: the clav read "estranho, quadrado, fora de groove". Held E-piano chords instead, chopped
    # by a Gate keyed from GATE TRIG (a hidden track playing the chop in the set's swing: a synced
    # tremolo would chop straight), then the guitar Pedal: "nota longa picotada"
    "KEYS CHOP": ("sounds/Piano & Keys/E-Piano Classic.adg", -11.0, -0.25, -20.0, None, ("break", "build", "drop")),
    # Live's API routes no Gate sidechain: a Compressor at inf:1 keyed by this track closes the
    # keys wherever it sounds, so it plays the chop's silences (a sine with exact note lengths)
    "GATE TRIG": ("instruments/Operator", -70.0, 0.0, None, None, ("break", "build", "drop")),
    # v11 ("precisamos de uma atmosfera"): a wide pad on the keys' chords, low, into a long shared tail
    "PAD":       ("sounds/Ambient & Evolving/Ambiente Pad.adv", -24.0, 0.0, None, None, ("break", "build", "drop")),
    "STAB HI":   (OWN + "stab_organ_short.wav", -19.0, 0.25, -18.0,
                  {"Vol < Vel": "60 %", "Transpose": "-1 st", "Detune": "-1 ct"}, ("build", "drop")),
}
AUDIO = {   # played loops: human timing MIDI does not have (Let The Rhythm's shaker and perc)
    "SHAKER LOOP": (LOOPS + "PMLxSVTxCioz_Shaker_Acti_Black_Far_Away_122bpm.wav", 122, -18.0, -0.35,
                    [(9, 17), (33, 49)]),
    "PERC LOOP":   (LOOPS + "SCBB_Perc_120_Perola2.wav", 120, -20.0, -0.3, [(9, 25)]),   # the drop's Latin is the congas
}
FX = ["REV CRASH", "SUB BOOM"]
EQ = {
    "HAT 16": {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "-4.0 dB"},
    "SHAKER": {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "-4.0 dB"},
    "BASS": {"8 Filter On A": "On", "8 Filter Type A": "Low Pass 12dB", "8 Frequency A": "900 Hz"},
    # the break/build bass keeps its sub (his rule: the low end never vanishes) but no body
    "BASS BREAK": {"8 Filter On A": "On", "8 Filter Type A": "Low Pass 48dB", "8 Frequency A": "300 Hz"},
    # the build's pulse: the kick's click and knock without its sub
    "KICK HP": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 48dB", "1 Frequency A": "180 Hz"},
    "RIDE": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "350 Hz"},
    "STAB": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "250 Hz"},
    "STAB HI": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "300 Hz"},
    # house piano: no low end under the bass, less box, more presence
    "PIANO": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "180 Hz",
              "3 Filter On A": "On", "3 Filter Type A": "Bell", "3 Frequency A": "400 Hz", "3 Gain A": "-2.5 dB",
              "6 Filter On A": "On", "6 Filter Type A": "Bell", "6 Frequency A": "2.50 kHz", "6 Gain A": "2.5 dB"},
    "KEYS CHOP": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "220 Hz"},
    "PAD": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "300 Hz",
            "8 Filter On A": "On", "8 Filter Type A": "Low Pass 12dB", "8 Frequency A": "7.00 kHz"},
}

# the closed hat's accent map, dB per 16th (his kit, measured): on-beat 16ths ~11 dB under the "&"
HAT_DB = [-10.8, -2.4, -0.5, -2.0, -11.3, -3.4, -0.4, -2.6, -11.9, -3.4, -0.8, -2.4, -10.5, -2.8, -0.8, -1.6]

# the bass (Live's C3 = 60), approved on v3: call (A) and answer (B), degrees 1/5 with the b2 (Db)
# and b6 (Ab) pushing into the next downbeat; low C on the 1, answers an octave up
C2, G2, Ab2, Bb2, C3, Db3, Eb3 = 36, 43, 44, 46, 48, 49, 51
BASS_A = [(0, C2, 3, 112), (3, C3, 1, 78), (6, G2, 2, 100), (10, C2, 1, 92), (11, Eb3, 2, 100),
          (14, Db3, 2, 106)]
BASS_B = [(2, C3, 1, 96), (3, C2, 1, 84), (6, Ab2, 2, 104), (8, G2, 1, 86), (10, Bb2, 1, 94),
          (11, C3, 2, 104), (14, Db3, 1, 98)]
BASS_TURN = [(0, C2, 3, 112), (3, C3, 1, 78), (6, G2, 2, 100), (8, Ab2, 1, 96), (10, Bb2, 1, 98),
             (12, C3, 1, 102), (14, Db3, 1, 104), (15, Eb3, 1, 96)]

# the stab: the organ plays major chords (note 60 = C major after Transpose/Detune), planing.
# 2-bar call and 2-bar answer, every hit in a hole of the bass bar it sits on;
# (step, semitones from C, length in 16ths, velocity)
STAB_CALL = [(2, 0, 1, 104), (5, 0, 1, 82), (7, 1, 2, 108), (9, 0, 1, 88), (13, 0, 1, 84),
             (17, -2, 1, 98), (21, -4, 1, 86), (23, -2, 2, 100), (28, 0, 1, 94), (31, 1, 1, 90)]
STAB_ANSWER = [(2, 0, 1, 104), (5, 0, 1, 82), (7, 1, 2, 108), (13, 1, 1, 86),
               (17, -4, 2, 98), (23, -2, 2, 100), (28, 0, 2, 106)]
# the short organ answers the call's phrase ends, an octave up (drop only)
STAB_HI = [(28, 12, 1, 92), (30, 13, 1, 84), (31, 12, 1, 96)]

# the theme (Live's C3 = 60, so 72 = C4): a 4-bar phrase, call (bars 1-2) and lift (bars 3-4),
# its notes from the track's colours (E and the b6/b7 Ab-Bb of the stab's planing, Db the push);
# (step in the 4 bars, MIDI pitch, length in 16ths, velocity)
# v11 ("a melodia ainda não ficou tão boa"): a hook, not a line -- one syncopated cell repeated,
# G G E Ab G, answered G G E Db C, then a falling turn Bb Ab G E C Bb; off-beat, short
HOOK = [(3, 79, 1, 96), (6, 79, 2, 104), (8, 76, 1, 84), (11, 80, 2, 110), (14, 79, 1, 92)]
ANSWER = [(3, 79, 1, 96), (6, 79, 2, 104), (8, 76, 1, 84), (11, 73, 2, 108), (14, 72, 2, 96)]
TURN = [(2, 82, 1, 100), (4, 80, 1, 92), (7, 79, 2, 104), (10, 76, 1, 90), (12, 72, 2, 98), (15, 70, 1, 86)]
THEME = ([(st, p, ln, v) for st, p, ln, v in HOOK] + [(st + 16, p, ln, v) for st, p, ln, v in ANSWER]
         + [(st + 32, p, ln, v) for st, p, ln, v in HOOK] + [(st + 48, p, ln, v) for st, p, ln, v in TURN])
ATMOS_SENDS = {"PAD": -8.0, "PIANO": -18.0, "STAB": -20.0, "STAB HI": -16.0, "KEYS CHOP": -18.0}

# the keys' held chords, one per bar of the 4-bar phrase: Cadd9, Dbmaj7, Cadd9, C7 (the theme's
# bar 4 spells C7b9: Db E G Bb C)
KEYS = [(60, 64, 67, 74), (61, 65, 68, 72), (60, 64, 67, 74), (58, 64, 67, 70)]
# the chop, per 16th, two bars that alternate; the build fills every 16th
CHOP_A = "x.xx.x.xx.x..x.x"
CHOP_B = "x..x.xx.x.xx.x.."
CHAINS = {
    "KEYS CHOP": [("Compressor", {"Threshold": "-50.0 dB", "Attack": "0.10 ms",
                                  "Release": "6.00 ms", "S/C EQ On": "Off"}),
                  ("Pedal", {"Type": "Overdrive", "Drive": "50 %", "Output": "-4.0 dB", "Dry/Wet": "65 %"})],
    "PIANO": [("Compressor", {"Ratio": "4.00 : 1", "Attack": "5.00 ms", "Release": "80.0 ms", "Threshold": "-22.0 dB"}),
              ("Saturator", {"Drive": "3.00 dB", "Dry/Wet": "60 %"})],
}

# the snare: 2 and 4 under the clap, ghosts that move between two bars, fills at 4 and 8;
# (16th step, velocity)
# v11 ("o snare só aparece numa parte, ele precisa dar o groove"): v10's snare doubled the clap's
# 2 and 4 and vanished under it; now it plays its own syncopations off the clap, everywhere
SNARE_A = [(4, 90), (12, 94), (7, 72), (10, 58), (15, 80)]
SNARE_B = [(4, 90), (12, 94), (2, 56), (7, 74), (13, 62)]
# the 909 ghost snares (old Chicago house), two bars, the "a" of 4 pulling into the next 1
CHI_A = [(3, 34), (6, 44), (10, 30), (15, 54)]
CHI_B = [(1, 28), (7, 48), (9, 32), (11, 40), (14, 36)]
SNARE_FILL_4 = [(13, 70), (15, 86)]
SNARE_FILL_8 = [(9, 70), (12, 100), (14, 82), (15, 96)]          # a groove, not a roll
SNARE_BUILD = [0, 3, 6, 8, 11, 14]                                # the last 2 bars: 3-3-2 rising

# conga tumbao, by priority: slap on the "a" of 2, open tones on the "e-a" of 4, bongos, a muted
# tone; (step, pad, velocity) -- the first four that fall in the bass's holes play
TUMBAO = [(7, 40, 92), (14, 38, 88), (15, 38, 96), (2, 43, 74), (10, 40, 64), (12, 45, 70), (9, 43, 66), (1, 45, 60)]

# percussion, interlocked: congas right (low slap 38, high muted 40, low bongo 43, high bongo 45)
CONGA_TRIPLET = [(38, 0.0), (40, 1 / 3), (40, 2 / 3), (43, 2.0), (45, 2 + 1 / 3), (45, 2 + 2 / 3),
                 (38, 3.0), (40, 3.25), (43, 3.5), (45, 3.75)]
TOM_STEPS = (5, 13)                             # 909 low tom, left: candidates, kept only in the bass's holes


def log(*a):
    print(*a, flush=True)


def _is_option(v):
    return isinstance(v, str) and not (v[:1].isdigit() or v[:1] in "+-.")


def setp(track, device, param, v):
    args = {"track": track, "device": device, "param": param}
    if isinstance(v, float):
        args["value"] = v                   # raw 0-1 (Compressor Ratio inf = 1.0)
    else:
        args["item" if _is_option(v) else "display"] = v
    return C("set_param", args)


def bass_pattern(bar):
    pos = (bar - 1) % 8
    return BASS_TURN if pos == 7 else (BASS_A if pos % 2 == 0 else BASS_B)


def bass_holes(bar):
    """The 16ths without a bass attack: the percussion's room (counting the bass's ringing
    notes too left one conga hit in some bars)."""
    busy = {st for st, *_ in bass_pattern(bar)}
    return [st for st in range(16) if st not in busy]


def stab_steps(bar):
    """The stab's 16ths in this bar (its 2-bar phrase, this bar's half)."""
    first = bar if (bar - 1) % 2 == 0 else bar - 1
    phrase = STAB_ANSWER if (first - 1) % 4 == 2 else STAB_CALL
    half = 0 if bar == first else 16
    return [st - half for st, *_ in phrase if half <= st < half + 16]


def devs(track):
    """The track's device names (get_track lists dicts: comparing a name with them was always
    False, and every run up to v7 stacked another EQ Eight / Pedal / Compressor on its tracks)."""
    return [d["name"] if isinstance(d, dict) else d for d in C("get_track", {"track": track, "clips": False})["devices"]]


def dedupe(track, keep_first=True):
    """Delete repeated effects (all but the first of each name), from the end."""
    names = devs(track)
    seen = set()
    drop = []
    for i, n in enumerate(names):
        if i > 0 and n in seen:
            drop.append(i)
        seen.add(n)
    for i in reversed(drop):
        C("delete_device", {"track": track, "device": i})
    return len(drop)


def lead(bar):
    """Who leads this bar (v9: "ter um lead ou alguns leads mas não tocar ao mesmo tempo"): the
    stab in the groove's second phrase, the piano's hint at 13-16 and its theme in the break,
    the chopped keys then the piano's cell in the build; in each 8 of the drop the piano leads
    bars 1-4 (keys under it) and the organ bars 5-8 (its short answer with it)."""
    sec = section(bar)
    if sec == "groove":
        return None if bar < 9 else "stab" if bar < 13 else "piano"
    if sec == "break":
        return "piano"
    if sec == "build":
        return "keys" if bar < BUILD_BARS[0] + 4 else "piano"
    if sec == "drop":
        return "piano" if (bar - DROP_BARS[0]) % 8 < 4 else "stab"
    return None


def section(bar):
    for name, (a, b) in (("groove", GROOVE_BARS), ("break", BREAK_BARS), ("build", BUILD_BARS),
                         ("drop", DROP_BARS)):
        if a <= bar < b:
            return name
    return None


def make_files():
    """The two organ stabs (copied so the browser finds them) and a C sub boom: a sine at
    C2 sliding down from 80 Hz, ~1 s; the pack's 'C1' bass hit measured D."""
    os.makedirs(OWN_DIR, exist_ok=True)
    for name, src in STAB_SRC.items():
        if not os.path.exists(OWN_DIR + name):
            shutil.copy(src, OWN_DIR + name)
    boom = OWN_DIR + "sub_boom_C2.wav"
    if not os.path.exists(boom):
        sr = 44100
        t = np.arange(int(1.1 * sr)) / sr
        f = 65.41 + (80.0 - 65.41) * np.exp(-t / 0.04)
        y = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t / 0.35)
        y[: int(0.003 * sr)] *= np.linspace(0, 1, int(0.003 * sr))
        y[-int(0.05 * sr):] *= np.linspace(1, 0, int(0.05 * sr))
        sf.write(boom, np.stack([y, y], axis=1) * 0.5, sr, subtype="PCM_24")
    return {"boom": boom}


def ensure_tracks():
    names = [t["name"] for t in C("get_song")["tracks"]]
    for t, (src, fader, pan, send, simpler, _) in TRACKS.items():
        if t not in names:
            C("create_track", {"kind": "midi", "name": t})
        if not devs(t):
            C("load_device", {"track": t, "path": src})
        for p, v in (simpler or {}).items():     # every run: a device left from a lost run too
            setp(t, 0, p, v)
        C("set_track", {"track": t, "volume_db": fader, "pan": pan})
        C("set_send", {"track": t, "send": 0, "db": send if send is not None else -70.0})
    for t, bands in EQ.items():
        if "EQ Eight" not in devs(t):
            C("load_device", {"track": t, "query": "EQ Eight", "roots": ["audio_effects"]})
        for p, v in bands.items():
            setp(t, "EQ Eight", p, v)
    for t in TRACKS:
        n = dedupe(t)
        if n:
            log(t, "removed", n, "repeated devices")
    # the atmosphere: one long shared tail (return C) under the melodic parts, high-passed
    if not any(r["name"].endswith("Atmos") for r in C("get_song")["returns"]):
        C("create_return", {"name": "Atmos"})
    atm = [r["name"] for r in C("get_song")["returns"] if r["name"].endswith("Atmos")][0]
    ret = "return:" + atm
    if "Hybrid Reverb" not in devs(ret):
        C("load_device", {"track": ret, "query": "Hybrid Reverb", "roots": ["audio_effects"]})
    dedupe(ret)
    if "EQ Eight" not in devs(ret):
        C("load_device", {"track": ret, "query": "EQ Eight", "roots": ["audio_effects"]})
    for p, v in {"Decay": "3.50 s", "Predelay": "25.0 ms", "Dry/Wet": "100 %"}.items():
        setp(ret, "Hybrid Reverb", p, v)
    for p, v in {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "350 Hz",
                 "8 Filter On A": "On", "8 Filter Type A": "Low Pass 12dB", "8 Frequency A": "6.00 kHz"}.items():
        setp(ret, "EQ Eight", p, v)
    C("set_track", {"track": ret, "volume_db": -6.0})
    sends = [r["name"] for r in C("get_song")["returns"]].index(atm)
    for t, db in ATMOS_SENDS.items():
        C("set_send", {"track": t, "send": sends, "db": db})
    names = [t["name"] for t in C("get_song")["tracks"]]
    if "KEYS DIST" in names:                 # v6's clav, replaced
        C("delete_track", {"track": "KEYS DIST"})
    for t, chain in CHAINS.items():
        for dev, params in chain:
            if dev not in devs(t):
                C("load_device", {"track": t, "query": dev, "roots": ["audio_effects"]})
            for p, v in params.items():
                try:
                    setp(t, dev, p, v)
                except Exception as e:
                    log(t, dev, p, e)
    if "Gate" in devs("KEYS CHOP"):
        C("delete_device", {"track": "KEYS CHOP", "device": "Gate"})   # v7's: no sidechain via the API
    setp("KEYS CHOP", "Compressor", "Ratio", 1.0)          # inf : 1
    C("set_device_input", {"track": "KEYS CHOP", "device": "Compressor", "source": "GATE TRIG", "channel": "Post FX"})
    if "Auto Filter" in devs("STAB"):
        C("delete_device", {"track": "STAB", "device": "Auto Filter"})   # v4's, its envelopes lost
    for t, (path, _, fader, pan, _) in AUDIO.items():
        if t not in names:
            C("create_track", {"kind": "audio", "name": t})
            C("set_track_input", {"track": t, "source": "No Input"})
        C("set_track", {"track": t, "volume_db": fader, "pan": pan})
        C("set_send", {"track": t, "send": 0, "db": -22.0})
    for t in FX:
        if t not in names:
            C("create_track", {"kind": "audio", "name": t})
            C("set_track_input", {"track": t, "source": "No Input"})
    C("set_track", {"track": "REV CRASH", "volume_db": -16.0})
    C("set_track", {"track": "SUB BOOM", "volume_db": -8.0})
    # Live's empty default tracks ("1-MIDI", "3-Audio"...): deleting one renumbers the rest, so
    # find them by being empty and delete from the end, by index
    for t in reversed(C("get_song")["tracks"]):
        if re.fullmatch(r"\d+-(MIDI|Audio)", t["name"]) and not t["devices"] and not t["clips"]:
            C("delete_track", {"track": t["i"]})
    # one short room for the whole kit (return A, Live's default Reverb)
    for p, v in {"Decay Time": "0.80 s", "Predelay": "5.00 ms", "Dry/Wet": "100 %"}.items():
        try:
            setp("return:0", "Reverb", p, v)
        except Exception as e:      # parameter names differ between Live versions
            log("room:", p, e)


# hands, ms of scatter per part (v9: "dar uma humanizada"): ghosts and congas loosest, the kick the grid
HUMAN_MS = {"SNARE": 4, "RIM 909": 7, "CONGAS": 6, "TOM 909": 5, "HAT 16": 4, "HAT OFF": 3, "HAT LIFT": 3,
            "SHAKER": 5, "PIANO": 5, "BASS": 4, "STAB": 3, "STAB HI": 3}


def _swing(notes, rnd, kind=None):
    """One pocket: every off-16th SW late, every hit scattered by its part's hands."""
    sc = HUMAN_MS.get(kind, 3) / 1000.0 / BEAT_S
    for n in notes:
        q = n[1] * 4
        if abs(q - round(q)) < 1e-6 and int(round(q)) % 2 == 1:
            n[1] += SW
        n[1] = round(max(0.0, n[1] + rnd.uniform(-sc, sc)), 4)
    return notes


def notes(kind, bar0, n_bars):
    rnd = np.random.default_rng(hash((kind, bar0)) % 2 ** 32)
    out = []
    for k in range(n_bars):
        b = bar0 + k                        # song bar, 1-based
        sec = section(b)
        pos = (b - 1) % 8                   # bar in its 8-bar phrase
        full = b >= 9                       # the groove's second phrase and later: fuller
        o = k * 4.0
        last = b == BUILD_BARS[1] - 1       # the bar before the drop: its last 2 beats breathe
        if kind == "KICK":
            for beat in range(4):
                if b == GROOVE_BARS[1] - 1 and beat == 3:
                    continue                # the prepared exit: the kick leaves a beat early
                out.append([60, o + beat, 1.0, 127])
        elif kind == "KICK HP":
            if sec in ("groove", "drop"):   # the 17:10 track's ghost on the "& of 3"
                if pos % 2 == 1 or sec == "drop":
                    out.append([60, o + 2.5, 0.25, int(rnd.uniform(52, 64))])
            elif sec == "build":            # the pulse: quarters, then 8ths, velocity rising
                i = b - BUILD_BARS[0]
                step = 1.0 if i < 5 else 0.5   # 8ths from the build's 6th bar: density climbs
                t = 0.0
                while t < 4.0 - 1e-9:
                    if not (last and t >= 2.0):
                        frac = (i * 4 + t) / 32.0
                        out.append([60, o + t, 0.25, int(56 + 44 * frac)])   # v4: 120 at the end put the build over the drop
                    t += step
        elif kind == "CLAP":                # the anchor: 2 and 4, a little groove only at phrase ends
            hits = [(4, 104), (12, 108)]
            if pos == 7:
                hits.append((2, 64))        # the "& of 1" closing each 8
            for st, v in hits:
                if last and st >= 8:
                    continue
                out.append([60, o + st * 0.25 + 0.008 / BEAT_S, 0.25, int(v * rnd.uniform(0.94, 1.04))])
        elif kind == "SNARE":               # the groove and the fills: it pulls the track
            hits = list(SNARE_A if pos % 2 == 0 else SNARE_B)
            if sec == "break":
                hits = [(st, v * 0.8) for st, v in hits if st not in (4, 12)]   # its syncopations; the clap holds 2 and 4
            if any(st == 14 and p == Db3 for st, p, _, _ in bass_pattern(b)):
                hits.append((15, 58))       # answers the bass's Db push
            if pos == 3:
                hits = [h for h in hits if h[0] < 13] + SNARE_FILL_4
            if pos == 7 and sec != "build":
                hits = [h for h in hits if h[0] < 12] + SNARE_FILL_8
            if b == BUILD_BARS[1] - 2:      # into the drop: a 3-3-2 groove rising (v10's 16th roll "muito rápido")
                hits = [(st, 66 + 5 * j) for j, st in enumerate(SNARE_BUILD)]
            if last:
                hits = [(0, 100), (3, 108), (6, 116)]   # then the breath
            lift = 1.06 if sec == "drop" else 1.0
            for st, v in hits:
                out.append([60, o + st * 0.25 + 0.006 / BEAT_S, 0.2, int(min(127, v * lift * rnd.uniform(0.9, 1.08)))])
        elif kind == "HAT 16":
            brk = sec == "break"
            for st in range(16):
                if brk and st % 4 == 0:     # the break: lighter, no on-beat 16ths
                    continue
                if last and st >= 8:
                    continue
                if pos % 2 == 1 and st == 13:   # a pocket every 2nd bar
                    continue
                if pos % 4 == 2 and st == 9:
                    continue
                if pos == 3 and st == 0:        # a breath on the 4th bar's downbeat
                    continue
                if pos == 7 and st >= 14 and sec != "build":   # a 32nd flutter into the 1
                    for j, v in enumerate((48, 60, 74, 88)):
                        out.append([60, o + 3.5 + j * 0.125, 0.1, v])
                    continue
                v = 127 * 10 ** (HAT_DB[st] / 20.0) * rnd.uniform(0.86, 1.04)
                out.append([60, o + st * 0.25, 0.15, int(max(18, min(127, v)))])
        elif kind == "HAT LIFT":            # the reserved third "&" layer: the drop lifts without anything new
            for st in (2, 6, 10, 14):
                if pos == 7 and st == 14:
                    continue
                out.append([60, o + st * 0.25, 0.25, int(rnd.uniform(92, 106))])
        elif kind == "HAT OFF":             # the "&"s, one breath per phrase
            for st in (2, 6, 10, 14):
                if (pos == 7 and st == 14) or (last and st >= 8):
                    continue
                out.append([60, o + st * 0.25, 0.3, int(rnd.uniform(94, 110))])
        elif kind == "SHAKER":              # Latin: the "&" pushes (~5 ms early), the "a" accented
            for st in (2, 3, 6, 7, 10, 11, 14, 15):
                if last and st >= 8:
                    continue
                v = rnd.uniform(90, 104) if st % 4 == 3 else rnd.uniform(58, 72)
                out.append([60, o + st * 0.25 - (0.005 / BEAT_S if st % 4 == 2 else 0.0), 0.12, int(v)])
        elif kind == "CONGAS":
            if sec == "build" and b >= BUILD_BARS[1] - 2:   # the build's last 2 bars: 16ths
                for st in range(16):
                    if last and st >= 8:
                        continue
                    p = (38, 40, 43, 40)[st % 4]
                    v = 62 + 40 * ((b - (BUILD_BARS[1] - 2)) * 16 + st) / 24.0
                    out.append([p, o + st * 0.25, 0.15, int(min(108, v * rnd.uniform(0.92, 1.05)))])
            elif pos in (3, 7):             # a triplet bar every 4
                for p, t in CONGA_TRIPLET:
                    out.append([p, o + t, 0.2, int(rnd.uniform(64, 86))])
            else:                           # a tumbao, in the bass's holes: Latin, and it answers the bass
                holes = set(bass_holes(b))
                hits = [h for h in TUMBAO if h[0] in holes][: (4 if full else 3)]
                for st, p, v in hits:
                    out.append([p, o + st * 0.25, 0.2, int(v * rnd.uniform(0.88, 1.08))])
        elif kind == "TOM 909":             # 909 low tom, left, on its own 16ths
            if sec == "groove" and pos < 4:
                continue                    # toms only in the second half of each groove phrase
            holes = bass_holes(b)
            for st in TOM_STEPS:
                if st in holes:             # never on a bass note: the 909 tom sits near its register
                    out.append([44, o + st * 0.25, 0.2, int(rnd.uniform(70, 98))])
            if pos == 7:
                out += [[44, o + 3.5, 0.1, 74], [44, o + 3.75, 0.1, 88]]
        elif kind == "RIM 909":             # Chicago: 909 ghost snares, laid back, never the same two bars
            if not full and sec == "groove":
                continue
            ghosts = CHI_A if pos % 2 == 0 else CHI_B
            if sec == "break":
                ghosts = ghosts[::2]
            for st, v in ghosts:
                if last and st >= 8:
                    continue
                out.append([38, o + st * 0.25 + 0.004 / BEAT_S, 0.12, int(v * rnd.uniform(0.85, 1.12))])
            if pos == 3:                    # a rim on the "a" of 4 in every 4th bar
                out.append([37, o + 3.75, 0.1, int(rnd.uniform(70, 84))])
        elif kind == "RIDE":                # the reserved shine: the drop's "&"s
            for st in (2, 6, 10, 14):
                out.append([51, o + st * 0.25, 0.3, int(rnd.uniform(92, 104))])
        elif kind == "CRASH":
            if b in (BREAK_BARS[0],):
                out.append([49, o, 1.0, 70])    # soft: the break's first beat
            if b in DROPS:
                out.append([49, o, 1.0, 110])
        elif kind in ("BASS", "BASS BREAK"):
            if kind == "BASS BREAK":
                # (v9: no longer out for the break's first half: the break sat 6 LU under the drop
                # with no sub; his rule, "não pode ficar sem sub, que faz o movimento e o groove")
                if sec == "build" and b >= BUILD_BARS[1] - 2:
                    continue                # the low end leaves for the build's last 2 bars
            pat = BASS_TURN if pos == 7 else (BASS_A if pos % 2 == 0 else BASS_B)
            for st, p, ln, v in pat:
                out.append([p, o + st * 0.25, ln * 0.25 * 0.85, int(v * rnd.uniform(0.95, 1.03))])
        elif kind == "STAB":
            if lead(b) != "stab":
                continue                    # it speaks only in its own turn
            if k % 2:
                continue                    # 2-bar phrases, written from their first bar
            phrase = STAB_ANSWER if (b - 1) % 4 == 2 else STAB_CALL
            if sec == "break":              # sparse: the phrase's first hits only, held longer
                phrase = [(st, s, 3, v - 10) for st, s, _, v in phrase if st in (2, 7, 17, 23)]
            for st, s, ln, v in phrase:
                t = o + st * 0.25
                if last or (b + 1 == BUILD_BARS[1] - 1 and st >= 24):
                    if t - o >= 6.0:        # the breath before the drop
                        continue
                out.append([60 + s, t, ln * 0.25 * 0.6, int(v * stab_scale(b, st) * rnd.uniform(0.94, 1.04))])
        elif kind == "PIANO":
            if k % 4:
                continue                    # 4-bar phrases, written from their first bar
            if lead(b) != "piano" and sec != "build":
                continue                    # its turns only
            for st, p, ln, v in THEME:
                t = st * 0.25
                if b + st // 16 >= END:
                    continue
                if sec == "build":          # compressed: each half bar repeats the theme's cell
                    continue
                if last and t >= 14.0:
                    continue
                # by hand: lay back on the beats, push the anticipations, velocity breathes
                hum = (0.006 if st % 4 == 0 else -0.005 if st % 4 == 3 else 0.0) / BEAT_S
                vel = v * {"groove": 0.6, "break": 0.95, "drop": 1.0}[sec] * rnd.uniform(0.9, 1.05)
                dur = ln * 0.25 * (0.9 if sec == "break" else 0.7)
                out.append([p, o + t + hum, dur, int(min(127, vel))])
                if sec == "drop":           # house piano: the octave below doubles it
                    out.append([p - 12, o + t + hum, dur, int(min(127, vel * 0.85))])
            if sec == "build" and k == 0:   # the cell (E-G-Ab) in 8ths, climbing an octave at the end
                for j in range(n_bars * 8):
                    bb = j // 8
                    if bar0 + bb >= BUILD_BARS[1]:
                        break
                    if bar0 + bb == BUILD_BARS[1] - 1 and (j % 8) >= 4:
                        continue            # the breath
                    if lead(bar0 + bb) != "piano":
                        continue            # the keys have the build's first half
                    p = (79, 79, 76, 80)[j % 4] + (12 if bar0 + bb >= BUILD_BARS[1] - 2 else 0)
                    v = 60 + 50 * j / (n_bars * 8.0)
                    out.append([p, o + bb * 4 + (j % 8) * 0.5, 0.35, int(v * rnd.uniform(0.92, 1.05))])
        elif kind == "KEYS CHOP":           # held: the gate does the rhythm
            if last or (sec == "drop" and lead(b) != "piano"):
                continue                    # in the drop it accompanies the piano, never the organ
            chord = KEYS[(b - 1) % 4]
            for p in chord:
                # v9: with the stab out of the break it sat 6 LU under the drop (his rule 3.8-5)
                out.append([p, o, 3.98, int((90 if sec == "break" else 92) * rnd.uniform(0.95, 1.03))])
        elif kind == "GATE TRIG":
            pat = "x" * 16 if sec == "build" and b >= BUILD_BARS[0] + 4 else (CHOP_A if pos % 2 == 0 else CHOP_B)
            for st, c in enumerate(pat):
                if c == ".":                # a silence: duck the whole 16th
                    out.append([60, o + st * 0.25, 0.25, 110])
                else:                       # a chop: duck its last 30 % so each attack stands apart
                    out.append([60, o + st * 0.25 + 0.175, 0.07, 110])
        elif kind == "PAD":                 # the keys' chords, held a bar each, an octave up
            if last:
                continue
            for p in KEYS[(b - 1) % 4]:
                out.append([p + 12, o, 3.95, int((64 if sec == "break" else 78) * rnd.uniform(0.95, 1.03))])
        elif kind == "STAB HI":
            if k % 2 or lead(b) != "stab":
                continue
            if sec == "build":              # one pickup into the drop, then silence
                if b == BUILD_BARS[1] - 2:
                    out += [[72, o + 4 + 1.0, 0.15, 90], [73, o + 4 + 1.5, 0.15, 98]]
                continue
            for st, s, ln, v in STAB_HI:
                out.append([60 + s, o + st * 0.25, ln * 0.25 * 0.6, int(v * rnd.uniform(0.94, 1.04))])
    return out if kind in ("KICK", "CRASH") else _swing(out, rnd, kind)


def stab_scale(bar, step):
    """Velocity factor = the stab's filter: groove 0.85, break 0.42, build rising to 1, drop 1."""
    sec = section(bar)
    if sec == "break":
        return 0.42
    if sec == "build":
        frac = ((bar - BUILD_BARS[0]) * 16 + step) / ((BUILD_BARS[1] - BUILD_BARS[0]) * 16.0)
        return 0.45 + 0.55 * frac
    return 1.0 if sec == "drop" else 0.85


def place_loop(track, path, src_bpm, a, b):
    """A played loop across bars [a, b): one clip of the file, then fill_range (an arrangement
    clip keeps its file's length; v3's loops covered 2 and 4 of 16 bars)."""
    beats = round(sf.info(path).duration * src_bpm / 60.0)   # auto-warp guesses wrong: pin it
    C("create_audio_clip", {"track": track, "path": path, "bar": a, "name": track, "warp": True,
                            "beats": beats})
    loop_bars = max(1, beats // 4)
    if b - a > loop_bars:
        C("fill_range", {"track": track, "src_start_bar": a, "src_end_bar": a + loop_bars,
                         "start_bar": a + loop_bars, "end_bar": b})


def build(files):
    for t, (_, _, _, _, _, secs) in TRACKS.items():
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": END + 8})
        for name, (a, b) in (("groove", GROOVE_BARS), ("break", BREAK_BARS), ("build", BUILD_BARS),
                             ("drop", DROP_BARS)):
            if name not in secs:
                continue
            for bar0 in range(a, b, 8):
                n = min(8, b - bar0)
                args = {"track": t, "bar": bar0, "length": n * 4.0, "name": "%s %s" % (t, name),
                        "notes": notes(t, bar0, n)}
                r = C("create_midi_clip", args)
                if isinstance(r, dict) and r.get("envelopes_lost"):
                    log("WARNING", t, bar0, "envelopes lost")
        log(t, "written")
    for t, (path, bpm, _, _, spans) in AUDIO.items():
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": END + 8})
        for a, b in spans:
            place_loop(t, path, bpm, a, b)
        log(t, "placed")
    for t in FX:
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": END + 8})
    for bar in DROPS:
        beat = (bar - 1) * 4.0
        C("create_audio_clip", {"track": "REV CRASH", "path": CRASH_REV, "warp": False, "name": "REV CRASH",
                                "beat": round(beat - CRASH_REV_S / BEAT_S - 0.02, 3)})
        C("create_audio_clip", {"track": "SUB BOOM", "path": files["boom"], "warp": False,
                                "name": "SUB BOOM C", "beat": beat})
    # the played loops are straight: they take the set's pocket from the pool (warped clips only);
    # the written parts carry it in their notes and get no pool groove
    if GROOVE not in [g["name"] for g in C("grooves")["grooves"]]:
        C("load_device", {"track": "SHAKER LOOP", "path": "user_library/Grooves/%s.agr" % GROOVE})
    # the pool's 57 file at 121 % amount = the written parts' 58.5 (50 + 7 x 1.21)
    C("set_groove", {"name": GROOVE, "timing": 100, "random": 0, "velocity": 0,
                     "groove_amount": round((SWING_PCT - 50.0) / 7.0, 3)})
    for t in AUDIO:
        C("apply_groove", {"track": t, "groove": GROOVE})
    # Live gives every new MIDI clip its default "Swing 16ths 66" and the API cannot clear a
    # clip's groove: neutralise it, or it doubles the swing baked into the notes (v2 measured
    # the hats 49 ms late, 70 %, for 17 ms written)
    for g in C("grooves")["grooves"]:
        if g["name"] != GROOVE:
            C("set_groove", {"name": g["name"], "timing": 0, "random": 0, "velocity": 0})
    if C("get_song")["is_playing"]:
        log("Live is playing: locators left as they are (stop and re-run to rename them)")
        cues = []
    else:
        C("clear_cues")
        cues = None
    for name, bar in (("GROOVE - stab enters at 9", 1), ("BREAK - kick out, pista", 17),
                      ("BUILD - HP kick, filter opens, breath", 25), ("DROP - crash, sub, ride, organ answers", 33)):
        if cues is None:
            C("set_cue", {"name": name, "bar": bar})
    # v1 rendered at 128: the song tempo moved after set_tempo(126) while the block was built.
    # Set it last and check it, every run
    C("set_tempo", {"bpm": BPM})
    assert abs(C("get_song")["tempo"] - BPM) < 1e-6, "Live's tempo is not %s" % BPM


if __name__ == "__main__":
    files = make_files()
    ensure_tracks()
    build(files)
