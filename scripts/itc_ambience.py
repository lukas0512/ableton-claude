"""In the City: more ambience, the low end kept mono.

His note (2026-11-05, ~22:55): "dar mais ambiência pra track um pouco". v6 measured mid width -12.3 dB against the
references' -6.9 (p25 -7.9), break width -11 (-7.7). The returns (Atmos, Plate) are high-passed at 180 Hz and ducked
by the kick, so they add space without blurring the kick or the sub. Moves, about +3 dB each:
- C-Atmos return -16 -> -12, its Hybrid Reverb decay 2.0 -> 2.6 s;
- the City bus (stabs + guitar) -> Atmos -20 -> -16; the Murder riff bus -> Atmos -18 -> -15;
- the voices -> Plate -14 -> -12 (the throws stay -12): the lead gets a room, not a wash;
- drums into D-Room: clap -16 -> -13, open hats -20/-21 -> -17/-18, ride -24 -> -21, perc group new at -22.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
SENDS = [
    ('CITY SYNTH', 2, -16.0), ('MURDER BUS - drop', 2, -15.0),
    ('VOX CITY - calls', 4, -12.0), ('VOX CITY - hooks', 4, -12.0), ('VOX CITY - radio', 4, -12.0),
    ('VOX MURDER', 4, -12.0), ('VOX MURDER - trades', 4, -12.0),
    ('CLAP', 3, -13.0), ('HAT OFF - persona', 3, -17.0), ('HAT OFF - imite', 3, -18.0), ('RIDE 909', 3, -21.0),
    ('PERC GROUP', 3, -22.0),
]


def apply():
    C('set_track', {'track': 'return:2', 'volume_db': -12.0})
    C('set_param', {'track': 'return:2', 'device': 'Hybrid Reverb', 'param': 'Decay', 'display': '2.60 s'})
    for t, s, db in SENDS:
        C('set_send', {'track': t, 'send': s, 'db': db})


if __name__ == '__main__':
    apply()
    for t, s, _ in SENDS:
        print(f'{t:22s}', s, round(C('get_track', {'track': t})['sends_db'][s], 1))
    print('atmos', C('get_track', {'track': 'return:2'})['vol_db'])
