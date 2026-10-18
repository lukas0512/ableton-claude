"""Drum grooves: step patterns with swing, accents and humanisation; build-up rolls.

Notes are [pitch, start_beat, duration_beats, velocity], start relative to the clip.
Swing follows the MPC convention on 16ths: 50 = straight, 66 = triplet feel; the
off-beat 16th of each pair is pushed to swing% of the pair's length.
"""
import random

# Live's default Drum Rack layout (C1 = 36 on the first pad)
DRUMS = {"kick": 36, "rim": 37, "snare": 38, "clap": 39, "closed_hat": 42,
         "pedal_hat": 44, "open_hat": 46, "tom_low": 45, "tom_mid": 47, "tom_high": 50,
         "crash": 49, "ride": 51, "shaker": 70, "perc": 67}

# 16-step patterns per bar. x = hit, X = accent, g = ghost, . = rest.
DEEP_HOUSE = {
    "kick":       "X...X...X...X...",
    "clap":       "....X.......X...",
    "closed_hat": "..x...x...x...x.",
    "shaker":     "gxgxgxgXgxgxgxgX",
    "open_hat":   "..x...x...x...x.",
    "rim":        "...g..x....g.x..",
}

# Starting points, not claims about current releases. Reference templates take priority.
TECH_HOUSE = {
    "kick":       "X...X...X...X...",
    "clap":       "....X.......X...",
    "closed_hat": "x.g.xgx.x.g.xgxg",
    "open_hat":   "..x...x...x...x.",
    "shaker":     ".g.x.g.x.g.x.g.x",
    "rim":        "...g..x....g..x.",
}

_VEL = {"X": 115, "x": 95, "g": 55}


def swing_offset(step, swing):
    """Beats to delay 16th number `step` (0-based) for a swing percentage."""
    if step % 2 == 0:
        return 0.0
    return (swing / 100.0 - 0.5) * 0.5


def steps_to_notes(pattern, pitch, bars=1, swing=54.0, humanize=0.0, seed=0,
                   vel_scale=1.0, length=0.1):
    """Turn a 16-step string (or a multiple of 16 for multi-bar patterns) into notes."""
    rng = random.Random(seed)
    per_bar = len(pattern)
    if per_bar % 16:
        raise ValueError("pattern length must be a multiple of 16")
    notes = []
    for bar in range(bars):
        for i, ch in enumerate(pattern):
            if ch not in _VEL:
                continue
            step = i % 16
            beat = bar * (per_bar / 4.0) + i * 0.25 + swing_offset(step, swing)
            if humanize:
                beat += rng.uniform(-humanize, humanize)
            vel = _VEL[ch] * vel_scale + (rng.uniform(-6, 6) if humanize else 0)
            notes.append([pitch, round(max(0.0, beat), 4), length,
                          int(max(1, min(127, vel)))])
    return notes


def pattern(style="deep_house", bars=1, swing=54.0, humanize=0.004, seed=0, parts=None):
    """Full kit pattern. Returns {part: notes}."""
    if not isinstance(bars, int) or not 1 <= bars <= 128:
        raise ValueError("bars must be an integer from 1 to 128")
    if not 50 <= swing <= 75:
        raise ValueError("swing must be from 50 to 75 percent")
    tables = {"deep_house": DEEP_HOUSE, "tech_house": TECH_HOUSE}
    style = style.strip().lower().replace(" ", "_")
    if style not in tables:
        raise ValueError("style must be deep_house or tech_house")
    table = tables[style]
    out = {}
    for k, (name, steps) in enumerate(table.items()):
        if parts and name not in parts:
            continue
        out[name] = steps_to_notes(steps, DRUMS[name], bars, swing, humanize, seed + k)
    return out


def build_roll(bars=8, pitch=DRUMS["clap"], vel_from=55, vel_to=127, gap_last_beat=True):
    """Classic build: quarters, then 8ths, 16ths, and 32nds in the final bar, with a
    velocity ramp. The last beat stays empty so the drop lands on silence."""
    plan = []
    quarter = max(1, bars // 4)
    for b in range(bars):
        if b < quarter:
            div = 1
        elif b < 2 * quarter:
            div = 2
        elif b < bars - 1:
            div = 4
        else:
            div = 8
        plan.append(div)
    total = bars * 4.0
    notes = []
    for b, div in enumerate(plan):
        step = 1.0 / div
        t = b * 4.0
        while t < (b + 1) * 4.0 - 1e-9:
            if gap_last_beat and t >= total - 1.0:
                break
            f = t / total
            vel = vel_from + (vel_to - vel_from) * f
            notes.append([pitch, round(t, 4), round(step * 0.9, 4), int(round(vel))])
            t += step
    return notes


def fill(kind="tom_run", pitch_map=None, start=12.0, length=4.0):
    """One-beat or one-bar fills placed at `start` beats into the bar."""
    pm = pitch_map or DRUMS
    if kind == "tom_run":
        seq = ["tom_high", "tom_high", "tom_mid", "tom_mid", "tom_low", "tom_low", "tom_low",
               "tom_low"]
        step = length / len(seq)
        return [[pm[p], round(start + i * step, 4), round(step * 0.9, 4), 90 + i * 4]
                for i, p in enumerate(seq)]
    raise ValueError("unknown fill %r" % kind)
