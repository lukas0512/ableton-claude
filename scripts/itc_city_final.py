"""In the City: his drop-2 ping-pong spread through the song, build 2's stab given motion.

He edited drop 2 by hand (2026-11-05, ~21:50) and kept it: "ajustei no segundo drop de um jeito que gostei mais ...
uma variação no começo, depois essa mais bounce, um fala, outro responde, um ping-pong ... a melodia final fica essa
do drop 2, tanto da guitarra quanto do stab ... espalhar esse riff ... o stab no build pode dar uma mexida".

What he built (read from the clips, start markers applied), bars 97-131:
- PING-PONG (drop 2, 119-130): the stab marks the "and" of 1 (its comp, itc_city_comp.py); the guitar answers on
  1.75-2.0 every bar: G4-E4 on the E bar (odd bars), D4-E4 on the A/B bar (even bars), under the voice too.
- VARIATION (break 2 97-104, build 2 113-116): E4 on 3.5 with a ghost D4 a 16th later, then E4 alone on 3.5.
Kept untouched: every guitar clip from bar 97 to 131. Written here:
- drop 1 (65-96) and the rest of drop 2 (131-168): the ping-pong;
- build 1 (57-64): his build-2 shape mirrored (variation, two bars of rest, the ping-pong going in);
- build 2's stab (113-120): from one B7sus4 on 0.5/2.5 to motion: 8ths from 115, 16th pushes from 119, the top voice
  climbing B4 -> C#5 -> D#5 (B7) so it leans into the drop's E.
  REJECTED the same night ("não gostei dessa subida do stab no build 2"): restored from the backup JSON; do not run
  the build2 step.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_claude import client
from itc_city_bass_lock import STABS, GTR, pocket

C = client.call
PING = {0: [(1.75, 67, .25, 100), (2.0, 64, .25, 90)],     # E bar
        1: [(1.75, 62, .25, 98), (2.0, 64, .30, 96)]}      # A/B bar
VAR = {0: [(3.5, 64, .30, 104), (3.75, 62, .12, 74)], 1: [(3.5, 64, .30, 100)]}
DROP1, DROP2_REST, BUILD1 = (65, 97), (131, 169), (57, 65)


def bar_notes(bar, kind):
    phase = 0 if bar % 2 == 1 else 1          # odd bars carry the E (65, 121 ...)
    src = PING if kind == 'ping' else VAR
    return [[p, pocket(b), d, float(v)] for b, p, d, v in src[phase]]


def build1_kind(bar):
    # his build 2 (113-120): var 113-116, rest 117-118, ping 119-120 -> build 1 (57-64)
    k = bar - 57
    return 'var' if k < 4 else (None if k < 6 else 'ping')


def clear(track, a_bar, z_bar):
    a, z = (a_bar - 1) * 4.0, (z_bar - 1) * 4.0
    for c in reversed(C('get_track', {'track': track, 'clips': True}).get('clips', [])):
        if c['start'] >= a - 1e-6 and c['end'] <= z + 1e-6:
            C('delete_clip', {'track': track, 'clip': c['i']})
        elif c['start'] < z and c['end'] > a:
            raise SystemExit(f'{track}: clip {c["name"]} {c["start"] / 4 + 1}-{c["end"] / 4 + 1} crosses {a_bar}-{z_bar}')


def section(track, a_bar, z_bar, kind_of):
    notes = []
    for bar in range(a_bar, z_bar):
        kind = kind_of(bar)
        if kind:
            notes += [[p, (bar - a_bar) * 4 + b, d, v] for p, b, d, v in bar_notes(bar, kind)]
    clear(track, a_bar, z_bar)
    C('create_midi_clip', {'track': track, 'bar': a_bar, 'length': (z_bar - a_bar) * 4, 'name': 'City Gtr ping-pong',
                           'notes': notes}, timeout=60.0)
    return len(notes)


def guitar():
    n = section(GTR, *DROP1, lambda b: 'ping')
    n += section(GTR, *DROP2_REST, lambda b: 'ping')
    n += section(GTR, *BUILD1, build1_kind)
    print('guitar notes written', n)


def build2_stab():
    """113-120: 0.5/2.5 for two bars, 8ths from 115, pushes from 119; top B4 -> C#5 -> D#5."""
    sus = [64, 66, 69, 71]          # B7sus4, top B4
    nine = [64, 66, 69, 73]         # B7sus4 add C#5
    dom = [63, 66, 69, 75]          # B7, top D#5
    notes = []
    for bar in range(113, 121):
        k = (bar - 113) * 4.0
        if bar < 115:
            hits, chord = [0.5, 2.5], sus
        elif bar < 117:
            hits, chord = [0.5, 1.5, 2.5], sus          # 3.5 is his guitar's E4 there
        elif bar < 119:
            hits, chord = [0.5, 1.5, 2.5, 3.5], nine
        else:
            hits, chord = [0.5, 1.5, 2.5, 3.25, 3.5, 3.75], dom
        for h in hits:
            vel = 84 + (bar - 113) * 3
            for p in chord:
                notes.append([p, k + pocket(h), 0.23, float(min(vel, 108))])
    clear(STABS, 113, 121)
    C('create_midi_clip', {'track': STABS, 'bar': 113, 'length': 32, 'name': 'City Stabs build', 'notes': notes},
      timeout=60.0)
    print('build 2 stab notes', len(notes))


if __name__ == '__main__':
    steps = {'guitar': guitar}          # build2_stab: rejected, kept for the record
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
