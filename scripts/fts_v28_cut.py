"""From The Streets v28: cut bars 113-120 (first half of build 2) out of the arrangement.

He found break 2 + build 2 (32 bars) too long. Everything from bar 121 moves 8 bars earlier.
Clips that start at 113 and run on (clap, off-beat hats, bass teaser) keep their place and
skip 32 beats of content by moving their markers; the whole-song hat clip is split in two
(original trimmed at 113, a copy starting from old bar 121's content placed at 113), so
its drawn filter envelope stays aligned with its notes.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server

OUT = Path.home() / 'Desktop/TRACKS 2027/From the streets/Remix 122/live-changes-v28_cut.json'
LOG = []
CUT_A, CUT_B = 113, 121
SHIFT = CUT_A - CUT_B                  # -8 bars
B = lambda bar: (bar - 1) * 4.0
MARKER_TRACKS = {'CLAP': 448, 'HAT OFF - persona': 448, 'HAT OFF - shaker shot': 448,
                 'BASS - teaser (HP)': 448}
PARK = 300                              # bar far past the song end


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    OUT.write_text(json.dumps(LOG, indent=2, default=str))
    print(cmd, args.get('track', ''), str(r)[:120], flush=True)
    return r


def main():
    assert not OUT.exists(), 'inspect the partial receipt before a retry'
    song = client.call('get_song')
    names = [t['name'] for t in song['tracks'] if t.get('kind') in ('midi', 'audio')]

    # 1. the whole-song hat clip: park a copy, trim the original at the cut
    C('duplicate_clip', track='HAT 16ths', clip={'at': 0}, beat=B(PARK))
    C('trim_clip', track='HAT 16ths', clip={'at': 0}, end_bar=CUT_A)
    # 2. the atmos wash that crosses the cut: end it where the build now ends
    C('trim_clip', track='ATMOS - riff wash', clip={'at': B(97)}, end_bar=CUT_A + 7.5)

    # 3. every other track: drop 113-120, pull 121+ back by 8 bars
    for n in names:
        if n not in MARKER_TRACKS and n != 'HAT 16ths':
            C('delete_clips_in_range', track=n, start_bar=CUT_A, end_bar=CUT_B)
        if n == 'HAT 16ths':
            continue
        C('shift_clips', track=n, from_bar=CUT_B, bars=SHIFT)

    # 4. clips starting at 113 that run on: skip 32 beats of their content, end 8 bars sooner
    for n, at in MARKER_TRACKS.items():
        c = next(x for x in client.call('get_track', {'track': n, 'markers': True})['clips']
                 if abs(x['start'] - at) < 1e-3)
        s0, e0 = c['start_marker'], c['end_marker']
        C('set_clip', track=n, clip={'at': at}, loop_end=e0 + 32, end_marker=e0 + 32)
        C('set_clip', track=n, clip={'at': at}, loop_start=s0 + 32, start_marker=s0 + 32)
        C('trim_clip', track=n, clip={'at': at}, end_beat=c['end'] - 32)

    # 5. the parked hat copy starts from old bar 121's content, placed at 113
    C('set_clip', track='HAT 16ths', clip={'at': B(PARK)}, loop_start=B(CUT_B),
      start_marker=B(CUT_B))
    C('shift_clips', track='HAT 16ths', from_bar=PARK, bars=CUT_A - PARK)
    C('trim_clip', track='HAT 16ths', clip={'at': B(CUT_A)}, end_bar=193 + SHIFT)

    # 6. locators after the cut move with the music
    for cue in song.get('cues', []):
        if cue['bar'] >= CUT_B:
            C('delete_cue', bar=cue['bar'])
            C('set_cue', name=cue['name'], bar=cue['bar'] + SHIFT)
        elif CUT_A <= cue['bar'] < CUT_B:
            C('delete_cue', bar=cue['bar'])
            C('set_cue', name='BUILD 2 - the break chops, the V (8 bars)', bar=cue['bar'])


if __name__ == '__main__':
    main()
