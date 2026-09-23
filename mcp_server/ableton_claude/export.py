"""Deliverables: bar-accurate edits of a rendered master and safe MP3 encoding.

edit() splices sections of a render on the bar grid: each section ends a crossfade
*after* its last bar and the next section starts exactly on its bar, so the beat grid of
the edit stays exact (a DJ can still beat-match it). encode_mp3() checks the true peak
of the *decoded* MP3 (lossy encoding adds overshoots) and re-encodes with less gain if
it exceeds the target.
"""
import os
import subprocess
import tempfile

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

from . import analysis


def bar_to_sample(bar, bpm, sr, first_bar_s=0.0):
    return int(round(((bar - 1) * 4 * 60.0 / bpm + first_bar_s) * sr))


def edit(x, sr, bpm, segments, xfade_ms=30.0, fade_in_ms=10.0, fade_out_bars=0.0):
    """x: (n, 2) render starting on bar 1. segments: [(start_bar, end_bar), ...]."""
    n_x = int(sr * xfade_ms / 1000.0)
    out = None
    for a, b in segments:
        s, e = bar_to_sample(a, bpm, sr), bar_to_sample(b, bpm, sr)
        if out is None:
            out = x[s:e].astype(np.float32).copy()
            continue
        # crossfade *before* the bar line: the outgoing section's last n_x samples fade
        # out against the incoming section's n_x samples of pre-roll, so the incoming
        # downbeat (usually a kick) lands at full level and exactly on the grid
        pre = x[max(0, s - n_x):s].astype(np.float32)
        t = np.linspace(0, np.pi / 2, len(pre), dtype=np.float32)[:, None]
        mix = out[-len(pre):] * np.cos(t) + pre * np.sin(t)
        out = np.concatenate([out[:-len(pre)], mix, x[s:e].astype(np.float32)])
    n_in = int(sr * fade_in_ms / 1000.0)
    if n_in:
        out[:n_in] *= np.linspace(0, 1, n_in, dtype=np.float32)[:, None]
    if fade_out_bars:
        n_out = min(len(out), int(fade_out_bars * 4 * 60.0 / bpm * sr))
        out[-n_out:] *= np.linspace(1, 0, n_out, dtype=np.float32)[:, None] ** 2
    return out


def _encode(x, sr, path, bitrate, tags):
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "in.wav")
        sf.write(wav, x, sr, subtype="FLOAT")
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", wav, "-codec:a", "libmp3lame",
               "-b:a", "%dk" % bitrate, "-id3v2_version", "3"]
        for k, v in (tags or {}).items():
            cmd += ["-metadata", "%s=%s" % (k, v)]
        subprocess.run(cmd + [path], check=True)


def _decode(path):
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "out.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, wav], check=True)
        y, sr = sf.read(wav, always_2d=True, dtype="float32")
    return y, sr


def encode_mp3(x, sr, path, tags=None, bitrate=320, tp_target=-1.0, attempts=3):
    """Encode, measure the decoded file, and back the gain off until its true peak is at
    or below tp_target. Returns measurements of the file as delivered."""
    gain_db = 0.0
    for _ in range(attempts):
        _encode(x * 10 ** (gain_db / 20.0), sr, path, bitrate, tags)
        y, ysr = _decode(path)
        tp = analysis.true_peak_db(y, ysr)
        if tp <= tp_target:
            break
        gain_db -= (tp - tp_target) + 0.05
    lufs = pyln.Meter(ysr).integrated_loudness(y)
    return {"file": path, "true_peak_dbtp": round(tp, 2), "integrated_lufs": round(lufs, 1),
            "gain_applied_db": round(gain_db, 2), "duration_s": round(len(y) / ysr, 2),
            "bitrate_kbps": bitrate}
