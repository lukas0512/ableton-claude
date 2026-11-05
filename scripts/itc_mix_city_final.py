"""In the City: the mix around the final City ping-pong, from a soloed pass in drop 2 (bars 121-129).

He (2026-11-05): "se dá uma mixada agora, encaixar de novo uma mix, fazer direitinho". Soloed against the kick:
bass -1.5 LU (taste.md: -3), clap -7.4 (-9), vocal -7.9 (-8.3), Murder riff -12.8 (-12), TOPS -12.2, City stabs
-14.1 (~-15 under the drums), City guitar -23.5 (two notes a bar: sparse parts read low; its fader is his, kept).
Masking: at 400-500 Hz the bass, the vocal and the stabs sat within 2-3 dB of each other; the bass was the loudest
element at 315-400 Hz, under the lead voice.
Moves: bass -1.5 dB and -1.5 dB at 400 Hz (its free band 6); clap -1.5 dB; TOPS -1 dB; the City bus -2 dB at 500 Hz
(its free band 4) so the stabs leave the voice its 500 Hz. Before: BASS -15.1, CLAP -5.7, TOPS +1.0.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call


def p(track, device, name, **kw):
    C('set_param', {'track': track, 'device': device, 'param': name, **kw})


def mix():
    C('set_track', {'track': 'BASS', 'volume_db': -16.6})
    C('set_track', {'track': 'CLAP', 'volume_db': -7.2})
    C('set_track', {'track': 'TOPS', 'volume_db': 0.0})
    for name, kw in (('6 Filter On A', {'value': 1.0}), ('6 Filter Type A', {'value': 3.0}),
                     ('6 Frequency A', {'display': '400 Hz'}), ('6 Gain A', {'value': -1.5}), ('6 Q A', {'display': '1.20'})):
        p('BASS', 'EQ Eight', name, **kw)
    for name, kw in (('4 Filter On A', {'value': 1.0}), ('4 Frequency A', {'display': '500 Hz'}),
                     ('4 Gain A', {'value': -2.0}), ('4 Q A', {'display': '1.40'})):
        p('CITY SYNTH', 'EQ Eight', name, **kw)


def show():
    for t in ('BASS', 'CLAP', 'TOPS'):
        print(t, C('get_track', {'track': t})['vol_db'])
    for t, b in (('BASS', 6), ('CITY SYNTH', 4)):
        d = {x['name']: x['display'] for x in C('get_device', {'track': t, 'device': 'EQ Eight'})['params']}
        print(t, b, d[f'{b} Filter On A'], d[f'{b} Filter Type A'], d[f'{b} Frequency A'], d[f'{b} Gain A'], d[f'{b} Q A'])


if __name__ == '__main__':
    mix()
    show()
