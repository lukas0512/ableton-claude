"""What plays in which bar, and the sections that follow from it.

Each stem's level per bar says whether it plays (relative to its own loud passages),
and the drum transcription splits drums into kick, mid percussion and hats. Sections
start where that set of elements changes, snapped to 4-bar lines, and are named by what
they contain: an intro before the bass arrives, a break without kick, the drop that
follows a break, an outro where elements leave.
"""
import numpy as np
import pyloudnorm as pyln

from . import grid as G

ELEMENTS = ("kick", "clap", "hats", "bass", "other", "vocals")


def stem_levels(stems, sr, g):
    out = {}
    bar = 4 * g["period"]
    for name, s in stems.items():
        m = s.mean(axis=1) if s.ndim == 2 else s
        lv = []
        for b in range(g["n_bars"]):
            a = int(G.bar_start(g, b) * sr)
            seg = m[a: a + int(bar * sr)]
            lv.append(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9) if len(seg) else -120.0)
        out[name] = np.array(lv)
    return out


def activity(levels, drum_res, n_bars, rel_db=18.0):
    act = {}
    for name in ("bass", "other", "vocals"):
        lv = levels[name]
        thr = max(-60.0, np.percentile(lv, 95) - rel_db)
        act[name] = lv >= thr
    need = {"kick": 2, "clap": 2, "hats": 4}
    for name, n in need.items():
        cnt = np.zeros(n_bars)
        for h in drum_res.get(name, {}).get("hits", []):
            if h["rel_db"] >= -18 and 0 <= h["bar"] < n_bars:
                cnt[h["bar"]] += 1
        act[name] = cnt >= n
    return act


def runs(mask, max_gap=1):
    """[[start_bar, end_bar)] where mask is on, bridging gaps of up to max_gap bars."""
    on = [i for i, v in enumerate(mask) if v]
    if not on:
        return []
    out = [[on[0], on[0] + 1]]
    for i in on[1:]:
        if i - out[-1][1] <= max_gap:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1])
    return out


def sections(act, lufs, n_bars, grid_bars=4, min_len=4):
    sig = np.array([[act[e][b] for e in ELEMENTS] for b in range(n_bars)], dtype=int)
    bounds = [0]
    for b in range(grid_bars, n_bars, grid_bars):
        prev = sig[max(0, b - grid_bars):b].mean(axis=0) >= 0.5
        nxt = sig[b:b + grid_bars].mean(axis=0) >= 0.5
        if (prev != nxt).any() and b - bounds[-1] >= min_len:
            bounds.append(b)
    bounds.append(n_bars)
    secs = []
    for a, b in zip(bounds, bounds[1:]):
        present = [e for i, e in enumerate(ELEMENTS) if sig[a:b, i].mean() >= 0.5]
        secs.append({"start_bar": a + 1, "end_bar": b, "bars": b - a, "elements": present,
                     "lufs": round(float(np.median(lufs[a:b])), 1)})
    # names
    seen_break = False
    for i, s in enumerate(secs):
        has = set(s["elements"])
        if "kick" not in has:
            s["label"] = "intro" if i == 0 else ("outro" if i == len(secs) - 1 else "break")
            seen_break = seen_break or s["label"] == "break"
        elif i == 0 or (i <= 2 and "bass" not in has and not seen_break):
            s["label"] = "intro"
        elif i == len(secs) - 1 and len(has) < len(set(secs[i - 1]["elements"])):
            s["label"] = "outro"
        elif i > 0 and secs[i - 1].get("label") == "break":
            s["label"] = "drop"
        else:
            s["label"] = "groove"
    return secs


def bar_lufs(x, sr, g):
    meter = pyln.Meter(sr)
    out = []
    for b in range(g["n_bars"]):
        a = int(G.bar_start(g, b) * sr)
        seg = x[a: a + int(4 * g["period"] * sr)]
        with np.errstate(divide="ignore"):
            v = meter.integrated_loudness(seg) if len(seg) > sr * 0.4 else -70.0
        out.append(v if np.isfinite(v) else -70.0)
    return np.array(out)


def analyze(x, sr, stems, g, drum_res):
    levels = stem_levels(stems, sr, g)
    act = activity(levels, drum_res, g["n_bars"])
    lufs = bar_lufs(x, sr, g)
    secs = sections(act, lufs, g["n_bars"])
    return {"sections": secs,
            "elements": {e: [[a + 1, b] for a, b in runs(act[e])] for e in ELEMENTS},
            "first_bar": {e: (int(np.argmax(act[e])) + 1 if act[e].any() else None) for e in ELEMENTS},
            "bar_lufs": [round(float(v), 1) for v in lufs],
            "stem_levels_db": {k: [round(float(v), 1) for v in lv] for k, lv in levels.items()}}
