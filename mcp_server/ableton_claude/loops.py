"""Loops built from one-shots and placed with a genre's measured groove.

A pack's drum loops carry their producer's feel and timbre together; one-shots carry
neither feel nor pattern. Choosing the one-shot by timbre (timbre.find_samples) and
placing it with the references' per-16th micro-timing, accents and timing variation
(ear.why.groove_template) gives a loop with the genre's sound and the genre's groove.
The result is a plain WAV at the song tempo: place it with create_audio_clip(warp=False).
"""
import os

import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100


def read(path, sr=SR):
    x, fs = sf.read(path, always_2d=True, dtype="float64")
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = x[:, :2]
    if fs != sr:
        g = np.gcd(int(fs), int(sr))
        x = signal.resample_poly(x, sr // g, fs // g, axis=0)
    return x


def write(path, y, sr=SR):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    peak = float(np.abs(y).max()) if y.size else 0.0
    if peak > 0.999:                                   # never clip the file itself
        y = y * (0.999 / peak)
    sf.write(path, y, sr, subtype="PCM_24")
    return path


def _length(bpm, bars, sr):
    return int(round(bars * 4 * 60.0 / bpm * sr))


def with_gaps(path, out, bpm, gaps, fade_ms=8.0, sr=SR):
    """A loop with holes: `gaps` = [(from_beat, to_beat), ...] silenced with short fades
    (a kick that leaves for the last two beats of a phrase, hats that vanish for a bar).
    Groove by absence: the ear leans into what stopped."""
    x = read(path, sr).copy()
    beat = 60.0 / bpm
    f = int(fade_ms / 1000.0 * sr)
    for a, b in gaps:
        i, j = int(round(a * beat * sr)), min(len(x), int(round(b * beat * sr)))
        if j <= i:
            continue
        if f and i >= f:
            x[i - f:i] *= np.linspace(1.0, 0.0, f)[:, None]
        x[i:j] = 0.0
        if f and j + f <= len(x):
            x[j:j + f] *= np.linspace(0.0, 1.0, f)[:, None]
    return write(out, x, sr)


def slice_beats(path, out, bpm, from_beat, to_beat, reverse=False, sr=SR):
    """Beats [from, to) of a loop at `bpm` as their own file, optionally reversed (the
    vocal's last bar sucked backwards into the drop)."""
    x = read(path, sr)
    beat = 60.0 / bpm
    y = x[int(round(from_beat * beat * sr)): int(round(to_beat * beat * sr))]
    return write(out, y[::-1] if reverse else y, sr)


def stretch_to(path, out, bpm, bars, sr=SR):
    """A one-shot FX (riser, sweep, downlifter) resampled to exactly `bars` at `bpm`, so
    it can be placed unwarped and end on the downbeat. Pitch moves with the length
    (a few percent), which noise-based FX do not mind; tonal material should be warped
    in Live instead."""
    x = read(path, sr)
    y = signal.resample(x, _length(bpm, bars, sr), axis=0)
    return write(out, y, sr)


def trim_hit(path, out, seconds, fade_ms=15.0, sr=SR):
    """The first `seconds` of a one-shot with a short fade: a 130 ms open hat cut to the
    references' hat length instead of ringing into the next 16th."""
    x = read(path, sr)[: int(seconds * sr)].copy()
    f = min(len(x), int(fade_ms / 1000.0 * sr))
    if f:
        x[-f:] *= np.linspace(1.0, 0.0, f)[:, None]
    return write(out, x, sr)


def reverse_to(path, out, sr=SR):
    """The file played backwards: a crash becomes a rise into the next downbeat."""
    return write(out, read(path, sr)[::-1], sr)


def _place(y, hit, a, end, gain, choke_ms, sr):
    """Add `hit` at sample `a`, cut at `end` with a short fade (a new hit chokes the old)."""
    seg = hit[: max(0, end - a)] * gain
    f = min(len(seg), int(choke_ms / 1000.0 * sr))
    if f and len(seg) < len(hit):
        seg = seg.copy()
        seg[-f:] *= np.linspace(1.0, 0.0, f)[:, None]
    m = min(len(seg), len(y) - a)
    if m > 0:
        y[a:a + m] += seg[:m]


def four_on_floor(shot, bpm, bars=4, sr=SR):
    """A one-shot on every beat, each cut at the next beat."""
    hit = read(shot, sr)
    y = np.zeros((_length(bpm, bars, sr), 2))
    beat = 60.0 / bpm
    starts = [int(round(k * beat * sr)) for k in range(bars * 4)] + [len(y)]
    for a, b in zip(starts, starts[1:]):
        _place(y, hit, a, b, 1.0, 10.0, sr)
    return y


def from_notes(shot, notes, bpm, bars, choke_ms=5.0, sr=SR):
    """A one-shot played by MIDI-style notes [[pitch, start_beat, dur_beats, vel], ...]
    (e.g. music.groove.build_roll): velocity scales the level, each hit is cut where the
    next begins. Pitch is ignored (one sample)."""
    hit = read(shot, sr)
    y = np.zeros((_length(bpm, bars, sr), 2))
    beat = 60.0 / bpm
    starts = sorted((int(round(n[1] * beat * sr)), n[3]) for n in notes)
    for i, (a, vel) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(y)
        _place(y, hit, a, end, max(0.0, min(127, vel)) / 127.0, choke_ms, sr)
    return y


def with_swing(template, swing_pct, bpm):
    """The template with its off-beat 16ths moved so their median delay behind the on-beats
    gives `swing_pct` (50 = straight); each step keeps its own lean against that median."""
    tsteps = [dict(s) for s in (template["steps"] if isinstance(template, dict) else template)]
    odd = [s["offset_ms"] for s in tsteps if s["step"] % 2 and s["offset_ms"] is not None]
    even = [s["offset_ms"] for s in tsteps if s["step"] % 2 == 0 and s["offset_ms"] is not None]
    if not odd:
        return {"steps": tsteps}
    eighth_ms = 60000.0 / bpm / 2.0
    shift = (swing_pct - 50.0) / 100.0 * eighth_ms - (np.median(odd) - (np.median(even) if even else 0.0))
    for s in tsteps:
        if s["step"] % 2 and s["offset_ms"] is not None:
            s["offset_ms"] = round(s["offset_ms"] + shift, 1)
    return {"steps": tsteps}


def from_template(shots, template, bpm, bars=4, steps=None, humanize=True, vel_db=1.0,
                  seed=0, choke_ms=5.0, swing_pct=None, sr=SR):
    """One-shots on the 16th steps of `template` (why.groove_template: offset_ms, accent_db,
    spread_ms per step), bars long at `bpm`.

    shots: {step: path} with "default" for every other step (e.g. an open hat on the
    off-beat 8ths 2/6/10/14 and a closed one elsewhere). steps: the steps to play
    (default: every step the references play). humanize adds each step's measured timing
    variation and +-vel_db of level, reproducibly from `seed`. swing_pct re-centres the
    off-beat 16ths (with_swing): a median template averages straight and swung references
    and lands flatter than most of them."""
    rng = np.random.default_rng(seed)
    if swing_pct is not None:
        template = with_swing(template, swing_pct, bpm)
    tsteps = template["steps"] if isinstance(template, dict) else template
    by_step = {s["step"]: s for s in tsteps}
    play = [s for s in (steps if steps is not None else range(16))
            if by_step.get(s, {}).get("offset_ms") is not None]
    cache = {}

    def shot_for(step):
        p = shots.get(step, shots.get(str(step), shots.get("default")))
        if p is None:
            return None
        if p not in cache:
            cache[p] = read(p, sr)
        return cache[p]

    six = 60.0 / bpm / 4.0
    y = np.zeros((_length(bpm, bars, sr), 2))
    hits = []
    for b in range(bars):
        for s in play:
            st = by_step[s]
            t = (b * 16 + s) * six + st["offset_ms"] / 1000.0
            g = st.get("accent_db") or 0.0
            if humanize:
                sd = min(6.0, 1.48 * (st.get("spread_ms") or 0.0))    # MAD -> sigma, capped
                t += rng.normal(0.0, sd / 1000.0)
                g += rng.normal(0.0, vel_db)
            hits.append((max(0, int(round(t * sr))), s, g))
    hits.sort()
    for i, (a, s, g) in enumerate(hits):
        hit = shot_for(s)
        if hit is None:
            continue
        end = hits[i + 1][0] if i + 1 < len(hits) else len(y)
        _place(y, hit, a, end, 10 ** (g / 20.0), choke_ms, sr)
    return y
