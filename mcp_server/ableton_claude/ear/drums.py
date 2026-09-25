"""Drum transcription from the separated drum stem.

Kick, clap/snare and hats are read from their own bands of the drum stem (no bass or
chords left in it to confuse them). Every hit gets a place on the 16-step grid, how
many milliseconds early or late it lands (microtiming), and how loud it is against the
instrument's own strong hits (accent). From those: a pattern per bar in 16 characters
(X accent, x normal, g ghost, o open hat, . rest), swing measured against the
instrument's own on-beats, and a groove template (average offset and accent per step).
"""
import collections

import numpy as np
from scipy import signal
from scipy.ndimage import median_filter, minimum_filter1d

from . import grid as G

BANDS = {"kick": (35.0, 130.0), "clap": (1200.0, 4000.0), "hats": (7000.0, 16000.0)}
MIN_GAP_S = {"kick": 0.10, "clap": 0.08, "hats": 0.045}
HOP = 64                   # ~1.5 ms at 44.1 kHz: microtiming needs better than 5 ms
OPEN_HAT_MS = 90.0


SMOOTH_S = {"kick": 0.020, "clap": 0.008, "hats": 0.003}   # at least a cycle of the band's lowest tone
BODY_S = {"clap": (0.005, 0.08)}   # a clap's energy after its first crack; a kick click has none


def _env_db(y, sr, lo, hi, smooth_s):
    """Band envelope in dB on a ~1.5 ms hop, smoothed by a centered window long enough
    that a low tone's own cycles do not look like attacks (a 52 Hz kick rippled +-4 dB
    under a 5 ms window, which read as a second kick 120 ms later)."""
    sos = signal.butter(4, [lo, min(hi, sr / 2 * 0.95)], "bandpass", fs=sr, output="sos")
    z = signal.sosfiltfilt(sos, y)
    w = max(1, int(smooth_s * sr))
    p = np.convolve(z * z, np.ones(w) / w, mode="same")
    n = len(p) // HOP
    e = p[: n * HOP].reshape(n, HOP).mean(axis=1)
    return 10 * np.log10(e + 1e-12), HOP / float(sr), z


def onsets(y, sr, name):
    """[(time_s, level_db, decay_ms)] for one drum band of a mono drum stem.

    An attack is a rise of at least 4 dB over the band's recent minimum; its time is where
    the envelope crosses halfway (in dB) from the valley before it to its peak. Timing from
    the valley, not from a fixed point, holds when dense hats or a tambourine never let
    the band fall between hits."""
    lo, hi = BANDS[name]
    env, dt, z = _env_db(y, sr, lo, hi, SMOOTH_S[name])
    sm = signal.medfilt(env, 3)
    flux = np.maximum(np.diff(sm, prepend=sm[0]), 0.0)
    w = max(3, int(max(0.012, 2.5 * SMOOTH_S[name]) / dt))
    rise = env - minimum_filter1d(env, w, origin=(w - 1) // 2)       # over the last rise window
    floor = median_filter(env, size=int(0.25 / dt) | 1)              # the band's running level
    loud = np.percentile(env, 99)
    cand, _ = signal.find_peaks(flux, distance=max(1, int(MIN_GAP_S[name] / dt)))
    out = []
    for i in cand:
        j = min(len(env) - 1, i + int(0.03 / dt))
        pk = i + int(np.argmax(env[i:j + 1]))
        if rise[pk] < 4.0 or env[pk] < floor[pk] + 6.0 or env[pk] < loud - 45.0:
            continue
        v0 = max(0, pk - w)
        v = v0 + int(np.argmin(env[v0:pk + 1]))
        thr = 0.5 * (env[v] + env[pk])
        k = v + int(np.argmax(env[v:pk + 1] >= thr))
        tail = env[pk: pk + int(0.3 / dt)]
        below = np.nonzero(tail < env[pk] - 12.0)[0]
        decay = (below[0] if len(below) else len(tail)) * dt * 1000.0
        level = float(env[pk])
        if name in BODY_S:                    # judge a clap by what it sustains
            a, b = BODY_S[name]
            seg = z[int((k * dt + a) * sr): int((k * dt + b) * sr)]
            level = float(10 * np.log10(np.mean(seg ** 2) + 1e-12)) if len(seg) else level
        out.append((k * dt, level, decay))
    return out


def _symbol(rel_db, open_hat=False):
    if open_hat:
        return "o"
    return "X" if rel_db >= -4 else "x" if rel_db >= -10 else "g"


MIN_RISE_DB = {"kick": 6.0, "clap": 5.0, "hats": 5.0}


def _slot_hits(y, sr, g, name):
    """Grid-synchronous detection: every 16th slot of every bar is checked for an attack
    (a rise of MIN_RISE_DB from the valley before it). Returns [(bar, step, offset_s,
    level_db, decay_ms)]. Knowing the grid, a kick's decaying body cannot pass for a hit
    in the next slot, and a slot yields at most one hit."""
    lo, hi = BANDS[name]
    env, dt, z = _env_db(y, sr, lo, hi, SMOOTH_S[name])
    flux = np.maximum(np.diff(signal.medfilt(env, 3), prepend=env[0]), 0.0)
    step_s = g["period"] / 4.0
    half = int(0.45 * step_s / dt)
    rw = max(3, int(max(0.02, 2.5 * SMOOTH_S[name]) / dt))
    loud = np.percentile(env, 99.5)
    out = []
    for bar in range(g["n_bars"]):
        for st in range(16):
            c = int(G.step_time(g, bar, st) / dt)
            a, b = max(1, c - half), min(len(env) - 1, c + half)
            if b <= a:
                continue
            i = a + int(np.argmax(flux[a:b]))
            pk = i + int(np.argmax(env[i: min(len(env), i + int(0.03 / dt))]))
            v0 = max(0, pk - rw)
            v = v0 + int(np.argmin(env[v0:pk + 1]))
            if env[pk] - env[v] < MIN_RISE_DB[name] or env[pk] < loud - 40.0:
                continue
            k = v + int(np.argmax(env[v:pk + 1] >= 0.5 * (env[v] + env[pk])))
            t = k * dt
            if abs(t - c * dt) > 0.45 * step_s:
                continue
            tail = env[pk: pk + int(0.3 / dt)]
            below = np.nonzero(tail < env[pk] - 12.0)[0]
            decay = (below[0] if len(below) else len(tail)) * dt * 1000.0
            level = float(env[pk])
            if name in BODY_S:
                ba, bb = BODY_S[name]
                seg = z[int((t + ba) * sr): int((t + bb) * sr)]
                level = float(10 * np.log10(np.mean(seg ** 2) + 1e-12)) if len(seg) else level
            out.append((bar, st, t - G.step_time(g, bar, st), level, decay))
    return out


def transcribe(drum_stem, sr, g, min_rel_db=-24.0, local_bars=8):
    """Per instrument: hits (bar, step, offset_ms, rel_db, open), bar patterns, swing,
    groove template. `g` is the grid from ear.grid. Accents are judged against the
    instrument's strong hits within +-`local_bars`, so a quiet breakdown still reads."""
    y = drum_stem.mean(axis=1) if drum_stem.ndim == 2 else drum_stem
    res = {}
    for name in BANDS:
        raw = _slot_hits(y, sr, g, name)
        if not raw:
            res[name] = {"hits": [], "patterns": {}, "hits_per_bar": 0.0}
            continue
        levels = np.array([r[3] for r in raw])
        bars = np.array([r[0] for r in raw])
        hits = []
        for (bar, st, off, lv, dec) in raw:
            near = levels[np.abs(bars - bar) <= local_bars]
            rel = lv - np.percentile(near, 90)
            if rel < min_rel_db:
                continue
            hits.append({"bar": int(bar), "step": int(st), "offset_ms": round(off * 1000, 1),
                         "rel_db": round(float(rel), 1),
                         "open": bool(name == "hats" and dec >= OPEN_HAT_MS)})
        pats = collections.defaultdict(lambda: ["."] * 16)
        for h in hits:
            pats[h["bar"]][h["step"]] = _symbol(h["rel_db"], h["open"])
        res[name] = {"hits": hits, "patterns": {b: "".join(p) for b, p in sorted(pats.items())},
                     "hits_per_bar": round(len(hits) / max(1, len({h["bar"] for h in hits})), 2)}
        res[name].update(_timing(hits, g))
    return res


def _timing(hits, g):
    """Swing against the instrument's own on-beats, and a per-step groove template."""
    if len(hits) < 16:
        return {}
    on = [h["offset_ms"] for h in hits if h["step"] % 2 == 0]
    off = [h["offset_ms"] for h in hits if h["step"] % 2 == 1]
    out = {}
    eighth_ms = g["period"] * 500.0
    if len(on) >= 8 and len(off) >= 8 and len(off) >= 0.15 * len(on):   # swing needs off-beat 16ths
        d = float(np.median(off) - np.median(on))
        out["swing_pct"] = round(50.0 + 100.0 * d / eighth_ms, 1)
        out["late_ms_offbeat_vs_onbeat"] = round(d, 1)
    ref_on = float(np.median(on)) if on else 0.0
    per_step = collections.defaultdict(list)
    per_step_v = collections.defaultdict(list)
    for h in hits:
        per_step[h["step"]].append(h["offset_ms"] - ref_on)
        per_step_v[h["step"]].append(h["rel_db"])
    tmpl = []
    for s in range(16):
        v = per_step.get(s, [])
        tmpl.append({"step": s, "n": len(v),
                     "offset_ms": round(float(np.median(v)), 1) if v else None,
                     "spread_ms": round(float(np.median(np.abs(np.array(v) - np.median(v)))), 1) if len(v) > 2 else None,
                     "accent_db": round(float(np.median(per_step_v[s])), 1) if v else None})
    out["template"] = tmpl
    dev = [abs(h["offset_ms"] - ref_on - (out.get("late_ms_offbeat_vs_onbeat", 0.0) if h["step"] % 2 else 0.0))
           for h in hits]
    out["timing_spread_ms"] = round(float(np.median(dev)), 1)
    return out


def section_patterns(res, bars, min_share=0.5):
    """Typical pattern per instrument over the given bars: a step counts when it is hit in
    at least `min_share` of the bars where the instrument plays, with its most common
    symbol. (The most common exact bar string fragments as soon as accents vary.)"""
    out = {}
    for name, r in res.items():
        pats = [r["patterns"].get(b) for b in bars if r["patterns"].get(b)]
        if not pats:
            continue
        prof, typ = [], []
        for st in range(16):
            sy = [p[st] for p in pats if p[st] != "."]
            share = len(sy) / len(pats)
            prof.append(round(share, 2))
            typ.append(collections.Counter(sy).most_common(1)[0][0] if share >= min_share and sy else ".")
        out[name] = {"pattern": "".join(typ), "step_share": prof,
                     "bars_playing": round(len(pats) / max(1, len(bars)), 2)}
    return out


def describe_pattern(p):
    """Words for a 16-step pattern: four on the floor, backbeat, off-beat 8ths..."""
    hits = [i for i, c in enumerate(p) if c != "."]
    words = []
    if all(p[i] != "." for i in (0, 4, 8, 12)):
        words.append("four on the floor")
    if all(p[i] in "Xx" for i in (4, 12)) and not any(p[i] in "Xx" for i in (0, 8)):
        words.append("backbeat on 2 and 4")
    if all(p[i] != "." for i in (2, 6, 10, 14)) and not any(p[i] != "." for i in (0, 4, 8, 12)):
        words.append("off-beat 8ths")
    if len(hits) >= 14:
        words.append("straight 16ths")
    if any(c == "g" for c in p):
        words.append("ghost notes on steps %s" % ",".join(str(i + 1) for i, c in enumerate(p) if c == "g"))
    if any(c == "o" for c in p):
        words.append("open hat on steps %s" % ",".join(str(i + 1) for i, c in enumerate(p) if c == "o"))
    return words
