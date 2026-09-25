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

Theme, tension and release (the user's second ask: "repetitiva, sem tema, sem tensao e
alivio, falta atmosfera"): a two-bar call and two-bar response in C minor hexatonic
(music.melody, seed 7) on Live's Atmo Pluck, hinted in the stab section (call only,
filtered), stated over the second groove, driven through the build with its filter
opening, full in the drop and echoed (response only) after it; the pad carries a real
progression under the grooves (Cm9 - Fm9 - Cm9 - Abmaj7 over the C pedal bass) and in
the main break climbs Cm9 - Abmaj9 - Fm9 - G7sus4 with its low-pass opening over 16 bars
(clip envelope), so the drop resolves a dominant; an 8-bar snare roll, the kick back four
bars early, a two-beat cut before the drop with only the vocal call and the reverse crash
left, a down-pitched kick impact on the drop; vibe chords answer the vocal in the second
half of the drop; pad, theme, stab, organ and vibes duck to the kick through a Compressor
with a real sidechain (set_device_input), and the returns get room (reverb 3.5 s, delay
filtered) for atmosphere.

Re-running is safe: clips are synced to the plan (missing ones added, strays removed,
existing ones kept), devices are loaded only when missing and their parameters set.

    build_after_midnight.py
"""
import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client, knowledge, loops  # noqa: E402
from ableton_claude.music import harmony as MH, melody  # noqa: E402

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
IMPACT = os.path.join(HITS, "FX/DCW_126_Kick_Down_Fx.wav")                  # down-pitched kick
VIBES = os.path.expanduser("~/Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs/"
                           "Loopmasters - Ultimate Deep House/WAV_LOOPS/MUSIC_LOOPS/NSL_125_Cm_VibeChords.wav")
THEME_INSTRUMENT = "sounds/Guitar & Plucked/Atmo Pluck.adg"
THEME_SEED = 7
THEME_CHORDS = ("Cm9", "Cm9", "Fm9", "Fm9")
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
    "Kick":      [(1, 49), (57, 71), (73, 89), (105, 119), (121, 151), (153, 185)],   # 2-bar gaps at phrase ends
    "Hats":      [(1, 57, "closed"), (57, 89, "open"), (97, 137, "open"), (137, 185, "closed")],   # open = lifted sections
    "Ghost":     [(17, 49, "a"), (57, 89, "a"), (93, 105, "a"), (105, 137, "b"), (137, 169, "a")],
    "Tops 1":    [(9, 57), (105, 169)],                # both top layers only in the drop
    "Tops 2":    [(57, 89), (97, 137)],                # main break: hats and tops return at 97
    "Perc Tops": [(33, 57), (73, 81), (89, 153)],      # out at 81-89 so the drop tops the pre-break
    "Clap":      [(17, 169)],                          # stays through breaks (81 % of references)
    "Bass":      [(17, 49), (57, 89), (97, 169)],      # back before the kick: groove without pulse
    "Stab":      [(33, 37), (41, 57), (65, 89), (93, 101), (105, 145)],   # shown, taken away, returned; drives the drop
    "Organ":     [(73, 89), (145, 153)],               # one supporting voice; returns known
    "Vox Chops": [(49, 57), (65, 73), (89, 105), (113, 137)],   # silent for the drop's first 8: the theme speaks
    "FX 1":      [(45, 49), (85, 89), (101, 105)],
    "FX 2":      [(49, 53), (89, 93), (137, 141), (181, 185)],
    "Riser":     [(101, 105)],
}
REMOVE_TRACKS = ["Roll", "Vibes"]                      # one story: too many voices were speaking
HITS_PLAN = {  # track: [(bar, variant)] one-shots on downbeats (reverse crash ends on it)
    "Crash": [(17, "hit"), (57, "hit"), (105, "hit"), (137, "hit"), (57, "rev"), (105, "rev")],
    "Impact": [(105, "hit")],
}
PREDROP_CUT = None                             # the references keep everything but the kick
PREDROP_TRACKS = []
# bar: (call?, response?, filter Hz, velocity scale) for the theme
THEME_PLAN = {41: (1, 0, 1200, 0.7), 45: (1, 0, 1200, 0.7),                 # hint: the question alone
              65: (1, 1, 3000, 0.9), 73: (1, 1, 3000, 0.9), 81: (1, 1, 3000, 0.9),
              97: (1, 0, None, 0.75), 99: (1, 0, None, 0.85), 101: (1, 0, None, 0.95), 103: (1, 0, None, 1.0),
              105: (1, 1, 12000, 1.0), 113: (1, 1, 12000, 1.0),
              121: (1, 1, 12000, 1.0), 129: (1, 1, 12000, 1.0),               # climax: octave doubled
              137: (0, 1, 8000, 0.85), 145: (0, 1, 8000, 0.85)}               # echo: the answer alone
THEME_OCTAVE_BARS = (121, 129)
THEME_UP_BARS = (103,)                  # the last question rises an octave into the drop
THEME_SWING = 60.0
# pad: (start, end, chords, bars per chord, velocity, filter points [[beat, Hz], ...])
PAD_PLAN = [
    (29, 31, ["Cm9"], 2, 40, [[0, 700], [8, 700]]),                     # a glimpse before the break
    (49, 57, ["Cm9", "Fm9"], 4, 84, [[0, 400], [32, 3000]]),
    (57, 89, ["Cm9", "Fm9", "Cm9", "Abmaj7"] * 4, 2, 48, [[0, 1800], [128, 1800]]),   # scenery, not a voice
    (89, 105, ["Cm9", "Cm9", "Abmaj9", "Abmaj9", "Fm9", "Fm9", "G7sus4", "G7sus4"], 2, 92,
     [[0, 300], [32, 900], [56, 4000], [64, 14000]]),                # dominant + filter = tension
    (105, 137, ["Cm9", "Fm9", "Cm9", "Abmaj7"] * 4, 2, 52, [[0, 3000], [128, 3000]]),
    (137, 153, ["Cm9", "Fm9"] * 2, 4, 60, [[0, 2500], [64, 2500]]),
]
SIDECHAIN = ["Pad", "Theme", "Stab", "Stab iv", "Organ"]      # duck to the kick
# buses: Live's API makes no group tracks, so tracks route into audio tracks that monitor
# in; each family is glued by one compressor and shares one short room (return C)
BUSES = {"Drum Bus": ["Kick", "Hats", "Tops 1", "Tops 2", "Perc Tops", "Clap", "Ghost", "Crash", "Impact"],
         "Music Bus": ["Stab", "Stab iv", "Organ", "Pad", "Theme"],
         "Vox Bus": ["Vox Chops", "Vox Call"]}
RETURNS = ["Reverb", "Delay", "Room"]        # Live shows them as A-Reverb, B-Delay, C-Room
VOX_CALLS = [44, 48, 71, 79, 88, 104, 116, 156, 164]   # the voice answers the theme (bar 7 of its phrase)
STAB_IV = [(87, 89), (135, 137)]               # Cm -> Fm turnaround; the Cm stab is cut there
KICK_DROPS = [45, 85]                          # the kick clip that loses its last beat
TOPS_SWUNG = ["Tops 1", "Tops 2", "Perc Tops"]
# the open hat, crash, snare ghosts and risers of v6 put 2-6 kHz at 4.5 % (references
# 1.6-3.2) and the riser + FX filled the four bars before the drop (drop jump 1.7 LU):
# transitions sit under the drums, not on top of them
LEVELS = {"Kick": -8.0, "Clap": -6.0, "Hats": -19.5, "Ghost": -16.0, "Tops 1": -13.0,
          "Tops 2": -13.0, "Perc Tops": -5.5, "Bass": -10.5, "Stab": -4.0, "Stab iv": -4.0,
          "Organ": -8.0, "Vox Chops": -6.0, "Vox Call": -6.0, "FX 1": -18.0, "FX 2": -14.0,
          "Riser": -20.0, "Crash": -18.0, "Pad": -14.0, "Theme": -9.0, "Impact": -12.0,
          "Drum Bus": 0.0, "Music Bus": 0.0, "Vox Bus": 0.0}
PANS = {"Hats": -0.1, "Tops 1": -0.25, "Tops 2": 0.25, "Perc Tops": 0.3, "Stab": 0.1,
        "Stab iv": 0.1, "Organ": -0.1, "Ghost": 0.15, "Theme": -0.15}
SENDS = {  # track: [A-Reverb (hall) dB, B-Delay dB, C-Room (short, glues the drums) dB]
    "Pad": [-14.0, None, None], "Stab": [-18.0, -22.0, -14.0], "Stab iv": [-18.0, -22.0, -14.0],
    "Organ": [-20.0, None, -16.0], "Vox Chops": [-16.0, -14.0, None], "Vox Call": [-14.0, -10.0, None],
    "Hats": [None, None, -22.0], "Clap": [None, None, -12.0], "Ghost": [None, -20.0, -14.0],
    "Perc Tops": [None, None, -16.0], "Tops 1": [None, None, -20.0], "Tops 2": [None, None, -20.0],
    "Crash": [-14.0, None, None], "Theme": [-14.0, -10.0, None]}
# v2's Drum Buss boom and bass saturation, made moot by the new kick; Dynamic Tube did not
# change this bass (its 2nd+3rd harmonics already sit 8-19 dB over the fundamental)
REMOVE = [("Kick", "Drum Buss"), ("Bass", "Saturator"), ("Bass", "Dynamic Tube")]
# (track, device, {param: number/text for the display, or an option name})
DEVICES = [
    # never above a root: a 34 Hz cut under the C1 bass and a 200 Hz one under the C3 pad
    # made the ear hear G minor (G1 took over the low end)
    ("Bass", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "25.0 Hz"}),
    # a clean mix: below 180 Hz belongs to kick and bass; the stab's and organ's 300 Hz
    # mud goes; the hats own nothing under 400 Hz
    ("Organ", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "200 Hz",
                           "2 Filter On A": "On", "2 Filter Type A": "Bell", "2 Frequency A": "350 Hz",
                           "2 Gain A": "-3.0 dB", "2 Q A": "1.0"}),
    ("Stab", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "160 Hz",
                          "2 Filter On A": "On", "2 Filter Type A": "Bell", "2 Frequency A": "300 Hz",
                          "2 Gain A": "-3.0 dB", "2 Q A": "1.0"}),
    ("Stab iv", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "160 Hz"}),
    ("Theme", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "220 Hz"}),
    ("Vox Chops", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "180 Hz"}),
    ("Vox Call", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "180 Hz"}),
    ("Clap", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "150 Hz"}),
    ("Ghost", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "200 Hz"}),
    ("Perc Tops", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "200 Hz"}),
    ("Crash", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "300 Hz"}),
    ("Riser", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "300 Hz"}),
    ("Hats", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "400 Hz",
                          "7 Filter On A": "Off"}),     # the new hats are dark already
    ("Tops 1", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "250 Hz",
                            "7 Filter On A": "On", "7 Filter Type A": "High Shelf",
                            "7 Frequency A": "10.0 kHz", "7 Gain A": "-4.0 dB"}),
    ("Tops 2", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "250 Hz",
                            "7 Filter On A": "On", "7 Filter Type A": "High Shelf",
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
                         "1 Frequency A": "180 Hz", "7 Filter On A": "Off"}),  # scenery sits above the bass
    ("return:A-Reverb", "Reverb", {"Decay Time": "3.5 s", "Predelay": "15 ms"}),
    ("return:C-Room", "Hybrid Reverb", {"Algo Type": "Quartz", "Decay": "0.6 s", "Size": "30 %",
                                        "Predelay": "5 ms", "Dry/Wet": "100 %"}),   # a short room, shared
    ("Drum Bus", "Glue Compressor", {"Threshold": "-10 dB", "Ratio": "4", "Attack": "3",
                                     "Release": ".2", "Output": "2.0 dB"}),      # ms, ratio, s
    ("Music Bus", "Glue Compressor", {"Threshold": "-14 dB", "Ratio": "2", "Attack": "30",
                                      "Release": ".4", "Output": "1.0 dB"}),
    ("Music Bus", "EQ Eight", {"1 Filter Type A": "High Pass 12dB", "1 Frequency A": "150 Hz"}),
    ("Vox Bus", "Compressor", {"Threshold": "-18 dB", "Ratio": "3.00 : 1", "Attack": "5.00 ms",
                               "Release": "60 ms", "Makeup": "On"}),
    ("return:B-Delay", "Delay", {"Ping Pong": "On", "Feedback": "35 %", "Filter On": "On",
                                 "Filter Freq": "1.2 kHz", "Filter Width": "6.0"}),
    ("Theme", "Auto Filter", {"Filter Type": "Low-pass", "Resonance": "12 %"}),
    ("Pad", "Auto Filter", {"Filter Type": "Low-pass", "Resonance": "10 %"}),
    ("Stab", "Auto Filter", {"Filter Type": "Low-pass", "Resonance": "8 %", "Frequency": "20.0 kHz"}),
    ("master", "Limiter", {"Input Gain": "10.4 dB"}),
]


COMPRESSOR = {"Threshold": "-22 dB", "Ratio": "4.00 : 1", "Attack": "1.00 ms", "Release": "90 ms",
              "Auto Release On/Off": "Off", "Makeup": "Off", "S/C On": "On", "S/C EQ On": "Off"}


def log(*a):
    print(*a, flush=True)


def _is_option(v):
    return isinstance(v, str) and not (v[:1].isdigit() or v[:1] in "+-.")


def setp(track, device, param, v):
    args = {"track": track, "device": device, "param": param}
    if isinstance(v, str) and v.startswith("item:"):
        args["item"] = v[5:]
    else:
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
    files["Impact:hit"] = IMPACT
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
    for c in clips:                                    # a kept clip that must now end earlier
        if c["start"] in have and "length" in want[c["start"]][1] and c["end"] > c["start"] + want[c["start"]][1]["length"] + 1e-3:
            C("trim_clip", {"track": track, "clip": {"at": c["start"]}, "end_beat": c["start"] + want[c["start"]][1]["length"]})
    for beat in sorted(set(want) - have):
        path, o = want[beat]
        args = {"track": track, "path": path, "beat": beat, "warp": bool(o.get("warp")), "name": track}
        for k in ("warp_mode", "detune", "pitch", "envelopes"):
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
            C("set_warp_markers", {"track": track, "clip": {"at": beat}, "beats": o.get("beats", LOOP_BEATS)})
            C("set_clip", {"track": track, "clip": {"at": beat}, "end_marker": b})
            C("set_clip", {"track": track, "clip": {"at": beat}, "looping": True, "loop_start": a, "loop_end": b})
        if "length" in o:
            C("trim_clip", {"track": track, "clip": {"at": beat}, "end_beat": beat + o["length"]})
    return len(set(want) - have), len({c["start"] for c in clips} - have)


# automation with a purpose, as clip envelopes (Live's API writes no arrangement lanes):
# (track, param, device, unit) -> points per 4-bar clip at bar X, default when None
AUTOMATION = {
    # the stab's low-pass closes over the 8 bars into the main break: tension by taking away
    "Stab": ("Frequency", "Auto Filter", "display", lambda bar: {
        33: [[0, 1200], [16, 1200]], 41: [[0, 1500], [16, 3000]], 45: [[0, 3000], [16, 9000]],
        81: [[0, 20000], [16, 4000]], 85: [[0, 4000], [16, 600]]}.get(bar, [[0, 20000], [16, 20000]])),
    # the vocal's last phrase of every loop throws into the delay
    "Vox Chops": ("send:1", None, "db", lambda bar: [[0, -14], [12, -14], [12.01, -5], [16, -5]]),
    # the bass leans in for the drop
    "Bass": ("volume", None, "db", lambda bar: [[0, -8.5], [16, -8.5]] if 105 <= bar < 137 else [[0, -10.5], [16, -10.5]]),
}


def loop_wants(files, track, ranges):
    want = {}
    for r in ranges:
        a, b = r[:2]
        variant = r[2] if len(r) > 2 else None
        opts = {"warp": True, "warp_mode": "complex_pro", "detune": VOX_DETUNE} if track == "Vox Chops" else {}
        if track in TOPS_SWUNG:
            opts = {"warp": True, "warp_mode": "beats"}
        step = 4
        if track == "Roll":
            step = 8                                            # an 8-bar file
        for bar in range(a, b, step):
            o = dict(opts)
            if bar + step > b:                                  # a range ending mid-loop: a gap
                o["length"] = (b - bar) * 4.0
            if track in AUTOMATION:
                param, device, unit, pts = AUTOMATION[track]
                o["envelopes"] = [{"param": param, "device": device, "points": pts(bar), "unit": unit}]
            want[(bar - 1) * 4.0] = (path_for(files, track, variant), o)
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
    stab = C("get_track", {"track": "Stab", "max_clips": 500})["clips"]
    for a, b in STAB_IV:                                              # the Cm stab makes room
        for c in stab:
            if c["start"] < (a - 1) * 4.0 < c["end"]:
                C("trim_clip", {"track": "Stab", "clip": {"at": c["start"]}, "end_bar": a})
    for t in (PREDROP_TRACKS if PREDROP_CUT else []):                 # two beats of air
        for c in C("get_track", {"track": t, "max_clips": 500})["clips"]:
            if c["start"] < PREDROP_CUT < c["end"]:
                C("trim_clip", {"track": t, "clip": {"at": c["start"]}, "end_beat": PREDROP_CUT})


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


def _env(points, send_a=None):
    env = [{"param": "Frequency", "device": "Auto Filter", "points": points, "unit": "display"}]
    if send_a:
        env.append({"param": "send:0", "points": send_a, "unit": "db"})
    return env


def pad_clips():
    """The pad's chords, voice-led (common tones held, changes on the 'and' of 4), with
    its low-pass drawn into each clip; the main break ends two beats early (the cut)."""
    C("delete_clips_in_range", {"track": "Pad", "start_bar": 1, "end_bar": END})
    for a, b, chords, per, vel, pts in PAD_PLAN:
        notes, _ = MH.progression_notes(chords, per, 53, 77, 4, 0.5, vel)
        length = (b - a) * 4.0
        if b == 105 and PREDROP_CUT:
            notes = [[p, st, min(d, PREDROP_CUT - (a - 1) * 4.0 - st), v] for p, st, d, v in notes
                     if st < PREDROP_CUT - (a - 1) * 4.0]
        send_a = [[0, -14], [length, -6]] if b in (57, 105) else [[0, -14], [length, -14]]   # breaks: the room grows
        C("create_midi_clip", {"track": "Pad", "bar": a, "length": length, "notes": notes,
                               "name": " ".join(dict.fromkeys(chords)), "envelopes": _env(pts, send_a)})


def theme_clips():
    """One motif for the whole track: the call asks (ends on the 2nd degree), the response
    answers (ends on the tonic). Where it plays, how open its filter is and how hard it is
    hit change per section; the build's two statements open the filter over 8 bars."""
    C("delete_clips_in_range", {"track": "Theme", "start_bar": 1, "end_bar": END})
    m = melody.call_and_response("C", "minor_hexatonic", THEME_CHORDS, 2, (62, 79), (55, 74), THEME_SEED)
    m = {k: MH.swing(v, THEME_SWING) for k, v in m.items() if k in ("call", "response")}   # same feel as the hats
    for bar, (call, resp, hz, scale) in sorted(THEME_PLAN.items()):
        for part, on, offset in (("call", call, 0), ("response", resp, 8)):
            if not on:
                continue
            notes = [[p, st, d, int(v * scale)] for p, st, d, v in m[part]]
            if bar in THEME_OCTAVE_BARS:
                notes += [[p - 12, st, d, int(v * 0.6)] for p, st, d, v in notes]
            if bar in THEME_UP_BARS:
                notes = [[p + 12, st, d, v] for p, st, d, v in notes]
            start = (bar - 1) * 4.0 + offset
            if hz is None:                                        # build: 97 -> 105, opening
                f0 = 2000 + (start - 384.0) / 32.0 * 8000
                pts = [[0, f0], [8, f0 + 2000]]
            else:
                pts = [[0, hz], [8, hz]]
            env = _env(pts)
            throw = -4 if bar == 103 else -10                      # the last question echoes into the drop
            env.append({"param": "send:1", "points": [[0, throw], [8, throw]], "unit": "db"})
            C("create_midi_clip", {"track": "Theme", "beat": start, "length": 8.0, "notes": notes,
                                   "name": "%s %s" % (part, bar), "envelopes": env})


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
    for track in SIDECHAIN:
        ensure_device(track, "Compressor")
        for p, v in COMPRESSOR.items():
            setp(track, "Compressor", p, v)
        r = C("set_device_input", {"track": track, "device": "Compressor", "source": "Kick", "channel": "Post Mixer"})
        log("  %-15s sidechain <- %s %s" % (track, r["type"], r["channel"]))


def main():
    C("set_tempo", {"bpm": BPM})
    order = list(PLAN) + list(HITS_PLAN) + ["Vox Call", "Stab iv", "Pad", "Theme"] + list(BUSES)
    song = C("get_song")
    before = [t["name"] for t in song["tracks"]]
    for name in order:
        if name not in before:
            C("create_track", {"kind": "midi" if name in ("Pad", "Theme") else "audio", "name": name})
    have_returns = [r["name"] for r in song.get("returns", [])]
    for name in RETURNS:
        if not any(r.endswith("-" + name) for r in have_returns):
            C("create_return", {"name": name})
    for bus, members in BUSES.items():
        C("set_track_input", {"track": bus, "source": "No Input"})   # never the interface's mic
        C("set_track", {"track": bus, "monitoring": "in"})
        for m in members:
            C("set_track_output", {"track": m, "dest": bus})
    for name in reversed(before):                      # the blank set's empty default tracks
        if name in order:
            continue                                   # (a set must keep at least one track,
        info = C("get_track", {"track": name})         #  so ours are created first)
        if not info.get("clips") and not info.get("devices"):
            C("delete_track", {"track": name})
    for name in REMOVE_TRACKS:
        if name in before:
            C("delete_track", {"track": name})
    files = make_loops()
    for name, (param, device, unit, pts) in AUTOMATION.items():
        if device:                          # a clip envelope needs its device before the clip
            ensure_device(name, device)
        if name in before:                  # sync keeps matching clips: envelopes need fresh ones
            C("delete_clips_in_range", {"track": name, "start_bar": 1, "end_bar": END})
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
    if not C("get_track", {"track": "Theme", "clips": False})["devices"]:
        C("load_device", {"track": "Theme", "path": THEME_INSTRUMENT})
    mix()                                   # devices first: clip envelopes need Auto Filter
    pad_clips()
    theme_clips()
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
