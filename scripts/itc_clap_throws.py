"""In the City, ear candy: the track's own clap thrown into the delay, nothing dry.

On the 4 of bars 68, 86, 124 and 142: inside the drops, off the 8-bar turns, and clear of every
transition and glitch on the timeline. Sends Only, so only the dark echo is heard.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
TRACK = 'CLAP - throw'
BARS = (68, 86, 124, 142)
CLAP_LATE = 0.0104      # the clap's own 5 ms behind the grid (taste.md, one pocket)


def main():
    names = [t['name'] for t in C('get_song', {})['tracks']]
    if TRACK not in names:
        C('create_track', {'kind': 'midi', 'name': TRACK})
        C('load_device', {'track': TRACK, 'path': 'user_library/Samples/Claude/Nobody Kit/SCHT_Clap2.wav'},
          timeout=40.0)
        C('copy_device', {'src_track': 'CLAP', 'src_device': 0, 'track': TRACK, 'device': 0})
    C('set_track_output', {'track': TRACK, 'dest': 'Sends Only'})
    C('set_send', {'track': TRACK, 'send': 1, 'db': -14.0})
    for bar in BARS:
        C('create_midi_clip', {'track': TRACK, 'bar': bar, 'length': 4, 'name': f'clap throw {bar}',
                               'notes': [[60, 3 + CLAP_LATE, 0.25, 100.0]]})
    tr = C('get_track', {'track': TRACK, 'clips': True})
    print(tr['devices'], tr.get('sends_db'), [(c['name'], c['start']) for c in tr['clips']])


if __name__ == '__main__':
    main()
