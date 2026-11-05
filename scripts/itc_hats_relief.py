"""In the City: the open hat lands with the drop, the shaker belongs to the release, the project is tidied.

His note (2026-11-05): "no drop 1 você esquece de voltar com o open hat ... muito estridente ... esse shaker toca a
track inteira, tem que dar espaço nos breaks, é movimento pra parte do alívio ... muito lixo no projeto".
His references (dub_house_streets) keep off-beat hats through every groove and take the hats away inside the
tense part of breaks. The shaker sat 5 ms ahead of the 16th pocket: its markers are moved onto it.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
SEC_16TH = 60 / 122 / 4
SHAKER = 'SHAKER played'
SHAKER_OUT = ((1, 25), (49, 65), (87, 89), (97, 121), (143, 145), (177, 185))   # bars with no shaker: intro, breaks, absences
POCKET = 0.0225 + 0.0106                                                        # 16th offset including its 5 ms lag


def clips(track):
    return C('get_track', {'track': track, 'clips': True}).get('clips', [])


def bar(c):
    return c['start'] / 4 + 1


def open_hat():
    """Fill the persona's rest at each drop's first 8 bars: the off-beat lands with the kick."""
    T = 'HAT OFF - persona'
    for first, last in ((65, 73), (121, 129)):
        beat0 = (first - 1) * 4.0
        clip = next(c for c in clips(T) if c['start'] <= beat0 < c['end'] and not c.get('muted'))
        info = C('set_clip', {'track': T, 'clip': {'at': clip['start']}, 'name': clip['name']})
        marker = info.get('start_marker') or 0.0
        notes = C('get_notes', {'track': T, 'clip': {'at': clip['start']}})
        a = beat0 - clip['start'] + marker
        z = (last - 1) * 4.0 - clip['start'] + marker
        have = {round(n[1], 3) for n in notes}
        add = [[60, a + k + 0.5, 0.5, 108.0] for k in range(int(z - a)) if round(a + k + 0.5, 3) not in have]
        C('add_notes', {'track': T, 'clip': {'at': clip['start']}, 'notes': notes + add, 'replace': True})
        print(f' persona {first}-{last}: added {len(add)}')


def soften():
    """The narrow peak at ~7.3 kHz is the stridency. No air boost on the open hats."""
    for T in ('HAT OFF - persona', 'HAT OFF - imite'):
        d = C('get_device', {'track': T, 'device': 'EQ Eight'})
        p = {x['name']: x['display'] for x in d['params']}
        for b in range(1, 9):
            if p[f'{b} Filter On A'] == 'On' and p[f'{b} Filter Type A'] == 'High Shelf':
                C('set_param', {'track': T, 'device': 'EQ Eight', 'param': f'{b} Gain A', 'value': 0.0})
        band = next(b for b in range(1, 9) if p[f'{b} Filter Type A'] == 'Bell' and p[f'{b} Filter On A'] == 'Off' or
                    (p[f'{b} Filter Type A'] == 'Bell' and p[f'{b} Gain A'] in ('0.00 dB', '-2.00 dB')))
        for name, kw in ((f'{band} Filter On A', {'value': 1.0}), (f'{band} Frequency A', {'display': '7.30 kHz'}),
                         (f'{band} Gain A', {'value': -4.0}), (f'{band} Q A', {'display': '2.00'})):
            C('set_param', {'track': T, 'device': 'EQ Eight', 'param': name, **kw})
        print(' eq', T, 'band', band)


def shaker():
    markers = [[k * 0.25 + (POCKET if k % 2 else 0.0), k * SEC_16TH] for k in range(33)]
    n = m = 0
    for c in clips(SHAKER):
        out = any(a <= bar(c) < z for a, z in SHAKER_OUT)
        if out and not c.get('muted'):
            C('set_clip', {'track': SHAKER, 'clip': {'at': c['start']}, 'muted': True})
            m += 1
        elif not out:
            C('set_warp_markers', {'track': SHAKER, 'clip': {'at': c['start']}, 'markers': markers})
            n += 1
    print(f' shaker: {m} clips out, {n} on the pocket')


if __name__ == '__main__':
    steps = {'open_hat': open_hat, 'soften': soften, 'shaker': shaker}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
