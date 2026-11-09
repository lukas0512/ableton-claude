"""From The Streets v28: groove by absence, and glitches that speak in the holes.

Positions are after the v28 cut (drop 2 = 121-152, outro A = 153-168).

  bass breath   the riff rests beats 2-4, the Murder riff crushed on beat 4   44 76 132 156
  kick out      beats 3-4 without kick, the City call in a tape stop           72 140 164
  full stop     kick, bass, clap, hats, congas, toms, ride out for beats 3-4   84 (City stutter)
                                                                              136 (the reversed crash fills it)
  hat rest      the 16th hats out for two bars                                 89-90 145-146
  hook rev cut  the hook B chop reversed then gated                            92.5 148.5
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server

R = Path.home() / 'Desktop/TRACKS 2027/From the streets/Remix 122'
G = R / 'glitch'
OUT = R / 'live-changes-v28_absence.json'
LOG = []
B = lambda bar: (bar - 1) * 4.0

DRUMS = ['KICK', 'BASS', 'CLAP', 'SNARE', 'HAT 16ths', 'HAT OFF - persona',
         'HAT OFF - shaker shot', 'HAT OFF - imite', 'CONGAS', 'TOM 909', 'RIDE 909']
HOLES = (
    [('BASS', B(b) + 1, B(b) + 4) for b in (44, 76, 132, 156)]
    + [('KICK', B(b) + 2, B(b) + 4) for b in (72, 140, 164)]
    + [(t, B(b) + 2, B(b) + 4) for b in (84, 136) for t in DRUMS]
    + [('HAT 16ths', B(b), B(b + 2)) for b in (89, 145)]
)
GLITCHES = (
    [('Riff crush', B(b) + 3, 1) for b in (44, 76, 132, 156)]
    + [('City tape stop', B(b) + 2, 2) for b in (72, 140, 164)]
    + [('City stutter', B(84) + 2, 2)]
    + [('Hook rev cut', B(b) + 2, 2) for b in (92, 148)]
)


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    OUT.write_text(json.dumps(LOG, indent=2, default=str))
    print(cmd, args.get('track', ''), str(r)[:110], flush=True)
    return r


def carve(track, holes):
    """Remove the notes inside each song-time hole, clip by clip (markers respected)."""
    clips = client.call('get_track', {'track': track, 'markers': True, 'max_clips': 400})['clips']
    for c in clips:
        if c['type'] != 'midi':
            continue
        mine = [(a, b) for a, b in holes if a < c['end'] and b > c['start']]
        if not mine:
            continue
        off = c['start_marker'] - c['start']          # song beat -> clip beat
        notes = client.call('get_notes', {'track': track, 'clip': {'at': c['start']}})
        keep = [n for n in notes
                if not any(a + off - 1e-3 <= n[1] < b + off - 1e-3 for a, b in mine)]
        if len(keep) < len(notes):
            C('add_notes', track=track, clip={'at': c['start']}, notes=keep, replace=True)


def main():
    assert not OUT.exists(), 'inspect the partial receipt before a retry'
    by_track = {}
    for t, a, b in HOLES:
        by_track.setdefault(t, []).append((a, b))
    for t, holes in by_track.items():
        carve(t, holes)

    tracks = [t['name'] for t in client.call('get_song')['tracks']]
    idx = tracks.index('FX - transitions') + 1
    C('create_track', kind='audio', name='FX - glitches', index=idx)
    C('set_track_input', track='FX - glitches', source='No Input')
    C('set_track_output', track='FX - glitches', dest='FX BUS')
    C('set_track', track='FX - glitches', volume_db=-6.0)
    C('set_send', track='FX - glitches', send=4, db=-18.0)     # E-Plate, the voices' space
    C('set_send', track='FX - glitches', send=1, db=-20.0)     # B-Delay
    for name, beat, beats in sorted(GLITCHES, key=lambda g: g[1]):
        C('create_audio_clip', track='FX - glitches', path=str(G / f'Glitch - {name}.wav'),
          beat=beat, name=f'{name} {beat / 4 + 1:g}', warp=True, beats=beats)


if __name__ == '__main__':
    main()
