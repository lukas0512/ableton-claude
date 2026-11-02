"""TECHNO #8 mix pass 2. Drop against the reference (bars 73-88 vs its 65-80, loudness matched):
low +2.2, low-mid +3.7, high-mid -5.1, high -6.5 dB. The build sat flat at -13.3 LUFS and lost
its sub two bars early. Cuts go where the energy is made (the kick's 125-200 Hz, the riff's own
230 Hz boost, the loop at 400), the air into the top loop and the hats, not the master.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server

BASS_FILE = '/Users/lukasgalhardo/Desktop/Projects 26:27/TECHNO #8 Project/Samples/Processed/Normalize/NCPZ1_BASSLOOP9_Fmin [2026-11-01 190524].wav'
LOOP_FILE = '/Users/lukasgalhardo/Desktop/Projects 26:27/TECHNO #8 Project/Samples/Processed/Normalize/NCPZ1_SYNTHLOOP19_Gmin [2026-11-01 182738].wav'
B = lambda bar: (bar - 1) * 4.0


def C(cmd, **a):
    r = server._journaled(cmd, a)
    print(cmd, a.get('track', ''), a.get('param', ''), str(r.get('display', '') if isinstance(r, dict) else r)[:60], flush=True)
    return r


def eq(track, band, ftype, hz, gain=None, q=None):
    d = 'EQ Eight'
    C('set_param', track=track, device=d, param=f'{band} Filter On A', value=1)
    C('set_param', track=track, device=d, param=f'{band} Filter Type A', item=ftype)
    C('set_param', track=track, device=d, param=f'{band} Frequency A', display=f'{hz} Hz')
    if gain is not None:
        C('set_param', track=track, device=d, param=f'{band} Gain A', display=f'{gain} dB')
    if q is not None:
        C('set_param', track=track, device=d, param=f'{band} Q A', value=q)


def has(track, name):
    return name in [d['name'] for d in client.call('get_track', {'track': track})['devices']]


def tone():
    for t in (1, 4, 6):
        if not has(t, 'EQ Eight'):
            C('load_device', track=t, path='audio_effects/EQ Eight')
            C('set_device_on', track=t, device='EQ Eight', on=True)
            for band in range(1, 9):
                C('set_param', track=t, device='EQ Eight', param=f'{band} Filter On A', value=0)
    eq(1, 3, 'Bell', 170, -3)
    eq(12, 2, 'Bell', 350, -2)
    eq(11, 2, 'Bell', 400, -2)
    eq(4, 3, 'Bell', 400, -2)
    eq(4, 4, 'High Shelf', 6000, 3)
    eq(6, 4, 'High Shelf', 9000, 2)


def build():
    # recreate the two build layers' last four bars: the sub stays until bar 127
    for n in ('BASS - build', 'SYNTH - build'):
        for c in client.call('get_track', {'track': n})['clips']:
            C('delete_clip', track=n, clip={'at': c['start']})
    for bar, pts in ((121, [[0, 20], [16, 20]]), (125, [[0, 20], [12, 20], [13, 60], [14, 200], [16, 200]])):
        C('create_audio_clip', track='BASS - build', path=BASS_FILE, bar=bar, warp=True, beats=16, name='bass: sub leaving',
          envelopes=[{'param': '1 Frequency A', 'device': 'EQ Eight', 'unit': 'display', 'points': pts}])
    C('trim_clip', track='BASS - build', clip={'at': B(125)}, end_beat=B(128) + 2)
    C('set_clip', track='BASS - build', clip={'at': B(121)}, gain_db=-2)
    for bar, hz, g in ((121, (450, 1400), (0, 4)), (125, (1400, 7000), (4, 9))):
        C('create_audio_clip', track='SYNTH - build', path=LOOP_FILE, bar=bar, warp=True, beats=16, name='synth opening',
          envelopes=[{'param': 'Frequency', 'device': 'Auto Filter', 'unit': 'display', 'points': [[0, hz[0]], [16, hz[1]]]},
                     {'param': 'Output', 'device': 'Utility', 'unit': 'db', 'points': [[0, g[0]], [16, g[1]]]}])
    C('trim_clip', track='SYNTH - build', clip={'at': B(125)}, end_beat=B(128) + 2)
    for t, v in (('KICK - build (HP)', -1), ('SYNTH - build', -14), ('VOX - calls', -12.3), ('VOX - phrases', -12.3),
                 ('VOX - chops', -10), (6, -17.4), (7, -14.9), (4, -21.7)):
        C('set_track', track=t, volume_db=v)
    C('re_enable_automation')


if __name__ == '__main__':
    build()
