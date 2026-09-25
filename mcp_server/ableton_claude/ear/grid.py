"""Beat and bar grid.

A neural beat tracker (Beat This, ISMIR 2024) finds beats and downbeats where a
listener taps them, which the low-band flux we used before did not: it lagged ~30 ms
behind soft kicks and, in sections without a kick, could land half a beat off. Dance
music keeps one tempo, so a straight line is fitted through the beats and the downbeat
phase is the one most detected downbeats agree on.
"""
import numpy as np

_A2B = None


def _tracker():
    global _A2B
    if _A2B is None:
        import torch
        from beat_this.inference import Audio2Beats
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        _A2B = Audio2Beats(checkpoint_path="final0", device=dev, dbn=False)
    return _A2B


def detect(x, sr):
    """Beat and downbeat times (s) from the neural tracker."""
    mono = x.mean(axis=1) if x.ndim == 2 else x
    beats, downbeats = _tracker()(mono.astype(np.float32), sr)
    return np.asarray(beats, float), np.asarray(downbeats, float)


def fit(beats, downbeats, duration_s, bpm_hint=None, tol_s=0.05):
    """Constant-tempo grid through detected beats.

    Returns {bpm, period, first_downbeat, downbeats (grid), n_bars, fit_ms}: the grid's
    bar starts, and the median distance of detected beats to it (how steady the track is).
    """
    b = np.sort(np.asarray(beats, float))
    if len(b) < 8:
        raise ValueError("too few beats to fit a grid")
    # Beat This reports beats on 20 ms frames (gaps alternate 480/500 ms at 123 BPM, so
    # their median is biased), and a section without kick can add half-beat detections.
    # Neither fools a phase comb: the true period is the one at which all beats line up
    # in phase (vector strength), extra or missing beats only lower the peak.
    p0 = 60.0 / bpm_hint if bpm_hint else float(np.median(np.diff(b)))

    def strength(ps):
        return np.abs(np.exp(2j * np.pi * b[None, :] / ps[:, None]).mean(axis=1))
    cands = p0 * (1 + np.linspace(-0.04, 0.04, 1601))
    p1 = cands[int(np.argmax(strength(cands)))]
    fine = p1 * (1 + np.linspace(-0.0005, 0.0005, 201))
    period = float(fine[int(np.argmax(strength(fine)))])
    t0 = (np.angle(np.exp(2j * np.pi * b / period).mean()) / (2 * np.pi)) * period
    ph = (b - t0) / period
    ok = np.abs(ph - np.round(ph)) * period < tol_s           # beats on the grid
    kk, bb = np.round(ph[ok]), b[ok]
    A = np.vstack([np.ones_like(kk), kk]).T
    (t0, period), *_ = np.linalg.lstsq(A, bb, rcond=None)
    t0 = float(t0) - np.floor(float(t0) / period) * period     # first grid beat >= 0
    d = np.asarray(downbeats, float)
    if len(d):
        phase = np.bincount(np.round((d - t0) / period).astype(int) % 4, minlength=4).argmax()
    else:
        phase = 0
    first = t0 + phase * period
    if first - 4 * period >= -0.02:                          # a full bar fits before it
        first -= 4 * period * np.floor((first + 0.02) / (4 * period))
    bar = 4 * period
    n_bars = int(np.floor((duration_s - first) / bar + 1e-6))
    fit_ms = float(np.median(np.abs(b - (t0 + period * np.round((b - t0) / period))))) * 1000
    return {"bpm": round(60.0 / period, 3), "period": float(period), "first_downbeat": float(first),
            "n_bars": n_bars, "fit_ms": round(fit_ms, 1)}


def bar_start(grid, bar_index):
    """Start time (s) of 0-based bar `bar_index`."""
    return grid["first_downbeat"] + bar_index * 4 * grid["period"]


def step_time(grid, bar_index, step, steps_per_bar=16):
    return bar_start(grid, bar_index) + step * 4 * grid["period"] / steps_per_bar


def locate(grid, t, steps_per_bar=16):
    """(bar, step, offset_s) of time t on the grid: nearest step, and how far off it."""
    s = 4 * grid["period"] / steps_per_bar
    pos = (t - grid["first_downbeat"]) / s
    n = int(np.round(pos))
    return n // steps_per_bar, n % steps_per_bar, (pos - n) * s


def analyze(x, sr, bpm_hint=None):
    beats, downbeats = detect(x, sr)
    g = fit(beats, downbeats, len(x) / sr, bpm_hint=bpm_hint)
    g["n_detected_beats"] = int(len(beats))
    return g
