"""In the City: one colour per family (taste.md section 8). Live's API cannot reorder or group tracks."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

COLOURS = {
    14: ['KICK', 'KICK - build (HP)', 'BASS', 'BASS - break', 'BASS - teaser (HP)', 'FX - sub boom'],
    1: ['LOW END'],
    15: ['CLAP', 'SNARE', 'CLAP - throw'],
    17: ['HAT 16ths', 'HAT OFF - persona', 'HAT OFF - shaker shot', 'HAT OFF - imite', 'RIDE 909', 'CRASH 909',
         'SHAKER played', 'SHAKER 16ths'],
    16: ['CONGAS', 'TOM 909', 'PERC LOOP', 'BREAKBEAT'],
    2: ['DRUMS', 'TOPS', 'PERC GROUP'],
    19: ['CITY SYNTH', 'MURDER RIFF (break 2)', 'MURDER RIFF (drop 2)', 'CHOPS - UKG babe'],
    4: ['MUSIC BUS', 'MURDER BUS - break', 'MURDER BUS - drop'],
    24: ['VOX CITY - calls', 'VOX CITY - hooks', 'VOX CITY - radio', 'VOX MURDER', 'VOX MURDER - trades', 'VOX - throws',
         'MURDER VOX+SCRATCH (drop 2)'],
    11: ['VOX BUS'],
    26: ['FX - transitions', 'FX - glitches'],
    12: ['FX BUS'],
    27: ['REF - City 2 City (original)', 'REF - Murder (original)'],
}

for colour, tracks in COLOURS.items():
    for t in tracks:
        client.call('set_track', {'track': t, 'color_index': colour})
names = {t for ts in COLOURS.values() for t in ts}
print('uncoloured:', [t['name'] for t in client.call('get_song', {})['tracks'] if t['name'] not in names])
