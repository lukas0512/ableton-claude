"""How good a render sounds to a trained listener: Meta's audiobox-aesthetics.

Four scores (1-10) per 10-second window, from a WavLM-based model trained on human
ratings (facebookresearch/audiobox-aesthetics, code and weights CC-BY 4.0):
CE content enjoyment, CU content usefulness, PC production complexity, PQ production
quality. A whole 5.7-minute track scores in ~2 s on Apple Silicon.

Measured on Murder pista (2026-10-28): v30 -> v31 moved the means by +0.02 but the breaks
and builds by +0.2-0.3 CE/PQ; ten Dub House Streets references sit at median CE 7.37,
PQ 8.26 (range CE 6.73-7.67, PQ 7.54-8.40), v31 at 7.13 / 8.19. The scores do not follow
tension: a break does not score lower than a drop. Use them as a guard (a change must not
make a section worse) and to rank variants, never as a pressure/release meter.

The weights (~0.4 GB) download on first use into <data>/Models/huggingface.
"""
import json
import os
from pathlib import Path

import numpy as np

from ..storage import DATA_DIR

AXES = {"CE": "content enjoyment", "CU": "content usefulness",
        "PC": "production complexity", "PQ": "production quality"}
SR = 16000
WIN_S = 10.0
# regression thresholds against the previous render of the same bars: the mean of a
# whole render moved at most 0.02 between v30 and v31; single windows moved up to 0.3
DROP_MEAN = 0.05
DROP_WINDOW = 0.3
GUARD_AXES = ("CE", "PQ")
CACHE = Path(DATA_DIR) / "aesthetics_cache.json"

_predictor = None


def predictor():
    global _predictor
    if _predictor is None:
        os.environ.setdefault("HF_HUB_CACHE", str(Path(DATA_DIR) / "Models" / "huggingface"))
        from audiobox_aesthetics.infer import initialize_predictor
        _predictor = initialize_predictor()
    return _predictor


def score_windows(mono, sr=SR, win_s=WIN_S, predict=None):
    """[{t, CE, CU, PC, PQ}] for each full window of a mono signal at 16 kHz (a tail
    shorter than half a window is dropped; a single short clip is scored as it is)."""
    import torch
    n = int(win_s * sr)
    starts = list(range(0, max(1, len(mono) - n // 2), n))
    batch = [{"path": torch.from_numpy(np.ascontiguousarray(mono[s:s + n], dtype=np.float32))[None],
              "sample_rate": sr} for s in starts]
    rows = (predict or predictor().forward)(batch)
    return [dict({"t": round(s / sr, 1)}, **{k: round(float(r[k]), 2) for k in AXES})
            for s, r in zip(starts, rows)]


def _mean(windows):
    return {k: round(float(np.mean([w[k] for w in windows])), 2) for k in AXES}


def score_file(path, start_s=0.0, end_s=None, predict=None, cache=True):
    """{mean, windows} of an audio file (any format the app reads). Whole files are cached
    by path, size and mtime: references are scored once."""
    from ..references import load_audio
    path = os.path.abspath(os.path.expanduser(path))
    st = os.stat(path)
    key = "%s|%d|%d|%s|%s" % (path, st.st_size, int(st.st_mtime), start_s, end_s)
    store = _load_cache() if cache else {}
    if key in store:
        return store[key]
    import soundfile as sf
    try:
        sr = sf.info(path).samplerate
    except Exception:         # m4a and friends: ffmpeg decodes at 44.1 kHz
        sr = 44100
    # read at the file's own rate: scipy's polyphase 44.1 -> 16 kHz took ~1 min per track,
    # the model's own torchaudio resampler takes a fraction of a second
    x, sr = load_audio(path, sr=sr)
    mono = x.mean(axis=1)[int(start_s * sr):None if end_s is None else int(end_s * sr)]
    windows = score_windows(mono, sr, predict=predict)
    for w in windows:
        w["t"] = round(w["t"] + start_s, 1)
    res = {"mean": _mean(windows), "windows": windows}
    if cache:
        store[key] = res
        _save_cache(store)
    return res


def _load_cache():
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}


def _save_cache(store):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(store, separators=(",", ":")))


def with_bars(windows, tempo, start_bar=1.0):
    """Label each window with the bar it starts on (for a render that starts at start_bar)."""
    return [dict(w, bar=round(start_bar + w["t"] * tempo / 240.0, 1)) for w in windows]


def compare(new, old, axes=GUARD_AXES):
    """Where `new` sounds worse than `old` (two scorings of the same bars): the mean of an
    axis falling more than DROP_MEAN, or a window more than DROP_WINDOW."""
    worse = []
    for k in axes:
        d = new["mean"][k] - old["mean"][k]
        if d < -DROP_MEAN:
            worse.append({"axis": k, "where": "whole render", "delta": round(d, 2)})
        for a, b in zip(new["windows"], old["windows"]):
            dw = a[k] - b[k]
            if dw < -DROP_WINDOW:
                worse.append({"axis": k, "where": "bar %s" % a["bar"] if "bar" in a else "%ss" % a["t"],
                              "delta": round(dw, 2)})
    return {"delta": {k: round(new["mean"][k] - old["mean"][k], 2) for k in AXES}, "worse": worse}


def against(mean, ref_means):
    """The render's place among references: their median and range per axis and the gap
    to the median (negative = under it)."""
    out = {}
    for k in AXES:
        v = [r[k] for r in ref_means]
        med = float(np.median(v))
        out[k] = {"render": mean[k], "refs_median": round(med, 2),
                  "refs_range": [round(min(v), 2), round(max(v), 2)],
                  "gap": round(mean[k] - med, 2)}
    return out


def findings(new, old=None, ref_means=None):
    """quality_gate findings from a render's scores: a regression against the previous
    render is a warning; the place among the references is information."""
    out = []
    if old is not None:
        for w in compare(new, old)["worse"]:
            out.append({"severity": "warn", "check": "sounds worse", "track": "master",
                        "detail": "%s (%s) %s by %+.2f against the previous render"
                                  % (w["axis"], AXES[w["axis"]], w["where"], w["delta"]),
                        "fix": "listen to that stretch in both renders; revert the change "
                               "that caused it unless it was meant"})
    if ref_means:
        a = against(new["mean"], ref_means)
        below = [k for k in GUARD_AXES if new["mean"][k] < a[k]["refs_range"][0]]
        out.append({"severity": "warn" if below else "info", "check": "aesthetics vs references",
                    "track": "master",
                    "detail": ", ".join("%s %.2f (refs %.2f, %.2f-%.2f)" % (
                        k, a[k]["render"], a[k]["refs_median"], *a[k]["refs_range"])
                        for k in GUARD_AXES)
                    + ("; under every reference in " + "/".join(below) if below else ""),
                    "fix": "find the section scoring lowest and compare it with the "
                           "references' same section" if below else "-"})
    return out
