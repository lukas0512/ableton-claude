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
DETUNE = {"BASS": 12, "BASS BREAK": 12, "STAB": 28, "VOX": 20, "CHORDS": 31}
VOX2 = PACKS + "Loopmasters - Ultimate Vocals MULTiFORMAT/HOUSE_VOCALS/PHRASES/UVOX_126_Gm_GUEYEHYEH.wav"
CHORDS = PACKS + "Loopmasters - Ultimate Deep House/WAV_LOOPS/MUSIC_LOOPS/NSL_122_Gm_SoftChord.wav"
GROOVE = "Swing 16ths 57"

SECTIONS = [("INTRO A - drums, DJ", 1), ("INTRO B - bass 17, perc 21, stab 25, voice teaser 29", 17),
            ("GROOVE - stab open", 33), ("BREAK 1 - kick out, groove stays", 49),
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

# track: (file key, beats per file, warped?, [(start_bar, end_bar)])
PLAN = {
    "KICK":       ("kick", 16, False, [(1, 49), (65, 97), (121, END)]),
    "CLAP":       ("clap", 16, False, [(9, END)]),
    "HATS 16":    ("hats", 16, False, [(1, END)]),
    "OPEN HAT":   ("open", 16, False, [(13, 49), (73, 97), (129, 153), (153, 169)]),
    "PERC":       ("perc", 16, True, [(21, 49), (57, 97), (105, 153), (153, 169)]),
    "BASS":       ("bass", 8, True, [(17, 49), (65, 97), (121, 169)]),
    "BASS BREAK": ("bass", 8, True, [(53, 65), (105, 121)]),
    "STAB":       ("stab", 8, True, [(25, 161)]),
    # the two voices trade: "Here is the solution" states, "Gueyehyeh" answers; the solution
    # line also runs a cappella through each build's breath into the drop
    "VOX":        ("vox", 16, True, [(29, 33), (41, 45), (61, 65), (73, 77), (89, 93), (101, 105),
                                     (117, 121), (129, 133), (145, 149)]),
    "VOX 2":      ("vox2", 16, True, [(81, 85), (109, 113), (137, 141)]),
    # the soft chords (stab 1): scenery under the breaks, doubling the stab in drop 2
    "CHORDS":     ("chords", 8, True, [(49, 65), (97, 121), (121, 153)]),
}
# the producer's own drums (let_the_rhythm kit) over kit A: the syncopated clap with its
# pickups and 32nd ramp, the early shaker, congas, the rolling 909 tom, the reserved ride
# and the late rims. 8-bar loops aligned to the phrases (their fills close each phrase).
# track: (instrument, kit part, [(start_bar, end_bar)])
MIDI = {
    "CLAP LTR": ("user_library/Samples/Claude/Nobody Kit/SCHT_Clap2.wav", "clap",
                 [(17, 49), (49, 65), (65, 97), (97, 121), (121, 169)]),
    "SHAKER":   ("user_library/Samples/Claude/Nobody Kit/KMRBI_AW_Shaker_One_Shot_Chuga.wav",
                 "hat_off_shaker_shot", [(9, 49), (53, 65), (65, 97), (101, 121), (121, 177)]),
    "CONGAS":   ("Percussion Core Kit", "congas", [(33, 49), (49, 65), (73, 97), (97, 121), (121, 169)]),
    "TOM 909":  ("909 Core Kit", "tom_909", [(41, 49), (81, 97), (121, 153)]),
    "RIDE":     ("909 Core Kit", "ride", [(73, 97), (121, 153)]),
    "RIM 909":  ("909 Core Kit", "rim_909", [(137, 169)]),
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
    for a, b, f0, f1 in ramps:
        if a <= bar <= b:
            x = (bar - a) / float(b - a)
            return f0 * (f1 / float(f0)) ** x            # exponential: even in the ear
    return 20000


LEVELS = {"FX RISER": -20.0, "FX DOWN": -18.0, "FX IMPACT": -12.0, "SUB BOOM": -14.0,
          "CLAP LTR": -9.0, "SHAKER": -18.0, "CONGAS": -15.0, "TOM 909": -18.0, "RIDE": -21.0,
          "RIM 909": -17.0, "VOX 2": -14.0, "CHORDS": -17.0,
          "KICK": -6.0, "KICK HP": -9.0, "CLAP": -15.0, "HATS 16": -17.0, "OPEN HAT": -19.0,
          "PERC": -19.0, "CRASH": -20.0, "BASS": -9.0, "BASS BREAK": -17.0, "STAB": -14.0,
          "VOX": -13.0}
PANS = {"OPEN HAT": 0.2, "PERC": -0.25, "STAB": 0.08, "SHAKER": 0.35, "CONGAS": 0.26,
        "TOM 909": -0.18, "RIDE": 0.1, "RIM 909": 0.12, "CHORDS": -0.12}
# (track, device, {param: display text or option})
DEVICES = [
    ("KICK HP", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 48dB", "1 Frequency A": "180 Hz"}),
    ("CLAP", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "150 Hz"}),
    ("HATS 16", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "350 Hz"}),
    ("OPEN HAT", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "400 Hz"}),
    ("PERC", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "250 Hz"}),
    ("CRASH", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "300 Hz"}),
    ("STAB", "EQ Eight", {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "160 Hz"}),
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
    ("STAB", "Auto Filter", {"Filter Type": "Low-pass", "Resonance": "10 %"}),
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
# sends: [A-Reverb (plate), B-Delay, C-Room (short, every drum)]
SENDS = {"CLAP": [None, None, -14.0], "HATS 16": [None, None, -22.0], "OPEN HAT": [None, None, -20.0],
         "PERC": [None, None, -18.0], "STAB": [-16.0, -22.0, None], "VOX": [-16.0, -18.0, None],
         "CRASH": [-16.0, None, None], "CLAP LTR": [None, None, -16.0], "SHAKER": [None, None, -21.0],
         "CONGAS": [None, None, -20.0], "TOM 909": [None, None, -22.0], "VOX 2": [-16.0, -18.0, None],
         "CHORDS": [-14.0, None, None], "FX RISER": [-18.0, None, None], "FX DOWN": [-16.0, None, None]}


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
         "bass": BASS, "stab": STAB, "vox": VOX, "perc": PERC, "vox2": VOX2, "chords": CHORDS}
    loops.write(f["kick"], loops.four_on_floor(KICK_SHOT, BPM))
    loops.write(f["clap"], loops.from_template({"default": CLAP_SHOT}, T["clap"]["template"], BPM,
                                               steps=[4, 12], seed=1, swing_pct=SWING))
    loops.write(f["hats"], loops.from_template({"default": HAT_SHOT}, T["hats"]["template"], BPM,
                                               steps=[0, 1, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15], seed=1, swing_pct=SWING))
    loops.write(f["open"], loops.from_template({"default": OPEN_SHOT}, T["hats"]["template"], BPM,
                                               steps=[2, 6, 10, 14], seed=1, swing_pct=SWING))
    f["riser4"] = loops.stretch_to(RISER, OUT + "P6_Riser_4bars_129.wav", BPM, 4)
    f.update(down=DOWNLIFTER, impact=IMPACT, boom=SUB_BOOM)
    loops.write(f["kick_q"], loops.four_on_floor(KICK_SHOT, BPM, bars=1))
    loops.write(f["kick_8"], loops.four_on_floor(KICK_SHOT, BPM * 2, bars=2))   # 8 hits in one bar
    return f


def ensure_tracks():
    names = [t["name"] for t in C("get_song")["tracks"]]
    for old in ("BASS 1 - DCW", "STAB 1 - Soft Chord", "VOX 1 - Gueyehyeh"):   # version 1, not chosen
        if old in names:
            C("delete_track", {"track": old})
    for old, new in (("BASS 2 - NSL", "BASS"), ("STAB 3 - SS Chord", "STAB"), ("VOX 4 - Solution", "VOX")):
        if old in names:
            C("set_track", {"track": old, "name": new})
    names = [t["name"] for t in C("get_song")["tracks"]]
    for t in ["KICK HP", "PERC", "BASS BREAK", "CRASH", "VOX 2", "CHORDS", "FX RISER", "FX DOWN",
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
    returns = [r["name"] for r in C("get_song")["returns"]]
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
            args.update(beats=beats, warp_mode="complex_pro" if track not in ("PERC",) else "beats")
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


def stab_env(beat):
    bar = beat / 4.0 + 1
    return [{"param": "Frequency", "device": "Auto Filter", "unit": "display",
             "points": [[0, round(stab_freq(bar))], [8, round(stab_freq(bar + 2))]]}]


def vox_env(beat):
    """The phrase's last word thrown into the delay (send B), dry before it."""
    return [{"param": "send:1", "unit": "db", "points": [[0, -40], [13.9, -40], [14.0, -6], [16, -6]]}]


def build(files):
    for track, (key, beats, warp, ranges) in PLAN.items():
        clear(track)
        env = {"STAB": stab_env, "VOX": vox_env, "VOX 2": vox_env}.get(track)
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
    for t in {x[0] for x in FX}:
        clear(t)
    for track, key, bar, bars in FX:
        if bars:
            place(track, files[key], bars * 4, bar, bar + bars, False)
        else:
            C("create_audio_clip", {"track": track, "path": files[key], "beat": (bar - 1) * 4.0,
                                    "name": track, "warp": False})
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
    # the kick's prepared exit: its last beat before each break
    for bar in BREAKS:
        cut_at("KICK", (bar - 1) * 4.0 - 1.0)
    # the breath: the last 2 beats before each drop empty, but the voice and the reverse crash
    for bar in DROPS:
        for t in ("CLAP", "HATS 16", "OPEN HAT", "PERC", "BASS BREAK", "STAB", "KICK HP", "CHORDS",
                  "FX RISER") + tuple(MIDI):
            cut_at(t, (bar - 1) * 4.0 - BREATH[bar])
    # the straight perc loop takes the pool's swing (it only follows while warped)
    pool = [g["name"] for g in C("grooves")["grooves"]]
    if GROOVE not in pool:
        C("load_device", {"track": "PERC", "path": "user_library/Grooves/%s.agr" % GROOVE})
    C("set_groove", {"name": GROOVE, "timing": 100, "random": 0, "velocity": 0, "groove_amount": 1.0})
    for t in ("PERC",) + tuple(MIDI):
        C("apply_groove", {"track": t, "groove": GROOVE})


def mix():
    for t, db in LEVELS.items():
        C("set_track", {"track": t, "volume_db": db, "pan": PANS.get(t, 0.0)})
    for track, device, params in DEVICES:
        have = [d["name"] for d in C("get_track", {"track": track, "clips": False})["devices"]]
        if device not in have:
            C("load_device", {"track": track, "query": device, "roots": ["audio_effects"]})
        for p, v in params.items():
            setp(track, device, p, v)
    for track, key in SIDECHAIN.items():
        C("set_device_input", {"track": track, "device": "Compressor", "source": key})
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
