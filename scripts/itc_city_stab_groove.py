"""In the City: the City stab comp given groove, still an accompaniment.

His note (2026-11-05, ~22:50): "o stab agora tá um pouco quadrado e sem groove, falta um pouco mais de movimento ali
depois da intro". The comp (itc_city_comp.py) played every hit at velocity 90, 0.23 beat long, on 0.5/2.5 only.
Now, same chords and the same place in the bar (it stays the marking, not a line):
- the off-beat 0.5 accented, 2.5 a little lighter; a ghost a 16th after the accent (0.75) and one at 2.75;
- every 2nd bar a soft push at 3.25, every 4th bar a pickup 3.5-3.75 into the next phrase;
- under a voice: 0.5 and one ghost (2.75);
- velocities and lengths vary by a fixed pattern (+-5, 0.18-0.26 beat), so no two bars of a 4-bar group are equal;
- the slow filter LFO deeper (12 -> 22 %) for movement over the phrases.
Left as they are: the builds (57-64, 113-120: he rejected motion there) and every bar where a hit would land
within a 16th of a guitar note (his ping-pong answers keep their place).
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_claude import client
from itc_city_bass_lock import BUS, STABS, GTR, bass, pocket, root_at
from itc_city_bounce import voiced_bars

C = client.call
FIXED = {4: [66, 67, 71, 74], 9: [64, 67, 71, 72], 11: [64, 66, 69, 71]}
SECTIONS = [(29, 57), (65, 97), (121, 169)]          # after the intro, drop 1, drop 2 (not the builds)
HUMAN_V = [0, 4, -3, 2, -5, 3, -1, 5]
HUMAN_L = [0.23, 0.21, 0.25, 0.20, 0.24, 0.22, 0.26, 0.19]


def bar_hits(bar, voiced):
    k = (bar - 1) % 4
    if voiced:
        return [(0.5, 100, 0), (2.75, 60, 1)]
    hits = [(0.5, 104, 0), (0.75, 62, 1), (2.5, 92, 0), (2.75, 58, 1)]
    if k % 2 == 1:
        hits.append((3.25, 74, 1))
    if k == 3:
        hits += [(3.5, 70, 1), (3.75, 80, 1)]
    return hits


def guitar_onsets():
    out = []
    for cl in C('get_track', {'track': GTR, 'clips': True})['clips']:
        if cl.get('muted'):
            continue
        info = C('set_clip', {'track': GTR, 'clip': cl['i'], 'name': cl['name']})
        sm = info.get('start_marker') or 0.0
        le = info.get('loop_end')
        for p, b, d, v in C('get_notes', {'track': GTR, 'clip': cl['i']}):
            if b < sm - 1e-6 or (le is not None and b >= le - 1e-6):
                continue
            s = cl['start'] + b - sm
            if cl['start'] - 1e-6 <= s < cl['end'] - 1e-6:
                out.append(s)
    return sorted(out)


def write():
    notes_b = bass()
    voiced = voiced_bars()
    gtr = guitar_onsets()
    clips = C('get_track', {'track': STABS, 'clips': True})['clips']
    changed = 0
    for cl in clips:
        a_bar, z_bar = int(cl['start'] // 4) + 1, int(round(cl['end'] / 4)) + 1
        if not any(sa <= a_bar < sz for sa, sz in SECTIONS):
            continue
        notes = []
        for bar in range(a_bar, z_bar):
            b0 = (bar - 1) * 4.0
            if b0 >= cl['end'] - 1e-6:
                break
            for j, (h, vel, ghost) in enumerate(bar_hits(bar, int(b0 // 4) in voiced)):
                s = b0 + pocket(h)
                if s >= cl['end'] - 1e-6 or any(abs(s - g) < 0.15 for g in gtr):
                    continue
                chord = FIXED.get(root_at(notes_b, s), FIXED[4])
                if ghost:
                    chord = chord[1:]                   # ghosts lighter: drop the bottom voice
                i = (bar * 3 + j) % 8
                v = max(40, min(112, vel + HUMAN_V[i]))
                d = 0.12 if ghost else HUMAN_L[i]
                notes += [[p, s - cl['start'], min(d, cl['end'] - s), float(v)] for p in chord]
        C('add_notes', {'track': STABS, 'clip': cl['i'], 'notes': notes, 'replace': True})
        changed += 1
    print('stab clips regrooved', changed)


def movement():
    C('set_param', {'track': STABS, 'device': 'Auto Filter', 'param': 'LFO Amount', 'display': '22 %'})


if __name__ == '__main__':
    steps = {'write': write, 'movement': movement}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
