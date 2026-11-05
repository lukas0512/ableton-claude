"""In the City: a three-dimensional stage. Low end mono, voice in front, music apart, texture at the back.

His note (2026-11-05): "a textura tem que ficar no fundo, mais baixinha ... fazer o 3D da track, stereo, e deixar o low
end mono". Measured against dub_house_streets: mid width -10.3 dB (refs -7.9..-5.7), high width -11 (-8.9..-3.4),
break width -10.4 (-9.3..-7.1); low width -46 and correlation 1.0 under 120 Hz already fine, so that stays.
The City synth and the Murder riff were both panned right: they now answer from opposite sides.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call


def eq(track, band, **kw):
    for suffix, value in kw.items():
        name = {'on': 'Filter On A', 'kind': 'Filter Type A', 'freq': 'Frequency A', 'gain': 'Gain A'}[suffix]
        arg = {'display': value} if suffix == 'freq' else {'value': value}
        C('set_param', {'track': track, 'device': 'EQ Eight', 'param': f'{band} {name}', **arg})


def texture():
    """Back of the room: lower, darker, thinner, more reverb than direct sound."""
    for track, fader in (('TEXTURE tape', -14.0), ('TEXTURE vinyl', -26.0)):
        C('set_track', {'track': track, 'volume_db': fader})
        eq(track, 1, on=1.0, kind=1.0, freq='400 Hz')
        eq(track, 8, on=1.0, kind=6.0, freq='5.00 kHz')
        C('set_send', {'track': track, 'send': 2, 'db': -10.0})      # C-Atmos


def utility(track, width):
    tr = C('get_track', {'track': track})
    if not any(d['class'] == 'StereoGain' for d in tr['devices']):
        C('load_device', {'track': track, 'query': 'Utility'}, timeout=30.0)
    C('set_param', {'track': track, 'device': 'Utility', 'param': 'Stereo Width', 'display': f'{width} %'})


def stage():
    C('set_track', {'track': 'CITY SYNTH', 'pan': -0.3})             # the riff stays right, the synth answers from the left
    C('set_track', {'track': 'RIDE 909', 'pan': -0.12})
    C('set_track', {'track': 'CHOPS - UKG babe', 'pan': -0.25})
    utility('TOPS', 130)
    utility('PERC GROUP', 120)
    C('set_param', {'track': 'MUSIC BUS', 'device': 'Utility', 'param': 'Stereo Width', 'display': '150 %'})
    # depth: the voices' plate starts later so the dry voice stays in front
    C('set_param', {'track': 'return:4', 'device': 0, 'param': 'Predelay', 'display': '45.0 ms'})
    C('set_param', {'track': 'return:4', 'device': 0, 'param': 'Stereo Image', 'value': 1.0})
    C('set_param', {'track': 'return:3', 'device': 0, 'param': 'Stereo Image', 'value': 1.0})


def mono_returns():
    """Break 2 read -21 dB side under 120 Hz (drops -47): the riff's lows into wide reverbs. High-pass them."""
    for ret in ('return:4', 'return:2'):             # plate, atmos
        tr = C('get_track', {'track': ret})
        if not any(d['class'] == 'Eq8' for d in tr['devices']):
            C('load_device', {'track': ret, 'query': 'EQ Eight'}, timeout=30.0)
        C('move_device', {'track': ret, 'device': 'EQ Eight', 'position': 0})   # before the reverb
        for name, kw in (('1 Filter On A', {'value': 1.0}), ('1 Filter Type A', {'value': 1.0}), ('1 Frequency A', {'display': '180 Hz'})):
            C('set_param', {'track': ret, 'device': 'EQ Eight', 'param': name, **kw})
        print(ret, [d['name'] for d in C('get_track', {'track': ret})['devices']])


if __name__ == '__main__':
    steps = {'texture': texture, 'stage': stage, 'mono': mono_returns}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
    p = {x['name']: x['display'] for x in C('get_device', {'track': 'return:4', 'device': 0})['params']}
    print({k: p[k] for k in ('Predelay', 'Stereo Image')})
    print({t: C('get_track', {'track': t})['vol_db'] for t in ('TEXTURE tape', 'TEXTURE vinyl')})
