"""Learn a genre from reference tracks, and hold a mix up against it.

analyze_reference(path) measures one track: loudness, a normalised 1/3-octave spectrum,
stereo, tempo, key, swing, and its structure (per-bar energy, low end and brightness,
segmented into intro / full / break / outro on a 4-bar grid). build_profile() turns a
folder of them into a genre profile of medians and typical ranges; compare_to_profile()
says where a mix sits against it, band by band and section by section.

Everything here is statistics over real records. It tells you where a mix or an
arrangement is unusual for the genre, not whether it is good.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import tempfile

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

from . import analysis
from .music import samples

AUDIO_EXT = (".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".ogg")
SR = 44100
KEY_METHOD = "bass_anchored_v1"
ANALYSIS_VERSION = 3          # bump to re-analyse cached tracks
THIRD_OCTAVES = [25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
                 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500,
                 16000]


def load_audio(path, sr=SR):
    """Stereo float32 at `sr`. Formats libsndfile cannot read (m4a) go through ffmpeg."""
    try:
        x, fs = sf.read(path, always_2d=True, dtype="float32")
    except Exception:
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "decoded.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(sr),
                            "-f", "wav", out], check=True)
            x, fs = sf.read(out, always_2d=True, dtype="float32")
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = x[:, :2]
    if fs != sr:
        g = np.gcd(int(fs), int(sr))
        x = signal.resample_poly(x, sr // g, fs // g, axis=0).astype(np.float32)
    return x, sr


def third_octave_db(mono, sr):
    """Power per 1/3-octave band in dB relative to the whole spectrum (shape only)."""
    f, p = signal.welch(mono, sr, nperseg=16384, noverlap=8192)
    total = p[(f >= 20) & (f <= 20000)].sum() + 1e-20
    out = []
    for fc in THIRD_OCTAVES:
        lo, hi = fc / 2 ** (1 / 6.0), fc * 2 ** (1 / 6.0)
        pw = p[(f >= lo) & (f < hi)].sum()
        out.append(10 * np.log10(pw / total + 1e-20))
    return out


def _band_env(mono, sr, lo, hi, hop):
    sos = signal.butter(4, [lo, hi], "bandpass", fs=sr, output="sos")
    y = signal.sosfilt(sos, mono)
    frames = len(y) // hop
    return np.sqrt(np.mean(y[: frames * hop].reshape(frames, hop) ** 2, axis=1) + 1e-12)


def _low_flux(mono, sr, hop=256):
    env = _band_env(mono, sr, 30, 150, hop)
    return np.maximum(np.diff(env, prepend=env[0]), 0), sr / float(hop)


def _grid_score(flux, fps, bpm):
    """Best phase and its score: low-band attacks summed on a beat grid at `bpm`."""
    period = 60.0 / bpm * fps
    phases = np.arange(0, period, 0.5)
    n = int((len(flux) - period) / period)
    idx = (phases[:, None] + np.arange(n)[None, :] * period).astype(int)
    scores = flux[np.clip(idx, 0, len(flux) - 1)].sum(axis=1)
    k = int(np.argmax(scores))
    return phases[k] / fps, float(scores[k])


def refine_tempo(mono, sr, bpm0, span=2.0, step=0.02):
    """Tempo to 0.02 BPM: the autocorrelation estimate is only good to ~1.5 BPM, and over
    a 6-minute track a 1 % error slides the bar grid by several bars."""
    flux, fps = _low_flux(mono, sr)
    best = max(((_grid_score(flux, fps, b)[1], b)
                for b in np.arange(bpm0 - span, bpm0 + span + 1e-9, step)))
    return round(float(best[1]), 2)


def beat_grid(mono, sr, bpm):
    """First beat time: the phase whose beat positions collect the most low-band attacks."""
    flux, fps = _low_flux(mono, sr)
    return _grid_score(flux, fps, bpm)[0]


def per_bar(x, sr, bpm, t0):
    """Per bar: loudness, kick (low band on the beats), bass (low band on the
    off-beats, where a kick has decayed) and brightness (6-16 kHz), all in dB. Splitting
    the low band this way tells a drums-only DJ intro from a full groove."""
    beat = 60.0 / bpm
    bar_s = 4 * beat
    mono = x.mean(axis=1)
    meter = pyln.Meter(sr)
    sos_lo = signal.butter(4, [30, 120], "bandpass", fs=sr, output="sos")
    sos_hi = signal.butter(4, [6000, 16000], "bandpass", fs=sr, output="sos")
    lo = signal.sosfilt(sos_lo, mono)
    hi = signal.sosfilt(sos_hi, mono)
    db = lambda v: 20 * np.log10(np.sqrt(np.mean(v ** 2)) + 1e-9)
    rows = []
    n = int((len(mono) / sr - t0) / bar_s)
    for b in range(n):
        a, e = int((t0 + b * bar_s) * sr), int((t0 + (b + 1) * bar_s) * sr)
        with np.errstate(divide="ignore"):
            lu = meter.integrated_loudness(x[a:e])
        on, off = [], []
        for k in range(4):
            s0 = t0 + b * bar_s + k * beat
            on.append(lo[int(s0 * sr): int((s0 + 0.2 * beat) * sr)])
            off.append(lo[int((s0 + 0.5 * beat) * sr): int((s0 + 0.9 * beat) * sr)])
        rows.append([lu if np.isfinite(lu) else -70.0, db(np.concatenate(on)),
                     db(np.concatenate(off)), db(hi[a:e])])
    return np.array(rows)


def segment(bars, grid=4, window=8, min_len=8, threshold=0.35):
    """Split the per-bar matrix into sections where its character changes, on a
    `grid`-bar lattice, and label each by kick, bass and loudness.

    Features are scaled by their own 10-90 % spread, so a part entering or leaving
    moves its feature by roughly 1 whatever its level; novelty compares the bars before
    and after each grid line, with windows that shrink near the edges so an ending (the
    bass leaving 8 bars before the end) is still seen."""
    n = len(bars)
    if n < 2 * grid:
        return [{"start": 0, "end": n, "label": "full"}]
    spread = np.percentile(bars, 90, axis=0) - np.percentile(bars, 10, axis=0)
    z = (bars - np.median(bars, axis=0)) / (spread + 1.0)
    nov = np.zeros(n + 1)
    for b in range(grid, n - grid + 1, grid):
        w = min(window, b, n - b)
        nov[b] = np.linalg.norm(np.median(z[b - w:b], axis=0) - np.median(z[b:b + w], axis=0))
    cuts = [0]
    for b in sorted(range(grid, n - grid + 1, grid), key=lambda k: -nov[k]):
        if nov[b] < threshold:
            break
        if all(abs(b - c) >= min(min_len, n - b) for c in cuts):
            cuts.append(b)
    cuts = sorted(cuts) + [n]
    # columns: lufs, kick, bass, high (see per_bar)
    lufs_ref, kick_ref, bass_ref = (np.percentile(bars[:, i], 80) for i in range(3))
    segs = []
    for a, e in zip(cuts, cuts[1:]):
        lu, kick, bass = (float(np.median(bars[a:e, i])) for i in range(3))
        kick_on, bass_on = kick >= kick_ref - 8, bass >= bass_ref - 8
        if kick_on and bass_on and lu >= lufs_ref - 4:
            label = "full"
        elif not kick_on:
            label = "break"
        else:
            label = "partial"
        segs.append({"start": int(a), "end": int(e), "label": label, "lufs": round(lu, 1),
                     "kick_db": round(kick, 1), "bass_db": round(bass, 1)})
    fulls = [i for i, s in enumerate(segs) if s["label"] == "full"]
    if fulls:
        for i, s in enumerate(segs):
            if i < fulls[0]:
                s["label"] = "intro"
            elif i > fulls[-1]:
                s["label"] = "outro"
    merged = [dict(segs[0])]
    for s in segs[1:]:
        if s["label"] == merged[-1]["label"]:
            m = merged[-1]
            wa, wb = m["end"] - m["start"], s["end"] - s["start"]
            for k in ("lufs", "kick_db", "bass_db"):
                m[k] = round((m[k] * wa + s[k] * wb) / float(wa + wb), 1)
            m["end"] = s["end"]
        else:
            merged.append(dict(s))
    return merged


def structure_summary(segs, n_bars):
    breaks = [s for s in segs if s["label"] in ("break", "partial")]
    fulls = [s for s in segs if s["label"] == "full"]
    intro = sum(s["end"] - s["start"] for s in segs if s["label"] == "intro")
    outro = sum(s["end"] - s["start"] for s in segs if s["label"] == "outro")
    main = max(breaks, key=lambda s: (s["label"] == "break", s["end"] - s["start"]), default=None)
    out = {"bars": n_bars, "intro_bars": intro, "outro_bars": outro,
           "n_breaks": sum(1 for s in segs if s["label"] == "break"),
           "full_lufs": round(float(np.median([s["lufs"] for s in fulls])), 1) if fulls else None}
    if main:
        after = [s for s in fulls if s["start"] >= main["end"]]
        out.update({
            "main_break_bars": main["end"] - main["start"],
            "main_break_at": round(main["start"] / float(n_bars), 3),
            "break_depth_lu": (round(after[0]["lufs"] - main["lufs"], 1) if after else None),
        })
    return out


def _file_id(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        h.update(f.read(1 << 20))
    return h.hexdigest()[:12]


def key_fields(mono, sr, bpm):
    """Bass-anchored key (see samples.estimate_key_bass_anchored), falling back to
    Krumhansl on mid-range chroma when the track has no steady bass."""
    k = samples.estimate_key_bass_anchored(mono, sr, bpm)
    if k is None or k["bass_share"] < 0.25:
        ks = samples.estimate_key(samples.chroma(mono, sr, fmin=130.0))
        return {"key": "%s %s" % (ks["tonic"], ks["mode"]), "key_confidence": ks["confidence"],
                "key_method": KEY_METHOD + "/krumhansl_fallback"}
    return {"key": "%s %s" % (k["tonic"], k["mode"]), "key_confidence": k["confidence"],
            "key_method": KEY_METHOD}


def analyze_reference(path, bpm=None):
    x, sr = load_audio(path)
    mono = x.mean(axis=1)
    mid = mono[int(len(mono) * 0.25): int(len(mono) * 0.25) + 60 * sr]
    tempo = bpm or refine_tempo(mono, sr, samples.estimate_tempo(
        mid if len(mid) > 10 * sr else mono, sr, lo=100.0, hi=140.0))
    t0 = beat_grid(mono[: 90 * sr], sr, tempo)
    bars = per_bar(x, sr, tempo, t0)
    segs = segment(bars)
    key = key_fields(mono, sr, tempo)
    meter = pyln.Meter(sr)
    integ = meter.integrated_loudness(x)
    tp = analysis.true_peak_db(x, sr)
    peak = float(np.abs(x).max())
    rms = float(np.sqrt(np.mean(mono ** 2)))
    bands, f, p = analysis.band_levels(mono, sr)
    swing = samples.estimate_swing(
        signal.sosfilt(signal.butter(4, 6000, "highpass", fs=sr, output="sos"), mid), sr, tempo)
    return analysis._plain({
        "file": os.path.basename(path), "id": _file_id(path), "version": ANALYSIS_VERSION,
        "duration_s": round(len(mono) / sr, 1), "bpm": tempo, "first_beat_s": round(t0, 3),
        **key, "swing_pct": swing,
        "loudness": {"integrated_lufs": round(integ, 1), "true_peak_dbtp": round(tp, 2),
                     "crest_db": round(analysis._db(peak) - analysis._db(rms), 1)},
        "bands_share": {k: v["share_pct"] for k, v in bands.items()},
        "tilt": analysis.spectral_tilt(f, p),
        "stereo": analysis.stereo(x, sr),
        "third_octave_db": [round(v, 2) for v in third_octave_db(mono, sr)],
        "segments": segs,
        "structure": structure_summary(segs, len(bars)),
        "bars_matrix": np.round(bars, 1).tolist(),
    })


def _stats(vals):
    v = np.array([x for x in vals if x is not None], dtype=float)
    if not v.size:
        return None
    return {"median": round(float(np.median(v)), 2), "p25": round(float(np.percentile(v, 25)), 2),
            "p75": round(float(np.percentile(v, 75)), 2), "n": int(v.size)}


def build_profile(folder, genre, cache=None, log=print, on_track=None):
    """Analyse every audio file in `folder` (deduplicated by content) into a profile.
    on_track(cache) runs after each new analysis, so callers can persist progress."""
    files = sorted(p for p in glob.glob(os.path.join(folder, "**", "*"), recursive=True)
                   if p.lower().endswith(AUDIO_EXT))
    cache = cache or {}
    tracks, seen = [], set()
    for p in files:
        fid = _file_id(p)
        if fid in seen:
            log("skip duplicate: %s" % os.path.basename(p))
            continue
        seen.add(fid)
        if fid in cache and cache[fid].get("version") != ANALYSIS_VERSION:
            del cache[fid]
        if fid in cache:
            r = cache[fid]
            m = np.array(r["bars_matrix"])
            r["segments"] = segment(m)
            r["structure"] = structure_summary(r["segments"], len(m))
            if not str(r.get("key_method", "")).startswith(KEY_METHOD):
                x, sr = load_audio(p)
                r.update(analysis._plain(key_fields(x.mean(axis=1), sr, r["bpm"])))
                log("re-keyed %-50s %s" % (r["file"][:50], r["key"]))
                if on_track:
                    on_track(cache)
            tracks.append(r)
            continue
        try:
            r = analyze_reference(p)
        except Exception as e:
            log("failed %s: %s" % (os.path.basename(p), e))
            continue
        cache[fid] = r
        tracks.append(r)
        if on_track:
            on_track(cache)
        log("%-60s %5.1f BPM  %-9s %6.1f LUFS  %3d bars  intro %s  break %s"
            % (r["file"][:60], r["bpm"], r["key"], r["loudness"]["integrated_lufs"],
               r["structure"]["bars"], r["structure"]["intro_bars"],
               r["structure"].get("main_break_bars")))
    keys = {}
    for t in tracks:
        keys[t["key"]] = keys.get(t["key"], 0) + 1
    modes = {"minor": sum(1 for t in tracks if t["key"].endswith("minor")),
             "major": sum(1 for t in tracks if t["key"].endswith("major"))}
    spec = np.median(np.array([t["third_octave_db"] for t in tracks]), axis=0)
    spec_lo = np.percentile(np.array([t["third_octave_db"] for t in tracks]), 25, axis=0)
    spec_hi = np.percentile(np.array([t["third_octave_db"] for t in tracks]), 75, axis=0)
    S = lambda k: _stats([t["structure"].get(k) for t in tracks])
    profile = {
        "genre": genre, "n_tracks": len(tracks), "source": folder,
        "bpm": _stats([t["bpm"] for t in tracks]),
        "swing_pct": _stats([t["swing_pct"] for t in tracks]),
        "keys": dict(sorted(keys.items(), key=lambda kv: -kv[1])), "modes": modes,
        "duration_s": _stats([t["duration_s"] for t in tracks]),
        "loudness": {k: _stats([t["loudness"][k] for t in tracks])
                     for k in ("integrated_lufs", "true_peak_dbtp", "crest_db")},
        "bands_share": {k: _stats([t["bands_share"][k] for t in tracks])
                        for k in tracks[0]["bands_share"]},
        "tilt": _stats([t["tilt"] for t in tracks]),
        "stereo": {k: _stats([t["stereo"][k] for t in tracks]) for k in tracks[0]["stereo"]},
        "third_octave": {"hz": THIRD_OCTAVES, "median_db": [round(float(v), 2) for v in spec],
                         "p25_db": [round(float(v), 2) for v in spec_lo],
                         "p75_db": [round(float(v), 2) for v in spec_hi]},
        "structure": {k: S(k) for k in ("bars", "intro_bars", "outro_bars", "n_breaks",
                                         "main_break_bars", "main_break_at", "break_depth_lu",
                                         "full_lufs")},
        "tracks": [{k: t[k] for k in ("file", "bpm", "key", "duration_s", "swing_pct")}
                   | {"lufs": t["loudness"]["integrated_lufs"], "structure": t["structure"]}
                   for t in tracks],
    }
    return analysis._plain(profile), cache


def compare_to_profile(path, profile, sections=None, tempo=None):
    """Where a mix sits against a genre: loudness, band shares and the 1/3-octave curve
    (shape only), with suggested moves for bands outside the references' middle half."""
    x, sr = load_audio(path)
    mono = x.mean(axis=1)
    mine = third_octave_db(mono, sr)
    prof = profile["third_octave"]
    eq = []
    for hz, m, med, lo, hi in zip(prof["hz"], mine, prof["median_db"], prof["p25_db"],
                                  prof["p75_db"]):
        if m > hi or m < lo:
            eq.append({"hz": hz, "mine_db": round(m, 1), "median_db": med,
                       "move_db": round(med - m, 1)})
    a = analysis.analyze(path, sections=sections, tempo=tempo)
    L = profile["loudness"]
    notes = []
    lufs = a["loudness"]["integrated_lufs"]
    if L["integrated_lufs"] and not (L["integrated_lufs"]["p25"] <= lufs <= L["integrated_lufs"]["p75"]):
        notes.append("integrated %.1f LUFS vs references %.1f (middle half %.1f to %.1f)"
                     % (lufs, L["integrated_lufs"]["median"], L["integrated_lufs"]["p25"],
                        L["integrated_lufs"]["p75"]))
    for k, st in profile["bands_share"].items():
        v = a["bands"][k]["share_pct"]
        if st and not (st["p25"] <= v <= st["p75"]):
            notes.append("%s holds %.1f%% of the energy vs %.1f%% typical (%.1f-%.1f)"
                         % (k, v, st["median"], st["p25"], st["p75"]))
    return analysis._plain({
        "loudness": a["loudness"], "bands_share": {k: v["share_pct"] for k, v in a["bands"].items()},
        "third_octave_db": [round(float(v), 2) for v in mine], "eq_moves": eq, "notes": notes,
        "sections": a.get("sections")})


def save_profile(profile, path):
    with open(path, "w") as f:
        json.dump(profile, f, indent=1)


def slug(genre):
    return re.sub(r"[^a-z0-9]+", "_", genre.lower()).strip("_")


# ---------------------------------------------------------------------------
# fingerprint: groove, harmony, timbre, width, dynamics, movement, arrangement
# ---------------------------------------------------------------------------

FP_VERSION = 1
FP_BANDS = {"low": (30, 150), "low_mid": (150, 500), "mid": (500, 2000),
            "high_mid": (2000, 6000), "high": (6000, 16000)}


def _band_onsets(mono, sr, lo, hi, hop=256, min_gap_s=0.06):
    """Onset times in one band: log-energy flux with a running-median threshold."""
    env = _band_env(mono, sr, lo, hi, hop)
    le = np.log10(env + 1e-9)
    flux = np.maximum(np.diff(le, prepend=le[0]), 0)
    fps = sr / float(hop)
    k = int(fps)                                         # ~1 s window
    pad = np.pad(flux, (k, k), mode="edge")
    med = np.array([np.median(pad[i:i + 2 * k]) for i in range(0, len(flux), 8)])
    med = np.repeat(med, 8)[:len(flux)]
    thr = med + 0.08
    out, last = [], -1e9
    for i in range(1, len(flux) - 1):
        if flux[i] > thr[i] and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
            t = (i + 0.5) * hop / sr
            if t - last >= min_gap_s:
                out.append(t)
                last = t
    return np.array(out)


def fingerprint(x, sr, bpm, t0, segments):
    """Measurements that describe how a track is made, beyond loudness and spectrum."""
    mono = x.mean(axis=1)
    mid, side = mono, (x[:, 0] - x[:, 1]) / 2.0
    beat = 60.0 / bpm
    bar_s = 4 * beat
    n_bars = segments[-1]["end"] if segments else int((len(mono) / sr - t0) / bar_s)
    full = np.zeros(n_bars, bool)
    for s in segments:
        if s["label"] == "full":
            full[s["start"]:s["end"]] = True
    if not full.any():
        full[:] = True

    # --- spectral frames
    n_fft, hop = 4096, 1024
    win = np.hanning(n_fft).astype(np.float32)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    n_frames = max(1, (len(mono) - n_fft) // hop)
    frame_bar = ((np.arange(n_frames) * hop + n_fft / 2) / sr - t0) // bar_s
    band_idx = {k: (freqs >= lo) & (freqs < hi) for k, (lo, hi) in FP_BANDS.items()}
    sel_c = (freqs >= 30) & (freqs <= 16000)
    sel_f = (freqs >= 200) & (freqs <= 16000)
    sel_ch = (freqs >= 130) & (freqs <= 2000)
    pcs = (np.round(69 + 12 * np.log2(freqs[sel_ch] / 440.0)).astype(int)) % 12
    cent, flat = np.zeros(n_frames), np.zeros(n_frames)
    bandM = {k: np.zeros(n_frames) for k in FP_BANDS}
    bandS = {k: np.zeros(n_frames) for k in FP_BANDS}
    chroma_bar = np.zeros((n_bars, 12))
    for f in range(n_frames):
        a = f * hop
        M = np.abs(np.fft.rfft(mid[a:a + n_fft] * win)) ** 2
        S = np.abs(np.fft.rfft(side[a:a + n_fft] * win)) ** 2
        pc = M[sel_c]
        cent[f] = (freqs[sel_c] * pc).sum() / (pc.sum() + 1e-20)
        pf = M[sel_f] + 1e-20
        flat[f] = np.exp(np.mean(np.log(pf))) / np.mean(pf)
        for k, m in band_idx.items():
            bandM[k][f] = M[m].sum()
            bandS[k][f] = S[m].sum()
        b = int(frame_bar[f])
        if 0 <= b < n_bars:
            chroma_bar[b] += np.bincount(pcs, weights=M[sel_ch], minlength=12)

    def per_bar(v, agg=np.mean):
        out = np.full(n_bars, np.nan)
        for b in range(n_bars):
            m = frame_bar == b
            if m.any():
                out[b] = agg(v[m])
        return out

    cent_bar = per_bar(np.log2(cent + 1.0))
    fb = full[:len(cent_bar)]
    res = {}

    # --- groove (onsets per band, on the bar grid)
    lows = _band_onsets(mono, sr, 30, 150)
    mids = _band_onsets(mono, sr, 500, 4000)
    highs = _band_onsets(mono, sr, 6000, 16000)

    def in_full(ts):
        b = ((ts - t0) // bar_s).astype(int)
        ok = (b >= 0) & (b < n_bars)
        return ts[ok][full[b[ok]]]

    lows_f, mids_f, highs_f = in_full(lows), in_full(mids), in_full(highs)
    n_full = max(1, int(full.sum()))
    beats = t0 + np.arange(int(n_bars * 4)) * beat
    beats_f = beats[full[(np.arange(len(beats)) // 4).clip(0, n_bars - 1)]]
    if len(lows_f) and len(beats_f):
        d = np.abs(beats_f[:, None] - lows_f[None, :]).min(axis=1)
        res["kick_on_beats"] = round(float(np.mean(d < 0.04)), 3)
    res["hat_hits_per_bar"] = round(len(highs_f) / n_full, 2)
    res["perc_hits_per_bar"] = round(len(mids_f) / n_full, 2)
    six = beat / 4.0
    pos = ((np.concatenate([mids_f, highs_f]) - t0) / six)
    frac = pos - np.floor(pos)
    near = np.round(pos).astype(int)
    on_grid = np.abs(pos - np.round(pos)) < 0.3
    if on_grid.any():
        res["offbeat_16th_share"] = round(float(np.mean(near[on_grid] % 2 == 1)), 3)
    pair = beat / 2.0
    ph = ((highs_f - t0) % pair) / pair
    off = ph[(ph > 0.35) & (ph < 0.85)]
    res["swing_pct"] = round(float(np.median(off)) * 100, 1) if len(off) >= 8 else None
    dev = []
    sw = (res["swing_pct"] or 50.0) / 100.0
    for t in highs_f:
        p = ((t - t0) % pair) / pair
        target = 0.0 if p < 0.25 or p > 0.8 else sw
        dist = min(abs(p - target), abs(p - 1.0)) if target == 0.0 else abs(p - target)
        dev.append(dist * pair * 1000)
    res["timing_spread_ms"] = round(float(np.median(dev)), 1) if dev else None

    # --- harmony
    cb = chroma_bar / (chroma_bar.sum(axis=1, keepdims=True) + 1e-20)
    tot = chroma_bar.sum(axis=0)
    tot = tot / (tot.sum() + 1e-20)
    res["tonal_strength"] = round(float(np.nanmedian(np.sort(cb[fb], axis=1)[:, -3:].sum(axis=1))), 3)
    res["pitch_classes_used"] = int((tot > 0.06).sum())
    cos = [float(np.dot(cb[i], cb[i + 1]) / (np.linalg.norm(cb[i]) * np.linalg.norm(cb[i + 1]) + 1e-12))
           for i in range(n_bars - 1)]
    res["harmonic_changes_per_8_bars"] = round(8 * float(np.mean(np.array(cos) < 0.85)), 2) if cos else None

    # --- timbre
    res["brightness_hz"] = round(float(2 ** np.nanmedian(cent_bar[fb]) - 1), 0)
    res["noisiness"] = round(float(np.nanmedian(per_bar(flat)[fb])), 4)
    lm = np.nanmedian(per_bar(bandM["low_mid"])[fb])
    hm = np.nanmedian(per_bar(bandM["high_mid"])[fb])
    res["warmth_db"] = round(float(10 * np.log10((lm + 1e-20) / (hm + 1e-20))), 1)

    # --- stereo width by band (side relative to mid)
    for k in ("low", "mid", "high"):
        m_ = np.nanmedian(per_bar(bandM[k])[fb])
        s_ = np.nanmedian(per_bar(bandS[k])[fb])
        res["width_%s_db" % k] = round(float(10 * np.log10((s_ + 1e-20) / (m_ + 1e-20))), 1)

    # --- movement ("automation")
    moves = []
    for a in range(0, n_bars - 16, 16):
        w = cent_bar[a:a + 16][fb[a:a + 16]]
        if len(w) >= 8:
            moves.append(float(np.nanstd(w)))
    res["brightness_movement_oct"] = round(float(np.median(moves)), 3) if moves else None
    return res


def fingerprint_file(path, bpm, t0, segments):
    x, sr = load_audio(path)
    return analysis._plain(fingerprint(x, sr, bpm, t0, segments))


def build_fingerprints(folder, cache, log=print, on_track=None):
    """Add a fingerprint to every cached reference in `folder` (needs build_profile first)."""
    files = sorted(p for p in glob.glob(os.path.join(folder, "**", "*"), recursive=True)
                   if p.lower().endswith(AUDIO_EXT))
    out = []
    for p in files:
        fid = _file_id(p)
        r = cache.get(fid)
        if r is None:
            continue
        if r.get("fp_version") != FP_VERSION:
            r["fingerprint"] = fingerprint_file(p, r["bpm"], r["first_beat_s"], r["segments"])
            r["fp_version"] = FP_VERSION
            log("fingerprint %-50s %s" % (r["file"][:50], r["fingerprint"]))
            if on_track:
                on_track(cache)
        if all(o["id"] != r["id"] for o in out):
            out.append(r)
    return out


def compare_fingerprint(ours, refs):
    """Percentile of each of our measurements among the references, with the references'
    middle half, so you can see which dimensions are typical and which stand out."""
    rows = {}
    for k, v in ours.items():
        vals = np.array([r["fingerprint"][k] for r in refs
                         if r.get("fingerprint") and r["fingerprint"].get(k) is not None], float)
        if v is None or not vals.size:
            continue
        pct = float((vals < v).mean() * 100 + (vals == v).mean() * 50)
        rows[k] = {"ours": v, "median": round(float(np.median(vals)), 3),
                   "p25": round(float(np.percentile(vals, 25)), 3),
                   "p75": round(float(np.percentile(vals, 75)), 3),
                   "percentile": round(pct), "n": int(vals.size),
                   "typical": bool(np.percentile(vals, 25) <= v <= np.percentile(vals, 75))}
    return rows
