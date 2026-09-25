"""Bass transcription from the separated bass stem: notes as MIDI, bar rhythms, and how
the line behaves (register, degrees, note lengths, how it dodges the kick).

Attacks are found on the 16-step grid, like the drums. A note lasts until the next
attack or until it falls 15 dB. Its pitch is the candidate whose harmonics best explain
the spectrum *and* whose fundamental is actually there: without that check the note an
octave below wins, because every harmonic of a tone is also a harmonic of its sub-octave.
"""
import collections

import numpy as np

from . import drums as D
from . import grid as G

NAMES = "C C# D Eb E F F# G Ab A Bb B".split()
DEGREES = ["1", "b2", "2", "b3", "3", "4", "#4", "5", "b6", "6", "b7", "7"]


def note_name(m):
    return "%s%d" % (NAMES[m % 12], m // 12 - 1)


def pitch_of(seg, sr, lo_midi=24, hi_midi=62):
    """(midi, confidence) of a mostly monophonic low tone, or (None, 0)."""
    if len(seg) < int(0.04 * sr):
        return None, 0.0
    n = 1 << 16
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    f = np.fft.rfftfreq(n, 1.0 / sr)
    df = f[1]

    def amp(fr):
        i0, i1 = int(fr * 0.985 / df), int(fr * 1.015 / df) + 1
        return float(spec[i0:i1].max()) if i1 > i0 and i1 < len(spec) else 0.0
    top = float(spec[(f > 25) & (f < 2000)].max()) + 1e-12
    best, best_s = None, 0.0
    for m in range(lo_midi, hi_midi + 1):
        f0 = 440.0 * 2 ** ((m - 69) / 12.0)
        a1 = amp(f0)
        if a1 < 0.12 * top:                    # the fundamental has to be there
            continue
        s = 0.0
        for h in range(1, 7):
            if h * f0 > 2500:
                break
            s += amp(h * f0) / h ** 0.3
            s -= 0.5 * amp((h + 0.5) * f0) / h ** 0.3   # energy between harmonics: wrong f0
        if s > best_s:
            best, best_s = m, s
    return best, round(best_s / top, 2)


def transcribe(bass_stem, sr, g, kick_hits=None, min_rel_db=-30.0):
    y = bass_stem.mean(axis=1) if bass_stem.ndim == 2 else bass_stem
    env, dt, _ = D._env_db(y, sr, 28.0, 400.0, 0.02)
    loud = np.percentile(env, 99.5)
    step_s = g["period"] / 4.0
    half = int(0.45 * step_s / dt)
    flux = np.maximum(np.diff(env, prepend=env[0]), 0.0)
    rw = int(0.05 / dt)
    attacks = []
    for bar in range(g["n_bars"]):
        for st in range(16):
            c = int(G.step_time(g, bar, st) / dt)
            a, b = max(1, c - half), min(len(env) - 1, c + half)
            if b <= a:
                continue
            i = a + int(np.argmax(flux[a:b]))
            pk = i + int(np.argmax(env[i: min(len(env), i + int(0.04 / dt))]))
            v0 = max(0, pk - rw)
            v = v0 + int(np.argmin(env[v0:pk + 1]))
            if env[pk] - env[v] < 5.0 or env[pk] < loud - 35.0:
                continue
            k = v + int(np.argmax(env[v:pk + 1] >= 0.5 * (env[v] + env[pk])))
            attacks.append((bar, st, k * dt, float(env[pk]), pk))
    notes = []
    for n, (bar, st, t, lv, pk) in enumerate(attacks):
        t_next = attacks[n + 1][2] if n + 1 < len(attacks) else len(y) / sr
        tail = env[pk: int(t_next / dt)]
        below = np.nonzero(tail < lv - 15.0)[0]
        t_end = min(t_next, pk * dt + (below[0] * dt if len(below) else len(tail) * dt))
        dur = max(0.03, t_end - t)
        a = int((t + min(0.03, dur * 0.3)) * sr)
        b = int((t + min(dur, 0.25)) * sr)
        m, conf = pitch_of(y[a:b], sr)
        if m is None:
            continue
        rel = lv - loud
        if rel < min_rel_db:
            continue
        notes.append({"bar": bar, "step": st, "offset_ms": round((t - G.step_time(g, bar, st)) * 1000, 1),
                      "pitch": m, "name": note_name(m), "dur_steps": round(dur / step_s, 2),
                      "rel_db": round(rel, 1), "conf": conf})
    notes = _add_sustained(y, sr, g, env, dt, notes, loud)
    return {"notes": notes, **stats(notes, g, kick_hits)}


def _add_sustained(y, sr, g, env, dt, notes, loud, rel_db=-30.0):
    """A pad-like bass or sub pedal fades in without an attack: where the stem sounds
    for a whole beat and no note covers it, read the pitch over that beat and join
    equal neighbours into long notes."""
    covered = set()
    for n in notes:
        start = n["bar"] * 4 + n["step"] / 4.0
        for k in range(int(start), int(np.ceil(start + n["dur_steps"] / 4.0))):
            covered.add(k)
    extra = []
    for k in range(g["n_bars"] * 4):
        if k in covered:
            continue
        t = G.bar_start(g, 0) + k * g["period"]
        a, b = int(t / dt), int((t + g["period"]) / dt)
        if b >= len(env) or np.median(env[a:b]) < loud + rel_db:
            continue
        m, conf = pitch_of(y[int((t + 0.05) * sr): int((t + g["period"] - 0.05) * sr)], sr)
        if m is None:
            continue
        if extra and extra[-1]["pitch"] == m and extra[-1]["_beat_end"] == k:
            extra[-1]["dur_steps"] += 4.0
            extra[-1]["_beat_end"] = k + 1
            continue
        extra.append({"bar": k // 4, "step": (k % 4) * 4, "offset_ms": 0.0, "pitch": m,
                      "name": note_name(m), "dur_steps": 4.0,
                      "rel_db": round(float(np.median(env[a:b]) - loud), 1), "conf": conf,
                      "sustained": True, "_beat_end": k + 1})
    for e in extra:
        e.pop("_beat_end")
    return sorted(notes + extra, key=lambda n: (n["bar"], n["step"]))


def stats(notes, g, kick_hits=None, tonic_pc=None):
    if not notes:
        return {}
    pcs = collections.Counter(n["pitch"] % 12 for n in notes)
    pitches = [n["pitch"] for n in notes]
    out = {"notes_per_bar": round(len(notes) / max(1, len({n["bar"] for n in notes})), 2),
           "register": note_name(int(np.median(pitches))),
           "range": [note_name(min(pitches)), note_name(max(pitches))],
           "pitch_classes": {NAMES[p]: round(c / len(notes), 2) for p, c in pcs.most_common()},
           "median_len_steps": round(float(np.median([n["dur_steps"] for n in notes])), 2),
           "short_share": round(float(np.mean([n["dur_steps"] < 1.0 for n in notes])), 2),
           "long_share": round(float(np.mean([n["dur_steps"] >= 4.0 for n in notes])), 2)}
    steps = collections.Counter(n["step"] for n in notes)
    out["onsets_by_step"] = [steps.get(s, 0) for s in range(16)]
    out["offbeat_share"] = round(sum(c for s, c in steps.items() if s % 4) / len(notes), 2)
    if kick_hits:
        kick = {(h["bar"], h["step"]) for h in kick_hits}
        out["with_kick_share"] = round(float(np.mean([(n["bar"], n["step"]) in kick for n in notes])), 2)
    iv = collections.Counter()
    for a, b in zip(notes, notes[1:]):
        if b["bar"] - a["bar"] <= 1:
            iv[b["pitch"] - a["pitch"]] += 1
    tot = sum(iv.values()) or 1
    out["intervals"] = {str(k): round(v / tot, 2) for k, v in iv.most_common(8)}
    if tonic_pc is not None:
        out["degrees"] = degrees(notes, tonic_pc)
    return out


def degrees(notes, tonic_pc):
    c = collections.Counter(DEGREES[(n["pitch"] - tonic_pc) % 12] for n in notes)
    return {d: round(k / len(notes), 2) for d, k in c.most_common()}


def bar_rhythms(notes):
    """{bar: 16-char onset string, x = attack, - = held from the previous step}."""
    out = collections.defaultdict(lambda: ["."] * 16)
    for n in notes:
        r = out[n["bar"]]
        r[n["step"]] = "x"
        for k in range(1, int(round(n["dur_steps"]))):
            if n["step"] + k < 16 and r[n["step"] + k] == ".":
                r[n["step"] + k] = "-"
    return {b: "".join(r) for b, r in out.items()}


def to_midi_notes(notes, g):
    """[[pitch, start_beat, dur_beats, velocity]] from bar 1, microtiming kept."""
    out = []
    for n in notes:
        start = n["bar"] * 4 + n["step"] / 4.0 + n["offset_ms"] / 1000.0 / g["period"]
        vel = int(np.clip(110 + n["rel_db"] * 2.5, 30, 127))
        out.append([n["pitch"], round(max(0.0, start), 4), round(n["dur_steps"] / 4.0, 4), vel])
    return out
