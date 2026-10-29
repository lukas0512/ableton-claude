"""Project #6 House: an original house track after three references the producer picked
(Ant Brooks "Spin It", Michel De Hey & Job De Jong "Get On Up", AMMIL "Body 2 Body"),
studied as `house_spin_body`: 129 BPM, G minor, hats swung ~56 % against their own
on-beats, bass ~Bb1 and 83-90 % off the beat, slow m9/sus harmony, drums leading.

Material, auditioned by the producer (2026-10-28, "versão 2"): kit A built from one-shots
ranked by the references' timbre (Sounds of Blanc kick "push" and clap "eyup", Gino Da
Koda hat, Dropgun short open hat) with the references' per-16th feel at 56 %; bass NSL
Midbass Gm, stab SS synth chord 09 Gm, voice UVOX "Here Is The Solution" (Gm). The loops
were measured out of tune with each other (bass -19, stab -35, voice -27 cents against a
-7 cent centre) and are detuned onto it. Percussion: 3Q Dub Tech House perc loop 05
(mid register, out of the bass's way), straight, so it takes the pool's 16ths 57 swing.

Form (184 bars, taste.md §1): intro A drums (16), intro B one layer per 4 bars (16),
groove (16), break 1 (8) + build 1 (8), DROP 1 (32, voice in its 2nd 8), main break (16)
+ build 2 (8), DROP 2 (32, everything from bar 1), outro A (16), outro B drums (16).
Breaks stay "pista": kick out, clap/hats/perc/stab keep going, a low-passed bass ~8 dB
under the drop in each break's second half. Builds: a high-passed kick in quarters, 8ths
in the last bar, then a 2-beat breath before every drop. The kick prepares its exits (its
last beat before a break is cut). The stab is disclosed by its low-pass: closed in intro B,
open in the groove, darker in breaks, opening through each build.

Re-running is safe: every managed track's clips are deleted and placed again.

    cd mcp_server && uv run python ../scripts/build_project6.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client, knowledge, loops  # noqa: E402
from ableton_claude.music import kits  # noqa: E402
import numpy as np  # noqa: E402
from scipy import signal  # noqa: E402

C = client.call
BPM = 129.0
BEAT_S = 60.0 / BPM
END = 185                                   # first bar after the track
PACKS = os.path.expanduser("~/Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs/")
OUT = os.path.expanduser("~/Desktop/Projects 26:27/Project #6 House Project/Samples/Claude/")
SWING = 56.0

KICK_SHOT = PACKS + "THE SOUNDS OF BLANC VOL. 2/DRUMS/KICKS/kick hits/SOBV2_KICK_push_hit.wav"
CLAP_SHOT = PACKS + "THE SOUNDS OF BLANC VOL. 2/DRUMS/CLAPS/clap hits/SOBV2_CLAP_eyup_hit.wav"
HAT_SHOT = PACKS + "Gino Da Koda - Groove Kingz Vol. 4/HATS/GDKGK4_HAT 04.wav"
OPEN_SHOT = PACKS + "Dropgun_Samples_-_Vocal_UK_House/one_shots/drums/hats/DS_VUKH_hat_one_shot_sunset_open_short.wav"
BASS = PACKS + "Loopmasters - Ultimate Deep House/WAV_LOOPS/BASS_LOOPS/NSL_122_Gm_Midbass.wav"
STAB = PACKS + "loop/G menor/SS_LH_Synth_Chord Loops_125_09_Gm.wav"
VOX = PACKS + "Loopmasters - Ultimate Vocals MULTiFORMAT/HOUSE_VOCALS/LOOPS/UVOX_126_Gm_TOPLINE_HEREISTHESOLUTION.wav"
PERC = PACKS + "3Q Samples Dub Tech House Vol 1/3Q_DUB1_LOOPS_128BPM/3Q_DUB1_PERC_LOOPS/3Q_DUB1_Perc_Loop_05.wav"
CRASH = PACKS + "Loopmasters - Essentials 13 Deep House/MONODELUXE DEEP HOUSE VOL2/SOUNDS AND FX/DRUMS/MD2_CRASH_2.wav"
CRASH_REV = (PACKS + "The Producer School - Fiction - Indie Dance/TPS - Fiction - Project Files/Ableton Live/"
             "TPS - Fiction - Project File 02/TPS - Fiction - Project File 02 Project/Samples/Processed/Reverse/Crash 909 R.aif")
CRASH_REV_S = 1.11
FXD = PACKS + "Loopmasters - Ultimate Deep House/SOUNDS_&_FX/"
RISER = FXD + "FX/DCW_126_The_Rise_Fx.wav"                  # 4 bars at 126
DOWNLIFTER = FXD + "FX/DCW_126_Classic_Downfiller_Fx.wav"
IMPACT = FXD + "FX/DCW_126_Kick_Down_Fx.wav"                # a down-pitched kick
SUB_BOOM = FXD + "BASS_HITS/WB_Optimal_1_Shots_Sub_Bass_Gmin.wav"   # G sub, the key's root
DETUNE = {"VOX": 20, "VOX ADLIB": 37, "STAB SS": 28}
ADLIB = PACKS + "Loopmasters - Ultimate Vocals MULTiFORMAT/HOUSE_VOCALS/PHRASES/UVOX_118_Gm_ADLIBS_DOOHAHH.wav"
VOX2 = PACKS + "Loopmasters - Ultimate Vocals MULTiFORMAT/HOUSE_VOCALS/PHRASES/UVOX_126_Gm_GUEYEHYEH.wav"
CHORDS = PACKS + "Loopmasters - Ultimate Deep House/WAV_LOOPS/MUSIC_LOOPS/NSL_122_Gm_SoftChord.wav"
GROOVE = "Swing 16ths 57"

SECTIONS = [("INTRO A - drums, DJ", 1), ("INTRO B - bass 17, chords 25, voice teaser 29", 17),
            ("GROOVE - chords open, voice + answer", 33), ("BREAK 1 - kick out, groove stays", 49),
            ("BUILD 1 - HP kick, stab opens", 57), ("DROP 1 - kick + bass back, voice in 2nd 8", 65),
            ("MAIN BREAK - stab dark, filtered bass in 2nd half", 97), ("BUILD 2 - HP kick 8ths", 113),
            ("STOP - the solution, a cappella", 120), ("DROP 2 - everything from bar 1", 121), ("OUTRO A - stab closing, no voice", 153),
            ("OUTRO B - drums, DJ", 169)]
DROPS = [65, 121]
# the breath before each drop, in beats: 2 before drop 1; before drop 2 the whole bar stops
# and "Here is the solution" speaks alone (its last word into the delay): the moment the
# track is remembered by, then the drop lands with the impact, the G sub boom and the crash
BREATH = {65: 2.0, 121: 4.0}
BREAKS = [49, 97]

# v3 ("sem groove... vários elementos tocando várias coisas sem se conversar"): the pack
# loops were each busy (the SS stab ~11 attacks a bar, the NSL bass ~8 notes, several on the
# kick) and two drum kits ran at once. Now: one drum system (kit A's kick + the producer's own
# let_the_rhythm parts), the soft chords as THE stab (4 off-beat hits a bar, Cm = iv9, the
# references' rhythm), and a bass written to speak in the chords' and the kick's holes.
# track: (file key, beats per file, warped?, [(start_bar, end_bar)])
PLAN = {
    "KICK":       ("kick", 16, False, [(1, 49), (65, 97), (121, END)]),
    # the stab: disclosed by its low-pass (closed in intro B, open in the groove, dark in breaks)
    # the piano: phrases built from its own chord hits (PIANO), placed A B A C (see piano_phrase)
    # the hook "Here is the solution" states, "Gueyehyeh" answers it, the "doo-ahh" ad-libs sit
    # under the drops as a second voice; the hook also runs a cappella into each drop
    # drop 2's sauce: the SS stab only at phrase ends (2 bars every 8), never a bed
    "STAB SS":    ("stab", 8, True, [(127, 129), (143, 145), (151, 153)]),
}
# v8: the voices warped syllable by syllable (rap_phrase): sung loosely, their syllables sat up
# to +-50 ms off the 16ths against a locked kit. Each syllable moves 60 % onto its 16th, the
# off-16ths 15.5 ms late (the set's pocket). One take per voice, duplicated to its bars.
# track: (padded source (half a beat of pre-roll), source bpm, pre-roll s, detune, bars)
VOICES = {
    "VOX":       ("P6_vox_solution_padded.wav", 126, 0.2385, 20, [29, 41, 61, 73, 89, 101, 117, 129, 145]),
    "VOX 2":     ("P6_vox_gueyehyeh_padded.wav", 126, 0.2385, 0, [45, 77, 93, 105, 133, 149]),
    "VOX ADLIB": ("P6_vox_doohahh_padded.wav", 118, 0.2546, 37, [65, 69, 81, 85, 121, 125, 137, 141]),
}
# absences inside the drops ("tirar a repetitividade, deixar os drops mais interessantes"):
# (bar, beat in bar 0-3, tracks) -> those tracks stop there until their next clip
# v5 ("o piano precisa ser menos repetitivo... call response... AB, AC"): the Soft Chord loop's
# own hits, sliced at 129 BPM (bar A's chord: 16ths 0.2 / 7 / 9.9; bar B's chord: 15.86 /
# 22.85 / 26.06), re-played in 2-bar phrases. A = the loop as written; B = the answer, the
# same chords earlier and on the off-beats, its last 2 beats empty for the voice/bass; C = the
# bounce, the chords chopped on the "e"s and pushed; D = held chords for the breaks.
PIANO_HITS = {"a0": 0.2, "a7": 7.0, "a10": 9.9, "b0": 15.86, "b7": 22.85, "b10": 26.06}
# v6 ("falta encaixar, parecem grooves diferentes"): every hit on the 16th grid (the loop's
# own 0.2 / 9.9 / 15.86 were its feel, not the set's), one swing (the hats' measured 15 ms),
# and the melody varies: "g" hits are the same chord 5 semitones down (Cm9 -> Gm9, iv -> i)
PIANO = {
    "A": [(0, "a0"), (7, "a7"), (10, "a10"), (16, "b0"), (23, "b7"), (26, "b10")],
    "B": [(2, "a7"), (7, "a10"), (10, "a7"), (13, "a10"), (18, "b0"), (23, "b7")],
    "C": [(0, "a0"), (3, "a7"), (6, "a10"), (10, "a7"), (16, "g0"), (19, "g7"), (22, "g10"),
          (27, "g7"), (30, "g10")],
    "E": [(0, "a0"), (7, "a7"), (10, "a10"), (16, "g0"), (23, "g7"), (26, "g10")],
    "D": [(0, "a0"), (16, "b0")],
}
PIANO_SWING_S = 0.0155
# v7 ("o groove dos synth ainda tá meio ruim, tá com muita cauda o timbre"): each hit was let
# ring until the next one; the references' stabs are 70 % short (~110 ms). Held only in D.
PIANO_STAB_S = 0.14
PIANO_HIT_AUDIO = {}
PIANO_SPANS = [(25, 49), (49, 65), (65, 97), (97, 121), (121, 161)]


def piano_phrase(bar):
    """Which phrase the 2-bar cell at `bar` plays: call and answers, never the same 4 times."""
    k = ((bar - 1) // 2) % 4                 # cell in its 8-bar phrase
    if bar < 33:
        return "A"                           # intro B: the loop itself, under its filter
    if 49 <= bar < 57 or 97 <= bar < 113:
        return "D" if k % 2 == 0 else "A"    # breaks: held, then answered
    if 121 <= bar < 153:
        return "AEAC"[k]                     # drop 2: the answer moves to the i chord
    return "ABAE"[k] if bar < 97 else "ABAC"[k]


HOLES = [(72, 2, ("CHORDS",)), (88, 2, ("KICK",)), (136, 2, ("KICK", "CHORDS")), (144, 0, ("CHORDS",))]
BASS_REST = {72: 8, 88: 8, 136: 8}            # the bass rests from this 16th in that bar
# the producer's own drums (let_the_rhythm): 8-bar loops aligned to the phrases (their fills
# close each phrase). track: (instrument, kit part, [(start_bar, end_bar)])
MIDI = {
    "SHAKER":   ("user_library/Samples/Claude/Nobody Kit/KMRBI_AW_Shaker_One_Shot_Chuga.wav",
                 "hat_off_shaker_shot", [(17, 49), (53, 65), (65, 97), (105, 121), (121, 177)]),
    "CONGAS":   ("Percussion Core Kit", "congas", [(41, 49), (73, 97), (105, 121), (129, 161)]),
    "TOM 909":  ("909 Core Kit", "tom_909", [(137, 153)]),
    "RIDE":     ("909 Core Kit", "ride", [(129, 153)]),
}
LIB = os.path.expanduser("~/Music/Ableton/User Library/Samples/Claude/Project6/")
# written parts on Simplers playing one-shots cut from the chosen sounds:
# track: (one-shot key, generator, [(start_bar, end_bar)])
GEN = {
    # v4 ("menos com o clap, tá muito a mais... mais groove de hat... um ghost snare"): his clap
    # sample on a plain 2 and 4 with rare pickups; a 909 ghost snare; a second hat on the "e"/"a"
    "CLAP LTR":  ("clap", "clap", [(9, 169)]),
    "GHOST SNARE": ("909", "ghost", [(33, 49), (53, 65), (65, 97), (105, 121), (121, 169)]),
    "HAT 2":     ("hat2", "hat2", [(33, 49), (65, 97), (105, 121), (121, 169)]),
    "HATS":      ("hat", "hats", [(1, 49), (49, 65), (65, 97), (97, 121), (121, END)]),
    "OPEN HAT":  ("open", "open", [(25, 49), (73, 97), (129, 153), (153, 169)]),
    "BASS":      ("bass", "bass", [(17, 49), (65, 97), (121, 169)]),
    "BASS BREAK": ("bass", "bass", [(53, 65), (105, 121)]),
}
# the high-passed kick of the builds: quarters, then 8ths in the last bar (1-bar files)
KICK_HP = [(61, "q"), (62, "q"), (63, "q"), (64, "8"),
           (113, "q"), (114, "q"), (115, "q"), (116, "q"), (117, "q"), (118, "q"), (119, "8")]   # bar 120 is the stop
KICK_HP_GAIN = {61: -6, 62: -5, 63: -4, 64: -2, 113: -8, 114: -7, 115: -6, 116: -5, 117: -4,
                118: -3, 119: -2, 120: 0}
# FX under the drums (taste: risers -20): (track, file key, bar, bars or None for one-shots)
FX = [("FX RISER", "riser4", 61, 4), ("FX RISER", "riser4", 117, 4),
      ("FX DOWN", "down", 49, None), ("FX DOWN", "down", 97, None), ("FX DOWN", "down", 153, None),
      ("FX IMPACT", "impact", 65, None), ("FX IMPACT", "impact", 121, None),
      ("SUB BOOM", "boom", 65, None), ("SUB BOOM", "boom", 121, None)]
CRASHES = [(17, "hit"), (33, "hit"), (65, "hit"), (65, "rev"), (121, "hit"), (121, "rev"), (153, "hit")]


def stab_freq(bar):
    """The stab's low-pass (Hz) at the start of `bar`: the hook disclosed by its filter."""
    ramps = [(25, 33, 400, 2500), (33, 49, 20000, 20000), (49, 57, 1500, 1200), (57, 65, 1200, 9000),
             (65, 97, 20000, 20000), (97, 113, 700, 1400), (113, 121, 1400, 12000),
             (121, 153, 20000, 20000), (153, 161, 20000, 900)]
    if 65 <= bar < 97 or 121 <= bar < 153:    # inside the drops: an 8-bar breath, 7 kHz -> open
        x = ((bar - 65) % 8) / 8.0
        return 7000 * (20000 / 7000.0) ** x
    for a, b, f0, f1 in ramps:
        if a <= bar <= b:
            x = (bar - a) / float(b - a)
            return f0 * (f1 / float(f0)) ** x            # exponential: even in the ear
    return 20000


LEVELS = {"FX RISER": -20.0, "FX DOWN": -18.0, "FX IMPACT": -12.0, "SUB BOOM": -14.0,
          "CLAP LTR": -11.0, "GHOST SNARE": -15.0, "HAT 2": -17.0, "STAB SS": -16.0, "PIANO GATE": -14.0, "SHAKER": -15.0, "CONGAS": -16.0, "TOM 909": -19.0, "RIDE": -21.0,
          "KICK": -8.0, "KICK HP": -11.0, "HATS": -16.0, "OPEN HAT": -17.0, "CRASH": -20.0,
          "BASS": -3.0, "BASS BREAK": -11.0, "CHORDS": 4.0,
          "VOX": -14.0, "VOX 2": -16.0, "VOX ADLIB": -22.0}
PANS = {"HAT 2": -0.25, "HATS": 0.08, "GHOST SNARE": 0.1, "STAB SS": 0.2, "OPEN HAT": 0.2, "SHAKER": 0.35, "CONGAS": 0.26, "TOM 909": -0.18, "RIDE": 0.1,
        "CHORDS": 0.0, "VOX 2": -0.1, "VOX ADLIB": 0.15}
# (track, device, {param: display text or option})
DEVICES = [
    ("KICK HP", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 48dB", "1 Frequency A": "180 Hz"}),
    ("OPEN HAT", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "400 Hz"}),
    ("CRASH", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "300 Hz"}),
    ("VOX", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "180 Hz"}),
    ("VOX 2", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "180 Hz"}),
    ("CHORDS", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "180 Hz"}),
    ("FX RISER", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "300 Hz"}),
    ("FX DOWN", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "200 Hz"}),
    ("RIDE", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "350 Hz"}),
    ("SHAKER", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "300 Hz"}),
    ("CONGAS", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "150 Hz"}),
    ("TOM 909", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "120 Hz"}),
    # the break's bass: the riff's sub and movement, no mids (never a high-pass on a bass)
    ("BASS BREAK", "EQ Eight", {"8 Filter On A": "On", "8 Filter Type A": "Low Pass 48dB", "8 Frequency A": "220 Hz"}),
    # the bass sample is stereo (its width read -9 dB): mono, like the references' (-30..-61)
    ("BASS", "Utility", {"Width": "0.0 %"}),
    ("BASS", "EQ Eight", {"3 Filter On A": "On", "3 Filter Type A": "Bell", "3 Frequency A": "160 Hz",
                          "3 Gain A": "-3.0 dB", "3 Q A": "1.0"}), ("BASS BREAK", "Utility", {"Width": "0.0 %"}),
    ("STAB SS", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "300 Hz",
                             "8 Filter On A": "On", "8 Filter Type A": "Low Pass 12dB", "8 Frequency A": "5.00 kHz"}),
    ("PIANO GATE", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "250 Hz"}),
    ("HAT 2", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "400 Hz"}),
    ("GHOST SNARE", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "200 Hz"}),
    ("LOW END", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "22.0 Hz"}),
    ("LOW END", "Glue Compressor", {"Threshold": "-18", "Ratio": "2", "Attack": "10", "Release": ".2", "Range": "2.5"}),
    ("LOW END", "Saturator", {"Type": "Soft Sine", "Drive": "2.0", "Dry/Wet": "30"}),
    ("CHORDS", "Auto Filter", {"Filter Type": "Low-pass", "Resonance": "10 %"}),
    ("VOX ADLIB", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "250 Hz"}),
    # v3c: above 6 kHz still 5-16 dB under the references (the hat samples are dark): air on
    # the hats and shaker, the kick's sub at 50 Hz (-4 dB), the chords' 1 kHz (+4) down
    ("HATS", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "350 Hz",
                          "8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "2.0 dB"}),
    ("OPEN HAT", "EQ Eight", {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "4.0 dB"}),
    ("SHAKER", "EQ Eight", {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "9.00 kHz", "8 Gain A": "4.0 dB"}),
    ("KICK", "EQ Eight", {"2 Filter On A": "On", "2 Filter Type A": "Bell", "2 Frequency A": "50.0 Hz",
                          "2 Gain A": "3.0 dB", "2 Q A": "1.2"}),
    ("CHORDS", "EQ Eight", {"4 Filter On A": "On", "4 Filter Type A": "Bell", "4 Frequency A": "1.00 kHz",
                            "4 Gain A": "-2.5 dB", "4 Q A": "0.8"}),
    # v5 drop 1: bass -9.8 dB vs drums (refs -4), mids -3 dB, 25-40 Hz -4..-10, -9.3 LUFS
    ("master", "Limiter", {"Input Gain": "9.5"}),
    # the kick owns its first ~120 ms
    ("BASS", "Compressor", {"Threshold": "-24 dB", "Ratio": "6.00 : 1", "Attack": "0.10 ms",
                            "Release": "120 ms", "Auto Release On/Off": "Off", "Makeup": "Off", "S/C On": "On"}),
    ("BASS BREAK", "Compressor", {"Threshold": "-24 dB", "Ratio": "4.00 : 1", "Attack": "0.10 ms",
                                  "Release": "120 ms", "Auto Release On/Off": "Off", "Makeup": "Off", "S/C On": "On"}),
    ("return:A-Reverb", "Reverb", {"Decay Time": "1.4 s", "Predelay": "20 ms"}),          # the plate
    ("return:B-Delay", "Delay", {"Ping Pong": "On", "Feedback": "30 %", "Filter On": "On",
                                 "Filter Freq": "1.5 kHz", "Filter Width": "6.0"}),
]
SIDECHAIN = {"BASS": "KICK", "BASS BREAK": "KICK HP"}
# v5 ("kick e baixo bem colado, gostoso, groovy, bounce"): one LOW END bus glues them
# (his let_the_rhythm chain: HP 30 Hz, Glue 2:1 10 ms 0.2 s range 2.5, soft-sine saturation)
LOW_END = ["KICK", "KICK HP", "BASS", "BASS BREAK", "SUB BOOM"]
# the Simplers of the written parts (device 0): hats follow the accent map (Vol < Vel 100 %),
# the bass keeps some dynamics and the cents that put the NSL G1 on the loops' centre
# Volume: a fresh Simpler sits at -12 dB; v3's first drop render read the bass 18.5 dB under
# the drums (references -4) and the highs at 0.6 % (references 2.4)
# v3b drop render vs the references' 1/3 octaves: 125-200 Hz +2..4 dB (the bass's register),
# everything above 300 Hz 4-11 dB under: the kick and bass were the mix, the groove was buried
SIMPLER = {"HAT 2": {"Vol < Vel": "100 %", "Volume": "-6"}, "CLAP LTR": {"Vol < Vel": "40 %", "Volume": "-4"},
           "HATS": {"Vol < Vel": "100 %", "Volume": "-3"}, "OPEN HAT": {"Vol < Vel": "100 %", "Volume": "-6"},
           "SHAKER": {"Volume": "-4"},
           "BASS": {"Vol < Vel": "40 %", "Detune": "12 ct", "Volume": "0"},
           "BASS BREAK": {"Vol < Vel": "40 %", "Detune": "12 ct", "Volume": "0"}}
# sends: [A-Reverb (plate), B-Delay, C-Room (short, every drum)]
# D-Atmos: one shared long tail, low and dark, under the chords and the voices (the atmosphere)
ATMOS = {"PIANO GATE": -24.0, "CHORDS": -26.0, "VOX ADLIB": -12.0, "VOX": -22.0, "VOX 2": -20.0, "STAB SS": -16.0,
         "OPEN HAT": -26.0, "SHAKER": -26.0}
SENDS = {"PIANO GATE": [-26.0, -20.0, None], "CHORDS": [-24.0, None, None], "GHOST SNARE": [None, None, -16.0], "HAT 2": [None, None, -22.0], "STAB SS": [-16.0, -18.0, None],
         "HATS": [None, None, -22.0], "OPEN HAT": [None, None, -20.0], "VOX": [-16.0, -18.0, None],
         "VOX ADLIB": [-12.0, None, None],
         "CRASH": [-16.0, None, None], "CLAP LTR": [None, None, -16.0], "SHAKER": [None, None, -21.0],
         "CONGAS": [None, None, -20.0], "TOM 909": [None, None, -22.0], "VOX 2": [-16.0, -18.0, None],
         "FX RISER": [-18.0, None, None], "FX DOWN": [-16.0, None, None]}


def log(*a):
    print(*a, flush=True)


def _is_option(v):
    return isinstance(v, str) and not (v[:1].isdigit() or v[:1] in "+-.")


def setp(track, device, param, v):
    args = {"track": track, "device": device, "param": param}
    args["item" if _is_option(v) else "display"] = v
    return C("set_param", args)


def make_files():
    os.makedirs(OUT, exist_ok=True)
    T = knowledge.load_profile("house_spin_body")["ear"]["drums"]
    f = {"kick": OUT + "P6_Kick_push_129.wav", "clap": OUT + "P6_Clap_eyup_129.wav",
         "hats": OUT + "P6_Hats_16_129.wav", "open": OUT + "P6_OpenHat_off_129.wav",
         "kick_q": OUT + "P6_KickHP_quarters_1bar_129.wav", "kick_8": OUT + "P6_KickHP_8ths_1bar_129.wav",
         "vox": VOX, "vox2": VOX2, "chords": CHORDS, "adlib": ADLIB, "stab": STAB}
    os.makedirs(LIB, exist_ok=True)
    f["hat"] = shot(HAT_SHOT, LIB + "P6_hat_gino04.wav", 0.12)
    f["open"] = shot(OPEN_SHOT, LIB + "P6_openhat_dropgun.wav", 0.30)
    f.update(make_piano())
    loops.write(LIB + "P6_clap_scht2.wav", loops.read(os.path.expanduser(
        "~/Music/Ableton/User Library/Samples/Claude/Nobody Kit/SCHT_Clap2.wav")))
    shot((
        PACKS + "3Q Samples Terrace Tech House 2/3Q_TT2_DRUM_HITS/3Q_TT2_HATS/3Q_TT2_Hat_15.wav"), LIB + "P6_hat2_3q15.wav", 0.10)
    # the bass: the NSL Midbass's own G1 (its first note, 0.06-0.48 s), played by a Simpler
    x = loops.read(BASS)
    a, n = int(0.06 * loops.SR), int(0.42 * loops.SR)
    y = x[a:a + n].copy()
    fade = int(0.012 * loops.SR)
    y[-fade:] *= np.linspace(1, 0, fade)[:, None] if y.ndim == 2 else np.linspace(1, 0, fade)
    f["bass"] = loops.write(LIB + "P6_bass_nsl_G1.wav", y)
    loops.write(f["kick"], loops.four_on_floor(KICK_SHOT, BPM))
    # (kit A's clap/hat loops are gone: the old open-hat loop overwrote the trimmed one-shot)
    f["riser4"] = loops.stretch_to(RISER, OUT + "P6_Riser_4bars_129.wav", BPM, 4)
    f.update(down=DOWNLIFTER, impact=IMPACT, boom=SUB_BOOM)
    loops.write(f["kick_q"], loops.four_on_floor(KICK_SHOT, BPM, bars=1))
    loops.write(f["kick_8"], loops.four_on_floor(KICK_SHOT, BPM * 2, bars=2))   # 8 hits in one bar
    return f


def shot(src, out, seconds):
    """A one-shot that starts on its attack (1 ms before it) and lasts `seconds`, faded out.
    v5's hat (GDKGK4_HAT 04) and open hat were 7 s files whose first hit came at 234 ms:
    every hat note sounded half a beat late, or not at all ("parece que são grooves diferentes")."""
    x = loops.read(src)
    mono = np.abs(x).max(1) if x.ndim == 2 else np.abs(x)
    a = max(0, int(np.argmax(mono > mono.max() * 0.1)) - int(0.001 * loops.SR))
    y = x[a:a + int(seconds * loops.SR)].copy()
    fade = min(len(y), int(0.015 * loops.SR))
    ramp = np.linspace(1, 0, fade)
    y[-fade:] *= ramp[:, None] if y.ndim == 2 else ramp
    return loops.write(out, y)


def make_piano():
    """The piano's phrases as unwarped 2-bar WAVs at 129 BPM: the loop stretched (and moved
    +31 cents onto the set's tuning) once, its six hits sliced, then re-placed per phrase with
    the set's 56 % swing on the off-16ths; each hit is faded out where the next one starts."""
    import subprocess
    import soundfile as sf
    tmp = OUT + "P6_piano_src_129.wav"
    dur = sf.info(CHORDS).duration
    r = 2 ** (31 / 1200.0)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", CHORDS, "-af",
                    "asetrate=%d,aresample=%d,atempo=%.6f" % (loops.SR * r, loops.SR,
                                                             dur / (8 * BEAT_S) / r), tmp], check=True)
    src = loops.read(tmp)
    s16 = BEAT_S / 4
    starts = sorted(PIANO_HITS.items(), key=lambda kv: kv[1])
    hits = {}
    for i, (name, st) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else 32.0
        a, b = int((st - 0.1) * s16 * loops.SR), int((end - 0.05) * s16 * loops.SR)
        hits[name] = src[max(0, a):b].copy()
    lead = 0.1 * s16                             # each slice starts this long before its attack
    for name in [k for k in hits if k.startswith("a")]:   # Gm9: the same voicing 5 semitones down
        hits["g" + name[1:]] = signal.resample(hits[name], int(len(hits[name]) * 2 ** (5 / 12.0)), axis=0)
    n = int(8 * BEAT_S * loops.SR)
    sw = PIANO_SWING_S                           # an off-16th lands this late (the hats' 15 ms)
    global PIANO_HIT_AUDIO
    PIANO_HIT_AUDIO = hits
    out = {}
    for ph, events in PIANO.items():
        y = np.zeros((n,) + src.shape[1:])
        ev = sorted(events)
        for j, (st, h) in enumerate(ev):
            t = st * s16 + (sw if abs(st - round(st)) < 1e-6 and int(round(st)) % 2 == 1 else 0)
            i0 = max(0, int((t - lead) * loops.SR))
            nxt = ev[j + 1][0] * s16 if j + 1 < len(ev) else 8 * BEAT_S
            room = max(0, int(nxt * loops.SR) - i0)
            if ph != "D":                        # stabs, not chords ringing into the next hit
                room = min(room, int(PIANO_STAB_S * loops.SR))
            seg = hits[h][:room].copy()
            fade = min(len(seg), int((0.03 if ph != "D" else 0.02) * loops.SR))
            if fade:
                ramp = np.linspace(1, 0, fade)
                seg[-fade:] *= ramp[:, None] if seg.ndim == 2 else ramp
            y[i0:i0 + len(seg)] += seg[:n - i0]
        out["piano_" + ph] = loops.write(OUT + "P6_piano_%s_129.wav" % ph, y)
    return out


# v6 ("usar um trance pra picar e fazer algo diferente no timbre e aleatório"): the piano's
# chord held (phase-vocoder stretched: a pad timbre of the same chord) and chopped by a 16th
# trance gate that opens only where the piano is silent (call and response at the 16th), each
# open step with its own random low-pass and pan. Seeded per cell: random, but reproducible.
GATE_SPANS = [(81, 97), (113, 121), (129, 153)]


def make_gate(bar, phrase, density):
    import librosa
    s16 = BEAT_S / 4
    n16 = 32
    rnd = np.random.default_rng(1000 + bar)
    piano_steps = {int(round(st)) for st, _ in PIANO[phrase]}
    chords = []
    for half in (0, 1):
        names = [h for st, h in PIANO[phrase] if (st >= 16) == bool(half)]
        chords.append("g0" if any(h.startswith("g") for h in names) else "a0")
    pads = {}
    for c in set(chords):
        x = PIANO_HIT_AUDIO[c]
        m = x.mean(1) if x.ndim == 2 else x
        pads[c] = librosa.effects.time_stretch(m.astype(np.float32), rate=len(m) / (16 * s16 * loops.SR) * 1.05)
    y = np.zeros((int(n16 * s16 * loops.SR), 2))
    for st in range(n16):
        if any(abs(st - p) <= 1 for p in piano_steps) or rnd.random() > density:
            continue
        pad = pads[chords[st // 16]]
        a = int(((st % 16) * s16) * loops.SR)
        n = int(s16 * 0.5 * loops.SR)
        seg = pad[a:a + n].copy()
        if len(seg) < n:
            continue
        cut = rnd.uniform(700, 6000)                  # the random timbre: a one-pole low-pass
        al = np.exp(-2 * np.pi * cut / loops.SR)
        seg = signal.lfilter([1 - al], [1, -al], seg)
        env = np.ones(n)
        f = int(0.003 * loops.SR)
        env[:f] = np.linspace(0, 1, f)
        env[-f:] = np.linspace(1, 0, f)
        seg *= env * rnd.uniform(0.7, 1.0)
        pan = rnd.uniform(-0.45, 0.45)
        t0 = int((st * s16 + (PIANO_SWING_S if st % 2 == 1 else 0)) * loops.SR)
        y[t0:t0 + n, 0] += seg * (1 - pan) ** 0.5
        y[t0:t0 + n, 1] += seg * (1 + pan) ** 0.5
    y /= max(1e-9, np.abs(y).max()) / 0.5
    return loops.write(OUT + "P6_gate_%03d.wav" % bar, y)


def ensure_tracks():
    names = [t["name"] for t in C("get_song")["tracks"]]
    for old in ("BASS 1 - DCW", "STAB 1 - Soft Chord", "VOX 1 - Gueyehyeh"):   # version 1, not chosen
        if old in names:
            C("delete_track", {"track": old})
    for old, new in (("BASS 2 - NSL", "BASS"), ("STAB 3 - SS Chord", "STAB"), ("VOX 4 - Solution", "VOX")):
        if old in names:
            C("set_track", {"track": old, "name": new})
    song = C("get_song")["tracks"]
    for t in song:      # v2's audio loops that the written parts replace, and v2's extra layers
        if t["name"] in ("CLAP", "HATS 16", "PERC", "STAB", "RIM 909") or (
                t["name"] in GEN and t["kind"] == "audio"):
            C("delete_track", {"track": t["name"]})
    names = [t["name"] for t in C("get_song")["tracks"]]
    for t, (key, _, _) in GEN.items():
        if t not in names:
            C("create_track", {"kind": "midi", "name": t})
        if not C("get_track", {"track": t, "clips": False})["devices"]:
            if SHOTS[key].endswith(".wav"):
                C("load_device", {"track": t, "path": "user_library/Samples/Claude/Project6/%s"
                                  % os.path.basename(SHOTS[key])})
            else:
                C("load_device", {"track": t, "query": SHOTS[key], "roots": ["drums"]})
    for t in ["KICK HP", "CRASH", "VOX 2", "VOX ADLIB", "CHORDS", "FX RISER", "FX DOWN",
              "FX IMPACT", "SUB BOOM"]:
        if t not in names:
            C("create_track", {"kind": "audio", "name": t})
            C("set_track_input", {"track": t, "source": "No Input"})
    for t, (inst, _, _) in MIDI.items():
        if t not in names:
            C("create_track", {"kind": "midi", "name": t})
        if not C("get_track", {"track": t, "clips": False})["devices"]:
            if inst.endswith(".wav"):
                C("load_device", {"track": t, "path": inst})
            else:
                C("load_device", {"track": t, "query": inst, "roots": ["drums"]})
    if "LOW END" not in [x["name"] for x in C("get_song")["tracks"]]:
        C("create_track", {"kind": "audio", "name": "LOW END"})
        C("set_track_input", {"track": "LOW END", "source": "No Input"})
        C("set_track", {"track": "LOW END", "monitoring": "in"})
    for t in LOW_END:
        if t in [x["name"] for x in C("get_song")["tracks"]]:
            C("set_track_output", {"track": t, "dest": "LOW END"})
    for t in ["STAB SS", "PIANO GATE"]:
        if t not in [x["name"] for x in C("get_song")["tracks"]]:
            C("create_track", {"kind": "audio", "name": t})
            C("set_track_input", {"track": t, "source": "No Input"})
    returns = [r["name"] for r in C("get_song")["returns"]]
    if not any(r.endswith("Atmos") for r in returns):
        if not any(r.endswith("Room") for r in returns):
            raise RuntimeError("create C-Room before D-Atmos")
        C("create_return", {"name": "Atmos"})
        C("load_device", {"track": "return:D-Atmos", "query": "Hybrid Reverb", "roots": ["audio_effects"]})
        for p, v in {"Algo Type": "Shimmer", "Decay": "3.0 s", "Size": "80 %", "Predelay": "30 ms",
                     "Dry/Wet": "100 %"}.items():
            setp("return:D-Atmos", "Hybrid Reverb", p, v)
        C("load_device", {"track": "return:D-Atmos", "query": "EQ Eight", "roots": ["audio_effects"]})
        for p, v in {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "350 Hz",
                     "8 Filter On A": "On", "8 Filter Type A": "Low Pass 12dB", "8 Frequency A": "6.00 kHz"}.items():
            setp("return:D-Atmos", "EQ Eight", p, v)
    if not any(r.endswith("Room") for r in returns):
        C("create_return", {"name": "Room"})
        C("load_device", {"track": "return:C-Room", "query": "Hybrid Reverb", "roots": ["audio_effects"]})
        for p, v in {"Algo Type": "Quartz", "Decay": "0.6 s", "Size": "30 %", "Predelay": "5 ms",
                     "Dry/Wet": "100 %"}.items():
            setp("return:C-Room", "Hybrid Reverb", p, v)


def clear(track):
    C("delete_clips_in_range", {"track": track, "start_bar": 1, "end_bar": END + 8})


def place(track, path, beats, a, b, warp, detune=0, envelopes=None, gain_db=None):
    """Clips of `beats` from bar a to bar b, the last one trimmed at b."""
    beat, stop = (a - 1) * 4.0, (b - 1) * 4.0
    while beat < stop - 1e-3:
        args = {"track": track, "path": path, "beat": beat, "name": track, "warp": warp}
        if warp:
            args.update(beats=beats, warp_mode="complex_pro")
            if detune:
                args["detune"] = detune
        if envelopes:
            args["envelopes"] = envelopes(beat)
        if gain_db is not None:
            args["gain_db"] = gain_db
        r = C("create_audio_clip", args)
        want_end = min(beat + beats, stop)
        if r.get("end", want_end) > want_end + 1e-3:
            C("trim_clip", {"track": track, "clip": {"at": beat}, "end_beat": want_end})
        beat += beats


def cut_at(track, beat):
    """End the clip that plays through `beat` at `beat` (a breath or a prepared exit)."""
    for c in C("get_track", {"track": track, "max_clips": 500})["clips"]:
        if c["start"] < beat - 1e-3 < c["end"] and c["end"] > beat + 1e-3:
            C("trim_clip", {"track": track, "clip": {"at": c["start"]}, "end_beat": beat})


SHOTS = {"hat": LIB + "P6_hat_gino04.wav", "open": LIB + "P6_openhat_dropgun.wav",
         "clap": LIB + "P6_clap_scht2.wav", "hat2": LIB + "P6_hat2_3q15.wav", "909": "909 Core Kit",
         "bass": LIB + "P6_bass_nsl_G1.wav"}
# the producer's hat accents (let_the_rhythm, measured): on-beat 16ths ~11 dB under the "and"
HAT_DB = [-10.8, -2.4, -0.5, -2.0, -11.3, -3.4, -0.4, -2.6, -11.9, -3.4, -0.8, -2.4, -10.5, -2.8, -0.8, -1.6]
BREAK_BARS = [(49, 65), (97, 121)]
# the bass speaks where the chords and the kick are silent. The chords hit 16ths 1 7 10 14
# (bar A, Cm over the G pedal) and 0 7 10 14 (bar B); the kick 0 4 8 12. 16th, MIDI, 16ths long
# v4 ("o baixo encaixar mais no groove do piano"): the soft chords hit 16ths 0.2, 7.0, 9.9 and
# push bar B's chord to 15.86; bar B 6.85, 10.06. The bass now locks with the piano on its
# accents (7, 10, the push) and answers in between (3, 13, the F pickup)
BASS_A = [(3, 43, 1.2), (7, 43, 0.8), (10, 46, 1.0), (14, 55, 0.6), (15.86, 48, 1.4)]   # G G Bb g' | C pushed
BASS_B = [(3, 48, 1.0), (7, 48, 0.8), (10, 46, 1.0), (13, 50, 0.7), (15, 41, 0.8)]       # C C Bb D | F
# the bounce: notes cut short (the gaps are the groove) and the octave G answering the piano


def _in(bar, spans):
    return any(a <= bar < b for a, b in spans)


def gen_notes(kind, bar, n_bars):
    """Notes for `n_bars` from song bar `bar`: phrase-aware variation, not a pasted loop."""
    rnd = np.random.default_rng(bar * 7 + len(kind))
    out = []
    for k in range(n_bars):
        b = bar + k
        pos = (b - 1) % 8                       # bar in its 8-bar phrase
        o = k * 4.0
        if kind == "hats":
            brk = _in(b, BREAK_BARS)
            for st in range(16):
                db = HAT_DB[st]
                if b <= 8 and st % 4 != 2:      # intro: the "and" only, then the 16ths join
                    continue
                if brk and st % 4 == 0:         # breaks: lighter, no on-beat 16ths
                    continue
                if pos % 2 == 1 and st == 13:   # a pocket every 2nd bar
                    continue
                if pos % 4 == 2 and st == 9:    # and another in the 3rd
                    continue
                if pos == 3 and st == 0:        # a breath on the 4th bar's downbeat
                    continue
                if pos == 7 and st >= 14:       # phrase end: a 32nd flutter rising into the 1
                    for j, v in enumerate((50, 62, 76, 90)):
                        out.append([60, o + 3.5 + j * 0.125, 0.1, v])
                    continue
                v = 127 * 10 ** ((db - (3 if brk else 0)) / 20.0) * rnd.uniform(0.9, 1.05)
                out.append([60, o + st * 0.25, 0.2, int(max(20, min(127, v)))])
        elif kind == "clap":                    # 2 and 4, a pickup closing every 4th bar
            for st, v in ((4, 104), (12, 108)):
                out.append([60, o + st * 0.25, 0.5, v])
            if pos in (3, 7):
                out.append([60, o + 15 * 0.25, 0.25, 72])
        elif kind == "ghost":                   # 909 snare (pad 38), quiet, two bar shapes
            shape = ((7, 38), (10, 30), (15, 44)) if (b - 1) % 2 == 0 else ((3, 32), (9, 36), (14, 40))
            if pos == 7:
                shape = ((7, 36), (13, 34), (14, 42), (15, 50))
            for st, v in shape:
                out.append([38, o + st * 0.25, 0.2, int(v * rnd.uniform(0.9, 1.1))])
        elif kind == "hat2":                    # the "e" and "a" only: a shuffle against the main hat
            for st in (1, 3, 5, 7, 9, 11, 13, 15):
                if (pos % 2 == 0 and st == 5) or (pos % 2 == 1 and st == 13):
                    continue
                v = (88 if st % 4 == 3 else 58) * rnd.uniform(0.88, 1.08)
                out.append([60, o + st * 0.25, 0.15, int(v)])
        elif kind == "open":
            for st in (2, 6, 10, 14):
                if pos == 7 and st == 14:       # the phrase breathes before its downbeat
                    continue
                if pos % 4 == 2 and st == 10:
                    continue
                out.append([60, o + st * 0.25, 0.3, int(rnd.uniform(92, 108))])
        elif kind == "bass":
            pat = BASS_A if (b - 1) % 2 == 0 else BASS_B
            for j, (st, pitch, ln) in enumerate(pat):
                if pos == 7 and st >= 11:       # space for the phrase's fill
                    continue
                if b in BASS_REST and st >= BASS_REST[b]:
                    continue
                v = 112 if j == 0 else int(rnd.uniform(92, 104))
                out.append([60 + pitch - 43, o + st * 0.25, ln * 0.25 * 0.92, v])
    # one pocket, baked: every off-16th of every written part (and the piano and the gate)
    # lands PIANO_SWING_S late; no pool groove on top, so nothing can drift apart
    sw = PIANO_SWING_S / BEAT_S
    for n in out:
        q = n[1] * 4
        if abs(q - round(q)) < 1e-6 and int(round(q)) % 2 == 1:
            n[1] = round(n[1] + sw, 4)
    return out


def stab_env(beat):
    bar = beat / 4.0 + 1
    return [{"param": "Frequency", "device": "Auto Filter", "unit": "display",
             "points": [[0, round(stab_freq(bar))], [8, round(stab_freq(bar + 2))]]}]


def vox_env(beat):
    """The phrase's last word thrown into the delay (send B), dry before it."""
    return [{"param": "send:1", "unit": "db", "points": [[0, -40], [13.9, -40], [14.0, -6], [16, -6]]}]


def warp_voices():
    from ableton_claude import server
    for track, (src, bpm, pre, det, bars) in VOICES.items():
        clear(track)
        r = server.rap_phrase(stem=OUT + src, source_bar=1, bars=4, source_bpm=bpm, source_downbeat=pre,
                              track=track, bar=bars[0], swing_ms=PIANO_SWING_S * 1000, name=track, out_dir=OUT)
        first = r["placed"]["beat"]
        for bar in bars[1:]:
            C("duplicate_clip", {"track": track, "clip": {"at": first}, "beat": (bar - 1) * 4.0 - 0.5})
        for c in C("get_track", {"track": track, "max_clips": 100})["clips"]:
            C("set_clip", {"track": track, "clip": {"at": c["start"]}, "detune": det})
        log(track, "warped per syllable")


def build(files):
    for track, (key, beats, warp, ranges) in PLAN.items():
        clear(track)
        env = {"VOX": vox_env, "VOX 2": vox_env}.get(track)
        for a, b in ranges:
            place(track, files[key], beats, a, b, warp, DETUNE.get(track, 0), envelopes=env)
        log(track, "placed")
    clear("KICK HP")
    for bar, kind in KICK_HP:
        place("KICK HP", files["kick_q" if kind == "q" else "kick_8"], 4, bar, bar + 1, False,
              gain_db=KICK_HP_GAIN[bar])
    clear("CRASH")
    for bar, kind in CRASHES:
        beat = (bar - 1) * 4.0
        if kind == "rev":
            beat = round(beat - CRASH_REV_S / BEAT_S - 0.02, 3)
        C("create_audio_clip", {"track": "CRASH", "path": CRASH_REV if kind == "rev" else CRASH,
                                "beat": beat, "name": "CRASH " + kind, "warp": False})
    warp_voices()
    clear("CHORDS")
    for a, b in PIANO_SPANS:
        for bar in range(a, b, 2):
            C("create_audio_clip", {"track": "CHORDS", "path": files["piano_" + piano_phrase(bar)],
                                    "beat": (bar - 1) * 4.0, "name": "PIANO " + piano_phrase(bar),
                                    "warp": False, "envelopes": stab_env((bar - 1) * 4.0)})
    log("CHORDS", "phrased")
    clear("PIANO GATE")
    for a, b in GATE_SPANS:
        for bar in range(a, b, 2):
            dens = 0.35 + 0.5 * (bar - a) / max(1, b - a - 2) if a == 113 else 0.55
            C("create_audio_clip", {"track": "PIANO GATE", "path": make_gate(bar, piano_phrase(bar), dens),
                                    "beat": (bar - 1) * 4.0, "name": "GATE", "warp": False})
    log("PIANO GATE", "chopped")
    for t in {x[0] for x in FX}:
        clear(t)
    for track, key, bar, bars in FX:
        if bars:
            place(track, files[key], bars * 4, bar, bar + bars, False)
        else:
            C("create_audio_clip", {"track": track, "path": files[key], "beat": (bar - 1) * 4.0,
                                    "name": track, "warp": False})
    for track, (_, kind, ranges) in GEN.items():
        clear(track)
        for a, b in ranges:
            bar = a
            while bar < b:
                n = min(8, b - bar)
                C("create_midi_clip", {"track": track, "beat": (bar - 1) * 4.0, "length": n * 4.0,
                                       "name": track, "notes": gen_notes(kind, bar, n)})
                bar += 8
        log(track, "written")
    for track, (_, part, ranges) in MIDI.items():
        clear(track)
        loop = kits.pattern("let_the_rhythm", 8, [part], None)[part]
        for a, b in ranges:
            bar = a
            while bar < b:
                n = min(8, b - bar) * 4.0
                C("create_midi_clip", {"track": track, "beat": (bar - 1) * 4.0, "length": n, "name": track,
                                       "notes": [x for x in loop if x[1] < n - 1e-3]})
                bar += 8
        log(track, "placed")
    for bar, beat, tracks in HOLES:
        for t in tracks:
            cut_at(t, (bar - 1) * 4.0 + beat)
    # the kick's prepared exit: its last beat before each break
    for bar in BREAKS:
        cut_at("KICK", (bar - 1) * 4.0 - 1.0)
    # the breath: the last 2 beats before each drop empty, but the voice and the reverse crash
    for bar in DROPS:
        for t in ("BASS BREAK", "KICK HP", "CHORDS", "FX RISER", "VOX 2", "VOX ADLIB", "STAB SS", "PIANO GATE") + tuple(MIDI) + tuple(GEN):
            cut_at(t, (bar - 1) * 4.0 - BREATH[bar])
    # the straight perc loop takes the pool's swing (it only follows while warped)
    pool = [g["name"] for g in C("grooves")["grooves"]]
    if GROOVE not in pool:
        C("load_device", {"track": "CLAP LTR", "path": "user_library/Grooves/%s.agr" % GROOVE})
    C("set_groove", {"name": GROOVE, "timing": 100, "random": 0, "velocity": 0, "groove_amount": 1.0})
    for t in tuple(MIDI):                     # the kit parts take the pool's 16ths 57 (= 15.5 ms)
        C("apply_groove", {"track": t, "groove": GROOVE})
    # the written parts carry it in their notes: their fresh clips get no pool groove


def mix():
    for t, db in LEVELS.items():
        C("set_track", {"track": t, "volume_db": db, "pan": PANS.get(t, 0.0)})
    for track, device, params in DEVICES:
        have = [d["name"] for d in C("get_track", {"track": track, "clips": False})["devices"]]
        if device not in have:
            C("load_device", {"track": track, "query": device, "roots": ["audio_effects"]})
        for p, v in params.items():
            setp(track, device, p, v)
    for track, params in SIMPLER.items():
        for p, v in params.items():
            C("set_param", {"track": track, "device": 0, "param": p, "display": v.replace(" ct", "").replace(" %", "")})
    for track, key in SIDECHAIN.items():
        C("set_device_input", {"track": track, "device": "Compressor", "source": key})
    for track, db in ATMOS.items():
        C("set_send", {"track": track, "send": 3, "db": db})
    for track, dbs in SENDS.items():
        for i, db in enumerate(dbs):
            if db is not None:
                C("set_send", {"track": track, "send": i, "db": db})


def cues():
    C("clear_cues")
    for name, bar in SECTIONS:
        C("set_cue", {"name": name, "bar": bar})


if __name__ == "__main__":
    C("set_tempo", {"bpm": BPM})
    files = make_files()
    ensure_tracks()
    mix()                      # devices first: the stab's clip envelopes address its Auto Filter
    build(files)
    cues()
    log("done")
