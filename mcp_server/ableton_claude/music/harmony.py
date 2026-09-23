"""Progressions to MIDI: voice-led chord parts with optional anticipation."""
from .theory import voice_lead


def progression_notes(chords, bars_per_chord=2, low=53, high=77, voices=4, anticipate=0.5,
                      velocity=88, beats_per_bar=4.0, legato=0.98, hold_last_bars=0):
    """Sustained chord part. Each change lands `anticipate` beats early (0.5 = the "and"
    of 4, a house staple). hold_last_bars extends the final chord. Returns
    (notes, voicings) with notes as [pitch, start, duration, velocity]."""
    voicings = voice_lead(chords, low=low, high=high, voices=voices)
    span = bars_per_chord * beats_per_bar
    n = len(voicings)
    notes = []
    for i, v in enumerate(voicings):
        start = i * span - (anticipate if i > 0 else 0.0)
        end = (i + 1) * span - (anticipate if i < n - 1 else 0.0)
        if i == n - 1:
            end += hold_last_bars * beats_per_bar
        for p in v:
            notes.append([p, round(start, 4), round((end - start) * legato, 4), velocity])
    return notes, voicings


def swing(notes, pct):
    """Push notes sitting on off-beat 16ths to `pct` swing (MPC convention)."""
    out = []
    for p, t, d, v in notes:
        step = t * 4.0
        if abs(step - round(step)) < 1e-6 and int(round(step)) % 2 == 1:
            t = t + (pct / 100.0 - 0.5) * 0.5
        out.append([p, round(t, 4), d, v])
    return out
