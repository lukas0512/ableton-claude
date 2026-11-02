"""TECHNO #8 mix pass 3. v2 drop against the reference: low-mid +3.3 (kick 12 dB over everything
at 125-250 Hz), highs -3.7, bass -1.3 dB against the drums (reference -9.4, he likes it loud: -3).
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server

C = lambda cmd, **a: print(cmd, a.get('param', a.get('track')), server._journaled(cmd, a).get('display', ''))
C('set_param', track=1, device='EQ Eight', param='3 Frequency A', display='190 Hz')
C('set_param', track=1, device='EQ Eight', param='3 Gain A', display='-4.5 dB')
C('set_param', track=4, device='EQ Eight', param='4 Gain A', display='4 dB')
C('set_track', track=6, volume_db=-16.4)
for t, d in ((2, -1.5), ('BASS - build', -1.5)):
    v = client.call('get_track', {'track': t})['vol_db']
    C('set_track', track=t, volume_db=round(v + d, 1))
C('re_enable_automation')
p = client.call('get_device', {'track': 'master', 'device': 0})['params'][9]
print(p)
print(server._journaled('set_param', {'track': 'master', 'device': 0, 'param': 'Limiter Input Gain', 'value': p['value'] + .01}))
print(client.call('get_device', {'track': 'master', 'device': 0})['params'][9])
