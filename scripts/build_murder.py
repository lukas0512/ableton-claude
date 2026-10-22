"""Murder: EP track 2, a 123 BPM dark house remix of UGK "Murder" (86.0 BPM, E minor,
A440), the sister of From The Streets: same family (stems from the record, the vocal
rules, club form) but its own groove: heavier, darker, straighter.

Material (offline analysis 2026-10-21, source bars from the first downbeat 0.8976 s):
- theme: the "Murder... Murder..." chant, src 3.5-8 (the intro)
- Pimp C verse src 7-40 (slow), Bun B verse src 45-80 (fast flow), "murder case" src 61.5
- bass riff (1 bar): E (1.5 beats) G (1.5) A|D (.5) D# (.5, leading tone back to E)
- 'other': low guitar riff B-D-A-A# (the bass a 5th up), src 9-25 alone; high keys
  melody (2 bars, D5 G#4 E4 .. C5 G4 | .. C5 C#5) with it at src 4-8, 26-29, 40-49

Stages: `python build_murder.py sketch` (two 8-bar groove sketches for the producer).

He then asked for a club ("pista") remix in the From The Streets way, sketch B's riff
bass as the lead idea: `pista` turns a copy of the FTS set (Murder Pista Project, 125 BPM,
FTS v36 form, drums/builds/FX/buses/master kept) into Murder: the bass plays Murder's
riff, the City synth bed becomes Murder's guitar riff (keys + guitar in the drops), every
City vocal becomes the Murder theme / Bun B / Pimp C, chops and glitches come from the
theme.
"""
import sys
from pathlib import Path

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp_server"))
from ableton_claude import client, server  # noqa: E402

BPM = 123.0
ROOT = Path("/Users/lukasgalhardo/Desktop/TRACKS 2027/Murder")
KIT = "user_library/Samples/Claude/Murder Kit/"
LOOPS = ROOT / "loops"
LOG = []


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args))
    return r


def beat(bar):
    return (bar - 1) * 4.0


def swing(notes, pct):
    """Off-beat 16ths late by (pct - 50) % of an 8th."""
    late = (pct - 50) / 100 * 0.5
    return [[p, round(t + (late if round(t * 4) % 2 else 0), 4), d, v] for p, t, d, v in notes]


def steps(pattern, bars, pitch=60, dur=.2, vel=None, late=0.0):
    """pattern: {bar_in_cycle: [16th steps]} or a list for every bar; vel(step) -> velocity."""
    out = []
    for b in range(bars):
        st = pattern[b % len(pattern)] if isinstance(pattern, dict) else pattern
        for s in st:
            out.append([pitch, b * 4 + s / 4 + late, dur, vel(s) if vel else 100])
    return out


# ---------------------------------------------------------------- sketch
DRUMS = {  # track: (sample, fader dB, pan)
    "KICK": ("DGH_KICK_025.wav", -4, 0),
    "CLAP": ("MD2_CLAP_6.wav", -9, 0),
    "SNARE": ("DGH_SNARE_013.wav", -12, 0),
    "HAT": ("DCW_Closed_Hat_04.wav", -16, .1),
    "OPEN HAT": ("DSB_HH_COOL.wav", -18, -.15),
    "RIM": ("DGH_PERCUSSION_006.wav", -15, .3),
    "CONGA": ("NSL_BongoCongas_26.wav", -14, -.3),
}
E1, G1, A1, D1, DS1 = 28, 31, 33, 26, 27
A_BAR, B_BAR, BARS = 1, 11, 8


def hat_vel(s):
    return 100 if s % 4 == 2 else (66 if s % 2 else 48)


def sketch_a():
    """Hypnotic: 4x4, clap 2+4, 16th hats accented on the off-beat, rim syncopation,
    bass rolling in 16ths between the kicks on Murder's riff, 52 % swing."""
    sw = 52
    parts = {
        "KICK": steps([0, 4, 8, 12], BARS, dur=.25, vel=lambda s: 118),
        "CLAP": steps([4, 12], BARS, late=.016, vel=lambda s: 104),
        "HAT": steps(list(range(16)), BARS, dur=.1, vel=hat_vel),
        "RIM": steps({0: [3, 10], 1: [7, 11, 14]}, BARS, dur=.1, vel=lambda s: 88),
        "OPEN HAT": [n for n in steps([2, 6, 10, 14], BARS, dur=.3, vel=lambda s: 90)
                     if n[1] >= 16],                       # the second half lifts
    }
    bass = []
    for b in range(BARS):
        for s in range(16):
            if s % 4 == 0:
                continue                                   # the kick owns the beat
            p = E1 if s < 6 else G1 if s < 12 else (A1 if b % 2 == 0 else D1) if s < 14 else DS1
            bass.append([p, b * 4 + s / 4, .2, 112 if s % 4 == 2 else 92])
    parts["BASS A - rolling"] = bass
    return {k: swing(v, sw) for k, v in parts.items()}


def sketch_b():
    """Murder bounce: snare on 2, clap on 4, off-beat hats, 3-3-2 congas, the bass on
    the record's own riff rhythm, 55 % swing."""
    sw = 55
    parts = {
        "KICK": steps([0, 4, 8, 12], BARS, dur=.25, vel=lambda s: 118),
        "SNARE": steps([4], BARS, late=.012, vel=lambda s: 100),
        "CLAP": steps([12], BARS, late=.016, vel=lambda s: 108),
        "HAT": steps([2, 6, 10, 13, 14], BARS, dur=.1,
                     vel=lambda s: 100 if s % 4 == 2 else 58),
        "CONGA": steps({0: [0, 3, 6, 10, 13], 1: [0, 3, 6, 9, 11, 14]}, BARS, dur=.15,
                       vel=lambda s: 96 if s in (0, 6, 10) else 74),
        "RIM": steps({0: [], 1: [], 2: [], 3: [15]}, BARS, dur=.1, vel=lambda s: 84),
    }
    bass = []
    for b in range(BARS):
        turn = A1 if b % 2 == 0 else D1
        for p, t, d, v in ((E1, .5, .45, 112), (E1, 1.25, .2, 96), (G1, 1.5, .7, 108),
                           (G1, 2.5, .2, 94), (turn, 3.0, .45, 104), (DS1, 3.5, .45, 100)):
            bass.append([p, b * 4 + t, d, v])
    parts["BASS B - riff"] = bass
    return {k: swing(v, sw) for k, v in parts.items()}


def _place_loop(track, path, markers, beats, bar, copies):
    for k in range(copies):
        at = beat(bar) + k * beats
        C("create_audio_clip", track=track, path=str(path), beat=at, warp=False,
          name=Path(path).stem)
        dur = sf.info(str(path)).duration - .001
        C("set_warp_markers", track=track, clip={"at": at},
          markers=[[b, min(t, dur)] for b, t in markers])
        r = C("set_clip", track=track, clip={"at": at}, warping=True, warp_mode="complex_pro",
              looping=False, start_marker=0, end_marker=beats)
        if r.get("length", beats) > beats + .02:
            C("trim_clip", track=track, clip={"at": at}, end_beat=at + beats)


def sketch():
    song = client.call("get_song")
    built = any(t["name"] == "KICK" for t in song["tracks"])
    empty = [t["name"] for t in song["tracks"] if t["name"][:2] in ("1-", "2-", "3-", "4-")
             and not t.get("clips") and not t.get("devices")]
    C("set_tempo", bpm=BPM)
    if not built:
        _tracks()

    for bar, parts, label in ((A_BAR, sketch_a(), "SKETCH A - hipnotico, rolling 16ths, 52 %"),
                              (B_BAR, sketch_b(), "SKETCH B - Murder bounce, riff, 55 %")):
        for track, notes in parts.items():
            C("create_midi_clip", track=track, bar=bar, length=BARS * 4, notes=notes,
              name=label.split(" -")[0])
        C("set_cue", name=label, bar=bar)
    meta = __import__("json").loads((LOOPS / "stem-remix.json").read_text())
    loop = meta["Murder other"]
    for bar in (A_BAR, B_BAR):
        _place_loop("LOOP - Murder guitar riff", loop["path"], loop["markers"], loop["beats"],
                    bar, BARS // 2)
    for name in empty:                                     # the blank set's empty tracks
        C("delete_track", track=name)                      # (Live keeps at least one)
    C("set_cue", name="end of sketches", bar=B_BAR + BARS + 1)
    print("sketch done")


def _tracks():
    for name, (wav, fader, pan) in DRUMS.items():
        C("create_track", kind="midi", name=name)
        C("load_device", track=name, path=KIT + wav)
        C("set_device_prop", track=name, device=0, prop="playback_mode", value=1)
        C("set_track", track=name, volume_db=fader, pan=pan)
    for name, preset, fader in (("BASS A - rolling", "sounds/Bass/Muted Dark Bass.adv", -10),
                                ("BASS B - riff", "sounds/Bass/Basic FM House Bass.adg", -10)):
        C("create_track", kind="midi", name=name)
        C("load_device", track=name, path=preset)
        C("load_device", track=name, query="Compressor", roots=["audio_effects"])
        C("set_device_input", track=name, device="Compressor", source="KICK",
          channel="Post Mixer")
        C("set_param", track=name, device="Compressor", param="Threshold", db=-22)
        C("set_param", track=name, device="Compressor", param="Ratio", display=4)
        C("set_track", track=name, volume_db=fader)
    C("create_track", kind="audio", name="LOOP - Murder guitar riff")
    C("set_track", track="LOOP - Murder guitar riff", volume_db=-8, pan=-.1)


# ---------------------------------------------------------------- pista (FTS copy)
import json  # noqa: E402

import numpy as np  # noqa: E402
from scipy import signal  # noqa: E402

from ableton_claude import stem_remix as sr  # noqa: E402

PISTA_BPM = 125.0
POCKET = sr.swing_beats(10.8, PISTA_BPM)      # FTS's one 16th pocket
SRC = Path("/Users/lukasgalhardo/Desktop/TRACKS 2027/From the streets")
STEM = SRC / "stems4/htdemucs/03 - UGK (Underground Kingz) - Murder"
MIX = SRC / "03 - UGK (Underground Kingz) - Murder.mp3"
VOX_DIR = ROOT / "vocals 125"
FX_DIR = ROOT / "fx 125"
LOOP_DETUNE = 10                               # the 'other' stem sits ~10 cents flat


def call(cmd, args):
    return C(cmd, **args)


def _clips(track):
    return client.call("get_track", {"track": track})["clips"]


def _clear(track):
    for c in reversed(_clips(track)):
        C("delete_clip", track=track, clip={"at": c["start"]})


# Murder's riff, one bar, in FTS's bass octave (E1 = 64 on BinBassTone) and pocket
def murder_riff(bars, e=64, vel=None):
    out = []
    for b in range(bars):
        turn = e + 5 if b % 2 == 0 else e - 2          # A, then D: the record alternates
        for k, (p, t, d, v) in enumerate(((e, 0, .55, 100), (e, .75, .55, 118),
                                          (e + 3, 1.5, .55, 118), (e + 3, 2.25, .4, 100),
                                          (turn, 3.0, .45, 108), (e - 1, 3.5, .45, 112))):
            late = POCKET if round(t * 4) % 2 else 0
            out.append([p, b * 4 + t + late, d, vel(b, k) if vel else v])
    return out


def pista_bass():
    for track, e in (("BASS", 64), ("BASS - teaser (HP)", 76)):
        for c in _clips(track):
            bars = int(round((c["end"] - c["start"]) / 4))
            ramp = None
            if "teaser" in track:                        # the teaser keeps its rising level
                ramp = lambda b, k, n=bars: int(70 + 20 * (b * 6 + k) / max(1, n * 6 - 1))
            C("add_notes", track=track, clip={"at": c["start"]},
              notes=murder_riff(bars, e, ramp), replace=True)
            C("set_clip", track=track, clip={"at": c["start"]}, name="Murder riff bass")


def _cut_loop(name, bar):
    x, fs = sf.read(str(STEM / "other.wav"), dtype="float32")
    g = sr.source_grid(str(MIX), 86.0)
    m = sr.cut_loop(x, fs, str(LOOPS / f"{name} (pocket {POCKET:.3f}).wav"), g["bpm"], g["downbeat"], bar, 2,
                    POCKET)
    return m


CITY_BED = [(29, 33), (33, 49), (49, 57), (57, 64), (65, 97), (113, 119), (119, 120),
            (121, 149), (149, 153), (153, 169)]   # the FTS v36 City synth clips (bars)


def pista_loops():
    """The City synth bed -> Murder's guitar riff; keys + guitar (the melody) in the drops."""
    guitar, keys = _cut_loop("Murder guitar riff", 24), _cut_loop("Murder keys+guitar", 41)
    T = "LOOP MURDER - riff bed"
    if any(t["name"] == "LOOP CITY - orig synth" for t in client.call("get_song")["tracks"]):
        _clear("LOOP CITY - orig synth")
        C("set_track", track="LOOP CITY - orig synth", name=T)
    spans = [(beat(a), beat(b)) for a, b in CITY_BED]
    for a, b in spans:
        bar = a / 4 + 1
        m = keys if 65 <= bar < 97 or 121 <= bar < 153 else guitar
        at = a
        while at < b - .01:
            n = min(m["beats"], b - at)
            sr.place_warped(call, T, m["path"], at, n, m["markers"],
                            name=Path(m["path"]).stem)
            C("set_clip", track=T, clip={"at": at}, detune=LOOP_DETUNE)
            at += n


def _radio(src, dst):
    x, fs = sf.read(src, dtype="float32")
    sos = signal.butter(4, [380, 3200], "bandpass", fs=fs, output="sos")
    y = np.tanh(2.2 * signal.sosfilt(sos, x, axis=0))
    sf.write(dst, (y / (np.abs(y).max() + 1e-9) * .5).astype(np.float32), fs)
    return dst


def _phrase(name, radio=False):
    meta = json.loads((VOX_DIR / "phrases.json").read_text())[name]
    if radio:
        meta = dict(meta, path=_radio(meta["path"], meta["path"].replace(".wav", " [radio].wav")))
    return meta


def _put(track, name, bar, radio=False, gain=None, label=None):
    m = _phrase(name, radio)
    at = beat(bar) - m["preroll"]
    sr.place_warped(call, track, m["path"], at, m["clip_beats"], m["markers"],
                    name=label or f"Murder {name}" + (" [radio]" if radio else ""), gain_db=gain)


VOCALS = {  # track: [(bar, phrase, radio, gain)]; FTS's slots, Murder's lines
    "VOX CITY - calls": [(32, "theme call", 0, 0), (40, "theme call", 0, 0),
                         (67, "theme call", 0, -2), (96, "theme call", 0, 0),
                         (117, "theme call", 0, 0), (121, "theme call", 0, 0),
                         (145, "theme call", 0, 0), (149, "theme call", 0, 0)],
    "VOX CITY - hooks": [(49, "theme", 0, -1.5), (53, "theme", 0, -1.5),
                         (64, "theme call", 0, 0),                    # a cappella pre-drop
                         (73, "bun verse 8", 0, -1),
                         (105, "theme", 0, -1.5), (109, "murder case", 0, 0),
                         (129, "bun verse a", 0, -1), (133, "bun verse b", 0, -1),
                         (137, "bun verse c", 0, -1), (141, "theme", 0, -1.5)],
    "VOX CITY - radio": [(17, "intro talk", 1, -6), (60, "theme call", 1, -6),
                         (120, "theme call", 1, -6), (161, "theme", 1, -6)],
    "VOX - throws": [(89, "murder case", 0, -3)],
}
RENAME = {"VOX CITY - calls": "VOX MURDER - theme calls", "VOX CITY - hooks": "VOX MURDER - hooks",
          "VOX CITY - radio": "VOX MURDER - radio", "VOX MURDER": "VOX MURDER - Pimp C",
          "VOX MURDER - trades": "VOX MURDER - trades"}


def pista_vocals():
    for t in VOCALS:
        _clear(t)
    for t, slots in VOCALS.items():
        for bar, name, radio, gain in slots:
            _put(t, name, bar, bool(radio), gain)
    for old, new in RENAME.items():
        if old != new:
            C("set_track", track=old, name=new)


# ---------------------------------------------------------------- chops + glitches
def _fx_files():
    FX_DIR.mkdir(parents=True, exist_ok=True)
    g = sr.source_grid(str(MIX), 86.0)
    chops, _ = sr.onset_chops(str(STEM / "vocals.wav"), str(FX_DIR), g["bpm"], g["downbeat"], 4,
                              beat=.75, lengths={"word": .42, "short": .2}, label="Murder chop")
    x, fs = sf.read(chops["word"], dtype="float32")
    sixteenth = int(60 / PISTA_BPM / 4 * fs)
    out = dict(chops)
    # stutter: the attack 4x in 16ths, then the whole word
    stut = np.concatenate([x[:sixteenth]] * 4 + [x])
    out["stutter"] = str(FX_DIR / "Murder stutter.wav"); sf.write(out["stutter"], stut, fs)
    # tape stop over half a beat
    n = len(x); rate = np.linspace(1, .15, n); pos = np.cumsum(rate); pos = pos[pos < n - 1]
    ts = np.stack([np.interp(pos, np.arange(n), x[:, c]) for c in range(x.shape[1])], 1)
    out["tapestop"] = str(FX_DIR / "Murder tape stop.wav"); sf.write(out["tapestop"], ts.astype(np.float32), fs)
    out["reverse"] = str(FX_DIR / "Murder reversed.wav"); sf.write(out["reverse"], x[::-1], fs)
    # 2-bar chop riff: "Mur-" on the 'a' of 2, "-der" pattern answering the riff's turn
    bar_n = int(240 / PISTA_BPM * fs); riff = np.zeros((2 * bar_n, x.shape[1]), np.float32)
    s_ = sf.read(chops["short"], dtype="float32")[0]
    for pos_beats, clip in ((1.75, s_), (2.5, x), (5.75, s_), (6.25, s_), (7.0, x)):
        i = int((pos_beats + (POCKET if round(pos_beats * 4) % 2 else 0)) * 60 / PISTA_BPM * fs)
        riff[i:i + len(clip)] += clip[:len(riff) - i]
    out["riff"] = str(FX_DIR / "Murder chop riff (2 bars).wav")
    sf.write(out["riff"], riff * (.5 / (np.abs(riff).max() + 1e-9)), fs)
    return out


def _place_file(track, path, at, name, warp=False):
    C("create_audio_clip", track=track, path=path, beat=at, warp=warp, name=name)


CHOP_SPANS = [(84, 85), (86, 87)] + [(b, b + 2) for b in range(89, 97, 2)] + \
    [(b, b + 2) for b in range(137, 153, 2)] + [(b, b + 2) for b in range(161, 169, 2)]


def pista_fx():
    f = _fx_files()
    T = "CHOPS - Murder"
    if any(t["name"] == "CHOPS - UKG babe" for t in client.call("get_song")["tracks"]):
        _clear("CHOPS - UKG babe")
        C("set_track", track="CHOPS - UKG babe", name=T)
    for a, n in [(beat(a), (b - a) * 4) for a, b in CHOP_SPANS]:
        C("create_audio_clip", track=T, path=f["riff"], beat=a, warp=True, beats=8, length=n,
          name="Murder chop riff")
    G = "FX - glitches"
    swap = {"City stutter": "stutter", "City tape stop": "tapestop", "Hook rev cut": "reverse"}
    for c in _clips(G):
        kind = next((v for k, v in swap.items() if c["name"].startswith(k)), None)
        if kind:
            C("delete_clip", track=G, clip={"at": c["start"]})
            _place_file(G, f[kind], c["start"], "Murder " + kind)
    X = "FX - transitions"
    for c in _clips(X):
        if c["name"].startswith("City synth tape"):
            C("delete_clip", track=X, clip={"at": c["start"]})
            _place_file(X, f["tapestop"], c["start"], "Murder tape stop")
    if any(t["name"] == "FX - babe scratch" for t in client.call("get_song")["tracks"]):
        _clear("FX - babe scratch")
        C("set_track", track="FX - babe scratch", name="FX - scratch (empty)")


def pista_cues():
    for c in client.call("get_song")["cues"]:
        if "City" in c["name"] or "hook B" in c["name"]:
            new = (c["name"].replace("City synth, the theme calls", "Murder riff, the theme calls")
                   .replace("hook B", "the theme").replace("City", "Murder"))
            C("delete_cue", beat=c["beat"])
            C("set_cue", name=new, beat=c["beat"])


def pista():
    song = client.call("get_song")
    assert abs(song["tempo"] - PISTA_BPM) < .01 and any(
        t["name"] == "LOOP CITY - orig synth" for t in song["tracks"]), "open the FTS copy"
    C("delete_track", track="REF - City 2 City (original)")
    pista_bass()
    pista_loops()
    pista_vocals()
    pista_fx()
    pista_cues()
    print("pista done")


# ---------------------------------------------------------------- dub (his own style)
# The producer's target style is TRACKS 2027/Dub House Streets (study 'dub_house_streets'):
# 128.5 BPM, swing 57 %, bass 93 % off the beat (9 % with the kick), sub 35 % / low 52 %,
# high-mid 3.2 % / high 2.7 %, -8.5 LUFS. He chose: bass off the kick, 128 + 57 %, body
# and brightness (not the one-big-break form).
DUB_BPM = 128.0
DUB_SWING = (57 - 50) / 100 * .5               # 0.035 beat: off-beat 16ths late
OLD_SWING = POCKET                               # FTS's 10.8 ms at 125


def dub_riff(bars, e=64, vel=None):
    """Murder's riff off the kick (.x-x..x-.x-x..x-): E E | G | G A|D | D#, all on the
    'e' / '&' / 'a' 16ths, short, so kick and bass take turns."""
    out = []
    for b in range(bars):
        turn = e + 5 if b % 2 == 0 else e - 2
        for k, (p, step, n16, v) in enumerate(((e, 1, 1, 104), (e, 3, 2, 118), (e + 3, 6, 2, 116),
                                               (e + 3, 9, 1, 100), (turn, 11, 2, 112),
                                               (e - 1, 14, 2, 114))):
            t = step / 4 + (DUB_SWING if step % 2 else 0)
            out.append([p, b * 4 + t, n16 / 4 * .9, vel(b, k) if vel else v])
    return out


def dub_bass():
    for track, e in (("BASS", 64), ("BASS - teaser (HP)", 76)):
        for c in _clips(track):
            bars = int(round((c["end"] - c["start"]) / 4))
            ramp = None
            if "teaser" in track:
                ramp = lambda b, k, n=bars: int(70 + 20 * (b * 6 + k) / max(1, n * 6 - 1))
            C("add_notes", track=track, clip={"at": c["start"]}, notes=dub_riff(bars, e, ramp),
              replace=True)
            C("set_clip", track=track, clip={"at": c["start"]}, name="Murder riff bass (off the kick)")


def dub_swing():
    """Every MIDI part's swung off-beat 16ths from FTS's pocket to 57 %; parts with their
    own offsets (the shaker's early 8ths, straight notes) keep them."""
    song = client.call("get_song")
    for t in song["tracks"]:
        if t.get("kind") != "midi" or t["name"].startswith("BASS"):
            continue
        for c in _clips(t["i"]):
            notes = client.call("get_notes", {"track": t["i"], "clip": {"at": c["start"]}})
            moved, out = 0, []
            for p, st, d, v in notes:
                off = st * 4 - np.floor(st * 4)              # in 16ths
                odd = int(np.floor(st * 4)) % 2 == 1
                if odd and abs(off * .25 - OLD_SWING) < .008:
                    st = st - OLD_SWING + DUB_SWING
                    moved += 1
                out.append([p, round(st, 4), d, v])
            if moved:
                C("add_notes", track=t["i"], clip={"at": c["start"]}, notes=out, replace=True)


def dub_tempo():
    """128 BPM and the 57 % pocket for everything warped to the old one: Murder's loops and
    vocal phrases are re-cut on the new pocket and placed again."""
    global POCKET
    C("set_tempo", bpm=DUB_BPM)
    POCKET = DUB_SWING
    g = sr.source_grid(str(MIX), 86.0)
    meta = json.loads((VOX_DIR / "phrases.json").read_text())
    for name, m in meta.items():
        b, n = m["source_bar"], m["beats"] // 4
        path = m["path"].replace(" [57].wav", ".wav").replace(".wav", " [57].wav")
        meta[name] = sr.cut_phrase(str(STEM / "vocals.wav"), path, g["bpm"], g["downbeat"],
                                   b, n, DUB_SWING)
    (VOX_DIR / "phrases.json").write_text(json.dumps(meta))
    _clear("LOOP MURDER - riff bed")
    pista_loops()
    pista_vocals_dub()


def pista_vocals_dub():
    tracks = {"VOX CITY - calls": "VOX MURDER - theme calls", "VOX CITY - hooks": "VOX MURDER - hooks",
              "VOX CITY - radio": "VOX MURDER - radio", "VOX - throws": "VOX - throws"}
    for old, new in tracks.items():
        _clear(new)
        for bar, name, radio, gain in VOCALS[old]:
            _put(new, name, bar, bool(radio), gain)


def dub_mix():
    """Body over sub in the bass, brightness in the drums and master, -8.5 LUFS."""
    C("set_param", track="BASS", device="EQ Eight", param="1 Frequency A", display=55)
    C("set_param", track="BASS", device="EQ Eight", param="1 Gain A", display=-3)
    C("set_param", track="BASS", device="Saturator", param="Dry/Wet", display=50)
    C("set_param", track="DRUMS", device="EQ Eight", param="4 Gain A", display=0)
    C("set_param", track="DRUMS", device="EQ Eight", param="2 Gain A", display=3)
    C("set_param", track="master", device="EQ Eight", param="3 Gain A", display=-1)
    lim = client.call("get_device", {"track": "master", "device": "Limiter"})
    gain = next(p for p in lim["params"] if p["name"] == "Input Gain")
    C("set_param", track="master", device="Limiter", param="Input Gain",
      db=float(gain["display"].split()[0]) + .6)


# ---------------------------------------------------------------- dub v3 (his notes)
# "warps não estão em dia; o groove precisa encaixar e diferenciar da outra track; o fim
# do build 1 está esquecido; quando sai o riff fica esquisito."
FX_TRACKS = ("FX - transitions", "FX - glitches", "FX - sub boom", "BREAKBEAT")
FTS_BPM = 125.0


def fix_warps():
    """One-shots placed unwarped at FTS's 125 BPM drift at 128 (a reversed crash no longer
    lands on the drop): warp each to its 125-BPM length in beats, start kept."""
    for tr in FX_TRACKS:
        for c in _clips(tr):
            if c.get("warping") or not c.get("file"):
                continue
            dur = sf.info(c["file"]).duration
            beats = dur * FTS_BPM / 60
            at = c["start"]
            C("set_warp_markers", track=tr, clip={"at": at}, markers=[[0, 0], [beats, dur - .0005]])
            C("set_clip", track=tr, clip={"at": at}, warping=True, warp_mode="complex",
              looping=False, start_marker=0, end_marker=beats)


def _bed_hz(bar):
    """The riff bed's filter over the song: in from the intro, shut in the breaks, opening
    through the builds, closing out after drop 2 (never a hard cut)."""
    curve = [(29, 700), (33, 9000), (49, 9000), (49.01, 1400), (57, 1400), (64.5, 14000),
             (65, 14000), (97, 14000), (113, 900), (120.5, 14000), (153, 14000), (169, 500)]
    for (a, fa), (b, fb) in zip(curve, curve[1:]):
        if a <= bar <= b:
            k = (bar - a) / (b - a) if b > a else 0
            return fa * (fb / fa) ** k
    return curve[-1][1] if bar > curve[-1][0] else curve[0][1]


BED_V3 = [(29, 64.5), (65, 97), (113, 120.5), (121, 169)]


def riff_bed_v3():
    global POCKET
    POCKET = DUB_SWING
    guitar, keys = _cut_loop("Murder guitar riff", 24), _cut_loop("Murder keys+guitar", 41)
    T = "LOOP MURDER - riff bed"
    _clear(T)
    for a, b in BED_V3:
        at = beat(a)
        while at < beat(b) - .01:
            bar = at / 4 + 1
            m = keys if 65 <= bar < 97 or 121 <= bar < 153 else guitar
            n = min(m["beats"], beat(b) - at)
            env = {"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                   "points": [[0, sr.filter_raw(_bed_hz(bar))],
                              [n, sr.filter_raw(_bed_hz(bar + n / 4))]]}
            sr.place_warped(call, T, m["path"], at, n, m["markers"], envelopes=[env],
                            name=Path(m["path"]).stem)
            C("set_clip", track=T, clip={"at": at}, detune=LOOP_DETUNE)
            at += n


def build1_end():
    """Bars 61-64: the theme call repeats faster (bar, bar, half, half, beat x2) over the
    opening riff, then the 2-beat breath and the a cappella call already at 64."""
    T = "VOX MURDER - theme calls"
    m = _phrase("theme call")
    for bar, beats in ((61, 4), (62, 4), (63, 2), (63.5, 2)):
        at = beat(bar) - m["preroll"]
        n = beats + m["preroll"]
        mk = [[b, t] for b, t in m["markers"] if b <= n] + \
             [[n, next(t for b, t in m["markers"] if b >= n)]]
        sr.place_warped(call, T, m["path"], at, n, mk, name="theme call - build 1",
                        gain_db=-2 + (bar - 61) * 1.5)


DUB_HATS = "xgXgxgXxxXX.xgXg"      # the references' typical 16th hats (dub_house_streets)
DUB_GHOST = "g.x.X.xxggx.X.xg"     # their typical clap/perc layer, here on the snare
VEL = {"X": 100, "x": 78, "g": 54}


def dub_groove():
    """Its own groove: straight 16th hats with ghosts (velocity by step, the 12th gone),
    dub ghost snares around the clap in the drops, FTS's congas and 909 tom muted."""
    for c in _clips("HAT 16ths"):
        notes = client.call("get_notes", {"track": "HAT 16ths", "clip": {"at": c["start"]}})
        out = []
        for p, st, d, v in notes:
            step = int(round((st - (DUB_SWING if int(st * 4) % 2 else 0)) * 4)) % 16
            ch = DUB_HATS[step]
            if ch != ".":
                out.append([p, st, d, VEL[ch] - (100 - v) * .3])
        C("add_notes", track="HAT 16ths", clip={"at": c["start"]}, notes=out, replace=True)
    for c in _clips("SNARE"):
        bars = int(round((c["end"] - c["start"]) / 4))
        notes = []
        for b in range(bars):
            for step, ch in enumerate(DUB_GHOST):
                if ch == ".":
                    continue
                t = b * 4 + step / 4 + (DUB_SWING if step % 2 else 0)
                notes.append([60, round(t, 4), .2, {"X": 92, "x": 60, "g": 40}[ch]])
        C("add_notes", track="SNARE", clip={"at": c["start"]}, notes=notes, replace=True)
    for tr in ("CONGAS", "TOM 909"):
        C("set_track", track=tr, mute=True)


def dub_v3():
    fix_warps()
    riff_bed_v3()
    build1_end()
    dub_groove()
    print("dub v3 done")


def _eq(track, band, kind, hz, db=None, q=None):
    C("set_param", track=track, device="EQ Eight", param=f"{band} Filter On A", value=1)
    C("set_param", track=track, device="EQ Eight", param=f"{band} Filter Type A", item=kind)
    C("set_param", track=track, device="EQ Eight", param=f"{band} Frequency A", display=hz)
    if db is not None:
        C("set_param", track=track, device="EQ Eight", param=f"{band} Gain A", display=db)
    if q is not None:
        C("set_param", track=track, device="EQ Eight", param=f"{band} Q A", display=q)


BREAKS = [(49, 57), (97, 113)]
BREAK_TRACKS = ("VOX MURDER - hooks", "VOX MURDER - Pimp C", "VOX MURDER - radio",
                "LOOP MURDER - riff bed", "LOOP MURDER - break 2 groove", "BREAKBEAT", "PERC LOOP")


def dub_mix2():
    """validate_against_genre(v2, dub_house_streets): bass 3.3 dB over the kick (refs: kick
    +6), kick 48 Hz (refs 62), clap backbeat 1 dB (refs 8), low-mid/mid and warmth high,
    hats dark, breaks 1.6 LU under the drops (refs 4.3)."""
    for tr in ("KICK", "KICK - build (HP)"):                       # kick up 3 semitones
        for c in _clips(tr):
            notes = client.call("get_notes", {"track": tr, "clip": {"at": c["start"]}})
            C("add_notes", track=tr, clip={"at": c["start"]},
              notes=[[63 if p == 60 else p, t, d, v] for p, t, d, v in notes], replace=True)
    C("set_track", track="BASS", volume_db=-17.3)
    C("set_track", track="CLAP", volume_db=1.3)
    C("set_track", track="HAT 16ths", volume_db=-21.5)
    _eq("DRUMS", 4, "Bell", 7000, 1.5)
    # the riff bed kept FTS's City-synth cuts (2.5k, 3.5k buzz): the guitar needs that air
    C("set_param", track="LOOP MURDER - riff bed", device="EQ Eight", param="3 Gain A", display=0)
    C("set_param", track="LOOP MURDER - riff bed", device="EQ Eight", param="7 Gain A", display=0)
    _eq("LOOP MURDER - riff bed", 5, "Bell", 300, -3, 1.0)
    C("set_param", track="MUSIC BUS", device="EQ Eight", param="2 Gain A", display=-2)
    for tr in BREAK_TRACKS:                                        # deeper breaks
        for c in _clips(tr):
            bar = c["start"] / 4 + 1
            if any(a <= bar < b for a, b in BREAKS):
                C("set_clip", track=tr, clip={"at": c["start"]},
                  gain_db=round(c.get("gain_db", 0) - 2.5, 2))


# ---------------------------------------------------------------- v4 (his notes, live)
# "o break tá igual da outra; uma swingada diferente; mais chops, call-response pegado no
# ritmo; um instrumento agudinho estranho (the keys loop: notes up to 33 cents flat, and my
# +10 cents detuned the in-tune guitar); se o baixo for igual da outra, muda (same
# BinBassTone timbre: swapped for sketch B's FM bass)."
V4_SWING = (60 - 50) / 100 * .5                 # 0.05 beat


def v4_swing():
    global DUB_SWING, OLD_SWING, POCKET
    OLD_SWING, DUB_SWING = DUB_SWING, V4_SWING
    dub_swing()
    POCKET = DUB_SWING
    g = sr.source_grid(str(MIX), 86.0)
    meta = json.loads((VOX_DIR / "phrases.json").read_text())
    for name, m in meta.items():
        path = m["path"].replace(" [57].wav", ".wav").replace(" [60].wav", ".wav") \
            .replace(".wav", " [60].wav")
        meta[name] = sr.cut_phrase(str(STEM / "vocals.wav"), path, g["bpm"], g["downbeat"],
                                   m["source_bar"], m["beats"] // 4, DUB_SWING,
                                   detected=g["beats"])
    (VOX_DIR / "phrases.json").write_text(json.dumps(meta))
    pista_vocals_dub()
    build1_end()


def v4_bass():
    for tr in ("BASS", "BASS - teaser (HP)"):
        devs = [d["name"] for d in client.call("get_track", {"track": tr})["devices"]]
        if devs[0] != "Basic FM House Bass":         # Live swaps the instrument in place
            C("load_device", track=tr, path="sounds/Bass/Basic FM House Bass.adg")
        for c in _clips(tr):
            if "FM" in c.get("name", ""):
                continue
            notes = client.call("get_notes", {"track": tr, "clip": {"at": c["start"]}})
            C("add_notes", track=tr, clip={"at": c["start"]},
              notes=[[p - 36, t, d, v] for p, t, d, v in notes], replace=True)
            C("set_clip", track=tr, clip={"at": c["start"]}, name="Murder riff bass (FM)")


BED_V4 = [(29, 64.5), (65, 120.5), (121, 169)]


def v4_loops():
    """Guitar only (in tune: detune 0), through break 2 too (FTS's keys loop out), the +12
    layer muted."""
    global LOOP_DETUNE, BED_V3
    LOOP_DETUNE, BED_V3 = 0, BED_V4
    _clear("LOOP MURDER - break 2 groove")
    C("set_track", track="LOOP MURDER +12 (drop 2 only)", mute=True)
    guitar = _cut_loop("Murder guitar riff", 24)
    T = "LOOP MURDER - riff bed"
    _clear(T)
    for a, b in BED_V4:
        at = beat(a)
        while at < beat(b) - .01:
            bar = at / 4 + 1
            n = min(guitar["beats"], beat(b) - at)
            env = {"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                   "points": [[0, sr.filter_raw(_bed_hz_v4(bar))],
                              [n, sr.filter_raw(_bed_hz_v4(bar + n / 4))]]}
            sr.place_warped(call, T, guitar["path"], at, n, guitar["markers"], envelopes=[env],
                            name="Murder guitar riff")
            at += n


def _bed_hz_v4(bar):
    curve = [(29, 700), (33, 9000), (49, 9000), (49.01, 1400), (57, 1400), (64.5, 14000),
             (65, 14000), (97, 14000), (97.01, 1800), (105, 1100), (113, 1100),
             (120.5, 14000), (153, 14000), (169, 500)]
    for (a, fa), (b, fb) in zip(curve, curve[1:]):
        if a <= bar <= b:
            return fa * (fb / fa) ** ((bar - a) / (b - a) if b > a else 0)
    return curve[-1][1] if bar > curve[-1][0] else curve[0][1]


def v4_breaks():
    """Dub breaks, not FTS's: no breakbeat and no chord bass under them."""
    C("set_track", track="BASS - break", mute=True)
    for c in _clips("BREAKBEAT"):
        if 97 <= c["start"] / 4 + 1 < 113:
            C("set_clip", track="BREAKBEAT", clip={"at": c["start"]}, muted=True)


# call-response chops on the bass's rests (bass: steps 1 3 6 9 11 14): (beat, chop)
CHOP_A = [(1.75, "short"), (2.5, "word"), (5.5, "short"), (5.75, "short"), (7.0, "word")]
CHOP_B = [(2.0, "word"), (3.25, "short"), (6.5, "short"), (6.75, "short"), (7.5, "word")]
CHOP_V4 = [(41, 49), (65, 73), (81, 97), (105, 113), (121, 129), (141, 153), (161, 169)]


def _chop_riff(f, pattern, name):
    x = sf.read(f["word"], dtype="float32")[0]
    sh, fs = sf.read(f["short"], dtype="float32")
    beat_s = 60 / DUB_BPM
    riff = np.zeros((int(8 * beat_s * fs) + 1, x.shape[1]), np.float32)
    for b, k in pattern:
        clip = x if k == "word" else sh
        i = int((b + (DUB_SWING if round(b * 4) % 2 else 0)) * beat_s * fs)
        riff[i:i + len(clip)] += clip[:len(riff) - i]
    path = str(FX_DIR / f"{name}.wav")
    sf.write(path, riff * (.5 / (np.abs(riff).max() + 1e-9)), fs)
    return path


def v4_chops():
    g = sr.source_grid(str(MIX), 86.0)
    f, _ = sr.onset_chops(str(STEM / "vocals.wav"), str(FX_DIR), g["bpm"], g["downbeat"], 4,
                          beat=.75, lengths={"word": .42, "short": .2}, label="Murder chop")
    a = _chop_riff(f, CHOP_A, "Murder chops A (128, 60 %)")
    b = _chop_riff(f, CHOP_B, "Murder chops B (128, 60 %)")
    T = "CHOPS - Murder"
    _clear(T)
    for s_, e in CHOP_V4:
        for k, bar in enumerate(range(s_, e, 2)):
            C("create_audio_clip", track=T, path=a if k % 2 == 0 else b, beat=beat(bar),
              warp=True, beats=8, length=8, name="Murder chops " + "AB"[k % 2])
    C("set_track", track=T, volume_db=-12)


def v4():
    v4_bass()
    v4_swing()
    v4_loops()
    v4_breaks()
    v4_chops()
    print("v4 done")


def v5_mix():
    """validate(v4): FM bass 11.3 dB under the kick (refs 6) and sub 26 %, low-mid/mid 9-10 %
    (refs 2.5-3.9: guitar + chops), clap backbeat 12.3 dB (refs 8), kick 70 Hz (refs 62:
    +3 st was too much), breaks still 1.5 LU under the drops (refs 4.3)."""
    C("set_track", track="BASS", volume_db=-12.3)
    C("set_track", track="LOOP MURDER - riff bed", volume_db=-3)
    C("set_track", track="CHOPS - Murder", volume_db=-14)
    C("set_track", track="CLAP", volume_db=-1.7)
    for tr in ("KICK", "KICK - build (HP)"):
        for c in _clips(tr):
            notes = client.call("get_notes", {"track": tr, "clip": {"at": c["start"]}})
            C("add_notes", track=tr, clip={"at": c["start"]},
              notes=[[62 if p == 63 else p, t, d, v] for p, t, d, v in notes], replace=True)
    for tr in BREAK_TRACKS + ("VOX MURDER - theme calls", "CHOPS - Murder"):
        for c in _clips(tr):
            bar = c["start"] / 4 + 1
            if any(a <= bar < b for a, b in BREAKS):
                C("set_clip", track=tr, clip={"at": c["start"]},
                  gain_db=round(c.get("gain_db", 0) - 2.5, 2))


def v6_bass_back():
    """He: "o timbre do baixo ficou lixo, o outro era melhor": BinBassTone back (notes +36,
    the off-kick riff and 60 % swing kept), level as in the v3 check (-17.3 dB)."""
    for tr in ("BASS", "BASS - teaser (HP)"):
        if client.call("get_track", {"track": tr})["devices"][0]["name"] == "Basic FM House Bass":
            C("delete_device", track=tr, device=0)
            C("load_device", track=tr, path="user_library/Samples/Claude/Nobody Kit/C_BinBassTone_01_SP.wav")
            devs = [d["name"] for d in client.call("get_track", {"track": tr})["devices"]]
            k = next(i for i, n in enumerate(devs) if n.startswith("C_BinBassTone"))
            if k:
                C("move_device", track=tr, device=k, position=0)
        C("set_param", track=tr, device=0, param="Volume", db=-12)   # FTS gain staging
        for c in _clips(tr):
            notes = client.call("get_notes", {"track": tr, "clip": {"at": c["start"]}})
            C("add_notes", track=tr, clip={"at": c["start"]},
              notes=[[p + 36, t, d, v] for p, t, d, v in notes], replace=True)
            C("set_clip", track=tr, clip={"at": c["start"]}, name="Murder riff bass (off the kick)")
    C("set_track", track="BASS", volume_db=-21.3)   # v6 validate: kick only 1 dB over the bass (refs 6)


# ---------------------------------------------------------------- v7: vocals sit, bass speaks
# He: "a mix precisa de muita atenção, os vocais não estão encaixando direito, o bass
# precisa de presença". 15-30 % of the syllables sat ~0.4 of a 16th off the grid (outside
# onset_markers' 0.35 tolerance, so never moved) and the rest moved only 60 %; v6
# validation: bass harmonics -22 dB (refs -8.6).
V7_QUANTIZE, V7_TOL = .85, .5
PIMP = {"VOX MURDER - Pimp C": [(21, 9, 8, 0), (97, 25, 8, -5)],
        "VOX MURDER - trades": [(147, 9, 2, 0), (151, 11, 2, 0)]}


def _cut_v7(name, src_bar, bars):
    import functools
    g = sr.source_grid(str(MIX), 86.0)
    orig = sr.onset_markers
    sr.onset_markers = functools.partial(orig, tol=V7_TOL)
    try:
        return sr.cut_phrase(str(STEM / "vocals.wav"), str(VOX_DIR / f"Murder {name} (src {src_bar}) [v7].wav"),
                             g["bpm"], g["downbeat"], src_bar, bars, DUB_SWING,
                             detected=g["beats"], quantize=V7_QUANTIZE)
    finally:
        sr.onset_markers = orig


def v7_vocals():
    global DUB_SWING
    DUB_SWING = V4_SWING
    meta = json.loads((VOX_DIR / "phrases.json").read_text())
    for name, m in meta.items():
        meta[name] = _cut_v7(name, m["source_bar"], m["beats"] // 4)
    (VOX_DIR / "phrases.json").write_text(json.dumps(meta))
    pista_vocals_dub()
    build1_end()
    for tr, slots in PIMP.items():
        _clear(tr)
        for bar, src, bars, gain in slots:
            m = _cut_v7(f"pimp src {src} {bars} bars", src, bars)
            sr.place_warped(call, tr, m["path"], beat(bar) - m["preroll"], m["clip_beats"],
                            m["markers"], name=f"Murder Pimp C src {src}", gain_db=gain)
    for tr in ("VOX MURDER - hooks", "VOX MURDER - radio", "VOX MURDER - theme calls"):
        for c in _clips(tr):                                   # breaks stay deeper
            if any(a <= c["start"] / 4 + 1 < b for a, b in BREAKS):
                C("set_clip", track=tr, clip={"at": c["start"]},
                  gain_db=round(c.get("gain_db", 0) - 5, 2))


def v7_mix():
    _eq("VOX BUS", 1, "High Pass 12dB", 140)
    _eq("VOX BUS", 5, "Bell", 300, -3, 1.2)
    _eq("VOX BUS", 3, "Bell", 3000, 2.5, 1.0)
    _eq("VOX BUS", 4, "High Shelf", 8000, 1.5)
    # the riff bed ducks under the voice (it ducked under FTS's bass, for the City synth)
    C("set_device_input", track="LOOP MURDER - riff bed", device="Compressor",
      source="VOX BUS", channel="Post FX")
    C("set_param", track="LOOP MURDER - riff bed", device="Compressor", param="Threshold", db=-24)
    C("set_param", track="LOOP MURDER - riff bed", device="Compressor", param="Ratio", display=3)
    _eq("LOOP MURDER - riff bed", 6, "Bell", 900, -1.5, 1.0)
    # bass presence: harmonics a small speaker can hear
    C("set_param", track="BASS", device="Saturator", param="Drive", db=12)
    C("set_param", track="BASS", device="Saturator", param="Dry/Wet", display=75)
    _eq("BASS", 3, "Bell", 900, 3, 1.0)


# ---------------------------------------------------------------- v8: every element in place
# He: "uma mix bem mais top nos detalhes, cada elemento equalizadinho e bem macio encaixado
# no seu lugar". From the solo pass (solo_pass.run, drop 1 bars 81-88 and 73-80, 1/3-octave
# spectra + masking) on v7.
def _bands(track):
    p = client.call("get_device", {"track": track, "device": "EQ Eight"})["params"]
    d = {q["name"]: q["display"] for q in p}
    return {k: (d[f"{k} Filter On A"], d[f"{k} Filter Type A"], d[f"{k} Gain A"]) for k in range(1, 9)}


def _free(track, used):
    for k, (on, kind, gain) in _bands(track).items():
        if k not in used and (on == "Off" or (kind == "Bell" and gain.startswith("0.00"))):
            used.add(k)
            return k
    raise RuntimeError("no free EQ band on " + track)


def _hp(track, hz, used):
    b = _bands(track)
    k = 1 if b[1][1].startswith("High Pass") or b[1][0] == "Off" else _free(track, used)
    used.add(k)
    _eq(track, k, "High Pass 12dB", hz)


V8 = {  # track: (fader dB change, high-pass Hz or None, [(kind, Hz, dB, Q)])
    "KICK": (0, None, [("Bell", 180, -3, 1.2), ("Bell", 3200, 2, .8)]),
    "KICK - build (HP)": (0, None, [("Bell", 180, -3, 1.2)]),
    "BASS": (0, None, [("Bell", 350, -2.5, 1.2)]),
    "CLAP": (-3, 180, [("Bell", 4500, -2, 1.5)]),
    "SNARE": (-2, 200, [("Bell", 160, -4, 2), ("High Shelf", 7000, -2, None)]),
    "HAT OFF - persona": (-4, 400, []),
    "HAT OFF - imite": (-4, 400, []),
    "HAT OFF - shaker shot": (-2, 400, []),
    "HAT 16ths": (0, 500, []),
    "PERC LOOP": (0, 300, []),
    "LOOP MURDER - riff bed": (0, 150, [("Bell", 2500, -3, 3), ("Bell", 500, -2, 1.5)]),
    "CHOPS - Murder": (0, 250, [("Bell", 3150, -2.5, 2.5)]),
    "VOX MURDER - hooks": (-1.5, None, [("Bell", 500, -2, 1.5)]),
}


def v8_mix():
    for tr, (fader, hp, bells) in V8.items():
        used = set()
        if hp:
            _hp(tr, hp, used)
        for kind, hz, db, q in bells:
            _eq(tr, _free(tr, used), kind, hz, db, q)
        if fader:
            v = client.call("get_track", {"track": tr})["vol_db"]
            C("set_track", track=tr, volume_db=round(v + fader, 2))


def v8b_mix():
    """validate(v8): too dark (high-mid 2.6, high 2.1 vs 3.2/2.7; warmth 9.2 vs 6.1, low-mid
    5.3 vs 2.5) and breaks 2.8 LU: v8 cut the off-beat hats and clap too far."""
    for tr, d in (("HAT OFF - persona", 2), ("HAT OFF - imite", 2), ("HAT OFF - shaker shot", 1),
                  ("CLAP", 1.5)):
        v = client.call("get_track", {"track": tr})["vol_db"]
        C("set_track", track=tr, volume_db=round(v + d, 2))
    _eq("master", 8, "High Shelf", 8000, 1)
    _eq("master", 4, "Bell", 250, -1.5, 1.0)      # was FTS's +1.5 @ 350: the warmth
    v8b_breaks()


def v8b_breaks():
    for tr in BREAK_TRACKS + ("VOX MURDER - theme calls", "CHOPS - Murder"):
        for c in _clips(tr):
            if any(a <= c["start"] / 4 + 1 < b for a, b in BREAKS):
                C("set_clip", track=tr, clip={"at": c["start"]},
                  gain_db=round(c.get("gain_db", 0) - 1.5, 2))


def v8c_mono():
    """validate(v8b): low end width -24 dB (refs -43): master Utility Bass Mono 120 Hz,
    before the limiter."""
    C("load_device", track="master", query="Utility", roots=["audio_effects"])
    devs = [d["name"] for d in client.call("get_track", {"track": "master"})["devices"]]
    if devs.index("Utility") > devs.index("Limiter"):
        C("move_device", track="master", device=devs.index("Utility"), position=devs.index("Limiter"))
    C("set_param", track="master", device="Utility", param="Bass Mono", value=1)


# ---------------------------------------------------------------- v9: UKG snare + keys stabs
# He: "um snare fazendo um groove meio UK garage ... e às vezes um synthzinho, pianos, keys,
# stab pra marcar, fazer um bounce, sem repetitivo, espaçado, não tocando sempre".
UKG = [[(4, 100), (7, 52), (10, 70), (12, 100), (15, 78)],          # 2-step snare, 2 bars
       [(2, 48), (4, 100), (9, 72), (12, 100), (14, 50), (15, 80)]]
SNARE_V9 = [(33, 49, .85), (65, 97, 1.0), (121, 153, 1.0)]


def _ukg_notes(bars, scale):
    out = []
    for b in range(bars):
        for step, v in UKG[b % 2]:
            t = b * 4 + step / 4 + (V4_SWING if step % 2 else 0)
            out.append([60, round(t, 4), .2, int(v * scale)])
    return out


def v9_snare():
    _clear("SNARE")
    for a, b, scale in SNARE_V9:
        C("create_midi_clip", track="SNARE", bar=a, length=(b - a) * 4,
          notes=_ukg_notes(b - a, scale), name="UKG 2-step snare")


# rootless voicings, locked to the bass riff (its turn: A on bars from an odd bar, D after)
EM9, AM9, D69 = [55, 59, 62, 66], [59, 60, 64, 67], [57, 59, 62, 66]
PHRASE = {"A": [(0, 3, EM9, .2), (0, 6, EM9, .35), (1, 11, D69, .45)],
          "B": [(0, 6, EM9, .3), (0, 11, AM9, .25), (1, 3, EM9, .2), (1, 9, EM9, .2)]}
KEYS_AT = [(35, "A"), (43, "A"),                                   # groove: 2 of every 8
           (67, "A"), (71, "B"), (79, "B"), (83, "A"), (87, "B"), (91, "A"), (95, "B"),
           (99, "A"), (103, "A"), (107, "B"),                      # break 2, under Pimp C
           (123, "A"), (127, "B"), (135, "B"), (143, "A"), (147, "B"), (151, "A"),
           (155, "A"), (163, "A")]


def v9_keys():
    T = "KEYS - wurli stabs"
    if not any(t["name"] == T for t in client.call("get_song")["tracks"]):
        C("create_track", kind="midi", name=T)
        C("load_device", track=T, path="sounds/Piano & Keys/Wurli Short Piano.adv")
        C("set_track_output", track=T, dest="MUSIC BUS")
        C("set_track", track=T, volume_db=-14, pan=-.15)
        C("set_send", track=T, send=1, db=-16)          # B-Delay
        C("load_device", track=T, query="EQ Eight", roots=["audio_effects"])
        _eq(T, 1, "High Pass 12dB", 180)
    _clear(T)
    for bar, ph in KEYS_AT:
        notes = []
        for b, step, chord, dur in PHRASE[ph]:
            t = b * 4 + step / 4 + (V4_SWING if step % 2 else 0)
            vel = 96 if dur > .3 else 84
            notes += [[p, round(t, 4), dur, vel - 4 * i] for i, p in enumerate(chord)]
        C("create_midi_clip", track=T, bar=bar, length=8, notes=notes, name="stab " + ph)


def v9():
    v9_snare()
    v9_keys()
    print("v9 done")


def v10_mix():
    """He: "encurta o reverb do clap, baixa o baixo, faz a mix direito, melhora o stab, a
    presença". Solo pass bars 83-90: keys -19 LU and dull (nothing above 3 kHz) under a
    riff 15-25 dB louder at 160-630 Hz; bass -4.7, clap -5.8 LU; clap tail ~445 ms (D-Room
    800 ms at -16 dB send + A-Reverb)."""
    C("set_send", track="CLAP", send=3, db=-24)
    C("set_send", track="CLAP", send=0, db=-70)
    C("set_param", track="return:D-Room", device="Reverb", param="Decay Time", display="600 ms")
    for tr, d in (("BASS", -3), ("CLAP", -2), ("LOOP MURDER - riff bed", -2), ("KEYS - wurli stabs", 4)):
        v = client.call("get_track", {"track": tr})["vol_db"]
        C("set_track", track=tr, volume_db=round(v + d, 2))
    used = set()
    _eq("LOOP MURDER - riff bed", 4, "Bell", 180, -3, 1.2)       # was a duplicate 630 cut
    K = "KEYS - wurli stabs"
    used = {1}
    _eq(K, _free(K, used), "Bell", 2500, 3, 1.0)
    _eq(K, _free(K, used), "High Shelf", 6000, 2)
    _eq(K, _free(K, used), "Bell", 300, -2, 1.2)
    if not any(d["name"] == "Saturator" for d in client.call("get_track", {"track": K})["devices"]):
        C("load_device", track=K, query="Saturator", roots=["audio_effects"])
        C("set_param", track=K, device="Saturator", param="Drive", db=5)
        C("set_param", track=K, device="Saturator", param="Dry/Wet", display=40)


# ---------------------------------------------------------------- v11: glued, wide, deep
# He: "esse fx de breakbeat está conflitando com o groove; as coisas não estão todas
# coladas; uma mix bem colada; tudo pensado no stereo, no paneamento e na track 3D".
# v10 validate: width mid -10.3 / high -9.2 dB (refs -6.9 / -6.1): too narrow.
# Not touched (his own moves after v10): BASS fader, CLAP sends, KEYS mute.
A, B, C_, D, E = range(5)                    # A-Reverb, B-Delay, C-Atmos, D-Room, E-Plate
PANS = {"HAT 16ths": .12, "HAT OFF - persona": .3, "HAT OFF - imite": -.3,
        "HAT OFF - shaker shot": .45, "RIDE 909": .2, "PERC LOOP": -.4,
        "LOOP MURDER - riff bed": .25, "KEYS - wurli stabs": -.3, "CHOPS - Murder": -.1}
SENDS = {  # depth: front dry (kick, bass, clap, lead vocal), middle a little room, back atmos
    "LOOP MURDER - riff bed": {C_: -16, D: -24},
    "KEYS - wurli stabs": {D: -20, B: -16},
    "CHOPS - Murder": {D: -24, B: -14},
    "VOX MURDER - hooks": {D: -28},
    "VOX MURDER - theme calls": {D: -28},
    "VOX MURDER - Pimp C": {D: -28},
    "VOX MURDER - radio": {C_: -16, D: -22},
}


def v11():
    C("set_track", track="BREAKBEAT", mute=True)
    for tr, pan in PANS.items():
        C("set_track", track=tr, pan=pan)
    for tr, sends in SENDS.items():
        for k, db in sends.items():
            C("set_send", track=tr, send=k, db=db)
    # the riff bed: wider above its low end (Utility width, low end kept mono)
    T = "LOOP MURDER - riff bed"
    if not any(d["name"] == "Utility" for d in client.call("get_track", {"track": T})["devices"]):
        C("load_device", track=T, query="Utility", roots=["audio_effects"])
    C("set_param", track=T, device="Utility", param="Stereo Width", display=140)
    C("set_param", track=T, device="Utility", param="Bass Mono", value=1)
    C("set_param", track=T, device="Utility", param="Bass Freq", display=200)


# ---------------------------------------------------------------- v12: stab candidates
# He muted the Wurli stabs ("não gostei muito"): the same phrases on three timbres, each
# on its own muted track, for him to audition by solo in Live.
STAB_CANDIDATES = {"STAB - twice for murder": "sounds/Synth Keys/Stab Twice for Murder.adv",
                   "STAB - dub pluck": "sounds/Guitar & Plucked/Chord Dub Pluck.adg",
                   "STAB - organ": "sounds/Piano & Keys/Organ Analog.adg"}


def v12_stabs():
    src = "KEYS - wurli stabs"
    clips = [(c["start"], client.call("get_notes", {"track": src, "clip": {"at": c["start"]}}),
              c["name"]) for c in _clips(src)]
    names = [t["name"] for t in client.call("get_song")["tracks"]]
    for T, preset in STAB_CANDIDATES.items():
        if T not in names:
            C("create_track", kind="midi", name=T)
            C("load_device", track=T, path=preset)
            C("set_track_output", track=T, dest="MUSIC BUS")
            C("load_device", track=T, query="EQ Eight", roots=["audio_effects"])
            _eq(T, 1, "High Pass 12dB", 180)
        C("set_track", track=T, volume_db=-12, pan=-.3, mute=True)
        C("set_send", track=T, send=3, db=-20)
        C("set_send", track=T, send=1, db=-16)
        _clear(T)
        for at, notes, name in clips:
            C("create_midi_clip", track=T, beat=at, length=8, notes=notes, name=name)


# ---------------------------------------------------------------- v13: pro mix + master pass
# He (2026-10-22): "mix bem melhor, timbres mais macios, comprimidas, fase, multibanda,
# conflitos de frequência... master top, profissional, igual o mercado, pra tocar sábado".
# Measured: master limiter at +16 dB input cut ~11 dB of the kick's peaks (premaster drop
# -17.1 LUFS, TP -5.6); 30 references (Dub House Streets x2 weight + Sexy Vibes): sub 50 ms
# range 11 vs 30 dB (the sub never breathes), kick attack/body 4.7 vs 6.0, 31-39 Hz +4-5 dB,
# 4-5 kHz -2.5, 16 kHz -3, highs too narrow (side/mid -9.5 vs -6.5), 500 Hz +3 / 1 kHz +2,
# low-mid/mid static, bars 17-48 louder than the drops, ceiling -1 vs refs ~0 dBTP.
def v13_mix():
    # 1. the sub breathes with the kick: deeper, faster duck on the bass
    C("set_param", track="BASS", device="Compressor", param="Threshold", db=-38)
    C("set_param", track="BASS", device="Compressor", param="Ratio", display=10)
    C("set_param", track="BASS", device="Compressor", param="Release", display=120)
    # 2. the deep sub (31-39 Hz) on the low-end bus: a bell, never a HP above E1 (41 Hz)
    _eq("LOW END", _free("LOW END", set()), "Bell", 35, -3, 1.2)
    # 4. presence on the drums (4-5 kHz), hats' spikes rounded (soft clip 1-2 dB)
    _eq("DRUMS", _free("DRUMS", set()), "Bell", 4800, 2, .7)
    C("set_param", track="DRUMS", device="Limiter", param="Mode", item="Soft Clip")
    C("set_param", track="DRUMS", device="Limiter", param="Threshold", db=-13)
    C("set_param", track="DRUMS", device="Limiter", param="Ceiling", db=-13)
    C("set_param", track="DRUMS", device="Limiter", param="Output", db=1.5)
    v13_mix_rest()


def v13_mix_rest():
    # 5./6. width of the highs: side-only high shelf on the drums (M/S EQ at the bus end)
    devs = [d["name"] for d in client.call("get_track", {"track": "DRUMS"})["devices"]]
    if devs.count("EQ Eight") < 2:
        C("load_device", track="DRUMS", query="EQ Eight", roots=["audio_effects"])
    ms = "EQ Eight#1"   # Name#k counts from 0
    C("set_device_prop", track="DRUMS", device=ms, prop="global_mode", value=2)
    for k in range(1, 9):
        C("set_param", track="DRUMS", device=ms, param=f"{k} Filter On A", value=0)
    C("set_param", track="DRUMS", device=ms, param="1 Filter On B", value=1)
    C("set_param", track="DRUMS", device=ms, param="1 Filter Type B", item="High Shelf")
    C("set_param", track="DRUMS", device=ms, param="1 Frequency B", display=3000)
    C("set_param", track="DRUMS", device=ms, param="1 Gain B", display=2.5)
    # 7. the music breathes with the kick, the 500 Hz box and 1 kHz bump out
    C("set_param", track="MUSIC BUS", device="Compressor", param="Threshold", db=-22)
    C("set_param", track="MUSIC BUS", device="Compressor", param="Ratio", display=3)
    C("set_param", track="MUSIC BUS", device="Compressor", param="Release", display=160)
    _eq("MUSIC BUS", _free("MUSIC BUS", set()), "Bell", 500, -2, 1.4)
    _eq("MUSIC BUS", _free("MUSIC BUS", set()), "Bell", 1000, -1.5, 2)
    _eq("VOX BUS", _free("VOX BUS", set()), "Bell", 500, -2, 1.4)
    # arrangement: the drops the loudest; breaks back up 1.5 dB
    _clear_range_snare_groove()
    for tr in ("LOOP MURDER - riff bed", "PERC LOOP", "CHOPS - Murder"):
        for c in _clips(tr):
            if 17 <= c["start"] / 4 + 1 < 49:
                C("set_clip", track=tr, clip={"at": c["start"]},
                  gain_db=round(c.get("gain_db", 0) - 1.5, 2))
    for tr in BREAK_TRACKS + ("VOX MURDER - theme calls", "CHOPS - Murder"):
        for c in _clips(tr):
            if any(a <= c["start"] / 4 + 1 < b for a, b in BREAKS):
                C("set_clip", track=tr, clip={"at": c["start"]},
                  gain_db=round(c.get("gain_db", 0) + 1.5, 2))


def _clear_range_snare_groove():
    """The UKG snare only in the drops: the groove keeps its lighter pocket (contrast)."""
    for c in _clips("SNARE"):
        if c["start"] / 4 + 1 < 49:
            C("delete_clip", track="SNARE", clip={"at": c["start"]})


def v13_master(limiter_gain=12.5, clip_db=-9.7):
    """Master: EQ (air shelf +2.5 @12k) -> Saturator -> Glue -> Utility (bass mono 150 Hz)
    -> soft clip (Limiter in Soft Clip mode, ~3 dB off the kick's peaks) -> Limiter True Peak
    -0.3 dBTP at ~+11 dB input (it was +16 at -1.0: ~11 dB of limiting)."""
    _eq("master", 8, "High Shelf", 12000, 2.5)
    C("set_param", track="master", device="Utility", param="Bass Freq", display=150)
    devs = [d["name"] for d in client.call("get_track", {"track": "master"})["devices"]]
    if devs.count("Limiter") < 2:
        C("load_device", track="master", query="Limiter", roots=["audio_effects"])
        devs = [d["name"] for d in client.call("get_track", {"track": "master"})["devices"]]
        C("move_device", track="master", device=len(devs) - 1, position=devs.index("Limiter"))
    clip, lim = "Limiter#0", "Limiter#1"          # Name#k counts from 0
    C("set_device_on", track="master", device=clip, on=True)
    C("set_param", track="master", device=clip, param="Mode", item="Soft Clip")
    C("set_param", track="master", device=clip, param="Threshold", db=clip_db)
    C("set_param", track="master", device=clip, param="Ceiling", db=clip_db)
    C("set_param", track="master", device=clip, param="Output", db=0)
    C("set_device_on", track="master", device=lim, on=True)
    C("set_param", track="master", device=lim, param="Mode", item="True Peak")
    C("set_param", track="master", device=lim, param="Ceiling", db=-0.3)
    C("set_param", track="master", device=lim, param="Threshold", db=-0.3)
    C("set_param", track="master", device=lim, param="Input Gain", db=limiter_gain)


def dub():
    dub_bass()
    dub_swing()
    dub_tempo()
    dub_mix()
    print("dub done")


if __name__ == "__main__":
    {"sketch": sketch, "pista": pista, "pista_loops": pista_loops, "pista_vocals": pista_vocals,
     "pista_fx": pista_fx, "pista_cues": pista_cues, "dub": dub, "dub_mix": dub_mix,
     "dub_v3": dub_v3, "dub_mix2": dub_mix2, "v4": v4, "v5_mix": v5_mix, "v6_bass_back": v6_bass_back,
     "v7_vocals": v7_vocals, "v7_mix": v7_mix, "v8_mix": v8_mix, "v8b_mix": v8b_mix, "v8b_breaks": v8b_breaks,
     "v9": v9, "v9_keys": v9_keys, "v10_mix": v10_mix, "v11": v11, "v12_stabs": v12_stabs,
     "v13_mix": v13_mix, "v13_mix_rest": v13_mix_rest, "v13_master": v13_master}[sys.argv[1]]()
