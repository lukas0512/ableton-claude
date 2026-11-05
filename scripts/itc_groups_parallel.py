"""In the City, polish 1: groups, parallel returns, ducked FX ("colar, macio, nada pontudo, mais pressão").

Measured first: congas crest 21.8 dB, perc loop 20.2, shaker 18.4, hat 15.5 against a clap at 14.1.
TOPS and PERC GROUP (made by hand, both into DRUMS) shave those tips only: threshold well over the
body, fast attack. Pressure goes on returns under the dry signal, so the dry transients stay:
F-Par Drums (DRUMS), G-Par Low (LOW END), H-Warm parallel saturation (MUSIC + VOX). The voices' plate,
the delay and the atmos duck ~3 dB under the kick so the tails stay out of its way.
Settings start from published parallel-compression recipes (house blends 20-35 %) and are set by render.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call


def comp(track, thr, ratio, attack, release, output=None, sc_eq=None, device='Compressor'):
    def p(name, **kw):
        C('set_param', {'track': track, 'device': device, 'param': name, **kw})
    p('Model', value=0.0)                # Peak
    p('Expansion Ratio', value=0.0)
    p('Threshold', display=f'{thr:.1f} dB')
    p('Ratio', display=f'{ratio:.2f} : 1')
    p('Attack', display=f'{attack:.2f} ms')
    p('Release', display=f'{release:.0f} ms')
    p('Knee', display='6.0 dB')
    if output is not None:
        p('Output', display=f'{output:.2f} dB')
    if sc_eq is not None:
        p('S/C EQ On', value=float(sc_eq))


def duck(ret):
    """Keyed by the kick: ~3 dB of ducking, back within 120 ms."""
    tr = C('get_track', {'track': ret})
    if not any(d['class'] == 'Compressor2' for d in tr['devices']):
        C('load_device', {'track': ret, 'query': 'Compressor'}, timeout=30.0)
    comp(ret, -18.0, 3.0, 0.5, 120, sc_eq=False)
    print(ret, C('set_device_input', {'track': ret, 'device': 'Compressor', 'source': 'KICK', 'channel': 'Post Mixer'}))
    C('set_param', {'track': ret, 'device': 'Compressor', 'param': 'S/C On', 'value': 1.0})


def main():
    comp('TOPS', -22.0, 3.0, 1.0, 60)
    comp('PERC GROUP', -24.0, 3.0, 2.0, 80)
    C('set_param', {'track': 'DRUMS', 'device': 'Glue Compressor', 'param': 'Attack', 'value': 4.0})  # 3 ms

    comp('return:F-Par Drums', -30.0, 8.0, 5.0, 100, output=6.0, sc_eq=False)
    comp('return:G-Par Low', -24.0, 4.0, 3.0, 120, output=4.0, sc_eq=False)
    C('set_param', {'track': 'return:H-Warm', 'device': 'Saturator', 'param': 'Type', 'value': 1.0})
    C('set_param', {'track': 'return:H-Warm', 'device': 'Saturator', 'param': 'Drive', 'display': '9.0 dB'})
    C('set_param', {'track': 'return:H-Warm', 'device': 'Saturator', 'param': 'Output', 'display': '-6.0 dB'})
    eq = 'EQ Eight'
    for name, kw in (('1 Filter On A', {'value': 1.0}), ('1 Filter Type A', {'value': 1.0}),
                     ('1 Frequency A', {'display': '200 Hz'}),
                     ('8 Filter On A', {'value': 1.0}), ('8 Filter Type A', {'value': 6.0}),
                     ('8 Frequency A', {'display': '7.00 kHz'})):
        C('set_param', {'track': 'return:H-Warm', 'device': eq, 'param': name, **kw})

    sends = [('DRUMS', 5, -6.0), ('LOW END', 6, -6.0), ('MUSIC BUS', 7, -14.0), ('VOX BUS', 7, -16.0)]
    for track, send, db in sends:
        C('set_send', {'track': track, 'send': send, 'db': db})
    for ret, db in (('return:F-Par Drums', -6.0), ('return:G-Par Low', -9.0), ('return:H-Warm', -6.0)):
        C('set_track', {'track': ret, 'volume_db': db})

    for ret in ('return:4', 'return:1', 'return:2'):   # plate, delay, atmos
        duck(ret)
    print('done')


if __name__ == '__main__':
    main()
