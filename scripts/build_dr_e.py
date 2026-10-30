"""Projeto #8 (DR E): an original house track after the sound and form of a daverose.music
Instagram reel ("This one's coming out on Halloween", 2026-10-30), with Lukas's bounce.

His brief: "quero que a nossa track use a dele de referência, o áudio do vídeo"; asked which
way, he chose a new track that mixes them: the reference's sound and form, his own pocket
(swing ~57 %) and the snare pulling the groove (Mochakk C's lesson).

The reference, measured (listen + analyze_reference on
~/Desktop/Tracks/refs_from_reels/daverose_halloween_reel.wav, 53 s):
  - 130 BPM, E minor (bass on G/E/A = b3/1/4), chords m11/maj9 that change ~4.6 times per
    8 bars; hats straight 16ths (swing 50 %, spread 3 ms): we keep the tempo and key, not
    the straight feel.
  - form of the clip: clap+hats intro, groove, a 16-bar break (kick and bass out, chords
    and voice in, -3.4 LU), a drop with everything back.
  - dark and heavy: sub 39 % + low 35 % of the power, mid 15 %, 2-6 kHz 2.3 %, highs 1.8 %;
    bass only 1.2 dB under the drums, 93 % off the beat, ~6 short notes a bar; a busy
    clap/perc layer with ghosts; the chords 18 dB under the drums.
Borrowed: feel and numbers, never his notes. The bass line, chords and drums are ours.

Lessons kept from today: hits on the grid, hands only push ahead, quarters never move;
one-shots' Vol < Vel 20-35 % (ghosts quieter, not "fofos"); clap dry.

Form: INTRO 1-4, GROOVE 5-12, BREAK 13-28, DROP 29-36.

    cd mcp_server && uv run python ../scripts/build_dr_e.py        (DR_CHORD=<file> to swap chords)
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
sys.path.insert(0, os.path.dirname(__file__))
from ableton_claude import client  # noqa: E402
import numpy as np  # noqa: E402
from build_mochakk_c import log, setp, devs, dedupe, CRASH_REV, CRASH_REV_S  # noqa: E402

C = client.call
BPM = 130.0
BEAT_S = 60.0 / BPM
SWING_PCT = 57.0                                # his pocket (Dub House Streets, Mochakk set median)
SW = (SWING_PCT - 50.0) / 100.0 * 0.5          # off-16th delay in beats (16 ms at 130)
INTRO, GROOVE, BREAK, DROP = (1, 5), (5, 13), (13, 29), (29, 37)
END = 37
KIT = "user_library/Samples/Claude/Nobody Kit/"
OWN = "user_library/Samples/Claude/DR E/"
OWN_DIR = os.path.expanduser("~/Music/Ableton/User Library/Samples/Claude/DR E/")
WA = os.path.expanduser("~/Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs/"
                        "Wave Alchemy - Chords and Stabs/resampled & effected/")
# chords already in E minor (a stock keys timbre failed him twice: audition these by ear)
CHORD_CHOICES = {"crystal": "key & piano/wasc_key_crystal_Emin11.wav",
                 "clean": "chords/wasc_chord_clean_Emin9.wav",
                 "reso": "stab/wasc_stab_Reso_Emin9.wav",
                 "bright": "key & piano/wasc_key_bright_Emin9.wav"}
CHORD_NAME = os.environ.get("DR_CHORD", "crystal")
CHORD_FILE = os.path.basename(CHORD_CHOICES[CHORD_NAME])

ALL = ("intro", "groove", "break", "drop")
# track: (source, fader dB, pan, room send dB, Simpler settings, sections)
TRACKS = {
    "KICK":     (KIT + "SCHT_Kick1.wav", -2.3, 0.0, None, {"Vol < Vel": "0.0 %"}, ("groove", "drop")),
    "CLAP":     (KIT + "SCHT_Clap2.wav", -9.5, 0.0, -26.0, {"Vol < Vel": "20 %"}, ALL),
    "SNARE":    (KIT + "AT_Infinite_Space_Snare_One_Shot_Resonate.wav", -8.0, 0.0, -24.0,
                 {"Vol < Vel": "35 %"}, ALL),
    "HAT":      (KIT + "HL_CH_CLOSED_HAT_SHOT_010.wav", -22.0, 0.05, -26.0, {"Vol < Vel": "35 %"}, ALL),
    "HAT OPEN": (KIT + "SCHT_Hat_Persona.wav", -16.0, 0.2, -24.0, {"Vol < Vel": "30 %"}, ("groove", "drop")),
    "SHAKER":   (KIT + "KMRBI_AW_Shaker_One_Shot_Chuga.wav", -19.0, 0.35, -24.0, {"Vol < Vel": "35 %"},
                 ("break", "drop")),
    "PERC":     ("drums/909 Core Kit.adg", -6.0, -0.2, -24.0, None, ALL),      # the busy ghost layer
    "BASS":     (KIT + "C_BinBassTone_01_SP.wav", -15.5, 0.0, None, {"Volume": "0.0 dB"}, ("groove", "drop")),
    "BASS BREAK": (KIT + "C_BinBassTone_01_SP.wav", -24.0, 0.0, None, {"Volume": "0.0 dB"}, ("break",)),
    "CHORDS":   (OWN + CHORD_FILE, -12.0, -0.1, -18.0, {"Vol < Vel": "40 %"}, ALL),
    "CRASH":    ("drums/909 Core Kit.adg", -12.0, 0.0, -24.0, None, ("drop",)),
}
CLASSIC = {"BASS": "30.0 ms", "BASS BREAK": "80.0 ms", "CHORDS": "90.0 ms"}   # note length = sound length
EQ = {
    "HAT": {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "-2.0 dB"},
    "BASS BREAK": {"8 Filter On A": "On", "8 Filter Type A": "Low Pass 48dB", "8 Frequency A": "300 Hz"},
    "CHORDS": {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "220 Hz"},
}
ATMOS_SENDS = {"CHORDS": -14.0}

BIN = 36                                        # BinBassTone is C1 at Simpler's 60
E1, A1, B1 = 28 + BIN, 33 + BIN, 35 + BIN
# chords: the Em sample at 60; Am a 4th under, Bm a 4th under too (darker than above)
PROG = [(60, E1), (60, E1), (53, A1), (55, B1)]  # 4 bars: i i iv v (minor v: no D#)


def chord_of(bar):
    return PROG[(bar - 1) % 4]


# the bass: ours, every attack off the quarters (the reference's 93 % off the beat), 1/b3/4/8
def bass_pattern(bar):
    r = chord_of(bar)[1]
    pos = (bar - 1) % 8
    if pos == 7:                                # the turn into the next 8
        return [(2, r, 2, 108), (6, r + 3, 1, 96), (9, r + 5, 1, 100), (11, r + 7, 1, 104), (14, r + 10, 1, 96)]
    if pos % 2 == 0:
        return [(2, r, 2, 108), (6, r + 3, 1, 96), (7, r, 1, 82), (10, r + 12, 1, 98), (13, r + 5, 2, 104)]
    return [(3, r, 1, 100), (6, r + 3, 2, 104), (9, r, 1, 86), (11, r + 7, 1, 94), (14, r + 3, 1, 98), (15, r, 1, 80)]


def bass_holes(bar):
    busy = {st for st, *_ in bass_pattern(bar)}
    return [st for st in range(16) if st not in busy]


SNARE_A = [(4, 88), (12, 92), (7, 64), (10, 52), (15, 76)]
SNARE_B = [(4, 88), (12, 92), (3, 50), (9, 60), (14, 70)]
SNARE_FILL = [(9, 70), (11, 84), (13, 92), (14, 78), (15, 100)]      # groovy, not a roll
SNARE_INTO_DROP = [(0, 70), (3, 76), (6, 82), (8, 88), (11, 94), (14, 100)]   # 3-3-2 rising
HAT_VEL = [52, 72, 104, 78] * 4                 # on, e, &, a
PERC_STEPS = [(2, 70), (3, 44), (6, 64), (7, 40), (9, 48), (10, 66), (11, 38), (13, 42), (14, 58)]
CHORD_GROOVE = [[(3, 2, 100), (10, 1, 84)], [(6, 2, 96), (14, 1, 88)]]       # sparse, to mark
HUMAN_MS = {"SNARE": 5, "PERC": 7, "HAT": 5, "HAT OPEN": 4, "SHAKER": 6, "CHORDS": 4, "BASS": 3}


def section(bar):
    for name, (a, b) in (("intro", INTRO), ("groove", GROOVE), ("break", BREAK), ("drop", DROP)):
        if a <= bar < b:
            return name


def _swing(notes, rnd, kind):
    """One pocket: off-16ths SW late; hands only push ahead; quarters stay on the grid."""
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
        o = k * 4.0
        sec = section(b)
        pos = (b - 1) % 8
        into_drop = b == DROP[0] - 1
        if kind == "KICK":
            for st in (0, 4, 8, 12):
                out.append([60, o + st * 0.25, 0.25, 120])
        elif kind == "CLAP":
            if into_drop:
                out.append([60, o + 1.0, 0.25, 100])
                continue
            for st in (4, 12):
                out.append([60, o + st * 0.25, 0.25, int(104 * rnd.uniform(0.95, 1.03))])
        elif kind == "SNARE":
            hits = list(SNARE_A if pos % 2 == 0 else SNARE_B)
            if sec in ("intro", "break"):
                hits = [(st, v * 0.85) for st, v in hits if st not in (4, 12)]
            if pos == 7:
                hits = [h for h in hits if h[0] < 9] + SNARE_FILL
            if into_drop:
                hits = SNARE_INTO_DROP
            for st, v in hits:
                out.append([60, o + st * 0.25, 0.2, int(min(127, v * rnd.uniform(0.92, 1.06)))])
        elif kind == "HAT":
            for st in range(16):
                if sec == "intro" and st % 2 == 0 and st % 4 != 2:
                    continue
                if into_drop and st >= 12:
                    continue                    # the breath before the drop
                out.append([60, o + st * 0.25, 0.1, int(HAT_VEL[st] * rnd.uniform(0.9, 1.08))])
        elif kind == "HAT OPEN":
            for st in (2, 6, 10, 14):
                out.append([60, o + st * 0.25, 0.25, int(rnd.uniform(78, 92))])
        elif kind == "SHAKER":
            for st in range(1, 16, 2):
                if into_drop and st >= 12:
                    continue
                out.append([60, o + st * 0.25, 0.1, int((96 if st % 4 == 3 else 64) * rnd.uniform(0.9, 1.08))])
        elif kind == "PERC":                    # rim 37 in the bass's holes, a clave 39 answer on the turn
            holes = set(bass_holes(b)) if sec in ("groove", "drop") else set(range(16))
            for st, v in PERC_STEPS:
                if st in holes and not (into_drop and st >= 12):
                    out.append([37, o + st * 0.25, 0.1, int(v * rnd.uniform(0.85, 1.12))])
            if pos == 7 and sec != "break":
                out.append([39, o + 3.5, 0.1, 82])
        elif kind == "CRASH":
            if b == DROP[0]:
                out.append([49, o, 1.0, 110])
        elif kind in ("BASS", "BASS BREAK"):
            for st, p, ln, v in bass_pattern(b):
                if into_drop and st >= 12:
                    continue
                out.append([p, o + st * 0.25, ln * 0.25 * 0.9, v])
        elif kind == "CHORDS":
            root = chord_of(b)[0]
            if sec == "break":                  # held chords: the night under the break
                if into_drop:
                    out.append([root, o, 3.0, 100])
                elif (b - BREAK[0]) % 2 == 0:
                    out.append([root, o, 7.5, int(92 + 6 * ((b - BREAK[0]) / 16))])
                continue
            if sec == "intro" and b < INTRO[1] - 2:
                continue
            for st, ln, v in CHORD_GROOVE[(b - 1) % 2]:
                out.append([root, o + st * 0.25, ln * 0.25, v])
    return _swing(out, rnd, kind) if kind not in ("KICK", "CRASH") else out


def make_files():
    os.makedirs(OWN_DIR, exist_ok=True)
    for rel in CHORD_CHOICES.values():
        dst = OWN_DIR + os.path.basename(rel)
        if not os.path.exists(dst):
            shutil.copy(WA + rel, dst)


def ensure_tracks():
    song = C("get_song")
    names = [t["name"] for t in song["tracks"]]
    if any(n in names for n in ("PIANO", "KEYS CHOP", "STAB HI")):
        raise SystemExit("this is the Mochakk C set: open a new Live set (Projeto #8) first")
    for t, (src, fader, pan, send, simpler, _) in TRACKS.items():
        if t not in names:
            C("create_track", {"kind": "midi", "name": t})
        have = devs(t)
        if t == "CHORDS" and have and have[0] != CHORD_FILE[:-4]:
            C("delete_device", {"track": t, "device": 0})     # swapping the chord timbre
            have = devs(t)
        if not have:
            C("load_device", {"track": t, "path": src})
        if t in CLASSIC:
            C("set_device_prop", {"track": t, "device": 0, "prop": "playback_mode", "value": 0})
            setp(t, 0, "Ve Release", CLASSIC[t])
        for p, v in (simpler or {}).items():
            setp(t, 0, p, v)
        C("set_track", {"track": t, "volume_db": fader, "pan": pan})
        C("set_send", {"track": t, "send": 0, "db": send if send is not None else -70.0})
    for t, bands in EQ.items():
        if "EQ Eight" not in devs(t):
            C("load_device", {"track": t, "query": "EQ Eight", "roots": ["audio_effects"]})
        for p, v in bands.items():
            setp(t, "EQ Eight", p, v)
    for t in TRACKS:
        dedupe(t)
    if not any(r["name"].endswith("Atmos") for r in C("get_song")["returns"]):
        C("create_return", {"name": "Atmos"})
    returns = [r["name"] for r in C("get_song")["returns"]]
    atm = [r for r in returns if r.endswith("Atmos")][0]
    ret = "return:" + atm
    if "Hybrid Reverb" not in devs(ret):
        C("load_device", {"track": ret, "query": "Hybrid Reverb", "roots": ["audio_effects"]})
    if "EQ Eight" not in devs(ret):
        C("load_device", {"track": ret, "query": "EQ Eight", "roots": ["audio_effects"]})
    dedupe(ret)
    for p, v in {"Decay": "3.50 s", "Predelay": "25.0 ms", "Dry/Wet": "100 %"}.items():
        setp(ret, "Hybrid Reverb", p, v)
    for p, v in {"1 Filter On A": "On", "1 Filter Type A": "High Pass 12dB", "1 Frequency A": "350 Hz",
                 "8 Filter On A": "On", "8 Filter Type A": "Low Pass 12dB", "8 Frequency A": "6.00 kHz"}.items():
        setp(ret, "EQ Eight", p, v)
    C("set_track", {"track": ret, "volume_db": -6.0})
    for t, db in ATMOS_SENDS.items():
        C("set_send", {"track": t, "send": returns.index(atm), "db": db})
    if "REV CRASH" not in names:
        C("create_track", {"kind": "audio", "name": "REV CRASH"})
        C("set_track_input", {"track": "REV CRASH", "source": "No Input"})
    C("set_track", {"track": "REV CRASH", "volume_db": -16.0})
    for t in reversed(C("get_song")["tracks"]):          # Live's empty default tracks
        if re.fullmatch(r"\d+-(MIDI|Audio)", t["name"]) and not t["devices"] and not t["clips"]:
            C("delete_track", {"track": t["i"]})
    for p, v in {"Decay Time": "0.80 s", "Predelay": "5.00 ms", "Dry/Wet": "100 %"}.items():
        try:
            setp("return:0", "Reverb", p, v)
        except Exception as e:
            log("room:", p, e)


def build():
    spans = {"intro": INTRO, "groove": GROOVE, "break": BREAK, "drop": DROP}
    for t, (*_, secs) in TRACKS.items():
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": END + 8})
        for name in secs:
            a, b = spans[name]
            for bar0 in range(a, b, 8):
                n = min(8, b - bar0)
                C("create_midi_clip", {"track": t, "bar": bar0, "length": n * 4.0,
                                       "name": "%s %s" % (t, name), "notes": notes(t, bar0, n)})
        log(t, "written")
    C("delete_clips_in_range", {"track": "REV CRASH", "start_bar": 1, "end_bar": END + 8})
    C("create_audio_clip", {"track": "REV CRASH", "path": CRASH_REV, "warp": False, "name": "REV CRASH",
                            "beat": round((DROP[0] - 1) * 4.0 - CRASH_REV_S / BEAT_S - 0.02, 3)})
    # Live's default pool groove would double the swing written in the notes
    for g in C("grooves")["grooves"]:
        C("set_groove", {"name": g["name"], "timing": 0, "random": 0, "velocity": 0})
    if not C("get_song")["is_playing"]:
        C("clear_cues")
        for name, bar in (("INTRO", 1), ("GROOVE - kick and bass", 5), ("BREAK - chords, no kick", 13),
                          ("DROP", 29)):
            C("set_cue", {"name": name, "bar": bar})
    C("set_tempo", {"bpm": BPM})
    assert abs(C("get_song")["tempo"] - BPM) < 1e-6, "Live's tempo is not %s" % BPM


if __name__ == "__main__":
    make_files()
    ensure_tracks()
    build()
