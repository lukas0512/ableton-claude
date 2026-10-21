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
    m = sr.cut_loop(x, fs, str(LOOPS / f"{name} (125).wav"), g["bpm"], g["downbeat"], bar, 2,
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


if __name__ == "__main__":
    {"sketch": sketch, "pista": pista, "pista_loops": pista_loops, "pista_vocals": pista_vocals,
     "pista_fx": pista_fx, "pista_cues": pista_cues}[sys.argv[1]]()
