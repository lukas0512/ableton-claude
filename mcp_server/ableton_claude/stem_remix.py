"""Remixing from an original's stems: what made "From The Streets" (2026-10-20) pass the
producer's ear, as reusable pieces (the first build was scripts/build_from_the_streets.py).

- Rap phrases cut bar-aligned at the source tempo and placed with warp markers on every
  source 16th; where a syllable starts near a 16th the marker sits on the syllable and
  moves it QUANTIZE of the way onto the 16th plus the kit's swing (Murder's hook ran
  +25 ms late, half its syllables a quarter-16th off; a straight rap over swung hats read
  early). Half a beat of pre-roll keeps the pickup into beat 1.
- Chops that start at a real syllable attack, unwarped (grid slices cut syllables in half).
- Loops from the originals' own instruments (demucs 'other' stem): the 2-bar window with
  the least vocal bleed that is most like the rest of the song, warped per 16th with the
  swing, tiled into one clip per section with an Auto Filter envelope.
- A breakbeat warped onto the track's pocket (its hits moved toward the swung 16ths).

Offline functions take arrays and paths; functions that touch Live take `call`
(client.call, or server._journaled so every change can be reverted).
"""
import json
import math
import os
import re
import statistics
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

QUANTIZE = 0.6        # how far each syllable moves toward its 16th (1 = hard quantize)
BREAK_QUANTIZE = 0.7  # a break's hits move further: drums sit on the grid, a voice talks
PREROLL = 0.5         # beats of source before a phrase's downbeat (rap lines start before it)
CHOP_LEAD_S = 0.004   # a chop file starts this long before the attack
BEAT_TOL_S = 0.04     # a detected source beat within this of the straight grid is used


# ---------------------------------------------------------------- audio helpers
def read_stereo(path, dtype="float32"):
    x, sr = sf.read(str(path), dtype=dtype)
    if x.ndim == 1:
        x = np.repeat(x[:, None], 2, axis=1)
    return x, sr


def highpass(x, hz, sr):
    return signal.sosfiltfilt(signal.butter(2, hz, "highpass", fs=sr, output="sos"), x, axis=0)


def edge(x, sr, a=.006, r=.030):
    """Fade in `a` s and out `r` s (no clicks at the cut)."""
    x = x.copy()
    na, nr = max(1, int(a * sr)), max(1, int(r * sr))
    x[:na] *= np.linspace(0, 1, na)[:, None]
    x[-nr:] *= np.linspace(1, 0, nr)[:, None]
    return x


def normalize(x, peak=.5):
    return x * (peak / max(float(np.abs(x).max()), 1e-6))


def write(path, x, sr):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), x.astype(np.float32), sr, subtype="PCM_24")
    return str(path)


def swing_beats(swing_ms, bpm):
    """Off-beat 16ths `swing_ms` late at `bpm`, in beats."""
    return (swing_ms or 0.0) / 1000.0 * bpm / 60.0


def filter_raw(hz):
    """Auto Filter Frequency as a raw envelope value: 0.3918 at 300 Hz, +0.1003 per
    octave (read from Live 12)."""
    return round(0.3918 + 0.1003 * math.log2(hz / 300.0), 4)


# ---------------------------------------------------------------- the source grid
def source_sixteenths(bpm, downbeat, bar, bars, detected=None, tol=BEAT_TOL_S):
    """Source times (s) of every 16th of `bars` bars from source bar `bar` (1 = the bar at
    `downbeat`), plus the end. The detected beats within `tol` of the straight grid fit a
    line (the window's local tempo and phase); every beat sits on it, evenly spaced;
    16ths are interpolated between beats (the originals were straight, swing 50-52 %)."""
    # Beat This reports beats on 20 ms frames and wanders on busy bars: snapping each beat to
    # its own detection made beats of 400-500 ms in a 444 ms record and the loop wobbled
    # ("fora de warp", Get Up 2026-11-06). The detections near the grid only steer a line
    # (local tempo + phase, outliers dropped); every beat sits on it.
    period = 60.0 / bpm
    det = np.asarray(detected if detected is not None else [], float)
    k0 = (bar - 1) * 4
    ks = np.arange(-4, bars * 4 + 5)
    grid_t = downbeat + (k0 + ks) * period
    kk, tt = [], []
    if len(det):
        for k, t in zip(ks, grid_t):
            near = det[np.argmin(np.abs(det - t))]
            if abs(near - t) < tol:
                kk.append(k)
                tt.append(near - t)
    a, b = 0.0, 0.0                         # offset (s) and drift (s per beat) from the grid
    if len(kk) >= 6:
        kk, tt = np.asarray(kk, float), np.asarray(tt, float)
        keep = np.ones(len(kk), bool)
        for _ in range(3):
            b, a = np.polyfit(kk[keep], tt[keep], 1)
            res = np.abs(tt - (a + b * kk))
            new = res < max(0.012, 2.5 * np.median(res[keep]))
            if new.sum() < 6 or (new == keep).all():
                break
            keep = new
        if np.median(np.abs(tt[keep] - (a + b * kk[keep]))) > 0.010:
            a, b = 0.0, 0.0                 # detections that disagree: the global fit is better
            # (Get Up bar 64: a line through them sat 46 ms off the record's kick, the
            # global grid 0-8 ms)
    elif kk:
        a = float(np.median(tt))
    beats = [float(downbeat + (k0 + k) * period + a + b * k) for k in range(bars * 4 + 1)]
    out = []
    for b0, b1 in zip(beats, beats[1:]):
        out += [b0 + (b1 - b0) * q / 4 for q in range(4)]
    return out + [beats[-1]]


def source_grid(mix_path, bpm_hint=None, cache_dir=None):
    """{bpm, downbeat, beats} of an original mix from the ear's beat tracker (Beat This),
    cached as JSON in `cache_dir`. Detect on the full mix, never on a vocal stem."""
    cache = None
    if cache_dir:
        cache = Path(cache_dir) / ("source-grid - %s.json" % Path(mix_path).stem)
        if cache.exists():
            return json.loads(cache.read_text())
    from .ear import grid
    x, sr = read_stereo(mix_path)
    beats, downbeats = grid.detect(x, sr)
    g = grid.fit(beats, downbeats, len(x) / sr, bpm_hint=bpm_hint)
    out = {"bpm": float(g["bpm"]), "downbeat": float(g["first_downbeat"]),
           "beats": [round(float(b), 4) for b in beats], "mix": str(mix_path)}
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(out))
    return out


def kick_stem_for(stem):
    """The DrumSep kick split_elements left next to a stem ('<x> - other.wav' ->
    'drums/<x> - kick.wav'), or None."""
    p = Path(stem)
    base = p.stem.rsplit(" - ", 1)[0]
    k = p.parent / "drums" / ("%s - kick.wav" % base)
    return k if k.exists() else None


def kick_beats(kick_path, cache_dir=None):
    """Attack times (s) of the hits in a kick stem: the record's own beat, steadier than a
    beat tracker's detections (Get Up 2026-11-06: within ~1 ms of the kick where Beat This
    sat up to 36 ms off it). Cached as JSON next to the source grid."""
    cache = Path(cache_dir) / ("kick-beats - %s.json" % Path(kick_path).stem) if cache_dir else None
    if cache and cache.exists():
        return json.loads(cache.read_text())
    import librosa
    y, sr = librosa.load(str(kick_path), sr=22050, mono=True)
    on = librosa.onset.onset_detect(y=y, sr=sr, hop_length=64, units="time", backtrack=True)
    n = int(.03 * sr)
    rms = np.array([np.sqrt(np.mean(y[int(t * sr): int(t * sr) + n] ** 2)) for t in on])
    out = [round(float(t), 4) for t in on[rms > rms.max() * .1]] if len(on) else []
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(out))
    return out


# ---------------------------------------------------------------- onsets and markers
def syllable_onsets(x, sr, a, b):
    """Onsets (s) in [a, b): spectral flux 150 Hz-8 kHz, peaks over median + 1.2 sd at
    least 70 ms apart. Syllables on a vocal stem, hits on a drum loop."""
    mono = x.mean(axis=1) if x.ndim == 2 else x
    seg = mono[int(a * sr): int(b * sr)]
    if len(seg) < 2048:
        return np.array([])
    f, t, Z = signal.stft(seg, sr, nperseg=1024, noverlap=768)
    M = np.log1p(np.abs(Z) * 50)[(f > 150) & (f < 8000)]
    flux = np.convolve(np.maximum(np.diff(M, axis=1), 0).sum(0), np.hanning(5) / 2.5, "same")
    pk, _ = signal.find_peaks(flux, height=np.median(flux) + 1.2 * np.std(flux),
                              distance=max(1, int(.07 * sr / 256)))
    return a + t[1:][pk]


def onset_markers(sixteenths, file_start, onsets, swing, quantize=QUANTIZE, preroll=PREROLL,
                  tol=.35):
    """Warp markers [[beat, seconds in file], ...]: one on every 16th (the off-beat ones
    `swing` beats late), except where an onset lies within `tol` of a 16th of one: there
    the marker sits on the onset and moves it `quantize` of the way onto the swung 16th.
    The first and last 16th stay on the grid. quantize=0 keeps the source's own timing on
    the swung grid; quantize=1 hard-quantizes."""
    six = np.asarray(sixteenths, float)
    targets = {}
    for o in onsets:
        k = int(np.argmin(np.abs(six - o)))
        if k == 0 or k == len(six) - 1:
            continue
        step = (six[k + 1] - six[k - 1]) / 2
        dev = (o - six[k]) / step                          # in 16ths
        if abs(dev) < tol and k not in targets:
            targets[k] = (float(o), dev)
    m = [[0.0, 0.0]]
    for k, t in enumerate(six):
        beat_k = preroll + k / 4 + (swing if k % 2 else 0.0)
        if beat_k <= 1e-9:
            continue
        if k in targets:
            o, dev = targets[k]
            m.append([round(beat_k + (1 - quantize) * dev / 4, 6), round(o - file_start, 6)])
        else:
            m.append([round(beat_k, 6), round(float(t) - file_start, 6)])
    return m


def grid_markers(sixteenths, file_start, swing):
    """A marker on every 16th, the off-beat ones `swing` beats late (instrument loops)."""
    return onset_markers(sixteenths, file_start, [], swing, preroll=0.0)


# ---------------------------------------------------------------- 1. rap phrases
def cut_phrase(stem, out_path, bpm, downbeat, bar, bars, swing, detected=None,
               quantize=QUANTIZE, preroll=PREROLL):
    """Cut `bars` bars from source bar `bar` of a vocal stem, with `preroll` beats before.
    The take is the mono centre (drops the instrumental's stereo spill), high-passed at
    90 Hz, gently expanded under the voice (separation bleed between words), faded and
    normalized to -6 dBFS. Returns {path, beats, clip_beats, preroll, markers,
    n_syllables, source_bar}: place it `preroll` beats before the target downbeat."""
    x, sr = read_stereo(stem)
    six = source_sixteenths(bpm, downbeat, bar, bars, detected)
    a = six[0] - preroll * 60.0 / bpm
    if a < 0 or six[-1] * sr > len(x):
        raise ValueError("source bars %d-%d fall outside the stem" % (bar, bar + bars - 1))
    mono = np.repeat(x.mean(axis=1, keepdims=True), 2, axis=1)
    hp = highpass(mono, 90, sr).astype(np.float32)
    take = hp[int(a * sr): int(six[-1] * sr)].copy()
    env = ndimage.uniform_filter1d(np.abs(take).mean(axis=1), size=int(.012 * sr))
    take *= np.clip((env / .02) ** .5, .3, 1.0)[:, None]
    take = normalize(edge(take, sr))
    path = write(out_path, take, sr)
    ons = syllable_onsets(x, sr, six[0], six[-1])
    return {"path": path, "beats": bars * 4, "clip_beats": bars * 4 + preroll,
            "preroll": preroll, "source_bar": bar,
            "markers": onset_markers(six, a, ons, swing, quantize, preroll),
            "n_syllables": int(len(ons))}


# ---------------------------------------------------------------- 2. onset chops
def onset_chops(stem, out_dir, bpm, downbeat, bar, detected=None, beat=0.0,
                lengths=None, before_s=.15, after_s=.30, label="chop"):
    """Chops of a vocal stem that start at a real syllable attack: the strongest onset
    (mean level over its first 80 ms) within [-before_s, +after_s] of source bar `bar`
    beat `beat`; the file starts CHOP_LEAD_S before it. Unwarped: the voice keeps its own
    speed. Returns ({name: path}, attack offset from the source grid in s)."""
    lengths = lengths or {"long": .90, "short": .40}
    x, sr = read_stereo(stem)
    mono = x.mean(axis=1)
    six = source_sixteenths(bpm, downbeat, bar, 1, detected)
    t0 = six[min(int(round(beat * 4)), 16)]
    ons = syllable_onsets(mono, sr, max(0.0, t0 - before_s), t0 + after_s)
    if len(ons):
        o = float(max(ons, key=lambda o: np.abs(mono[int(o * sr): int((o + .08) * sr)]).mean()))
    else:
        o = t0
    hp = highpass(np.repeat(mono[:, None], 2, axis=1), 90, sr).astype(np.float32)
    out = {}
    for name, length in lengths.items():
        take = hp[max(0, int((o - CHOP_LEAD_S) * sr)): int((o + length) * sr)].copy()
        take = normalize(edge(take, sr, .003, .04))
        out[name] = write(Path(out_dir) / ("%s - %s (onset-aligned, src %s).wav" % (label, name, bar)),
                          take, sr)
    return out, o - t0


# ---------------------------------------------------------------- 3. loops from the 'other' stem
def _band_profile(x, sr):
    mono = x.mean(axis=1) if x.ndim == 2 else x
    f, p = signal.welch(mono, sr, nperseg=4096)
    edges = np.geomspace(60, 12000, 19)
    return np.log10(np.array([p[(f >= lo) & (f < hi)].sum() for lo, hi in zip(edges, edges[1:])])
                    + 1e-12)


def loop_candidates(other, sr, bpm, downbeat, bars=2, vocals=None, detected=None,
                    first_bar=1, last_bar=None, min_level_db=-30.0):
    """Every `bars`-bar window of an 'other' stem, ranked: least vocal (vocal stem level
    against the window's own level, i.e. what bleeds through separation) and most typical
    (band profile closest to the median window: the song's own sound, not a fill or a
    break). Windows more than `min_level_db` under the loudest are skipped (silence).
    Returns [{bar, vocal_db, typical_db, level_db, score}] best first."""
    total_bars = int((len(other) / sr - downbeat) / (4 * 60.0 / bpm))
    last = min(last_bar or total_bars, total_bars) - bars + 1
    rows = []
    for b in range(max(1, first_bar), last + 1):
        six = source_sixteenths(bpm, downbeat, b, bars, detected)
        a, z = int(six[0] * sr), int(six[-1] * sr)
        seg = other[a:z]
        lvl = 10 * np.log10(np.mean(seg ** 2) + 1e-12)
        voc = -120.0
        if vocals is not None:
            voc = 10 * np.log10(np.mean(vocals[a:z] ** 2) + 1e-12) - lvl
        rows.append({"bar": b, "level_db": lvl, "vocal_db": voc, "profile": _band_profile(seg, sr)})
    if not rows:
        return []
    top = max(r["level_db"] for r in rows)
    rows = [r for r in rows if r["level_db"] > top + min_level_db]
    med = np.median(np.array([r["profile"] for r in rows]), axis=0)
    for r in rows:
        r["typical_db"] = float(10 * np.sqrt(np.mean((r.pop("profile") - med) ** 2)))
    rank_v = {id(r): i for i, r in enumerate(sorted(rows, key=lambda r: r["vocal_db"]))}
    rank_t = {id(r): i for i, r in enumerate(sorted(rows, key=lambda r: r["typical_db"]))}
    for r in rows:
        r["score"] = rank_v[id(r)] + rank_t[id(r)]
    rows.sort(key=lambda r: (r["score"], r["vocal_db"]))
    return [{"bar": r["bar"], "score": int(r["score"]),
             **{k: round(float(r[k]), 2) for k in ("vocal_db", "typical_db", "level_db")}}
            for r in rows]


def cut_loop(other, sr, out_path, bpm, downbeat, bar, bars, swing, detected=None):
    """A `bars`-bar loop of the 'other' stem from source bar `bar`, cut on the source
    downbeats (2 ms / 4 ms edges), with a warp marker on every 16th (off-beats `swing`
    beats late). Returns {path, beats, markers, source_bar}."""
    six = source_sixteenths(bpm, downbeat, bar, bars, detected)
    a = six[0]
    take = normalize(edge(other[int(a * sr): int(six[-1] * sr)].copy(), sr, .002, .004))
    return {"path": write(out_path, take, sr), "beats": bars * 4, "source_bar": bar,
            "markers": grid_markers(six, a, swing)}


def section_file(loop, bars, out_path, gate=None):
    """The loop tiled over `bars` bars at source time, one file for one clip per section
    (no audible loop seams, one filter envelope across the section). Bars where
    gate(bar_in_section) is False are silenced with 5 ms fades: e.g. a loop that answers
    only in the 2nd bar of each pair. Returns (path, markers)."""
    x, sr = read_stereo(loop["path"])
    L = len(x) / sr
    tile_beats = float(loop["beats"])
    tile_bars = max(1, int(round(tile_beats / 4)))
    n = int(math.ceil(bars / tile_bars))
    seg = len(x) // tile_bars
    f = int(.005 * sr)
    tiles, mk = [], [[0.0, 0.0]]
    for j in range(n):
        t = x.copy()
        for i in range(tile_bars):
            if gate and not gate(j * tile_bars + i):
                a, b = i * seg, (i + 1) * seg if i < tile_bars - 1 else len(t)
                t[a:a + f] *= np.linspace(1, 0, f)[:, None]
                t[a + f:b - f] = 0
                t[b - f:b] *= np.linspace(0, 1, f)[:, None] if b < len(t) else 0
        tiles.append(t)
        mk += [[round(b + tile_beats * j, 6), round(s + j * L, 6)] for b, s in loop["markers"][1:]]
    return write(out_path, np.concatenate(tiles), sr), mk


# ---------------------------------------------------------------- 5. breakbeats
def loop_bpm_from_name(path):
    m = re.search(r"(?<!\d)(\d{2,3})(?:\s*|_)?bpm", Path(path).stem, re.I) \
        or re.search(r"(?:^|[_ -])(\d{2,3})(?:[_ -])", Path(path).stem)
    return float(m.group(1)) if m else None


def break_loop(x, sr, loop_bpm, swing, quantize=BREAK_QUANTIZE, tol=.4):
    """Warp markers that put a drum break into the track's pocket: the file's own 16th
    grid at `loop_bpm`, each hit within `tol` of a 16th moved `quantize` of the way onto
    the swung 16th. Returns (markers, beats)."""
    dur = len(x) / sr
    step = 60.0 / loop_bpm / 4
    n16 = int(round(dur / step))
    six = np.minimum(np.arange(n16 + 1) * step, dur - .001)
    ons = syllable_onsets(x, sr, 0, dur)
    return onset_markers(six, 0.0, ons, swing, quantize, preroll=0.0, tol=tol), n16 / 4


# ---------------------------------------------------------------- placing in Live
def has_device(call, track, name):
    return any(d["name"] == name or d.get("class") == name.replace(" ", "")
               for d in call("get_track", {"track": track, "clips": False})["devices"])


def ensure_auto_filter(call, track):
    if not has_device(call, track, "Auto Filter"):
        call("load_device", {"track": track, "query": "Auto Filter", "roots": ["audio_effects"]})


def filter_envelope(f0, f1, beats, open_by=None):
    """Auto Filter Frequency from f0 to f1 Hz over `beats` (or reaching f1 at `open_by`)."""
    pts = [[0, filter_raw(f0)]]
    if open_by and open_by < beats:
        pts.append([open_by, filter_raw(f1)])
    pts.append([beats, filter_raw(f1)])
    return {"param": "Frequency", "device": "Auto Filter", "unit": "raw", "points": pts}


def place_warped(call, track, path, at, beats, markers, envelopes=None, name=None,
                 warp_mode="complex_pro", gain_db=None):
    """An audio clip at beat `at`, exactly `beats` long, warped by `markers`
    ([[beat, s], ...]; the last one is clamped inside the file). Markers do not resize a
    clip, so a clip Live made longer is trimmed (only where nothing lies after it).
    The clip is created already pinned to the beats the file spans: created unwarped, Live
    sized it by the file's seconds at the set's tempo, and a 135 BPM loop in a 130 BPM set
    ended ~2.6 beats short of every section (Get Up, 2026-11-06)."""
    dur = sf.info(path).duration - .001
    end_beat = float(beats)
    if len(markers) >= 2:
        (b0, s0), (b1, s1) = markers[-2], markers[-1]
        if s1 > s0:
            end_beat = max(end_beat, b1 + (dur - s1) * (b1 - b0) / (s1 - s0))
    call("create_audio_clip", {"track": track, "path": path, "beat": at, "warp": True,
                               "beats": round(end_beat, 4),
                               "name": name or Path(path).stem, "envelopes": envelopes or None})
    clip = {"at": at}
    call("set_warp_markers", {"track": track, "clip": clip,
                              "markers": [[b, min(t, dur)] for b, t in markers]})
    args = {"track": track, "clip": clip, "warping": True, "warp_mode": warp_mode,
            "looping": False, "start_marker": 0, "end_marker": beats}
    if gain_db is not None:
        args["gain_db"] = gain_db
    call("set_clip", args)
    mine = [c for c in call("get_track", {"track": track})["clips"] if abs(c["start"] - at) < .01]
    trimmed = bool(mine and mine[0]["end"] > at + beats + .02)
    if trimmed:
        call("trim_clip", {"track": track, "clip": clip, "end_beat": at + beats})
    return {"track": track, "beat": at, "beats": beats, "path": path, "trimmed": trimmed}


def set_pocket_ms(call):
    """The set's swing: median lateness (ms) of the off-beat 16ths over its unmuted MIDI
    parts (quality_gate's pocket). 0.0 when no part has enough off-beat notes."""
    from . import quality_gate as gate
    song = call("get_song")
    offs = []
    for t in song["tracks"]:
        if t.get("kind") != "midi" or t.get("mute"):
            continue
        det = call("get_track", {"track": t["i"]})
        times = []
        for c in det.get("clips", []):
            if c.get("type") == "midi":
                times += [c["start"] + n[1] for n in call("get_notes", {"track": t["i"],
                                                                        "clip": {"at": c["start"]}})]
        o = gate.off16_offset_ms(times, song.get("tempo", 120.0))
        if o is not None:
            offs.append(o)
    return round(statistics.median(offs), 2) if offs else 0.0


def default_out_dir(path):
    return str(Path(path).parent / "claude-remix")


def save_meta(out_dir, name, meta):
    """Keep what a tool cut (paths, markers) next to the audio, so it can be placed again."""
    p = Path(out_dir) / "stem-remix.json"
    data = json.loads(p.read_text()) if p.exists() else {}
    data[name] = meta
    os.makedirs(out_dir, exist_ok=True)
    p.write_text(json.dumps(data, indent=1))
    return str(p)
