"""Source separation with Demucs (htdemucs): drums, bass, other, vocals.

Stems stay in memory: a 6-minute stereo stem is ~127 MB as float, so writing four of
them per reference would fill a disk quickly. What is kept is what the stems tell us.
"""
import numpy as np
from scipy import signal

_MODEL = None
SOURCES = ("drums", "bass", "other", "vocals")


def _model():
    global _MODEL
    if _MODEL is None:
        from demucs.pretrained import get_model
        _MODEL = get_model("htdemucs")
        _MODEL.eval()
    return _MODEL


def _device():
    from . import torch_device
    return torch_device()


def separate(x, sr, device=None):
    """x: (n, 2) float at sr. Returns {source: (n, 2) float32 at sr}."""
    import torch
    from demucs.apply import apply_model
    m = _model()
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    y = x
    if sr != m.samplerate:
        g = np.gcd(int(sr), int(m.samplerate))
        y = signal.resample_poly(x, m.samplerate // g, sr // g, axis=0)
    wav = torch.from_numpy(np.ascontiguousarray(y.T, dtype=np.float32))
    ref = wav.mean(0)
    mean, std = ref.mean(), ref.std() + 1e-8
    dev = device or _device()
    with torch.no_grad():
        try:
            out = apply_model(m, ((wav - mean) / std)[None], device=dev, shifts=0, split=True,
                              overlap=0.25, progress=False)[0]
        except (RuntimeError, NotImplementedError):
            if dev == "cpu":
                raise
            out = apply_model(m, ((wav - mean) / std)[None], device="cpu", shifts=0, split=True,
                              overlap=0.25, progress=False)[0]
    out = (out * std + mean).cpu().numpy()
    stems = {}
    for i, name in enumerate(m.sources):
        s = out[i].T
        if sr != m.samplerate:
            g = np.gcd(int(sr), int(m.samplerate))
            s = signal.resample_poly(s, sr // g, m.samplerate // g, axis=0)
        s = s[: len(x)]
        if len(s) < len(x):
            s = np.pad(s, ((0, len(x) - len(s)), (0, 0)))
        stems[name] = s.astype(np.float32)
    return stems
