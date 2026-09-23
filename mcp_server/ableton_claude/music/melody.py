"""Melody generation built on call and response.

A call rises and ends on an unstable degree (a question); the response echoes the
call's opening rhythm (that is what makes it sound like an answer to *that* call),
falls, and resolves on the tonic or the third. Strong beats land on chord tones,
weak positions carry scale passing tones, and leaps are recovered by step.
"""
import random

from .theory import Scale, chord_pcs, note_name

# onsets in 16th steps inside a half bar (8 steps = 2 beats)
BUSY_CELLS = [(0, 3, 6), (0, 2, 4, 6), (0, 3, 5), (2, 4, 6), (0, 3), (3, 6), (0, 2, 6)]
SPARSE_CELLS = [(0,), (0, 6), (2,), (0, 4), (3,)]

OPEN_DEGREES = (2, 4, 5, 7)     # endings that ask
CLOSED_DEGREES = (1, 3)         # endings that answer

# degree by interval above the tonic, so gapped scales (pentatonic, hexatonic) keep
# the usual names: F in G minor hexatonic is still the 7th, not the "6th note"
_INTERVAL_DEGREE = {0: 1, 1: 2, 2: 2, 3: 3, 4: 3, 5: 4, 6: 5, 7: 5, 8: 6, 9: 6, 10: 7, 11: 7}


def degree(scale, pitch):
    return _INTERVAL_DEGREE[(pitch - scale.tonic) % 12]


def _rhythm(rng, halves, echo=None):
    """Onset steps for a phrase of `halves` half-bars; the final half holds one long
    note on its downbeat. `echo` reuses a call's opening cells."""
    cells = []
    for h in range(halves - 1):
        if echo is not None and h < 2:
            cells.append(echo[h])
        elif h == halves - 2:
            cells.append(rng.choice(SPARSE_CELLS + BUSY_CELLS[:3]))
        else:
            cells.append(rng.choice(BUSY_CELLS))
    cells.append((0,))
    steps = []
    for h, cell in enumerate(cells):
        steps.extend(h * 8 + s for s in cell)
    return steps, cells


def _pick(rng, cands, prev, target, prev_leap, before=None):
    """Choose the candidate that best follows the contour, favouring steps and
    recovering after leaps; ties are broken by the seeded rng. `before` is the note
    two back: returning to it right away (A-Bb-A-Bb) sounds stuck, so it costs extra."""
    scored = []
    for c in cands:
        iv = c - prev
        cost = abs(iv) * 1.0 + abs(c - target) * 0.6
        if abs(iv) > 7 and abs(iv) != 12:
            cost += 30
        if prev_leap >= 5 and iv >= 0:
            cost += 6            # after a leap up, step back down
        if prev_leap <= -5 and iv <= 0:
            cost += 6
        if iv == 0:
            cost += 2.5          # avoid static lines
        if before is not None and c == before and iv != 0:
            cost += 3.0          # avoid ping-pong between two notes
        scored.append((cost + rng.random() * 0.8, c))
    return min(scored)[1]


def _leap_target(tones, prev, low, high, rising):
    """A chord tone a 4th to a 5th away in the phrase's direction (the opening leap of a
    gap-fill figure), or None."""
    sign = 1 if rising else -1
    cands = [prev + sign * d for d in (7, 5, 6)
             if low <= prev + sign * d <= high and (prev + sign * d) % 12 in tones]
    return cands[0] if cands else None


def _phrase(scale, chords_by_bar, steps, start_pitch, low, high, rng, rising, ending,
            leap_first=True):
    notes = []
    prev = start_pitch
    prev_leap = 0
    n = len(steps)
    peak = min(high, start_pitch + 9) if rising else max(low, start_pitch - 9)
    for k, st in enumerate(steps):
        bar = st // 16
        chord = chords_by_bar[min(bar, len(chords_by_bar) - 1)]
        tones = chord_pcs(chord)
        strong = st % 8 == 0 or k == 0
        last = k == n - 1
        target = start_pitch + (peak - start_pitch) * (k / max(1, n - 1)) if k < n - 1 else (
            start_pitch if not rising else peak)
        if last:
            wanted = [p for p in range(low, high + 1) if p % 12 in tones
                      and degree(scale, p) in ending]
            if not wanted:
                wanted = [p for p in range(low, high + 1) if p % 12 in tones]
            pitch = min(wanted, key=lambda p: (abs(p - prev), p))
        elif k == 0:
            pitch = start_pitch
        elif k == 1 and leap_first and _leap_target(tones, prev, low, high, rising):
            # gap-fill: open with a leap, then the prev_leap rule steps back into the gap
            pitch = _leap_target(tones, prev, low, high, rising)
        else:
            if strong:
                cands = [p for p in range(low, high + 1) if p % 12 in tones]
            else:
                cands = [scale.step(prev, d) for d in (-2, -1, 1, 2)]
                cands = [p for p in cands if low <= p <= high]
            before = notes[-2][0] if len(notes) >= 2 else None
            pitch = _pick(rng, cands, prev, target, prev_leap, before)
        prev_leap = pitch - prev if k else 0
        notes.append([pitch, st * 0.25])
        prev = pitch
    return notes


def _durations(notes, phrase_beats, legato=0.9, max_len=1.5, last_len=1.75):
    out = []
    for i, (p, t) in enumerate(notes):
        if i + 1 < len(notes):
            d = min(max_len, (notes[i + 1][1] - t) * legato)
        else:
            d = min(last_len, phrase_beats - t - 0.25)
        out.append([p, t, round(max(0.125, d), 4)])
    return out


def call_and_response(tonic="G", mode="minor", chords=("Gm7", "Gm7", "Bbmaj7", "Bbmaj7"),
                      phrase_bars=2, call_range=(62, 79), response_range=(55, 74),
                      seed=7):
    """Generate a call (first half of `chords`) and its response (second half).

    chords: one chord symbol per bar, len = 2 * phrase_bars.
    Returns {"call": notes, "response": notes, "call_ends": degree, ...}; notes are
    [pitch, start_beat, duration, velocity] relative to each phrase's own start.
    """
    if len(chords) != 2 * phrase_bars:
        raise ValueError("need %d chords (one per bar)" % (2 * phrase_bars))
    scale = Scale(tonic, mode)
    rng = random.Random(seed)
    halves = phrase_bars * 2
    beats = phrase_bars * 4.0

    call_chords = list(chords[:phrase_bars])
    resp_chords = list(chords[phrase_bars:])

    call_steps, call_cells = _rhythm(rng, halves)
    lo, hi = call_range
    first_tones = chord_pcs(call_chords[0])
    start = min((p for p in range(lo, hi + 1) if p % 12 in first_tones),
                key=lambda p: abs(p - (lo + (hi - lo) * 0.35)))
    call = _phrase(scale, call_chords, call_steps, start, lo, hi, rng, True, OPEN_DEGREES)

    resp_steps, _ = _rhythm(rng, halves, echo=call_cells)
    lo, hi = response_range
    r_tones = chord_pcs(resp_chords[0])
    r_start = min((p for p in range(lo, hi + 1) if p % 12 in r_tones),
                  key=lambda p: abs(p - (call[0][0] - 5)))
    resp = _phrase(scale, resp_chords, resp_steps, r_start, lo, hi, rng, False,
                   CLOSED_DEGREES)

    def finish(ph):
        out = []
        for i, (p, t, d) in enumerate(_durations(ph, beats)):
            strong = (t * 4) % 8 == 0
            vel = (106 if strong else 88) + rng.randint(-5, 5)
            if i == len(ph) - 1:
                vel = 100
            out.append([p, t, d, vel])
        return out

    call_n, resp_n = finish(call), finish(resp)
    return {
        "call": call_n,
        "response": resp_n,
        "call_ends_on_degree": degree(scale, call_n[-1][0]),
        "response_ends_on_degree": degree(scale, resp_n[-1][0]),
        "call_names": [note_name(n[0]) for n in call_n],
        "response_names": [note_name(n[0]) for n in resp_n],
    }


def shift(notes, beats):
    return [[p, round(t + beats, 4), d, v] for p, t, d, v in notes]


def audit(notes, scale, chords_by_bar, bar_beats=4.0):
    """Check a line against the rules it was built with. Returns a list of problems."""
    problems = []
    for i, (p, t, d, v) in enumerate(notes):
        if not scale.contains(p):
            problems.append("%s at beat %.2f is outside %s" % (note_name(p), t, scale))
        chord = chords_by_bar[min(int(t // bar_beats), len(chords_by_bar) - 1)]
        if (t * 4) % 8 == 0 and p % 12 not in chord_pcs(chord):
            problems.append("%s on strong beat %.2f is not in %s" % (note_name(p), t, chord))
        if i and abs(p - notes[i - 1][0]) > 7 and abs(p - notes[i - 1][0]) != 12:
            problems.append("leap of %d semitones at beat %.2f" % (p - notes[i - 1][0], t))
    return problems
