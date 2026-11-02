"""TECHNO #8 mix pass 1: faders from the soloed levels against the kick (bars 73-76).

Measured (LU vs kick): bass -6.4, clap15 -17.5, clap13 -17.6, hats -18.8, open -21.3,
perc -17.9, top -11.1, ping -26.6, loop -14.9, riff -13.2. Render read 8 dB darker than the
reference above 2 kHz: the claps and hats were buried, the kick and bass did the rest.
Targets: bass -3, the two claps -8.5 together, hats -16, open -19, riff -12, loop -16.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server

MOVES = {2: +3.0, 4: +1.5, 6: +3.0, 7: +2.0, 8: +6.0, 9: +6.0, 10: +4.0, 11: -1.0, 12: +1.0}
ABS = {'KICK - build (HP)': -12.0, 'BASS - build': -9.4, 'SYNTH - build': -17.0}


def main():
    for t, d in MOVES.items():
        v = client.call('get_track', {'track': t})['vol_db']
        print(t, server._journaled('set_track', {'track': t, 'volume_db': round(v + d, 1)}).get('vol_db'))
    for t, v in ABS.items():
        server._journaled('set_track', {'track': t, 'volume_db': v})
    server._journaled('re_enable_automation', {})


main()
