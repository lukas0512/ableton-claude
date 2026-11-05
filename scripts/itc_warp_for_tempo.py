"""In the City: before any tempo change, pin every unwarped active clip to the beat it plays on now.

An unwarped clip keeps its length in seconds: at 127 BPM a 24-beat chop run would end ~180 ms late.
Each file is pinned at its exact rate at 125 BPM, so at 125 it plays as before; the old state is printed
as JSON for a manual restore (warping off). Reversed crashes and tom runs then follow the tempo.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
BPM = 125.0


def main():
    if C('get_song', {})['tempo'] != BPM:
        raise SystemExit('run this at 125 BPM: the pin is computed from it')
    log = []
    for t in C('get_song', {})['tracks']:
        if t['kind'] != 'audio' or t['mute']:
            continue
        for c in C('get_track', {'track': t['i'], 'clips': True}).get('clips', []):
            if c.get('muted') or c.get('warping'):
                continue
            at = {'at': c['start']}
            before = C('set_clip', {'track': t['i'], 'clip': at, 'name': c['name']})
            # unwarped: the played region is loop_start..loop_end, in seconds
            s0, s1 = before.get('loop_start') or 0.0, before.get('loop_end')
            per_sec = BPM / 60.0
            C('set_clip', {'track': t['i'], 'clip': at, 'warping': True, 'warp_mode': 'complex_pro'})
            sample_s = C('warp_markers', {'track': t['i'], 'clip': at})['sample_s']
            C('set_warp_markers', {'track': t['i'], 'clip': at,
                                   'markers': [[0.0, 0.0], [sample_s * per_sec, sample_s]]})
            after = C('set_clip', {'track': t['i'], 'clip': at, 'looping': False,
                                   'loop_start': s0 * per_sec, 'loop_end': s1 * per_sec,
                                   'start_marker': s0 * per_sec, 'end_marker': s1 * per_sec})
            log.append({'track': t['name'], 'start': c['start'], 'name': c['name'], 'seconds': [s0, s1],
                        'end_before': c['end'], 'end_after': after.get('end'),
                        'markers_after': [after.get('start_marker'), after.get('end_marker')]})
    print(json.dumps(log, indent=0)[:3500])
    print('pinned', len(log))


if __name__ == '__main__':
    main()
