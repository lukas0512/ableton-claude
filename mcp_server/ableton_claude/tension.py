"""Tension and release around a track's main break, from the per-bar matrix.

A break can create tension by taking things away; release can restore pulse, bass or
spectral contrast without becoming louder. These are independent cues. Measured on the same
[lufs, kick, bass, high] per-bar matrix references.per_bar produces, so a render and the
cached references compare directly:

- depth_lu: drop (first 16 bars) over the break, in LU
- kick_out_db / bass_out_db: how far kick and bass drop out in the break
- build_lu_per_bar / build_high_db_per_bar: the ramp over the 7 bars before the last
- predrop_dip_lu: the last bar before the drop against the 4 before it
- drop_jump_lu: first 8 bars of the drop over the last 4 before it (the release)
- drop_jump_kick_db / drop_jump_bass_db: what the drop brings back
- drop_vs_pre_break_lu: whether the drop tops the groove before the break
"""
import numpy as np

KEYS = ("depth_lu", "kick_out_db", "bass_out_db", "build_lu_per_bar",
        "build_high_db_per_bar", "predrop_dip_lu", "drop_jump_lu", "drop_jump_kick_db",
        "drop_jump_bass_db", "drop_vs_pre_break_lu")


def _slope(v):
    v = np.asarray(v, float)
    return float(np.polyfit(np.arange(len(v)), v, 1)[0]) if len(v) >= 2 else 0.0


def main_break(segments):
    """(break_start, break_end, drop) in 0-based bars: the longest 'break' segment
    (a 'partial' one if there is no full break) and the first 'full' segment after it."""
    pairs = []
    for section in segments:
        if section["label"] not in ("break", "partial"):
            continue
        after = sorted((s for s in segments if s["label"] == "full" and s["start"] >= section["end"]), key=lambda s: s["start"])
        if after and 0 <= section["start"] < section["end"] <= after[0]["start"]:
            pairs.append((section, after[0]))
    if not pairs:
        return None
    main, drop = max(pairs, key=lambda pair: (pair[0]["label"] == "break", pair[0]["end"] - pair[0]["start"]))
    return main["start"], main["end"], drop["start"]


def metrics(bars, brk_start, brk_end, drop):
    B = np.asarray(bars, float)
    if B.ndim != 2 or B.shape[1] < 4 or not np.isfinite(B[:, :4]).all():
        raise ValueError("bars must be a finite matrix with at least four columns")
    if not 0 <= brk_start < brk_end <= drop < len(B):
        raise ValueError("need 0 <= break start < break end <= drop < number of bars")
    L, K, S, H = B[:, 0], B[:, 1], B[:, 2], B[:, 3]
    d16, br = slice(drop, min(drop + 16, len(B))), slice(brk_start, brk_end)
    last4, first8 = slice(max(0, drop - 4), drop), slice(drop, min(drop + 8, len(B)))
    pre = slice(max(0, brk_start - 8), brk_start)
    m = {"depth_lu": np.median(L[d16]) - np.median(L[br]),
         "kick_out_db": np.median(K[d16]) - np.median(K[br]),
         "bass_out_db": np.median(S[d16]) - np.median(S[br]),
         "build_lu_per_bar": _slope(L[max(brk_start, drop - 8):drop - 1]) if drop - max(brk_start, drop - 8) >= 3 else None,
         "build_high_db_per_bar": _slope(H[max(brk_start, drop - 8):drop - 1]) if drop - max(brk_start, drop - 8) >= 3 else None,
         "predrop_dip_lu": L[drop - 1] - np.median(L[max(0, drop - 5):drop - 1]) if drop > 1 else None,
         "drop_jump_lu": np.median(L[first8]) - np.median(L[last4]),
         "drop_jump_kick_db": np.median(K[first8]) - np.median(K[last4]),
         "drop_jump_bass_db": np.median(S[first8]) - np.median(S[last4]),
         "drop_vs_pre_break_lu": np.median(L[d16]) - np.median(L[pre]) if brk_start > 0 else None}
    return {k: round(float(v), 2) if v is not None else None for k, v in m.items()}


def for_track(bars, segments):
    where = main_break(segments)
    if where is None:
        return None
    out = metrics(bars, *where)
    out["break_bars"] = [where[0] + 1, where[1]]     # 1-based inclusive, for people
    out["drop_bar"] = where[2] + 1
    return out


def profile_stats(cache_entries):
    """Distribution over cached references (needs 'segments' and 'bars_matrix')."""
    rows = [for_track(r["bars_matrix"], r["segments"]) for r in cache_entries
            if r.get("bars_matrix") and r.get("segments")]
    rows = [r for r in rows if r]
    stats = {}
    for k in KEYS:
        v = np.array([r[k] for r in rows if r[k] is not None and np.isfinite(r[k])], float)
        if v.size:
            stats[k] = {"median": round(float(np.median(v)), 2),
                        "p25": round(float(np.percentile(v, 25)), 2),
                        "p75": round(float(np.percentile(v, 75)), 2), "n": int(v.size)}
    return stats


def compare(ours, prof):
    rows = {}
    for k in KEYS:
        p, v = prof.get(k), ours.get(k)
        if p is None or v is None:
            continue
        rows[k] = {"ours": v, "median": p["median"], "p25": p["p25"], "p75": p["p75"],
                   "verdict": "ok" if p["p25"] <= v <= p["p75"] else
                   ("low" if v < p["p25"] else "high")}
    return rows
