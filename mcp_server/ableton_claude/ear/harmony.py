"""Chords, key and harmonic rhythm from the separated harmonic stem ("other": pads,
keys, stabs, guitars, leads), anchored by the bass.

Per beat, the pitch-class energy of the harmonic stem is matched against chord
templates (triads, sevenths, sus, add9, ninths); the bass note adds weight to the root
it plays. Chords may only change on beats 1 and 3 and each change costs a little, so a
held Gm7 is not re-read as Bbmaj7 on every beat (Viterbi over beats).
"""
import collections

import numpy as np
from scipy import signal

from . import grid as G

NAMES = "C C# D Eb E F F# G Ab A Bb B".split()
QUALITIES = {  # suffix: (intervals, weights)
    "": ([0, 4, 7], [1, 1, .8]), "m": ([0, 3, 7], [1, 1, .8]),
    "7": ([0, 4, 7, 10], [1, 1, .8, .9]), "maj7": ([0, 4, 7, 11], [1, 1, .8, .9]),
    "m7": ([0, 3, 7, 10], [1, 1, .8, .9]), "sus4": ([0, 5, 7], [1, 1, .8]),
    "sus2": ([0, 2, 7], [1, 1, .8]), "7sus4": ([0, 5, 7, 10], [1, 1, .8, .9]),
    "add9": ([0, 2, 4, 7], [1, .7, 1, .8]), "m9": ([0, 2, 3, 7, 10], [1, .7, 1, .8, .9]),
    "maj9": ([0, 2, 4, 7, 11], [1, .7, 1, .8, .9]), "m6": ([0, 3, 7, 9], [1, 1, .8, .8]),
    "dim": ([0, 3, 6], [1, 1, 1]), "m7b5": ([0, 3, 6, 10], [1, 1, 1, .9]),
    "m11": ([0, 3, 5, 7, 10], [1, 1, .5, .8, .9]),
}
MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
ROMAN = ["I", "bII", "II", "bIII", "III", "IV", "#IV", "V", "bVI", "VI", "bVII", "VII"]


def _templates():
    labels, T, sizes, roots = [], [], [], []
    for root in range(12):
        for q, (iv, w) in QUALITIES.items():
            v = np.zeros(12)
            for i, ww in zip(iv, w):
                v[(root + i) % 12] = ww
            labels.append((root, q))
            T.append(v / np.linalg.norm(v))
            sizes.append(len(iv))
            roots.append(root)
    return labels, np.array(T), np.array(sizes), np.array(roots)


def chroma_per_beat(stem, sr, g, fmin=110.0, fmax=3000.0):
    y = stem.mean(axis=1) if stem.ndim == 2 else stem
    n_fft, hop = 8192, 2048
    f, t, Z = signal.stft(y, sr, nperseg=n_fft, noverlap=n_fft - hop, boundary=None, padded=False)
    mag = np.sqrt(np.abs(Z))                                # compress: several notes count
    sel = (f >= fmin) & (f <= fmax)
    pcs = (np.round(69 + 12 * np.log2(f[sel] / 440.0)).astype(int)) % 12
    M = np.zeros((12, mag.shape[1]))
    for p in range(12):
        M[p] = mag[sel][pcs == p].sum(axis=0)
    n_beats = g["n_bars"] * 4
    out = np.zeros((n_beats, 12))
    energy = np.zeros(n_beats)
    for k in range(n_beats):
        a = G.bar_start(g, 0) + k * g["period"]
        m = (t >= a) & (t < a + g["period"])
        if m.any():
            out[k] = M[:, m].mean(axis=1)
            energy[k] = out[k].sum()
    norm = np.linalg.norm(out, axis=1, keepdims=True) + 1e-12
    return out / norm, energy


def recognize(chroma, energy, bass_pc=None, change_penalty=0.35, silent_rel=0.02):
    """Per-beat chord labels via Viterbi. bass_pc: per-beat bass pitch class or None."""
    labels, T, sizes, roots = _templates()
    n = len(chroma)
    em = chroma @ T.T                                          # cosine similarity
    em -= 0.03 * (sizes - 3)[None, :]                          # richer chords must earn it
    if bass_pc is not None:
        for k in range(n):
            if bass_pc[k] is None:
                continue
            em[k, roots == bass_pc[k]] += 0.2
            for j, (r, q) in enumerate(labels):
                if r != bass_pc[k] and (bass_pc[k] - r) % 12 in QUALITIES[q][0]:
                    em[k, j] += 0.04
    silent = energy < silent_rel * (np.percentile(energy, 95) + 1e-12)
    S = len(labels)
    score = em[0].copy()
    back = np.zeros((n, S), dtype=np.int32)
    for k in range(1, n):
        best_prev = int(np.argmax(score))
        stay = score
        if k % 2 == 0:                                         # beats 1 and 3 may change
            move = score[best_prev] - change_penalty
            choose_move = move > stay
            back[k] = np.where(choose_move, best_prev, np.arange(S))
            score = np.maximum(stay, move) + em[k]
        else:
            back[k] = np.arange(S)
            score = stay + em[k]
    path = np.zeros(n, dtype=np.int32)
    path[-1] = int(np.argmax(score))
    for k in range(n - 1, 0, -1):
        path[k - 1] = back[k, path[k]]
    out = []
    for k in range(n):
        if silent[k]:
            out.append(None)
            continue
        r, q = labels[path[k]]
        top2 = np.sort(em[k])[-2:]
        out.append({"root": int(r), "quality": q, "label": NAMES[r] + q,
                    "fit": round(float(em[k, path[k]]), 3), "margin": round(float(top2[1] - top2[0]), 3)})
    return out


def segments(per_beat):
    """Merge equal consecutive beats: [{start_beat, beats, label, root, quality}]."""
    segs = []
    for k, c in enumerate(per_beat):
        lab = c["label"] if c else "N"
        if segs and segs[-1]["label"] == lab:
            segs[-1]["beats"] += 1
        else:
            segs.append({"start_beat": k, "beats": 1, "label": lab,
                         "root": c["root"] if c else None, "quality": c["quality"] if c else None})
    return segs


def key_of(segs, bass_notes=None):
    """Key from chord tones weighted by duration plus the bass's pitch classes
    (Krumhansl-Schmuckler profiles). Returns (tonic_pc, mode, confidence)."""
    prof = np.zeros(12)
    for s in segs:
        if s["root"] is None:
            continue
        for i, w in zip(*QUALITIES[s["quality"]]):
            prof[(s["root"] + i) % 12] += w * s["beats"]
    if bass_notes:
        for n in bass_notes:
            prof[n["pitch"] % 12] += 2.0 * max(0.25, n["dur_steps"]) / 4.0
    if prof.sum() == 0:
        return None, None, 0.0
    best = []
    for tonic in range(12):
        for mode, p in (("major", MAJOR), ("minor", MINOR)):
            best.append((np.corrcoef(prof, np.roll(p, tonic))[0, 1], tonic, mode))
    best.sort(reverse=True)
    return best[0][1], best[0][2], round(float(best[0][0] - best[1][0]), 3)


def roman(root, quality, tonic, mode):
    iv = (root - tonic) % 12
    num = ROMAN[iv]
    minorish = quality.startswith("m") and not quality.startswith("maj") or quality in ("dim", "m7b5")
    if minorish:
        num = num.lower()
    suffix = quality[1:] if quality.startswith("m") and not quality.startswith("maj") else quality
    if mode == "minor":                     # write minor-key numerals relative to i
        num = num.replace("bIII", "III").replace("biii", "iii").replace("bVI", "VI") \
            .replace("bvi", "vi").replace("bVII", "VII").replace("bvii", "vii")
    return num + ("" if suffix in ("", "m") else suffix)


def bar_chords(per_beat, n_bars):
    """The chord on beat 1 of each bar (and on beat 3 if it differs)."""
    out = []
    for b in range(n_bars):
        c1 = per_beat[b * 4] if b * 4 < len(per_beat) else None
        c3 = per_beat[b * 4 + 2] if b * 4 + 2 < len(per_beat) else None
        l1 = c1["label"] if c1 else "N"
        l3 = c3["label"] if c3 else "N"
        out.append(l1 if l1 == l3 else "%s %s" % (l1, l3))
    return out


def loops(bar_labels, min_repeat=2):
    """Most common repeating chord cycles (2, 4 or 8 bars): [(cycle, count)]."""
    found = collections.Counter()
    for size in (2, 4, 8):
        for s in range(0, len(bar_labels) - size + 1, size):
            cyc = tuple(bar_labels[s:s + size])
            if "N" in cyc:
                continue
            found[cyc] += 1
    return [(" | ".join(c), n) for c, n in found.most_common(6) if n >= min_repeat]


def analyze(other_stem, sr, g, bass_notes=None):
    chroma, energy = chroma_per_beat(other_stem, sr, g)
    bass_pc = [None] * len(chroma)
    if bass_notes:                          # the bass note sounding in each beat
        for n in bass_notes:
            start = n["bar"] * 4 + n["step"] / 4.0
            end = start + max(0.25, n["dur_steps"] / 4.0)
            for k in range(int(np.floor(start)), int(np.ceil(end))):
                if 0 <= k < len(bass_pc) and bass_pc[k] is None and min(end, k + 1) - max(start, k) >= 0.25:
                    bass_pc[k] = n["pitch"] % 12
    # Over a pedal (a bass note held for 2+ bars) the upper chords move while the root
    # stays: read the chord without the bass there and write it as a slash chord.
    pedal = [False] * len(chroma)
    if bass_notes:
        for n in bass_notes:
            if n["dur_steps"] >= 32:
                start = n["bar"] * 4 + n["step"] // 4
                for k in range(start, min(len(pedal), start + int(n["dur_steps"] // 4))):
                    pedal[k] = True
    full = recognize(chroma, energy, bass_pc)
    if any(pedal):
        upper = recognize(chroma, energy, None)
        per_beat = []
        for k, (f_, u) in enumerate(zip(full, upper)):
            if pedal[k] and u and bass_pc[k] is not None and u["root"] != bass_pc[k]:
                u = dict(u, label="%s/%s" % (u["label"], NAMES[bass_pc[k]]), bass=bass_pc[k])
                per_beat.append(u)
            else:
                per_beat.append(f_)
    else:
        per_beat = full
    segs = segments(per_beat)
    tonic, mode, conf = key_of(segs, bass_notes)
    bars = bar_chords(per_beat, g["n_bars"])
    for s in segs:
        if s["root"] is not None and tonic is not None:
            s["roman"] = roman(s["root"], s["quality"], tonic, mode)
    held = [s["beats"] for s in segs if s["root"] is not None]
    changes = sum(1 for a, b in zip(bars, bars[1:]) if a != b and "N" not in (a, b))
    playing = sum(1 for b in bars if b != "N")
    return {"key": ("%s %s" % (NAMES[tonic], mode)) if tonic is not None else None,
            "tonic_pc": tonic, "mode": mode, "key_confidence": conf,
            "segments": segs, "bars": bars,
            "changes_per_8_bars": round(8.0 * changes / max(1, playing), 2),
            "median_chord_beats": float(np.median(held)) if held else None,
            "qualities": dict(collections.Counter(s["quality"] or "N" for s in segs if s["root"] is not None).most_common()),
            "loops": loops(bars)}
