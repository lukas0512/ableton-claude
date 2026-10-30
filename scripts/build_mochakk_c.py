"""Mochakk C: an original groove-first house track after the Mochakk Mixmag Lab Mocambique
set (2026-10-30). Reference = the track at 17:10 (cut alone 17:19-22:32 by reference_from_set),
direction A: C with the bass's half-step push (Db, Ab) under a C major colour; the whole set's
12 tracks studied as `mochakk_set` give the feel.

The producer's brief for it: "abuse do bounce, com hats percs e etc, groove, a track precisa
fazer a gente balançar e não soar robótica". What the set measures for that:
  - 126 BPM; hats swing 57 % against their own on-beats (middle half 56-59): the off-16ths
    ~17 ms late. One pocket, baked into every written part; no pool groove on them.
  - a busy, quiet percussion layer with ghosts (clap/perc ~xgxxxgxgxgxxxgxx) over 4x4.
  - bass 73 % off the beat, 38 % with the kick, only ~4 dB under the drums; in the 17:10
    track a played electric bass, degrees 1/5 with b2/b6 pushes.

Stage 1 (this file): a 16-bar groove block, two 8-bar phrases, to approve the bounce before
any arrangement. Parts follow his Let The Rhythm kit (music_drum_kit), the notes are written
here with phrase variation, velocity accents and +-3 ms scatter so no bar repeats exactly.

Re-running is safe: every managed track's clips in the block are deleted and written again.

    cd mcp_server && uv run python ../scripts/build_mochakk_c.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

C = client.call
BPM = 126.0
BEAT_S = 60.0 / BPM
BARS = 16
SWING_PCT = 57.0
SW = (SWING_PCT - 50.0) / 100.0 * 0.5          # off-16th delay in beats (0.035 = 16.7 ms)
SCATTER = 0.003 / BEAT_S                       # +-3 ms, beats
KIT = "user_library/Samples/Claude/Nobody Kit/"
GROOVE = "Swing 16ths 57"
LOOPS = os.path.expanduser("~/Music/Ableton/User Library/Samples/Claude/Nobody Kit/")

# track: (source, fader dB, pan, send to the room dB, Simpler settings)
TRACKS = {
    "KICK":      (KIT + "SCHT_Kick1.wav", -2.3, 0.0, None, {"Vol < Vel": "0.0 %"}),
    "CLAP":      (KIT + "SCHT_Clap2.wav", -6.0, 0.0, -21.0, {"Vol < Vel": "40 %"}),
    "HAT 16":    (KIT + "HL_CH_CLOSED_HAT_SHOT_010.wav", -16.0, 0.0, -22.5, {"Vol < Vel": "100 %"}),
    "HAT OFF":   (KIT + "SCHT_Hat_Persona.wav", -11.0, 0.2, -21.0, {"Vol < Vel": "100 %"}),
    "SHAKER":    (KIT + "KMRBI_AW_Shaker_One_Shot_Chuga.wav", -15.0, 0.35, -21.0, {"Vol < Vel": "100 %"}),
    "CONGAS":    ("drums/Percussion Core Kit.adg", -9.8, 0.26, -21.0, None),
    "TOM 909":   ("drums/909 Core Kit.adg", -6.0, -0.18, None, None),
    "RIM 909":   ("drums/909 Core Kit.adg", -4.0, 0.12, -24.0, None),
    "BASS":      ("sounds/Bass/Electric Bass Soft.adg", -6.0, 0.0, None, None),
}
AUDIO = {   # played loops: human timing MIDI does not have (Let The Rhythm's shaker and perc)
    "SHAKER LOOP": (LOOPS + "PMLxSVTxCioz_Shaker_Acti_Black_Far_Away_122bpm.wav", 122, -14.0, -0.35),
    "PERC LOOP":   (LOOPS + "SCBB_Perc_120_Perola2.wav", 120, -17.0, -0.3),
}

EQ = {
    "HAT 16": {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "-4.0 dB"},
    "SHAKER": {"8 Filter On A": "On", "8 Filter Type A": "High Shelf", "8 Frequency A": "8.00 kHz", "8 Gain A": "-4.0 dB"},
    "BASS": {"8 Filter On A": "On", "8 Filter Type A": "Low Pass 12dB", "8 Frequency A": "900 Hz"},
}

# the closed hat's accent map, dB per 16th (his kit, measured): on-beat 16ths ~11 dB under the "&"
HAT_DB = [-10.8, -2.4, -0.5, -2.0, -11.3, -3.4, -0.4, -2.6, -11.9, -3.4, -0.8, -2.4, -10.5, -2.8, -0.8, -1.6]

# the bass (Live's C3 = 60): two-bar call (A) and answer (B), degrees 1/5 with the b2 (Db) and
# b6 (Ab) pushing into the next downbeat; (step, MIDI pitch, length in 16ths, velocity).
# v2: the 17:10 track plays its low C on the 1 and answers an octave up (G2-Db3, its register
# ~Ab2); v1 sat every note in the low octave. The octave leaps are part of the bounce.
C2, G2, Ab2, Bb2, C3, Db3, Eb3 = 36, 43, 44, 46, 48, 49, 51
BASS_A = [(0, C2, 3, 112), (3, C3, 1, 78), (6, G2, 2, 100), (10, C2, 1, 92), (11, Eb3, 2, 100),
          (14, Db3, 2, 106)]
BASS_B = [(2, C3, 1, 96), (3, C2, 1, 84), (6, Ab2, 2, 104), (8, G2, 1, 86), (10, Bb2, 1, 94),
          (11, C3, 2, 104), (14, Db3, 1, 98)]
BASS_TURN = [(0, C2, 3, 112), (3, C3, 1, 78), (6, G2, 2, 100), (8, Ab2, 1, 96), (10, Bb2, 1, 98),
             (12, C3, 1, 102), (14, Db3, 1, 104), (15, Eb3, 1, 96)]   # bar 8: a walk up into the 1

# congas (Percussion Core Kit): low slap 38, high muted 40, low bongo 43, high bongo 45
CONGA_A = {38: [1, 7], 40: [6, 9], 43: [11]}
CONGA_B = {38: [1, 7, 13], 40: [6, 9, 15], 43: [11]}
CONGA_TRIPLET = [(38, 0.0), (40, 1 / 3), (40, 2 / 3), (43, 2.0), (45, 2 + 1 / 3), (45, 2 + 2 / 3),
                 (38, 3.0), (40, 3.25), (43, 3.5), (45, 3.75)]


def log(*a):
    print(*a, flush=True)


def _is_option(v):
    return isinstance(v, str) and not (v[:1].isdigit() or v[:1] in "+-.")


def setp(track, device, param, v):
    args = {"track": track, "device": device, "param": param}
    args["item" if _is_option(v) else "display"] = v
    return C("set_param", args)


def ensure_tracks():
    names = [t["name"] for t in C("get_song")["tracks"]]
    for t, (src, fader, pan, send, simpler) in TRACKS.items():
        if t not in names:
            C("create_track", {"kind": "midi", "name": t})
        if not C("get_track", {"track": t, "clips": False})["devices"]:
            C("load_device", {"track": t, "path": src})
        for p, v in (simpler or {}).items():     # every run: a device left from a lost run too
            setp(t, 0, p, v)
        C("set_track", {"track": t, "volume_db": fader, "pan": pan})
        C("set_send", {"track": t, "send": 0, "db": send if send is not None else -70.0})
    # v1 measured hats 7 dB over the set and brighter (7.4 vs 5.3 kHz), the bass's upper
    # harmonics 9 dB over its warm, dark references: shelve the hats, low-pass the bass
    for t, bands in EQ.items():
        if "EQ Eight" not in C("get_track", {"track": t, "clips": False})["devices"]:
            C("load_device", {"track": t, "query": "EQ Eight", "roots": ["audio_effects"]})
        for p, v in bands.items():
            setp(t, "EQ Eight", p, v)
    for t, (path, _, fader, pan) in AUDIO.items():
        if t not in names:
            C("create_track", {"kind": "audio", "name": t})
            C("set_track_input", {"track": t, "source": "No Input"})
        C("set_track", {"track": t, "volume_db": fader, "pan": pan})
        C("set_send", {"track": t, "send": 0, "db": -22.0})
    # Live's empty default tracks ("1-MIDI", "3-Audio"...): deleting one renumbers the rest, so
    # find them by being empty and delete from the end, by index
    import re
    for t in reversed(C("get_song")["tracks"]):
        if re.fullmatch(r"\d+-(MIDI|Audio)", t["name"]) and not t["devices"] and not t["clips"]:
            C("delete_track", {"track": t["i"]})
    # one short room for the whole kit (return A, Live's default Reverb)
    for p, v in {"Decay Time": "0.80 s", "Predelay": "5.00 ms", "Dry/Wet": "100 %"}.items():
        try:
            setp("return:0", "Reverb", p, v)
        except Exception as e:      # parameter names differ between Live versions
            log("room:", p, e)


def _swing(notes, rnd):
    """One pocket: every off-16th SW late, every hit +-3 ms; the kick is the grid."""
    for n in notes:
        q = n[1] * 4
        if abs(q - round(q)) < 1e-6 and int(round(q)) % 2 == 1:
            n[1] += SW
        n[1] = round(max(0.0, n[1] + rnd.uniform(-SCATTER, SCATTER)), 4)
    return notes


def notes(kind, bar0, n_bars):
    rnd = np.random.default_rng(hash((kind, bar0)) % 2 ** 32)
    out = []
    for k in range(n_bars):
        b = bar0 + k                        # song bar, 1-based
        pos = (b - 1) % 8                   # bar in its 8-bar phrase
        second = (b - 1) // 8 % 2 == 1      # the second phrase: a little fuller
        o = k * 4.0
        if kind == "KICK":
            for beat in range(4):
                out.append([60, o + beat, 1.0, 127])
        elif kind == "CLAP":                # his syncopated backbeat, a 32nd ramp into bar 8
            hits = [(4, 104), (12, 108)]
            if pos % 2 == 1:
                hits.append((2, 70))        # the "& of 1" in every 2nd bar
            if pos % 4 == 3:
                hits.append((15, 76))       # a 16th pickup closing every 4th bar
            if pos == 7:
                hits += [(13.5, 48), (14, 58), (14.5, 68)]
            for st, v in hits:
                out.append([60, o + st * 0.25 + 0.008 / BEAT_S, 0.25, int(v * rnd.uniform(0.94, 1.04))])
        elif kind == "HAT 16":
            for st in range(16):
                if pos % 2 == 1 and st == 13:   # a pocket every 2nd bar
                    continue
                if pos % 4 == 2 and st == 9:
                    continue
                if pos == 3 and st == 0:        # a breath on the 4th bar's downbeat
                    continue
                if pos == 7 and st >= 14:       # phrase end: a 32nd flutter into the 1
                    for j, v in enumerate((48, 60, 74, 88)):
                        out.append([60, o + 3.5 + j * 0.125, 0.1, v])
                    continue
                v = 127 * 10 ** (HAT_DB[st] / 20.0) * rnd.uniform(0.86, 1.04)
                out.append([60, o + st * 0.25, 0.15, int(max(18, min(127, v)))])
        elif kind == "HAT OFF":             # the "&"s, one breath per phrase
            for st in (2, 6, 10, 14):
                if pos == 7 and st == 14:
                    continue
                out.append([60, o + st * 0.25, 0.3, int(rnd.uniform(94, 110))])
        elif kind == "SHAKER":              # 16ths, the swung "e"/"a" leaning, ~5 ms early on the "&"
            for st in range(16):
                if st % 4 == 0 and not second:
                    continue                # the first phrase leaves the downbeats to the kick
                v = (92 if st % 2 == 1 else 64 if st % 4 == 2 else 44) * rnd.uniform(0.85, 1.08)
                t = o + st * 0.25 - (0.005 / BEAT_S if st % 4 == 2 else 0.0)
                out.append([60, t, 0.12, int(v)])
        elif kind == "CONGAS":
            if pos == 3 or pos == 7:        # a triplet bar every 4
                for p, t in CONGA_TRIPLET:
                    out.append([p, o + t, 0.2, int(rnd.uniform(64, 84))])
            else:
                for p, steps in (CONGA_B if second or pos % 2 else CONGA_A).items():
                    for st in steps:
                        out.append([p, o + st * 0.25, 0.2, int(rnd.uniform(62, 84))])
        elif kind == "TOM 909":             # 909 low tom on the "e"/"a": rolling, out of the bass's way
            for st in (3, 6, 7, 9, 11, 14):
                if pos % 2 == 1 and st == 6:
                    continue
                out.append([44, o + st * 0.25, 0.2, int(rnd.uniform(64, 96))])
            if pos == 7:
                out += [[44, o + 3.5, 0.1, 70], [44, o + 3.75, 0.1, 84]]
        elif kind == "RIM 909":             # rims 3/6/11/14, ghost snares 9/13; only the second phrase
            if not second:
                continue
            for st, p, v in ((3, 37, 70), (6, 37, 46), (9, 38, 40), (11, 37, 84), (13, 38, 36), (14, 37, 58)):
                out.append([p, o + st * 0.25, 0.15, int(v * rnd.uniform(0.9, 1.1))])
        elif kind == "BASS":
            pat = BASS_TURN if pos == 7 else (BASS_A if pos % 2 == 0 else BASS_B)
            for st, p, ln, v in pat:
                out.append([p, o + st * 0.25, ln * 0.25 * 0.85, int(v * rnd.uniform(0.95, 1.03))])
    return out if kind == "KICK" else _swing(out, rnd)


def build():
    for t in TRACKS:
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": BARS + 1})
        for bar0 in range(1, BARS + 1, 8):
            C("create_midi_clip", {"track": t, "bar": bar0, "length": 32.0, "name": t,
                                   "notes": notes(t, bar0, 8)})
        log(t, "written")
    for t, (path, bpm, _, _) in AUDIO.items():
        C("delete_clips_in_range", {"track": t, "start_bar": 1, "end_bar": BARS + 1})
        beats = round(sf.info(path).duration * bpm / 60.0)   # auto-warp guesses wrong: pin it
        C("create_audio_clip", {"track": t, "path": path, "bar": 1, "name": t, "warp": True,
                                "beats": beats, "length": BARS * 4.0})
        log(t, "placed", beats, "beats")
    # the played loops are straight: they take the set's pocket from the pool (warped clips only);
    # the written parts carry it in their notes and get no pool groove
    if GROOVE not in [g["name"] for g in C("grooves")["grooves"]]:
        C("load_device", {"track": "SHAKER LOOP", "path": "user_library/Grooves/%s.agr" % GROOVE})
    C("set_groove", {"name": GROOVE, "timing": 100, "random": 0, "velocity": 0, "groove_amount": 1.0})
    for t in AUDIO:
        C("apply_groove", {"track": t, "groove": GROOVE})
    # Live gives every new MIDI clip its default "Swing 16ths 66" and the API cannot clear a
    # clip's groove: neutralise it, or it doubles the swing baked into the notes (v2 measured
    # the hats 49 ms late, 70 %, for 17 ms written)
    for g in C("grooves")["grooves"]:
        if g["name"] != GROOVE:
            C("set_groove", {"name": g["name"], "timing": 0, "random": 0, "velocity": 0})
    C("set_cue", {"name": "GROOVE BLOCK - approve the bounce", "bar": 1})
    # v1 rendered at 128: the song tempo moved after set_tempo(126) while the block was built.
    # Set it last and check it, every run
    C("set_tempo", {"bpm": BPM})
    assert abs(C("get_song")["tempo"] - BPM) < 1e-6, "Live's tempo is not %s" % BPM


if __name__ == "__main__":
    ensure_tracks()
    build()
