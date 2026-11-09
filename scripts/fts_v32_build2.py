"""From The Streets v32: break 2 -> build 2 -> pre-drop rebuilt as a climb with identity.

His notes: "a passagem do break 2 pro build 2 precisa ser revista... criar a atmosfera e
pressão pro drop... sem loops batidos falando a coisa errada... uma subida, e um pre drop com
identidade, esse que tá parece que mata a energia toda, podemos usar uns fills".

  113  soft crash; the kick comes back in quarters, its velocity rising (Vol<Vel 100 %)
  113-116  sparse (clap/off-beat hats rest), the break chops, the loops, the bass teaser
  117  clap and hats back; the City call once, his one-bar cut on the downbeat
  119  kick in 8ths; loops, perc and the break run on to 120.5 (they used to stop at 119)
  120  kick in 16ths, a 909 tom run
  120.5-121  the identity: the title's first syllable stuttering (no DJ rewind), then the drop
Removed: the hook B chops (six repeats of the same words) and the bar-long a cappella that
stopped everything at 119.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server

R = Path.home() / 'Desktop/TRACKS 2027/From the streets/Remix 122'
LOG_PATH = R / 'live-changes-v32_build2.json'
LOG = []
B = lambda bar: (bar - 1) * 4.0


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    LOG_PATH.write_text(json.dumps(LOG, indent=2, default=str))
    print(cmd, args.get('track', ''), str(r)[:110], flush=True)
    return r


def clips(track):
    return client.call('get_track', {'track': track, 'markers': True, 'max_clips': 400})['clips']


def at_bar(track, bar):
    return next((c for c in clips(track) if abs(c['start'] - B(bar)) < 0.02), None)


def copy_pattern(track, src_bar, dst_bar, bars):
    """Copy `bars` bars of notes from src to dst inside the same long clip (markers respected)."""
    c = next(c for c in clips(track) if c['type'] == 'midi' and c['start'] <= B(dst_bar) < c['end'])
    off = c['start_marker'] - c['start']
    notes = client.call('get_notes', {'track': track, 'clip': {'at': c['start']}})
    a, b = B(src_bar) + off, B(src_bar + bars) + off
    d = B(dst_bar) - B(src_bar)
    lo, hi = B(dst_bar) + off, B(dst_bar + bars) + off
    keep = [n for n in notes if not lo - 1e-3 <= n[1] < hi - 1e-3]
    new = [[p, t + d, dur, v] for p, t, dur, v in notes if a - 1e-3 <= t < b - 1e-3]
    C('add_notes', track=track, clip={'at': c['start']}, notes=keep + new, replace=True)


def kick_notes():
    n = [[60, k, 1, 84 + 3 * k] for k in range(16)]                     # 113-116 quarters
    n += [[60, 16 + k, 1, 100 + 2 * k] for k in range(8)]              # 117-118
    n += [[60, 24 + k * .5, .5, 108 + (k % 2 == 0) * 8] for k in range(8)]   # 119 8ths
    n += [[60, 28 + k * .25, .25, 112 + (k % 2 == 0) * 10] for k in range(8)]  # 120 16ths to 120.5
    return [[p, t, d, min(127, v)] for p, t, d, v in n]


def main():
    assert not LOG_PATH.exists(), 'inspect the partial receipt before a retry'
    # kick: velocity must shape the build; every other kick note is 127, so nothing else moves
    vels = {n[3] for c in clips('KICK') for n in client.call('get_notes', {'track': 'KICK', 'clip': {'at': c['start']}})}
    assert vels == {127.0}, vels
    C('set_param', track='KICK', device=0, param='Vol < Vel', value=1.0)
    C('create_midi_clip', track='KICK', bar=113, length=30, notes=kick_notes(),
      name='build 2 - kick returns 4ths>8ths>16ths')
    C('apply_groove', track='KICK', groove='Swing 16ths 66', start_bar=113, end_bar=121)

    # drums back for the second half (the v30 carve emptied 119-120)
    for t in ('CLAP', 'HAT OFF - persona', 'HAT OFF - shaker shot'):
        copy_pattern(t, 125, 117, 4)
    C('set_clip', track='PERC LOOP', clip={'at': B(113)}, muted=False)
    C('duplicate_clip', track='CRASH 909', clip={'at': B(17)}, beat=B(113))

    # vocals: no repeated chops, no stopping a cappella; one call on 117's downbeat
    for c in clips('VOX CITY'):
        if B(112.9) <= c['start'] < B(121) and ('chop' in c['name'] or 'PRE-DROP' in c['name']):
            C('delete_clip', track='VOX CITY', clip={'at': c['start']})
    for c in clips('VOX - throws'):
        if B(118) <= c['start'] < B(121):
            C('delete_clip', track='VOX - throws', clip={'at': c['start']})
    C('duplicate_clip', track='VOX CITY', clip={'at': B(40)}, beat=B(117))

    # the loops, perc, break and bass run on to 120.5
    for t in ('LOOP MURDER - guitar riff', 'LOOP CITY - orig synth', 'PERC LOOP'):
        C('fill_range', track=t, src_start_bar=117, src_end_bar=119, start_bar=119, end_bar=120.5)
    C('duplicate_clip', track='BREAKBEAT', clip={'at': B(111)}, beat=B(119))
    C('trim_clip', track='BREAKBEAT', clip={'at': B(119)}, end_bar=120.5)
    last = max((c for c in clips('BASS - break') if c['start'] < B(121)), key=lambda c: c['start'])
    if last['end'] < B(120.5):
        C('fill_range', track='BASS - break', src_start_bar=last['start'] / 4 + 1,
          src_end_bar=last['end'] / 4 + 1, start_bar=last['end'] / 4 + 1, end_bar=120.5)

    # the pre-drop: a 909 tom run on 120, the title stuttering on 120.5, no DJ rewind
    rew = at_bar('FX - transitions', 120.5)
    if rew:
        C('delete_clip', track='FX - transitions', clip={'at': rew['start']})
    C('create_audio_clip', track='FX - transitions', path=str(R / '909 tom run.wav'), beat=B(120),
      name='909 tom run (pre-drop 2)', warp=True, beats=2)
    C('create_audio_clip', track='FX - glitches', path=str(R / 'glitch/Glitch - City stutter.wav'),
      beat=B(120.5), name='City stutter (pre-drop 2 identity)', warp=True, beats=2)


if __name__ == '__main__':
    main()
