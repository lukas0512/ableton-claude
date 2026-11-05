"""In the City: break 1 (bar 49) no longer falls dry.

His note (2026-11-05): "no primeiro break cai muito seco, temos que usar mais FX, crashes etc". What was there: a
soft 909 crash (velocity 88), the drop wash at -19 dB (fader) +4 dB (clip), a one-beat riff stutter at 48.75; the
kick stops at the bar line. Added:
- the crash at full velocity (112) and a send to C-Atmos (-16 dB) for its tail;
- a reverse crash (Core Library 'Cymbal Crash Reverse Gnirob') ending exactly on the downbeat of 49;
- an impact on the downbeat ('Impact Dub Chamber', dub flavour, low) on the same FX track;
- the drops' sub boom copied to bar 49 (weight where the kick leaves);
- the wash +4 dB (clip gain 4 -> 8).
His taste (taste.md): no risers or snare rolls into drops; these are the arrival of a break, not a build.
"""
from pathlib import Path
import sys

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
LIB = '/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Samples/'
T = 'FX - break hits'
BAR = 49
DOWN = (BAR - 1) * 4.0
BPM = 127.0


def find(name):
    for p in Path('/Applications/Ableton Live 12 Suite.app/Contents/App-Resources').rglob(name):
        return str(p)
    raise SystemExit('not found: ' + name)


def track():
    names = [t['name'] for t in C('get_song', {})['tracks']]
    if T not in names:
        C('create_track', {'kind': 'audio', 'name': T, 'index': names.index('FX - glitches') + 1})
        for _ in range(3):
            try:
                C('set_track_input', {'track': T, 'source': 'No Input'})
                break
            except client.BridgeError:
                pass
        C('set_track_output', {'track': T, 'dest': 'FX BUS'})
        colour = C('get_track', {'track': 'FX - transitions'}).get('color_index')
        C('set_track', {'track': T, 'volume_db': -12.0, **({'color_index': colour} if colour is not None else {})})
        C('set_send', {'track': T, 'send': 2, 'db': -14.0})          # C-Atmos


def hits():
    rev = find('Cymbal Crash Reverse Gnirob.wav')
    imp = find('Impact Dub Chamber.aif')
    rev_beats = sf.info(rev).duration * BPM / 60.0
    have = C('get_track', {'track': T, 'clips': True}).get('clips', [])
    if not any(abs(c['start'] - (DOWN - rev_beats)) < 0.05 for c in have):
        C('create_audio_clip', {'track': T, 'path': rev, 'beat': DOWN - rev_beats, 'name': 'reverse crash into break 1',
                                'warp': False, 'gain_db': 0.0})
    if not any(abs(c['start'] - DOWN) < 0.05 for c in have):
        C('create_audio_clip', {'track': T, 'path': imp, 'beat': DOWN, 'name': 'impact break 1', 'warp': False,
                                'gain_db': -6.0})
    print('reverse crash', round(rev_beats, 2), 'beats before bar', BAR)


def crash_and_boom():
    crash = C('get_notes', {'track': 'CRASH 909', 'clip': {'at': DOWN}})
    C('add_notes', {'track': 'CRASH 909', 'clip': {'at': DOWN}, 'notes': [[p, b, d, 112.0] for p, b, d, v in crash],
                    'replace': True})
    C('set_send', {'track': 'CRASH 909', 'send': 2, 'db': -16.0})
    booms = C('get_track', {'track': 'FX - sub boom', 'clips': True})['clips']
    if not any(abs(c['start'] - DOWN) < 0.05 for c in booms):
        C('duplicate_clip', {'track': 'FX - sub boom', 'clip': {'at': 256.0}, 'beat': DOWN})
    C('set_clip', {'track': 'FX - transitions', 'clip': {'at': DOWN}, 'gain_db': 8.0})


if __name__ == '__main__':
    track()
    hits()
    crash_and_boom()
    for t in (T, 'FX - sub boom', 'CRASH 909'):
        x = C('get_track', {'track': t, 'clips': True})
        print(t, x['vol_db'], [(round(c['start'] / 4 + 1, 2), c['name']) for c in x['clips'] if 44 <= c['start'] / 4 + 1 < 53])
