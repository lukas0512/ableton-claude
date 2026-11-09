"""Let The Rhythm v8: the main-break EP solo, built on the vocal's theme and played by hand.

The vocal hook "lift your hands" sings C#5 - A4 - F#4 (5-3-1 of F#m, pitch-tracked from the
loop at the set's +1 st). The solo states that theme alone like a voice, answers it, harmonises
it in thirds, lifts it an octave and falls into the tension; in the tension it calls and
answers before the vocal enters (105-108) and then compresses to every half bar up high
(113-116) into the drop's stab pickup. Under it the comp keeps the bass's hits
(.75 / 2.75 / 3.5; F#m - E | A - E F#m).

Humanised: lay-back on strong beats, pushes early, +-6 ms scatter, velocity and length
variation, half-step grace notes, ghost repeats, double stops rolled low to high.
"""
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import server

RNG = np.random.default_rng(127)
F, E, A = [54, 57, 61], [56, 59, 64], [57, 61, 64]
COMP = [(0.75, F), (2.75, E), (3.5, E), (4.75, A), (6.75, E), (7.5, F)]


def comp(cycles, vel):
    out = []
    for c in range(cycles):
        v = vel(c)
        for b, ch in COMP:
            for k, p in enumerate(ch):
                t = c * 8 + b + .006 * k + RNG.normal(0, .006)
                out.append([p, round(t, 4), round(.2 + RNG.uniform(-.03, .04), 3),
                            int(np.clip(v + 4 * (k == 0) + RNG.integers(-4, 5), 1, 127))])
    return out


def play(phrase):
    """phrase: (beat, pitch | [pitches], length, velocity, flags). flags: g = grace below."""
    out = []
    for b, p, d, v, *fl in phrase:
        fl = fl[0] if fl else ''
        frac = b % 1
        shift = .012 if frac == 0 else (-.014 if frac in (.75, .25) else 0)
        t0 = b + shift + RNG.normal(0, .012)
        ps = p if isinstance(p, list) else [p]
        for k, q in enumerate(sorted(ps)):
            vel = int(np.clip(v - 8 * (k < len(ps) - 1) + RNG.integers(-6, 7), 1, 127))
            out.append([q, round(t0 + .014 * k, 4), round(d * RNG.uniform(.85, 1.08), 3), vel])
        if 'g' in fl:
            top = max(ps)
            out.append([top - 1, round(t0 - .07, 4), .06, max(1, v - 28)])
        if 'h' in fl:      # ghost repeat on the next 16th
            out.append([max(ps), round(t0 + .25 + RNG.normal(0, .01), 4), .1, max(1, v - 40)])
    return out


THEME = [(0, 73), (.5, 69), (1.25, 66)]


def solo():
    """Main break 97-104 (clip at beat 384, 32 beats)."""
    s = [  # 1-2: the theme alone, like the voice, then its echo
        (1.0, 73, .4, 84), (1.5, 69, .55, 78), (2.25, 66, 1.4, 86, 'g'),
        (4.75, 73, .3, 80), (5.25, 71, .25, 70), (5.5, 69, .5, 76), (6.25, 66, 1.1, 82, 'h'),
        # 3-4: the theme in thirds on the comp's push, then a turn up and back
        (9.0, [73, 76], .4, 90), (9.5, [69, 73], .5, 84), (10.25, [66, 69], 1.2, 90, 'g'),
        (11.75, 71, .2, 72), (12.0, 73, .25, 80), (12.75, 76, .5, 90), (13.5, 78, .25, 84),
        (13.75, 76, .3, 80), (14.25, 73, 1.5, 88, 'g'),
        # 5-6: an octave up, answered on the comp's hits
        (17.0, 85, .4, 98), (17.5, 81, .5, 90), (18.25, 78, .9, 94, 'g'),
        (19.5, 76, .2, 74), (19.75, 78, .25, 70), (20.75, 81, .5, 92), (21.5, 80, .2, 72),
        (21.75, 78, .25, 84), (22.25, 76, .3, 82), (22.75, 73, 1.0, 88, 'h'),
        # 7-8: the comp's rhythm climbing, the theme falling from the top into the tension
        (24.75, 73, .25, 84), (26.75, 76, .25, 88), (27.5, 78, .4, 92), (28.75, 81, .5, 98),
        (29.5, [81, 85], .45, 106), (30.0, [78, 81], .5, 98), (30.75, [73, 78], 1.2, 100, 'g'),
    ]
    return play(s) + comp(4, lambda c: 42 + 4 * c)


def tension_lead():
    """Tension 105-116 (clip at beat 416, 48 beats): added over its own crescendo comp."""
    s = [  # 105-108: call and answer before the vocal comes in at 109
        (1.0, 73, .4, 86), (1.5, 69, .5, 80), (2.25, 66, 1.2, 88, 'g'),
        (4.75, 76, .3, 84), (5.25, 73, .3, 78), (6.0, 69, 1.2, 84, 'h'),
        (9.0, 73, .4, 90), (9.5, 69, .5, 84), (10.25, 66, 1.0, 90, 'g'),
        (12.75, 78, .3, 90), (13.25, 76, .3, 86), (13.5, 73, .25, 82), (14.0, 69, 1.4, 90),
    ]
    # 113-115.5: the theme every half bar, an octave up, rising in force; 116 left to the stab
    for k in range(6):
        b = 32 + 2 * k
        s += [(b, 85, .2, 84 + 4 * k), (b + .5, 81, .2, 80 + 4 * k), (b + 1.25, 78, .45, 86 + 4 * k)]
    return play(s)


if __name__ == '__main__':
    print(server._journaled('add_notes', dict(track='EP KEYS', clip={'at': 384}, replace=True,
                                              notes=solo())))
    print(server._journaled('add_notes', dict(track='EP KEYS', clip={'at': 416}, replace=False,
                                              notes=tension_lead())))
