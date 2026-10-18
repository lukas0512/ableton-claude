"""Per-element timbre, measured inside a finished mix.

A master can't be unmixed, but a four-on-the-floor track exposes each element somewhere:
the kick owns the low band on the beat, the bass owns it on the off-beat once the kick
has decayed, the hats own 6-16 kHz, the clap owns 1-4 kHz on beats 2 and 4 against 1
and 3, and a breakdown exposes the pads and chords. Measuring the same windows in the
references gives every element a range, so "is the kick right?" gets a number.

Inputs are what references.analyze_reference already stores: tempo, first beat, the
per-bar matrix [lufs, kick, bass, high] and labelled segments (bar indices).
"""
import numpy as np
from scipy import signal

from . import references as R

TIMBRE_VERSION = 1

# what each measure means, for reports and tool output
DESCRIBE = {
    "kick_pitch_hz": "kick body pitch, 15-115 ms after the beat",
    "kick_decay_ms": "kick length: time for its low band to fall 20 dB (bars without bass)",
    "kick_over_bass_db": "low band on the beat minus on the off-beat (kick vs bass weight)",
    "bass_harmonics_db": "bass 2nd+3rd harmonic over its fundamental (round <-> growly)",
    "hat_brightness_hz": "spectral centroid of top-end hits, 25 ms after each onset",
    "hat_decay_ms": "top-end hit length: time for 6-16 kHz to fall 12 dB",
    "hat_level_db": "6-16 kHz level relative to the bar's loudness",
    "clap_backbeat_db": "1-4 kHz on beats 2+4 over beats 1+3 (clap/snare presence)",
    "clap_tail_ms": "backbeat length: time for 1-4 kHz to fall 15 dB after beats 2 and 4",
    "break_brightness_hz": "breakdown spectral centroid (pads, chords, vocals)",
    "break_warmth_db": "breakdown 150-500 Hz over 2-6 kHz",
    "break_width_db": "breakdown side over mid, 150 Hz-6 kHz",
}


def _band(mono, sr, lo, hi):
    sos = signal.butter(4, [lo, hi], "bandpass", fs=sr, output="sos")
    return signal.sosfilt(sos, mono)


def _env_db(y, sr, hop_s=0.002):
    hop = max(1, int(hop_s * sr))
    n = len(y) // hop
    e = np.sqrt(np.mean(y[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(e), hop / float(sr)


def _decay_ms(env, dt, onsets, drop_db, max_ms, search_ms=25.0, min_n=8):
    """Median time from each onset's peak until the envelope is drop_db below it."""
    out = []
    for t in onsets:
        i0 = int(t / dt)
        i1 = i0 + max(1, int(search_ms / 1000.0 / dt))
        if i0 < 0 or i1 >= len(env):
            continue
        pk = i0 + int(np.argmax(env[i0:i1]))
        tail = env[pk: pk + int(max_ms / 1000.0 / dt)]
        below = np.nonzero(tail < env[pk] - drop_db)[0]
        out.append((below[0] if len(below) else len(tail)) * dt * 1000.0)
    return round(float(np.median(out)), 1) if len(out) >= min_n else None


def _spectrum(seg, sr, n_fft):
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n_fft)) ** 2
    return spec, np.fft.rfftfreq(n_fft, 1.0 / sr)


def _median(v, nd=1):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return round(float(np.median(v)), nd) if v else None


def element_timbre(x, sr, bpm, t0, segments, bars=None):
    """x: (n, 2) float audio. segments: [{"start", "end", "label"}] in bars from t0."""
    mono = x.mean(axis=1)
    side = (x[:, 0] - x[:, 1]) / 2.0
    beat = 60.0 / bpm
    bar_s = 4 * beat
    if bars is None:
        bars = R.per_bar(x, sr, bpm, t0)
    bars = np.asarray(bars, float)
    n_bars = len(bars)
    label = np.array([""] * n_bars, dtype=object)
    for s in segments:
        label[s["start"]:min(s["end"], n_bars)] = s["label"]
    full = [b for b in range(n_bars) if label[b] == "full"]
    L, K, S, H = bars[:, 0], bars[:, 1], bars[:, 2], bars[:, 3]
    res = {}
    if not full:
        return res
    k_full = np.median(K[full])
    beats = lambda bs, which=(0, 1, 2, 3): [t0 + b * bar_s + k * beat for b in bs for k in which]

    # --- kick: pitch everywhere it plays; length only where the bass is out of the way
    kick_bars = [b for b in range(n_bars) if K[b] > k_full - 6]
    exposed = [b for b in kick_bars if K[b] - S[b] >= 10]
    pitch = []
    for t in beats(exposed if len(exposed) >= 8 else kick_bars):
        a = int((t + 0.015) * sr)
        seg = mono[a: a + int(0.1 * sr)]
        if len(seg) < int(0.1 * sr):
            continue
        spec, f = _spectrum(seg, sr, 1 << 16)
        m = (f >= 35) & (f <= 150)
        pitch.append(float(f[m][np.argmax(spec[m])]))
    res["kick_pitch_hz"] = _median(pitch)
    lo_env, dt = _env_db(_band(mono, sr, 30, 150), sr)
    res["kick_decay_ms"] = _decay_ms(lo_env, dt, beats(exposed), 20.0, 400.0)
    res["kick_over_bass_db"] = _median([K[b] - S[b] for b in full])

    # --- bass: harmonic content on the off-beats, where the kick has decayed
    s_full = np.median(S[full])
    ratios = []
    n_win = int(0.4 * beat * sr)
    win = np.hanning(n_win)
    for b in full:
        if S[b] < s_full - 10:
            continue
        for k in range(4):
            a = int((t0 + b * bar_s + (k + 0.5) * beat) * sr)
            seg = mono[a: a + n_win]
            if len(seg) < n_win:
                continue
            spec = np.abs(np.fft.rfft(seg * win, 1 << 17)) ** 2
            f = np.fft.rfftfreq(1 << 17, 1.0 / sr)
            m = (f >= 30) & (f <= 200)
            f0 = float(f[m][np.argmax(spec[m])])

            def energy(h):
                mm = (f >= h * f0 * 0.975) & (f <= h * f0 * 1.025)
                return float(spec[mm].max()) if mm.any() else 0.0
            e1 = energy(1)
            if e1 > 0:
                ratios.append(10 * np.log10((energy(2) + energy(3)) / e1 + 1e-12))
    res["bass_harmonics_db"] = _median(ratios)

    # --- hats / top-end percussion
    on = R._band_onsets(mono, sr, 6000, 16000)
    fb = ((on - t0) // bar_s).astype(int)
    on_full = on[np.isin(fb, full)]
    cents = []
    n25 = int(0.025 * sr)
    for t in on_full:
        a = int(t * sr)
        seg = mono[a: a + n25]
        if len(seg) < n25:
            continue
        spec, f = _spectrum(seg, sr, 4096)
        m = (f >= 2000) & (f <= 18000)
        cents.append(float((f[m] * spec[m]).sum() / (spec[m].sum() + 1e-20)))
    res["hat_brightness_hz"] = _median(cents, 0)
    hi_env, dt = _env_db(_band(mono, sr, 6000, 16000), sr)
    res["hat_decay_ms"] = _decay_ms(hi_env, dt, on_full, 12.0, 200.0, search_ms=10.0)
    res["hat_level_db"] = _median([H[b] - L[b] for b in full])

    # --- clap / snare on the backbeat
    mid = _band(mono, sr, 1000, 4000)
    rms = lambda t: float(np.sqrt(np.mean(mid[int(t * sr): int((t + 0.08) * sr)] ** 2)) + 1e-12)
    bb = []
    for b in full:
        t = [t0 + b * bar_s + k * beat for k in range(4)]
        if int((t[3] + 0.08) * sr) < len(mid):
            bb.append(20 * np.log10((rms(t[1]) + rms(t[3])) / (rms(t[0]) + rms(t[2]))))
    res["clap_backbeat_db"] = _median(bb)
    mid_env, dt = _env_db(mid, sr)
    res["clap_tail_ms"] = _decay_ms(mid_env, dt, beats(full, (1, 3)), 15.0, 450.0)

    # --- the breakdown's sound (pads, chords, vocals)
    brk = [b for b in range(n_bars) if label[b] == "break"]
    if len(brk) >= 4:
        cen, lm, hm, sm, mm_ = [], 0.0, 0.0, 0.0, 0.0
        n_fft = 4096
        f = np.fft.rfftfreq(n_fft, 1.0 / sr)
        wide = (f >= 30) & (f <= 16000)
        b_lm, b_hm = (f >= 150) & (f < 500), (f >= 2000) & (f < 6000)
        b_w = (f >= 150) & (f < 6000)
        w = np.hanning(n_fft)
        for b in brk:
            a0, a1 = int((t0 + b * bar_s) * sr), int((t0 + (b + 1) * bar_s) * sr)
            for a in range(a0, min(a1, len(mono) - n_fft), n_fft):
                M = np.abs(np.fft.rfft(mono[a:a + n_fft] * w)) ** 2
                Sd = np.abs(np.fft.rfft(side[a:a + n_fft] * w)) ** 2
                cen.append(np.log2((f[wide] * M[wide]).sum() / (M[wide].sum() + 1e-20) + 1.0))
                lm += M[b_lm].sum()
                hm += M[b_hm].sum()
                mm_ += M[b_w].sum()
                sm += Sd[b_w].sum()
        res["break_brightness_hz"] = round(float(2 ** np.median(cen) - 1), 0) if cen else None
        res["break_warmth_db"] = round(float(10 * np.log10((lm + 1e-20) / (hm + 1e-20))), 1)
        res["break_width_db"] = round(float(10 * np.log10((sm + 1e-20) / (mm_ + 1e-20))), 1)
    return res


def timbre_file(path, bpm, t0, segments, bars=None):
    x, sr = R.load_audio(path)
    return element_timbre(x, sr, bpm, t0, segments, bars)


def compare(ours, profile_timbre):
    """Each measure against the references' middle half: 'low' / 'ok' / 'high'."""
    rows = {}
    for k, v in ours.items():
        p = profile_timbre.get(k)
        if v is None or not p:
            continue
        verdict = "ok" if p["p25"] <= v <= p["p75"] else ("low" if v < p["p25"] else "high")
        rows[k] = {"ours": v, "median": p["median"], "p25": p["p25"], "p75": p["p75"],
                   "verdict": verdict, "what": DESCRIBE.get(k, "")}
    return rows


def build_timbre(folder, cache, log=print, on_track=None):
    """Add element timbre to every cached reference in `folder` (needs build_profile)."""
    import glob
    import os
    files = sorted(p for p in glob.glob(os.path.join(folder, "**", "*"), recursive=True)
                   if p.lower().endswith(R.AUDIO_EXT))
    out = []
    for p in files:
        r = cache.get(R._file_id(p))
        if r is None:
            continue
        if r.get("timbre_version") != TIMBRE_VERSION:
            r["timbre"] = R.analysis._plain(timbre_file(p, r["bpm"], r["first_beat_s"],
                                                        r["segments"], r.get("bars_matrix")))
            r["timbre_version"] = TIMBRE_VERSION
            log("timbre %-48s %s" % (r["file"][:48], r["timbre"]))
            if on_track:
                on_track(cache)
        if all(o["id"] != r["id"] for o in out):
            out.append(r)
    return out


def profile_stats(refs):
    keys = sorted({k for r in refs for k in (r.get("timbre") or {})})
    stats = {}
    for k in keys:
        v = np.array([r["timbre"][k] for r in refs
                      if r.get("timbre") and r["timbre"].get(k) is not None], float)
        if v.size:
            stats[k] = {"median": round(float(np.median(v)), 2),
                        "p25": round(float(np.percentile(v, 25)), 2),
                        "p75": round(float(np.percentile(v, 75)), 2), "n": int(v.size)}
    return stats


def rank_samples(rows, targets):
    """Rank measured samples by distance to a timbre target.

    rows: [{"name", "file", <metric>: value, ...}]
    targets: {metric: {"median", "p25", "p75"}} - usually a genre profile's timbre, or a
    hand-made target. Each metric's distance is measured in units of the references'
    middle-half width, so a 1 kHz miss in brightness and a 20 ms miss in decay weigh by
    how much they matter in the genre, not by their units."""
    scored = []
    for r in rows:
        d, used = 0.0, 0
        for k, t in targets.items():
            v = r.get(k)
            if v is None:
                continue
            width = max(1e-9, t["p75"] - t["p25"])
            d += ((v - t["median"]) / width) ** 2
            used += 1
        if used == len(targets):
            scored.append((round(d ** 0.5, 3), r))
    return [dict(r, distance=d) for d, r in sorted(scored, key=lambda s: s[0])]


# ----------------------------------------------------------------------------
# one-shots: measure a sample library once, then pick by a genre's element timbre

ONESHOT_VERSION = 1
# element -> {one-shot measure: profile measure}
ELEMENT_TARGETS = {
    "hat": {"brightness_hz": "hat_brightness_hz", "decay_ms": "hat_decay_ms"},
    "clap": {"mid_tail_ms": "clap_tail_ms"},
    "kick": {"low_pitch_hz": "kick_pitch_hz", "low_decay_ms": "kick_decay_ms"},
}


def oneshot(path):
    """Brightness and lengths of a one-shot (or the median over the hits of a short loop),
    measured with the same windows element_timbre uses inside a mix."""
    x, sr = R.load_audio(path)
    m = x.mean(axis=1)[: int(60 * sr)]
    pad = np.zeros(int(0.3 * sr))
    m = np.concatenate([pad, m, pad])
    on = R._band_onsets(m, sr, 6000, 16000)
    if len(on) == 0:
        env = np.abs(m)
        on = np.array([max(0.0, np.argmax(env) / sr - 0.002)])
    n25 = int(0.025 * sr)
    cents = []
    for t in on:
        seg = m[int(t * sr): int(t * sr) + n25]
        if len(seg) == n25:
            spec, f = _spectrum(seg, sr, 4096)
            sel = (f >= 2000) & (f <= 18000)
            cents.append(float((f[sel] * spec[sel]).sum() / (spec[sel].sum() + 1e-20)))
    hi, dt = _env_db(_band(m, sr, 6000, 16000), sr)
    mid, _ = _env_db(_band(m, sr, 1000, 4000), sr)
    lo, _ = _env_db(_band(m, sr, 30, 150), sr)
    first = float(on[0])
    seg = m[int((first + 0.015) * sr): int((first + 0.115) * sr)]
    pitch = None
    if len(seg) == int(0.1 * sr) and np.sqrt(np.mean(seg ** 2)) > 1e-4:
        spec, f = _spectrum(seg, sr, 1 << 16)
        sel = (f >= 35) & (f <= 150)
        pitch = round(float(f[sel][np.argmax(spec[sel])]), 1)
    return {"brightness_hz": _median(cents, 0),
            "decay_ms": _decay_ms(hi, dt, on, 12.0, 200.0, search_ms=10.0, min_n=1),
            "mid_tail_ms": _decay_ms(mid, dt, on, 15.0, 450.0, min_n=1),
            "low_pitch_hz": pitch,
            "low_decay_ms": _decay_ms(lo, dt, on[:1], 20.0, 400.0, min_n=1),
            "hits": int(len(on))}


def measure_folder(folder, cache_path=None, exts=(".wav", ".aif", ".aiff", ".flac"),
                   max_files=3000, log=None):
    """oneshot() for every sample under folder, cached by path + size + mtime."""
    import glob
    import json
    import os
    cache = {}
    if cache_path and os.path.exists(cache_path):
        cache = json.load(open(cache_path))
    rows, dirty = [], False
    files = sorted(p for p in glob.glob(os.path.join(folder, "**", "*"), recursive=True)
                   if p.lower().endswith(exts))[:max_files]
    for p in files:
        st = os.stat(p)
        key = "%s|%d|%d|%d" % (p, st.st_size, int(st.st_mtime), ONESHOT_VERSION)
        if key not in cache:
            try:
                cache[key] = R.analysis._plain(oneshot(p))
            except Exception as e:           # unreadable file: remember, skip
                cache[key] = {"error": str(e)[:200]}
            dirty = True
            if log and len(cache) % 100 == 0:
                log("measured %d samples" % len(cache))
        r = cache[key]
        if "error" not in r:
            rows.append(dict(r, file=p, name=os.path.basename(p)))
    if cache_path and dirty:
        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        tmp = cache_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(cache, f)
        os.replace(tmp, cache_path)
    return rows


def find_samples(rows, profile_timbre, element):
    """Rank measured one-shots for an element ('hat', 'clap', 'kick') by the genre's
    timbre profile."""
    if element not in ELEMENT_TARGETS:
        raise ValueError("element: %s" % sorted(ELEMENT_TARGETS))
    targets = {k: profile_timbre[v] for k, v in ELEMENT_TARGETS[element].items()
               if v in profile_timbre}
    return rank_samples(rows, targets)
