"""Objective mix measurements: loudness, peaks, tonal balance, stereo image.

These are the "ears": numbers that stand in for listening. They catch technical
problems (clipping, mud, phasey low end, loudness off target, a flat energy curve)
but say nothing about whether a groove feels good.
"""
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

BANDS = [  # name, low Hz, high Hz
    ("sub", 20, 60),
    ("low", 60, 250),
    ("low_mid", 250, 500),
    ("mid", 500, 2000),
    ("high_mid", 2000, 6000),
    ("high", 6000, 20000),
]

TARGETS = {  # integrated LUFS, max true peak dBTP
    "club": (-8.0, -0.5),
    "streaming": (-14.0, -1.0),
}


def _db(x, floor=-120.0):
    return float(max(floor, 20.0 * np.log10(max(float(x), 1e-12))))


def load(path):
    x, sr = sf.read(path, always_2d=True, dtype="float32")
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    return x[:, :2], sr


def true_peak_db(x, sr):
    up = signal.resample_poly(x, 4, 1, axis=0)
    return _db(np.max(np.abs(up)))


def band_levels(mono, sr):
    """Power per band in dB, from a Welch PSD. Also the share of total power."""
    f, p = signal.welch(mono, sr, nperseg=8192, noverlap=4096)
    total = p[(f >= 20) & (f <= 20000)].sum() + 1e-20
    out = {}
    for name, lo, hi in BANDS:
        sel = (f >= lo) & (f < hi)
        pw = p[sel].sum()
        out[name] = {"db": round(10 * np.log10(pw + 1e-20), 1),
                     "share_pct": round(100 * pw / total, 1)}
    return out, f, p


def spectral_tilt(f, p):
    """Slope in dB/octave from 100 Hz to 10 kHz. Pink noise is -3; most finished
    dance mixes sit roughly between -4 and -6."""
    sel = (f >= 100) & (f <= 10000)
    oct_ = np.log2(f[sel])
    db = 10 * np.log10(p[sel] + 1e-20)
    slope = np.polyfit(oct_, db, 1)[0]
    return round(float(slope), 2)


def _lowpass(x, sr, hz):
    sos = signal.butter(4, hz, "low", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def stereo(x, sr):
    l, r = x[:, 0], x[:, 1]

    def corr(a, b):
        if np.std(a) < 1e-9 or np.std(b) < 1e-9:
            return 1.0
        return float(np.corrcoef(a, b)[0, 1])

    lo = _lowpass(x, sr, 120)
    mid, side = (l + r) / 2, (l - r) / 2
    return {"correlation": round(corr(l, r), 3),
            "low_correlation_below_120hz": round(corr(lo[:, 0], lo[:, 1]), 3),
            "side_to_mid_db": round(_db(np.sqrt(np.mean(side ** 2))) -
                                    _db(np.sqrt(np.mean(mid ** 2))), 1)}


def short_term_curve(x, sr, window_s=3.0, hop_s=1.0):
    meter = pyln.Meter(sr)
    w, h = int(window_s * sr), int(hop_s * sr)
    vals = []
    for i in range(0, max(1, len(x) - w + 1), h):
        seg = x[i:i + w]
        with np.errstate(divide="ignore"):
            v = meter.integrated_loudness(seg) if len(seg) >= int(0.4 * sr) else -70.0
        vals.append(v if np.isfinite(v) else -70.0)
    return np.array(vals)


def analyze(path, target="club", sections=None, tempo=None):
    """sections: [{"name": "Drop", "start_bar": 161, "end_bar": 193}, ...] with bars
    relative to the start of the audio file (bar 1 = first sample). Needs tempo."""
    x, sr = load(path)
    dur = len(x) / sr
    meter = pyln.Meter(sr)
    integrated = meter.integrated_loudness(x)
    st = short_term_curve(x, sr)
    gated = st[st > max(-70.0, integrated - 20)]
    lra = float(np.percentile(gated, 95) - np.percentile(gated, 10)) if len(gated) > 3 else 0.0
    mono = x.mean(axis=1)
    rms = np.sqrt(np.mean(mono ** 2))
    peak = np.max(np.abs(x))
    tp = true_peak_db(x, sr)
    bands, f, p = band_levels(mono, sr)
    st_img = stereo(x, sr)

    res = {
        "file": path,
        "duration_s": round(dur, 2),
        "loudness": {
            "integrated_lufs": round(integrated, 1),
            "short_term_max_lufs": round(float(st.max()), 1),
            "loudness_range_lu": round(lra, 1),
            "true_peak_dbtp": round(tp, 2),
            "sample_peak_dbfs": round(_db(peak), 2),
            "crest_db": round(_db(peak) - _db(rms), 1),
        },
        "bands": bands,
        "spectral_tilt_db_per_oct": spectral_tilt(f, p),
        "stereo": st_img,
    }

    if sections and tempo:
        bar_s = 4 * 60.0 / float(tempo)
        out = []
        for s in sections:
            a = int((s["start_bar"] - 1) * bar_s * sr)
            b = int((s["end_bar"] - 1) * bar_s * sr)
            seg = x[a:b]
            if len(seg) < sr:
                continue
            bl, _, _ = band_levels(seg.mean(axis=1), sr)
            with np.errstate(divide="ignore"):
                lu = meter.integrated_loudness(seg)
            out.append({"name": s["name"], "lufs": round(lu, 1) if np.isfinite(lu) else None,
                        "sub_share": bl["sub"]["share_pct"], "low_share": bl["low"]["share_pct"],
                        "high_share": bl["high"]["share_pct"]})
        res["sections"] = out

    res["flags"] = flags(res, target)
    return res


def flags(res, target="club"):
    lufs_t, tp_t = TARGETS.get(target, TARGETS["club"])
    L, B, S = res["loudness"], res["bands"], res["stereo"]
    out = []
    if L["true_peak_dbtp"] > tp_t:
        out.append("true peak %.1f dBTP above %.1f: risk of clipping after encoding"
                   % (L["true_peak_dbtp"], tp_t))
    diff = L["integrated_lufs"] - lufs_t
    if abs(diff) > 2:
        out.append("integrated %.1f LUFS is %.1f LU %s the %s target (%.0f)"
                   % (L["integrated_lufs"], abs(diff), "above" if diff > 0 else "below",
                      target, lufs_t))
    if L["crest_db"] < 7:
        out.append("crest %.1f dB: heavily limited, transients likely squashed" % L["crest_db"])
    if S["low_correlation_below_120hz"] < 0.8:
        out.append("low end below 120 Hz is not mono (correlation %.2f): phase issues on club "
                   "systems" % S["low_correlation_below_120hz"])
    if S["correlation"] < 0.2:
        out.append("overall correlation %.2f: mix will collapse badly in mono" % S["correlation"])
    if B["low_mid"]["share_pct"] > 18:
        out.append("low-mids 250-500 Hz hold %.0f%% of energy: likely muddy"
                   % B["low_mid"]["share_pct"])
    lows = B["sub"]["share_pct"] + B["low"]["share_pct"]
    if lows > 75:
        out.append("sub+low hold %.0f%% of energy: bottom-heavy" % lows)
    if lows < 35:
        out.append("sub+low hold only %.0f%% of energy: thin for a club track" % lows)
    tilt = res["spectral_tilt_db_per_oct"]
    if tilt > -3.0:
        out.append("tilt %.1f dB/oct: bright/harsh balance" % tilt)
    if tilt < -7.0:
        out.append("tilt %.1f dB/oct: dark/dull balance" % tilt)
    if L["loudness_range_lu"] < 3 and res["duration_s"] > 120:
        out.append("loudness range %.1f LU over %.0f s: very flat energy curve, "
                   "arrangement may feel static" % (L["loudness_range_lu"], res["duration_s"]))
    return out


def compare(path, reference_path):
    """Band-by-band difference: mix minus reference, after matching loudness."""
    a, b = analyze(path), analyze(reference_path)
    shift = a["loudness"]["integrated_lufs"] - b["loudness"]["integrated_lufs"]
    diffs = {k: round(a["bands"][k]["db"] - b["bands"][k]["db"] - shift, 1) for k in a["bands"]}
    return {
        "loudness_diff_lu": round(shift, 1),
        "band_diff_db_loudness_matched": diffs,
        "tilt_diff": round(a["spectral_tilt_db_per_oct"] - b["spectral_tilt_db_per_oct"], 2),
        "correlation": [a["stereo"]["correlation"], b["stereo"]["correlation"]],
        "crest": [a["loudness"]["crest_db"], b["loudness"]["crest_db"]],
        "mix": a["loudness"], "reference": b["loudness"],
    }
