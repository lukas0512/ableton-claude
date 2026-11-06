"""In the City: "bem pista bem forte" (2026-11-06), on the v9 groove: a louder master and a heavier kick, tried on
drop 2 (bars 121-129) with itc_master's measures (LUFS, true peak, the kick band's crest = punch, the mid-band pump,
sub share).

Kick: fader -5.3 dB, EQ 50 Hz -1.5 / 90 Hz +1 / 250 -2 / 400 -3. A heavier kick here = more of its 90 Hz body (its
fundamental sits at 66 Hz, the sub under it is already 39 % of the mix: refs 35) and a little more level, so it
leads the limiter.
Drop 2, 8 bars (the pump reading is not comparable with v8b: the congas changed the mid band after each beat):
  v9      -8.17 LUFS  punch 10.55  pump 0.89  sub 38.4
  loud    -7.79       10.27        1.40       42.1   (club master: the sub comes back)
  kick    -7.44        9.92        0.59       39.7   <- v10: kick fader -4.0, 90 Hz +2.5, v8b master
  both    -6.98        9.41        1.17       43.6   (louder than the refs' p75 -7.3, kick rounded)
  both18  -7.45        9.90        0.78       39.6
usage: itc_forte.py <config> [...] | itc_forte.py apply <config>
"""
from pathlib import Path
import sys

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import itc_master as M

C = M.C
KICK0 = dict(fader=-5.3, body=1.0)
CONFIGS = {
    'v9': dict(master='v8b', **KICK0),
    'loud': dict(master='club', **KICK0),
    'kick': dict(master='v8b', fader=-4.0, body=2.5),
    'both': dict(master='club', fader=-4.0, body=2.5),
    'both18': dict(master='sub2g', fader=-4.0, body=2.5),
}


def apply(cfg):
    M.apply(M.CONFIGS[cfg['master']])
    C('set_track', {'track': 'KICK', 'volume_db': cfg['fader']})
    C('set_param', {'track': 'KICK', 'device': 'EQ Eight', 'param': '4 Gain A', 'value': cfg['body']})


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[:1] == ['apply']:
        apply(CONFIGS[args[1]])
        print('applied', args[1])
        raise SystemExit
    for name in args:
        apply(CONFIGS[name])
        f = M.render(f'ITC forte {name}')
        print(name, M.measure(*sf.read(f)), flush=True)
