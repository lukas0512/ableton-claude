"""Get Up (working title): a new track after Phunky Phantom "Get Up Stand Up" (135 BPM, 1997/98,
vinyl-era), set on channel 1 of a fresh set by the producer (2026-11-06).

His brief: "quero usar bastante esses synths, usar as melodias... reinventar. Esses timbres são
bons, só que a compressão de antigamente era mais solta, ela tá bem aberta. Quero uma parada mais
fechada, mais groove, uma bateria mais pegada, crisp, mas não tão aguda, não tão aberta. Mas com a
mesma energia, bastante forte. Começar um esboço: um primeiro loop, um build-up e drop."

What the reference measures (listen / analyze_reference, 2026-11-06):
  - 135.0 BPM, hats swing 57 % (off-16ths 16 ms late), straight 909-style 16ths, an open hat on
    the "&", a clap layer full of ghosts; -9.0 LUFS integrated with a 12.5 dB crest and +3.4 dBTP
    (the "open", loose vinyl master), side/mid -10 dB.
  - harmony: Esus4 / Esus2 pads over an A bass (A 55 %, E 32 %, C 9 %): A dorian-minor colour;
    the synth stem sits +16 cents, the vocal +18, the bass -6.
  - bass: rolling off-beat ..x-x--x..x-x--x, 5.6 notes a bar, A1 register.
  - the vocal is a 2-bar chant repeated through the record (bars 73-88, 105-128, 144-208).

The new track, stage 1 (a sketch: loop, break, build, drop, 48 bars):
  - 130 BPM, closer to his 2027 tech house refs (129-130) and "mais groove"; the record's swing (57 %)
    baked into every written part, Live's pool groove neutralised.
  - drums: his Let The Rhythm kit (Nobody Kit samples), tighter than the record: one DRUMS bus with
    a Glue (2:1, 10 ms, range 4) and a -2.5 dB shelf at 9 kHz ("crisp, não tão aguda").
  - bass: written new on the record's notes (A, E, C, G), in the kick's holes.
  - the record's own synths (demucs 'other' stem) as loops, placed by place_loop after this script:
    SYNTH A (bar 64, the Esus4 riff) in the groove, BREAK CHORDS (bars 121-128) in the break and
    build, SYNTH B (bar 196, the loud lead section) in the drop. The chant from the break (121-122).

The loops (place_loop, with Live at the record's 135.017 BPM while placing, then back to 130: placed
at 130 the clip took the section file's length in seconds and lost ~2.6 beats at each section end):
  SYNTH A 1-16 Auto Filter 900 -> 3500 Hz by bar 9 (v1 opened to 8 kHz: the groove sat as full as the drop);
  BREAK CHORDS 17-24 at 1.8 kHz, 25-32 1.8 -> 10 kHz, volume -9 -> -4 dB, last 2 beats empty;
  SYNTH B 29-32 (the drop's lead previewed) 500 -> 3000 Hz, -16 -> -9 dB, last 2 beats empty;
  SYNTH B 33-48 at 8 kHz, volume held at -6.5 dB; every synth clip detuned -16 cents.
Master: Glue (2:1, 10 ms, auto, range 3, -19 dB) -> Limiter True Peak -1 dB, input 14 dB.
v2 measured (limiter +11): groove -11.2, break -12.2..-13.8, build -13.6 -> -10.8 -> -12.0 (lows out),
drop -10.0..-10.3 LUFS per 2 bars, -1.0 dBTP.

v3 (his notes on v2: "muita coisa fora de warp e fora de tempo e muito sem groove, mas a ideia vc
entendeu mais ou menos, é um hard house com uns bass de UKG às vezes, uma mistura"):
  - the warp: stem_loop snapped each warp marker to Beat This's own detection (20 ms frames, ±50 ms
    on this vinyl): beats of 400-500 ms in a 444 ms record, the loops wobbled. The record is steady
    (its DrumSep kick sits 0-8 ms from one global grid); the loops are now cut on the kick's grid
    (stem_remix.kick_beats, fitted as a line) and placed already pinned to their beats, so they are
    neither wobbling nor ~2.6 beats short at 130.
  - hard house, after his HARD HOUSE folder (22 refs, 140-150 BPM: Tidy, Glazby, Lisa Lashes, BK):
    straight-ish 16ths (refs swing 52 %, now 54 % instead of the record's 57), a 909 snare rolling the
    8ths with ghosts (refs' clap/perc xgX.X.X.), the open hat on every "&" louder, the classic
    off-beat bass ..x-..x-..x-..x- on the root (refs 95 % off the beat).
  - UKG "às vezes": a 2-step bass phrase (reese) carries the groove's first 8 and the break, and
    answers the off-beat bass in the 8th bar of every drop phrase.

    cd mcp_server && uv run python ../scripts/build_get_up.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client  # noqa: E402
from ableton_claude import stem_remix as SR  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

C = client.call
BPM = 130.0
BEAT_S = 60.0 / BPM
END = 49
SWING_PCT = 54.0                               # v3: hard house refs 52 % (record 57): straighter, still pushed
SW = (SWING_PCT - 50.0) / 100.0 * 0.5          # off-16th delay in beats (0.02 = 9 ms)
KIT = "user_library/Samples/Claude/Nobody Kit/"
OWN_DIR = os.path.expanduser("~/Music/Ableton/User Library/Samples/Claude/Get Up/")
GROOVE = "Swing 16ths 57"
REF_DIR = os.path.expanduser("~/Desktop/TRACKS 2027/House Bangers/")
STEMS = REF_DIR + "02. Phunky Phantom - Get Up Stand Up (Original Mix) elements/"
VOX_STEM = STEMS + "02. Phunky Phantom - Get Up Stand Up (Or - vocals.wav"
REF_BPM, REF_FIRST_BEAT_S = 135.017, 0.212
LOOPS = os.path.expanduser("~/Music/Ableton/User Library/Samples/Claude/Nobody Kit/")
CRASH_REV = os.path.expanduser(
    "~/Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs/The Producer School - Fiction - Indie Dance/"
    "TPS - Fiction - Project Files/Ableton Live/TPS - Fiction - Project File 02/"
    "TPS - Fiction - Project File 02 Project/Samples/Processed/Reverse/Crash 909 R.aif")
CRASH_REV_S = 1.11

GROOVE_BARS, BREAK_BARS, BUILD_BARS, DROP_BARS = (1, 17), (17, 25), (25, 33), (33, 49)
DROPS = [33]
ALL = ("groove", "break", "build", "drop")
DRUM_BUS = "DRUMS"

# track: (source, fader dB, pan, room send dB, Simpler settings, sections it plays)
TRACKS = {
    "KICK":       (KIT + "SCHT_Kick1.wav", -2.3, 0.0, None, {"Vol < Vel": "0.0 %"}, ("groove", "drop")),
    "KICK HP":    (KIT + "SCHT_Kick1.wav", -9.0, 0.0, None, {"Vol < Vel": "100 %"}, ("build", "drop")),
    "CLAP":       (KIT + "SCHT_Clap2.wav", -7.0, 0.0, -24.0, {"Vol < Vel": "35 %"}, ALL),
    "HAT 16":     (KIT + "HL_CH_CLOSED_HAT_SHOT_010.wav", -19.0, 0.0, -22.5, {"Vol < Vel": "100 %"}, ALL),
    "HAT OFF":    (KIT + "SCHT_Hat_Persona.wav", -11.0, 0.2, -21.0, {"Vol < Vel": "35 %"}, ALL),
    "HAT LIFT":   (KIT + "SCHT_Hat_Imite.wav", -13.0, -0.2, -21.0, {"Vol < Vel": "35 %"}, ("drop",)),
    "SHAKER":     (KIT + "KMRBI_AW_Shaker_One_Shot_Chuga.wav", -17.0, 0.35, -21.0, {"Vol < Vel": "35 %"}, ALL),
    # v3: hard house's rolling 909 snare on the 8ths, ghosts on the "e" of 1 and 3 (xgX.X.X.)
    "SNARE 909":  ("drums/909 Core Kit.adg", -14.0, -0.1, -24.0, None, ("groove", "build", "drop")),
    "RIDE":       ("drums/909 Core Kit.adg", -15.0, 0.1, -30.0, None, ("drop",)),
    "CRASH":      ("drums/909 Core Kit.adg", -11.0, 0.0, -24.0, None, ("break", "drop")),
    "BASS":       ("sounds/Bass/Basic FM House Bass.adg", -7.0, 0.0, None, None, ("groove", "drop")),
    "BASS BREAK": ("sounds/Bass/Basic FM House Bass.adg", -12.0, 0.0, None, None, ("break", "build")),
    # v3: the UKG side: a 2-step reese phrase (groove's first 8, the drop's phrase ends); -13 dB: at
    # -10 the groove read sub 50 % (hard house refs 26 %), bass -1.8 dB vs drums (refs -7)
    "BASS UKG":   ("sounds/Bass/Basic Reese Bass.adg", -13.0, 0.0, None, None, ("groove", "drop")),
}
BUS_MEMBERS = ["CLAP", "HAT 16", "HAT OFF", "HAT LIFT", "SHAKER", "SNARE 909", "RIDE", "PERC LOOP"]
AUDIO = {   # a played loop: human timing MIDI does not have
    "PERC LOOP": (LOOPS + "SCBB_Perc_120_Perola2.wav", 120, -19.0, -0.3, [(9, 17), (25, 33), (33, 49)]),
}
# the record's synths and chant: placed by place_loop / the vox clips, not written here
# v2: VOX -4 (the chant lifted the mix +1.5 LU and +4 dB at 4-10 kHz), SYNTH B +1.5 (groove and drop sat 0.5 LU apart)
LOOP_TRACKS = {"SYNTH A": (-8.0, -0.1), "BREAK CHORDS": (-9.0, 0.0), "SYNTH B": (-6.5, 0.1), "VOX": (-13.0, 0.0)}
FX = ["REV CRASH", "SUB BOOM"]
# the record's synths: (source bar, bars) in the 'other' stem, cut on the record's kick grid
OTHER_STEM = STEMS + "02. Phunky Phantom - Get Up Stand Up (Or - other.wav"
REF_MIX = REF_DIR + "02. Phunky Phantom - Get Up Stand Up (Original Mix).flac"
LOOP_DIR = STEMS + "claude-remix/"
LOOP_SRC = {"GUSU synth A": (64, 4), "GUSU synth B": (196, 4), "GUSU break chords": (121, 8)}
SYNTH_DETUNE = -16                             # the stem sits +16 cents
# (track, loop, start bar, end bar, filter from Hz, to Hz, open by beat, volume dB ramp, end gap beats)
PLACEMENTS = [
    ("SYNTH A", "GUSU synth A", 1, 17, 900, 3500, 32, None, 0),
    ("BREAK CHORDS", "GUSU break chords", 17, 25, 1800, 1800, None, None, 0),
    ("BREAK CHORDS", "GUSU break chords", 25, 33, 1800, 10000, None, (-9.0, -4.0), 2),
    ("SYNTH B", "GUSU synth B", 29, 33, 500, 3000, None, (-16.0, -9.0), 2),
    ("SYNTH B", "GUSU synth B", 33, 49, 8000, 8000, None, (-6.5, -6.5), 0),
]
EQ = {
    # "crisp, mas não tão aguda": the top of the hats and shaker trimmed, the drum bus shelf does the rest
    "HAT 16": {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "-3.0 dB"},
    "HAT OFF": {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "9.00 kHz", "8 Gain A": "-2.0 dB"},
    "SHAKER": {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "-4.0 dB"},
    "BASS": {"8 Filter On A": "On", "8 Filter Type A": "Low Pass 12dB", "8 Frequency A": "1.20 kHz"},
    "BASS UKG": {"8 Filter On A": "On", "8 Filter Type A": "Low Pass 12dB", "8 Frequency A": "1.80 kHz"},
    "SNARE 909": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "200 Hz",
                  "8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "-3.0 dB"},
    # the break/build bass keeps its sub (his rule: the low end never vanishes) but no body
    "BASS BREAK": {"8 Filter On A": "On", "8 Filter Type A": "Low Pass 48dB", "8 Frequency A": "300 Hz"},
    "KICK HP": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 48dB", "1 Frequency A": "180 Hz"},
    "RIDE": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "350 Hz"},
    # the record's synths: they sit over the new bass, not under it ("never above the root": A = 55 Hz,
    # these loops carry no bass; the stem's 'other' leaks some low mids)
    "SYNTH A": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "150 Hz"},
    "SYNTH B": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "150 Hz"},
    "BREAK CHORDS": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "150 Hz"},
    "VOX": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "180 Hz"},
}
HAT_DB = [-10.8, -2.4, -0.5, -2.0, -11.3, -3.4, -0.4, -2.6, -11.9, -3.4, -0.8, -2.4, -10.5, -2.8, -0.8, -1.6]

# the bass, MIDI numbers (A = 33 = 55 Hz): the record's notes (A, E, C, G), rolling in the kick's
# holes; call (A), answer (B), a turn closing each 8 (step, pitch, length in 16ths, velocity)
A1, C2, E1, G1, A2, D2, E2 = 33, 36, 28, 31, 45, 38, 40
BASS_A = [(2, A1, 2, 112), (5, A1, 1, 84), (7, A2, 1, 98), (10, A1, 2, 108), (13, A1, 1, 86), (15, G1, 1, 100)]
BASS_B = [(2, A1, 2, 110), (5, A2, 1, 90), (7, A1, 1, 96), (10, C2, 2, 104), (13, A1, 1, 84), (14, E1, 2, 102)]
BASS_TURN = [(2, A1, 2, 112), (6, C2, 1, 96), (7, C2, 1, 88), (10, G1, 1, 100), (11, A1, 1, 96),
             (13, E1, 1, 104), (15, A2, 1, 100)]
# v3 hard house: the off-beat bass on the root, an octave pop and a G push for movement
HH_A = [(2, A1, 1.6, 112), (6, A1, 1.6, 104), (10, A1, 1.6, 112), (14, A1, 1.6, 104)]
HH_B = [(2, A1, 1.6, 112), (6, A2, 1.4, 100), (10, A1, 1.6, 112), (13, G1, 0.8, 88), (14, A1, 1.6, 104)]
HH_C = [(2, A1, 1.6, 112), (6, A1, 1.6, 104), (10, C2, 1.6, 108), (14, G1, 1.6, 102)]
# UKG: a 2-step phrase, syncopated, rests where the off-beat bass would sit
UKG_1 = [(3, A1, 3, 112), (7, C2, 1, 92), (10, A1, 2, 104), (13, E2, 1, 88), (14, D2, 1, 90), (15, C2, 1, 96)]
UKG_2 = [(2, A1, 2, 108), (6, G1, 2, 100), (9, A1, 1, 88), (11, C2, 2, 104), (14, E1, 2, 102)]
UKG_ANSWER = [(2, A1, 1, 104), (3, A2, 1, 84), (6, G1, 1, 96), (7, A1, 2, 104), (10, C2, 1, 96),
              (11, D2, 1, 92), (13, E2, 1, 98), (15, A2, 1, 92)]
HUMAN_MS = {"SNARE 909": 5, "HAT 16": 6, "HAT OFF": 4, "HAT LIFT": 4, "SHAKER": 7, "BASS": 2, "BASS BREAK": 3, "BASS UKG": 4}


def log(*a):
    print(*a, flush=True)


def _is_option(v):
    return isinstance(v, str) and not (v[:1].isdigit() or v[:1] in "+-.")


def setp(track, device, param, v):
    args = {"track": track, "device": device, "param": param}
    if isinstance(v, float):
        args["value"] = v
    else:
        args["item" if _is_option(v) else "display"] = v
    return C("set_param", args)


def devs(track):
    return [d["name"] if isinstance(d, dict) else d for d in C("get_track", {"track": track, "clips": False})["devices"]]


def section(bar):
    for name, (a, b) in (("groove", GROOVE_BARS), ("break", BREAK_BARS), ("build", BUILD_BARS),
                         ("drop", DROP_BARS)):
        if a <= bar < b:
            return name
    return None


def bass_role(bar):
    """v3: (who, notes) per bar. UKG carries the groove's first 8 and the break; the hard house
    off-beat bass the groove's second 8 and the drop; UKG answers in every phrase's 8th bar."""
    sec, pos = section(bar), (bar - 1) % 8
    if sec in ("break", "build"):
        return "BASS BREAK", (UKG_1 if pos % 2 == 0 else UKG_2)
    if sec == "groove" and bar < 9:
        return "BASS UKG", (UKG_1 if pos % 2 == 0 else UKG_2)
    if pos == 7:
        return "BASS UKG", UKG_ANSWER
    return "BASS", (HH_A, HH_B, HH_A, HH_C, HH_A, HH_B, HH_C)[pos]


def make_files():
    """The chant (bars 121-122 of the record's vocal stem, its cleanest 2 bars, no drums under it)
    and an A sub boom for the drop's downbeat."""
    os.makedirs(OWN_DIR, exist_ok=True)
    vox = OWN_DIR + "chant 2 bars (ref 121).wav"
    if not os.path.exists(vox):
        y, sr = sf.read(VOX_STEM)
        bar = 4 * 60.0 / REF_BPM
        a = REF_FIRST_BEAT_S + 120 * bar - 0.010
        seg = y[int(a * sr): int((a + 2 * bar + 0.010) * sr)].copy()
        n_in, n_out = int(0.008 * sr), int(0.040 * sr)
        seg[:n_in] *= np.linspace(0, 1, n_in)[:, None]
        seg[-n_out:] *= np.linspace(1, 0, n_out)[:, None]
        sf.write(vox, seg, sr, subtype="PCM_24")
    boom = OWN_DIR + "sub_boom_A1.wav"
    if not os.path.exists(boom):
        sr = 44100
        t = np.arange(int(1.1 * sr)) / sr
        f = 55.0 + (75.0 - 55.0) * np.exp(-t / 0.04)
        y = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t / 0.35)
        y[: int(0.003 * sr)] *= np.linspace(0, 1, int(0.003 * sr))
        y[-int(0.05 * sr):] *= np.linspace(1, 0, int(0.05 * sr))
        sf.write(boom, np.stack([y, y], axis=1) * 0.5, sr, subtype="PCM_24")
    return {"vox": vox, "boom": boom}


def cut_loops():
    """The record's synth loops on its own kick grid, swing untouched (the record's feel passes
    through: markers on its straight 16ths)."""
    g = SR.source_grid(REF_MIX, bpm_hint=REF_BPM, cache_dir=LOOP_DIR)
    kick = SR.kick_stem_for(OTHER_STEM)
    beats = SR.kick_beats(kick, LOOP_DIR) if kick else g["beats"]
    x, rate = SR.read_stereo(OTHER_STEM)
    loops = {}
    for name, (bar, bars) in LOOP_SRC.items():
        loops[name] = SR.cut_loop(x, rate, LOOP_DIR + name + ".wav", g["bpm"], g["downbeat"], bar, bars,
                                  0.0, beats)
        loops[name]["name"] = name
        SR.save_meta(LOOP_DIR, name, loops[name])
        six = [s for b, s in loops[name]["markers"] if b == int(b)]
        log(name, "beats %.0f-%.0f ms" % (1000 * min(np.diff(six)), 1000 * max(np.diff(six))))
    return loops


def place_loops(loops):
    for t in {p[0] for p in PLACEMENTS}:
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": END + 8})
    for t, name, a, b, f0, f1, open_by, ramp, gap in PLACEMENTS:
        path, mk = SR.section_file(loops[name], b - a, LOOP_DIR + "sections/%s %d-%d.wav" % (name, a, b - 1))
        beats = (b - a) * 4 - gap
        SR.ensure_auto_filter(C, t)
        envs = [SR.filter_envelope(f0, f1, beats, open_by)]
        if ramp:
            envs.append({"param": "volume", "unit": "db", "points": [[0, ramp[0]], [beats, ramp[1]]]})
        r = SR.place_warped(C, t, path, (a - 1) * 4.0, beats, mk, envs, name="%s %d-%d" % (name, a, b - 1))
        C("set_clip", {"track": t, "clip": {"at": (a - 1) * 4.0}, "detune": SYNTH_DETUNE})
        clip = [c for c in C("get_track", {"track": t})["clips"] if abs(c["start"] - (a - 1) * 4.0) < .01][0]
        log(t, a, b, "clip %.2f beats (want %.2f)" % (clip["end"] - clip["start"], beats), "trimmed" if r["trimmed"] else "")


def audio_track(name):
    names = [t["name"] for t in C("get_song")["tracks"]]
    if name not in names:
        C("create_track", {"kind": "audio", "name": name})
        C("set_track_input", {"track": name, "source": "No Input"})


def ensure_tracks():
    song = C("get_song")
    ref = song["tracks"][0]
    if ref["name"] != "REF - Get Up Stand Up":
        C("set_track", {"track": 0, "name": "REF - Get Up Stand Up"})
    C("set_track", {"track": "REF - Get Up Stand Up", "mute": True})
    # the drum bus first, so the kit lands under it
    audio_track(DRUM_BUS)
    C("set_track", {"track": DRUM_BUS, "monitoring": "in", "volume_db": 0.0})
    for dev in ("Glue Compressor", "EQ Eight"):
        if dev not in devs(DRUM_BUS):
            C("load_device", {"track": DRUM_BUS, "query": dev, "roots": ["audio_effects"]})
    # Glue's Attack/Release are steps (raw 5 = 10 ms, 6 = Auto); Range reads positive
    for p, v in {"Ratio": "2", "Attack": 5.0, "Release": 6.0, "Range": "4.00 dB",
                 "Threshold": "-22.0 dB", "Output": "1.0 dB"}.items():
        try:
            setp(DRUM_BUS, "Glue Compressor", p, v)
        except Exception as e:
            log("glue:", p, e)
    for p, v in {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "9.00 kHz",
                 "8 Gain A": "-2.5 dB"}.items():
        setp(DRUM_BUS, "EQ Eight", p, v)
    names = [t["name"] for t in C("get_song")["tracks"]]
    for t, (src, fader, pan, send, simpler, _) in TRACKS.items():
        if t not in names:
            C("create_track", {"kind": "midi", "name": t})
        if not devs(t):
            C("load_device", {"track": t, "path": src})
        for p, v in (simpler or {}).items():
            setp(t, 0, p, v)
        C("set_track", {"track": t, "volume_db": fader, "pan": pan})
        C("set_send", {"track": t, "send": 0, "db": send if send is not None else -70.0})
    for t, (path, _, fader, pan, _) in AUDIO.items():
        audio_track(t)
        C("set_track", {"track": t, "volume_db": fader, "pan": pan})
        C("set_send", {"track": t, "send": 0, "db": -22.0})
    for t, (fader, pan) in LOOP_TRACKS.items():
        audio_track(t)
        C("set_track", {"track": t, "volume_db": fader, "pan": pan})
        C("set_send", {"track": t, "send": 0, "db": -70.0})
    for t in FX:
        audio_track(t)
    C("set_track", {"track": "REV CRASH", "volume_db": -16.0})
    C("set_track", {"track": "SUB BOOM", "volume_db": -9.0})
    for t, bands in EQ.items():
        if "EQ Eight" not in devs(t):
            C("load_device", {"track": t, "query": "EQ Eight", "roots": ["audio_effects"]})
        for p, v in bands.items():
            setp(t, "EQ Eight", p, v)
    for t in BUS_MEMBERS:
        C("set_track_output", {"track": t, "dest": DRUM_BUS})
    # the bass: the kick owns the first ~120 ms (6:1, 0.1 ms, 120 ms; S/C EQ off: it hears the body)
    for t in ("BASS", "BASS BREAK", "BASS UKG"):
        if "Compressor" not in devs(t):
            C("load_device", {"track": t, "query": "Compressor", "roots": ["audio_effects"]})
        for p, v in {"Ratio": "6.00 : 1", "Attack": "0.10 ms", "Release": "120 ms",
                     "Threshold": "-30.0 dB", "S/C EQ On": "Off"}.items():
            try:
                setp(t, "Compressor", p, v)
            except Exception as e:
                log(t, "comp:", p, e)
        try:
            C("set_device_input", {"track": t, "device": "Compressor", "source": "KICK", "channel": "Post FX"})
        except Exception as e:
            log(t, "sidechain:", e)
    # v3 render: the reese was stereo in its lows (corr 0.77 under 120 Hz, -2.4 dB in mono)
    if "Utility" not in devs("BASS UKG"):
        C("load_device", {"track": "BASS UKG", "query": "Utility", "roots": ["audio_effects"]})
    setp("BASS UKG", "Utility", "Bass Mono", "On")
    setp("BASS UKG", "Utility", "Bass Freq", "200 Hz")
    if "RIM 909" in [t["name"] for t in C("get_song")["tracks"]]:
        C("delete_track", {"track": "RIM 909"})       # v2's Chicago ghosts, replaced by SNARE 909
    for t in reversed(C("get_song")["tracks"]):
        if re.fullmatch(r"\d+-(MIDI|Audio)", t["name"]) and not t["devices"] and not t["clips"]:
            C("delete_track", {"track": t["i"]})
    # one short room for the kit (return A)
    for p, v in {"Decay Time": "0.80 s", "Predelay": "5.00 ms", "Dry/Wet": "100 %"}.items():
        try:
            setp("return:0", "Reverb", p, v)
        except Exception as e:
            log("room:", p, e)


def _swing(notes, rnd, kind=None):
    sc = HUMAN_MS.get(kind, 2) / 1000.0 / BEAT_S
    for n in notes:
        q = n[1] * 4
        on_grid = abs(q - round(q)) < 1e-6
        if on_grid and int(round(q)) % 2 == 1:
            n[1] += SW
        if not (on_grid and int(round(q)) % 4 == 0):
            n[1] = round(max(0.0, n[1] - rnd.uniform(0.0, sc)), 4)
    return notes


def notes(kind, bar0, n_bars):
    rnd = np.random.default_rng(abs(hash((kind, bar0))) % 2 ** 32)
    out = []
    for k in range(n_bars):
        b = bar0 + k
        sec = section(b)
        pos = (b - 1) % 8
        o = k * 4.0
        last = b == BUILD_BARS[1] - 1
        if kind == "KICK":
            for beat in range(4):
                if b == GROOVE_BARS[1] - 1 and beat == 3:
                    continue                # the prepared exit
                out.append([60, o + beat, 1.0, 127])
        elif kind == "KICK HP":
            if sec == "drop":               # a ghost on the "& of 3" every 2nd bar: more pegada
                if pos % 2 == 1:
                    out.append([60, o + 2.5, 0.25, int(rnd.uniform(52, 64))])
            elif sec == "build":            # the pulse: quarters, then 8ths, velocity rising
                i = b - BUILD_BARS[0]
                step = 1.0 if i < 5 else 0.5
                t = 0.0
                while t < 4.0 - 1e-9:
                    if not (last and t >= 2.0):
                        frac = (i * 4 + t) / 32.0
                        out.append([60, o + t, 0.25, int(56 + 44 * frac)])
                    t += step
        elif kind == "CLAP":                # 2 and 4, the record's ghosts as a pickup into 4 and a phrase end
            hits = [(4, 106), (12, 110)]
            if pos % 2 == 1:
                hits.append((11, 58))       # a ghost before 4, every 2nd bar
            if pos == 7:
                hits += [(2, 64), (14, 70), (15, 82)]
            for st, v in hits:
                if last and st >= 8:
                    continue
                out.append([60, o + st * 0.25, 0.25, int(v * rnd.uniform(0.94, 1.04))])
        elif kind == "HAT 16":
            brk = sec == "break"
            for st in range(16):
                if brk and st % 4 == 0:
                    continue
                if last and st >= 8:
                    continue
                if pos % 2 == 1 and st == 13:
                    continue
                if pos % 4 == 2 and st == 9:
                    continue
                if pos == 3 and st == 0:
                    continue
                if pos == 7 and st >= 14 and sec != "build":
                    for j, v in enumerate((48, 60, 74, 88)):
                        out.append([60, o + 3.5 + j * 0.125, 0.1, v])
                    continue
                v = 127 * 10 ** (HAT_DB[st] / 20.0) * rnd.uniform(0.86, 1.04)
                out.append([60, o + st * 0.25, 0.15, int(max(18, min(127, v)))])
        elif kind in ("HAT OFF", "HAT LIFT"):
            for st in (2, 6, 10, 14):
                if (pos == 7 and st == 14) or (last and st >= 8):
                    continue
                out.append([60, o + st * 0.25, 0.3, int(rnd.uniform(94, 110))])
        elif kind == "SHAKER":
            for st in (2, 3, 6, 7, 10, 11, 14, 15):
                if last and st >= 8:
                    continue
                v = rnd.uniform(90, 104) if st % 4 == 3 else rnd.uniform(58, 72)
                out.append([60, o + st * 0.25 - (0.005 / BEAT_S if st % 4 == 2 else 0.0), 0.12, int(v)])
        elif kind == "SNARE 909":           # hard house: the 8ths rolling, ghosts on the "e" of 1 and 3
            if sec == "groove" and b < 5:
                continue                    # enters at bar 5: one new layer per 4 bars
            hits = {0: 58, 1: 36, 2: 92, 4: 82, 6: 92, 8: 58, 9: 36, 10: 92, 12: 82, 14: 92}
            if pos == 7 and sec != "build":
                hits.update({13: 54, 15: 70})   # a pickup closing each 8, not a roll
            for st, v in hits.items():
                if last and st >= 8:
                    continue
                out.append([38, o + st * 0.25, 0.12, int(v * rnd.uniform(0.9, 1.08))])
        elif kind == "RIDE":
            for st in (2, 6, 10, 14):
                out.append([51, o + st * 0.25, 0.3, int(rnd.uniform(92, 104))])
        elif kind == "CRASH":
            if b == BREAK_BARS[0]:
                out.append([49, o, 1.0, 70])
            if b in DROPS or b == DROPS[0] + 8:
                out.append([49, o, 1.0, 110 if b in DROPS else 90])
        elif kind in ("BASS", "BASS BREAK", "BASS UKG"):
            who, pat = bass_role(b)
            if who != kind:
                continue
            if kind == "BASS BREAK" and sec == "build" and b >= BUILD_BARS[1] - 2:
                continue                    # the low end leaves for the build's last 2 bars
            for st, p, ln, v in pat:
                out.append([p, o + st * 0.25, ln * 0.25 * 0.85, int(v * rnd.uniform(0.95, 1.03))])
    return out if kind in ("KICK", "CRASH") else _swing(out, rnd, kind)


def place_audio_loop(track, path, src_bpm, a, b):
    beats = round(sf.info(path).duration * src_bpm / 60.0)
    C("create_audio_clip", {"track": track, "path": path, "bar": a, "name": track, "warp": True,
                            "beats": beats, "warp_mode": "beats"})
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
                C("create_midi_clip", {"track": t, "bar": bar0, "length": n * 4.0,
                                       "name": "%s %s" % (t, name), "notes": notes(t, bar0, n)})
        log(t, "written")
    for t, (path, bpm, _, _, spans) in AUDIO.items():
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": END + 8})
        for a, b in spans:
            place_audio_loop(t, path, bpm, a, b)
        log(t, "placed")
    for t in FX + ["VOX"]:
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": END + 8})
    for bar in DROPS:
        beat = (bar - 1) * 4.0
        if os.path.exists(CRASH_REV):
            C("create_audio_clip", {"track": "REV CRASH", "path": CRASH_REV, "warp": False, "name": "REV CRASH",
                                    "beat": round(beat - CRASH_REV_S / BEAT_S - 0.02, 3)})
        C("create_audio_clip", {"track": "SUB BOOM", "path": files["boom"], "warp": False,
                                "name": "SUB BOOM A", "beat": beat})
    # the chant: 2 bars of the record, warped to 130 and tuned (-18 cents); where it speaks:
    # the groove's last 2 bars (announcing the break), the break's 1st and 5th bar, the drop's 2nd 8
    for bar in (15, 17, 21, 41, 45):
        C("create_audio_clip", {"track": "VOX", "path": files["vox"], "bar": bar, "name": "VOX chant",
                                "warp": True, "beats": 8, "warp_mode": "complex_pro", "detune": -18})
    if GROOVE not in [g["name"] for g in C("grooves")["grooves"]]:
        C("load_device", {"track": "PERC LOOP", "path": "user_library/Grooves/%s.agr" % GROOVE})
    # the pool's 57 file at (54-50)/7 amount = the written parts' 54 %
    C("set_groove", {"name": GROOVE, "timing": 100, "random": 0, "velocity": 0,
                     "groove_amount": round((SWING_PCT - 50.0) / 7.0, 3)})
    for t in AUDIO:
        C("apply_groove", {"track": t, "groove": GROOVE})
    for g in C("grooves")["grooves"]:
        if g["name"] != GROOVE:
            C("set_groove", {"name": g["name"], "timing": 0, "random": 0, "velocity": 0})
    if not C("get_song")["is_playing"]:
        C("clear_cues")
        C("set_tempo", {"bpm": BPM})
        for name, bar in (("GROOVE - record's riff, kit tight", 1), ("BREAK - kick out, chords + chant", 17),
                          ("BUILD - HP kick, chords open, breath", 25), ("DROP - crash, sub, lead synth, ride", 33)):
            C("set_cue", {"name": name, "bar": bar})
    C("set_tempo", {"bpm": BPM})
    assert abs(C("get_song")["tempo"] - BPM) < 1e-6, "Live's tempo is not %s" % BPM


if __name__ == "__main__":
    files = make_files()
    loops = cut_loops()
    C("set_tempo", {"bpm": BPM})
    ensure_tracks()
    build(files)
    place_loops(loops)
    log("done")
