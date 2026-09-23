"""Understand audio samples: key, tempo, swing, loop length and role.

Key: chroma (FFT energy folded to 12 pitch classes) correlated with the
Krumhansl-Kessler major/minor profiles in all 24 keys. Tempo: autocorrelation of an
onset-strength envelope. Swing: where the off-beat 16ths land inside each pair.
"""
import re

import numpy as np
import soundfile as sf

from .theory import NOTE_NAMES

KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def load_mono(path, max_seconds=None):
    x, sr = sf.read(path, always_2d=True, dtype="float32")
    if max_seconds:
        x = x[: int(max_seconds * sr)]
    return x.mean(axis=1), sr


def chroma(mono, sr, fmin=55.0, fmax=2000.0, n_fft=8192):
    hop = n_fft // 2
    win = np.hanning(n_fft)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    sel = (freqs >= fmin) & (freqs <= fmax)
    midi = 69 + 12 * np.log2(freqs[sel] / 440.0)
    pcs = np.round(midi).astype(int) % 12
    acc = np.zeros(12)
    for i in range(0, max(1, len(mono) - n_fft), hop):
        mag = np.abs(np.fft.rfft(mono[i:i + n_fft] * win))[sel] ** 2
        acc += np.bincount(pcs, weights=mag, minlength=12)
    total = acc.sum()
    return acc / total if total > 0 else acc


def bass_notes(mono, sr, bpm, max_bars=16):
    """Dominant fundamental per beat for low material (30-300 Hz). Needs a long window:
    near 100 Hz a semitone is ~6 Hz, finer than an 8192-point FFT can resolve."""
    n_fft = 32768
    beat = 60.0 / bpm
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    sel = (freqs >= 30) & (freqs <= 300)
    midi = np.round(69 + 12 * np.log2(freqs[sel] / 440.0)).astype(int)
    out = []
    n_beats = min(int(len(mono) / sr / beat), max_bars * 4)
    for b in range(n_beats):
        c = int((b + 0.5) * beat * sr)
        seg = mono[max(0, c - n_fft // 2): c + n_fft // 2]
        if len(seg) < n_fft:
            seg = np.pad(seg, (0, n_fft - len(seg)))
        mag = np.abs(np.fft.rfft(seg * np.hanning(n_fft)))[sel]
        if mag.max() < 1e-4:
            out.append(None)
            continue
        acc = np.bincount(midi - midi.min(), weights=mag ** 2)
        out.append(int(np.argmax(acc)) + int(midi.min()))
    return out


def estimate_key(ch):
    """Best of 24 keys by correlation with the KK profiles. Confidence is the gap to
    the runner-up (0 = coin toss); relative keys are close by nature."""
    scores = []
    for tonic in range(12):
        for mode, prof in (("major", KK_MAJOR), ("minor", KK_MINOR)):
            r = np.corrcoef(ch, np.roll(prof, tonic))[0, 1]
            scores.append((float(r), NOTE_NAMES[tonic], mode))
    scores.sort(reverse=True)
    best, second = scores[0], scores[1]
    return {"tonic": best[1], "mode": best[2], "score": round(best[0], 3),
            "confidence": round(best[0] - second[0], 3),
            "runner_up": "%s %s" % (second[1], second[2])}


def offbeat_bass_notes(mono, sr, bpm, max_bars=96, lo=30.0, hi=200.0):
    """Bass pitch on each off-beat, where a four-on-the-floor kick has decayed: a short
    window (0.4 beat from the 'and') keeps the kick out, and zero-padding the FFT gives
    the frequency precision a short window lacks (fine for one dominant low partial)."""
    beat = 60.0 / bpm
    n_win = int(0.4 * beat * sr)
    n_fft = 1 << 17
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    sel = (freqs >= lo) & (freqs <= hi)
    win = np.hanning(n_win)
    out = []
    n_beats = min(int(len(mono) / sr / beat) - 1, max_bars * 4)
    for b in range(n_beats):
        a = int((b + 0.5) * beat * sr)
        seg = mono[a:a + n_win]
        if len(seg) < n_win:
            break
        mag = np.abs(np.fft.rfft(seg * win, n=n_fft))[sel]
        if mag.max() < 1e-3 * (np.abs(seg).max() + 1e-9) * n_win:
            out.append(None)
            continue
        f0 = freqs[sel][int(np.argmax(mag))]
        out.append(int(round(69 + 12 * np.log2(f0 / 440.0))))
    return out


def estimate_key_bass_anchored(mono, sr, bpm, max_bars=96):
    """Key for dance music: the tonic is where the bass lives, the mode is which third
    sits above it. Krumhansl profiles were fitted on cadential tonal music and misread
    modal grooves over a pedal (and a kick's tuned fundamental pulls them around), so
    this votes with the bass notes, sampled between beats where the kick has decayed."""
    notes = [n for n in offbeat_bass_notes(mono, sr, bpm, max_bars=max_bars) if n is not None]
    if len(notes) < 8:
        return None
    votes = np.bincount([n % 12 for n in notes], minlength=12).astype(float)
    tonic = int(np.argmax(votes))
    share = votes[tonic] / votes.sum()
    ch = chroma(mono, sr, fmin=130.0)
    minor3, major3 = ch[(tonic + 3) % 12], ch[(tonic + 4) % 12]
    mode = "minor" if minor3 >= major3 else "major"
    return {"tonic": NOTE_NAMES[tonic], "mode": mode, "bass_share": round(float(share), 3),
            "third_ratio": round(float(max(minor3, major3) / (min(minor3, major3) + 1e-9)), 2),
            "confidence": round(float(share * min(1.0, abs(minor3 - major3) /
                                                  (minor3 + major3 + 1e-9) * 2)), 3)}


def onset_envelope(mono, sr, hop=512, n_fft=2048):
    """Spectral flux. Returns (env, fps, offset_s): env[k] belongs to the time
    offset_s + k / fps. A new sound raises a Hann-windowed frame's energy fastest when
    it sits 3/4 of the way into the window, so that is where the onset is placed."""
    win = np.hanning(n_fft)
    prev = None
    env = []
    for i in range(0, max(1, len(mono) - n_fft), hop):
        mag = np.abs(np.fft.rfft(mono[i:i + n_fft] * win))
        if prev is not None:
            env.append(np.maximum(mag - prev, 0).sum())
        prev = mag
    env = np.array(env)
    if env.size and env.max() > 0:
        env = env / env.max()
    return env, sr / float(hop), (hop + 0.75 * n_fft) / float(sr)


def estimate_tempo(mono, sr, lo=90.0, hi=150.0):
    env, fps, _ = onset_envelope(mono, sr)
    if env.size < 16:
        return None
    env = env - env.mean()
    ac = np.correlate(env, env, mode="full")[env.size - 1:]
    best, best_v = None, -1e9
    for bpm in np.arange(lo, hi + 0.01, 0.1):
        lag = 60.0 * fps / bpm
        v = 0.0
        for mult in (1, 2, 4):          # beat, half bar, bar
            l = lag * mult
            i = int(l)
            if i + 1 >= ac.size:
                break
            v += ac[i] + (ac[i + 1] - ac[i]) * (l - i)
        if v > best_v:
            best, best_v = bpm, v
    return round(float(best), 1)


def onsets(mono, sr, threshold=0.25, min_gap_s=0.05):
    env, fps, offset = onset_envelope(mono, sr, hop=128, n_fft=1024)
    out, last = [], -1e9
    for i in range(1, env.size - 1):
        if env[i] > threshold and env[i] >= env[i - 1] and env[i] >= env[i + 1]:
            t = offset + i / fps
            if t - last >= min_gap_s:
                out.append(t)
                last = t
    return out


def estimate_swing(mono, sr, bpm):
    """Median position of off-beat 16ths inside their 8th-note pair, as MPC swing %."""
    pair = 60.0 / bpm / 2.0
    ratios = []
    for t in onsets(mono, sr):
        pos = (t % pair) / pair
        if 0.35 < pos < 0.85:            # off-beat hits only
            ratios.append(pos)
    if len(ratios) < 4:
        return None
    return round(float(np.median(ratios)) * 100.0, 1)


def band_shares(mono, sr):
    spec = np.abs(np.fft.rfft(mono[: min(len(mono), sr * 30)])) ** 2
    f = np.fft.rfftfreq(min(len(mono), sr * 30), 1.0 / sr)
    tot = spec.sum() + 1e-20
    low = spec[f < 150].sum() / tot
    high = spec[f > 5000].sum() / tot
    cent = float((spec * f).sum() / tot)
    return low, high, cent


def bpm_from_name(path):
    m = re.search(r"(?<!\d)(\d{2,3})\s*(?:bpm|BPM)|_(\d{2,3})_", path)
    if not m:
        return None
    v = int(m.group(1) or m.group(2))
    return v if 60 <= v <= 200 else None


def analyze_sample(path, tempo=None, max_seconds=60):
    mono, sr = load_mono(path, max_seconds=max_seconds)
    dur = len(mono) / float(sr)
    low, high, cent = band_shares(mono, sr)
    ch = chroma(mono, sr)
    key = estimate_key(ch)
    tonal = float(np.sort(ch)[-3:].sum())        # energy in the top 3 pitch classes
    ons = onsets(mono, sr)
    named = bpm_from_name(path)
    est = estimate_tempo(mono, sr) if dur > 4 else None
    bpm = tempo or named or est
    bars = dur / (4 * 60.0 / bpm) if bpm else None
    density = len(ons) / bars if bars else None
    if low > 0.6 and density and density >= 3:
        role = "kick" if tonal < 0.55 else "bass"
    elif low > 0.6:
        role = "bass" if tonal >= 0.45 else "sub/808"
    elif high > 0.45 or cent > 5000:
        role = "hats/shaker" if density and density >= 6 else "cymbal/fx"
    elif tonal > 0.45:
        role = "tonal (keys/synth/vocal)"
    else:
        role = "perc/fx"
    swing = estimate_swing(mono, sr, bpm) if bpm and len(ons) >= 8 else None
    return {
        "file": path, "duration_s": round(dur, 3),
        "bpm_from_name": named, "bpm_estimated": est, "bpm_used": bpm,
        "bars": round(bars, 2) if bars else None,
        "loop_bars_guess": (int(round(bars)) if bars and abs(bars - round(bars)) < 0.08
                            and round(bars) in (1, 2, 4, 8, 16) else None),
        "key": key, "tonal_strength": round(tonal, 3),
        "top_pitch_classes": [NOTE_NAMES[i] for i in np.argsort(ch)[::-1][:4]],
        "onsets_per_bar": round(density, 2) if density else None,
        "swing_pct": swing,
        "low_share": round(float(low), 3), "high_share": round(float(high), 3),
        "centroid_hz": round(cent), "role_guess": role,
    }
