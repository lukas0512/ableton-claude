"""In the City: the City synth channel split into its guitar and its pad.

His note (2026-11-05): "separar o synth/guitar do canal city synth do pad que está tocando no fundo". The Gate (floor
-36) only lowered the pad between hits; under each hit the pad still played. BS-Roformer SW (6 stems: guitar, piano,
other...) pulls the guitar chords out clean: silence between hits at -66 dB, where htdemucs_6s left the guitar 8 dB
under a mixed 'other'. The 'other' stem holds the held chord pad (B3-E4) and the high synth line.
Stems: Samples/Processed/City synth split/<file> - guitar|pad.wav (made by the BS-Roformer-SW pass).

CITY GUITAR and CITY PAD play the same clips as CITY SYNTH (position, warp markers, markers, gain) and feed CITY SYNTH,
which now monitors "in" as their bus: its EQ, filter, compressor, sends, pan and fader stay. Its Gate goes off (nothing
left to gate) and its own clips are muted, so `pad` at -inf is the guitar alone; raise CITY PAD to bring the pad back.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, elements

C = client.call
SRC = 'CITY SYNTH'
STEMS = Path('/Users/lukasgalhardo/Desktop/Projects 26:27/In the City  Project/Samples/Processed/City synth split')
NAMES = {'guitar': 'CITY GUITAR', 'pad': 'CITY PAD'}


batch = client.batch


def place():
    names = [t['name'] for t in C('get_song', {})['tracks']]
    if all(n in names for n in NAMES.values()):
        print('already placed')
        return
    info, by_file = elements.source_clips(C, SRC)
    results = {}
    for src in by_file:
        stem = Path(src).stem
        results[src] = {'elements': {k: {'file': str(STEMS / f'{stem} - {k}.wav'), 'silent': False} for k in NAMES}}
        for e in results[src]['elements'].values():
            assert Path(e['file']).exists(), e['file']
    index = names.index(SRC)
    out = elements.place(C, batch, SRC, index, info, by_file, results, mute_source=True)
    print(out)
    colour = C('get_track', {'track': SRC}).get('color_index')
    for k, new in NAMES.items():
        made = next(t for t in out['tracks'] if t.startswith(k.upper()))
        C('set_track', {'track': made, 'name': new, 'volume_db': 0.0, 'pan': 0.0})
        if colour is not None:
            C('set_track', {'track': new, 'color_index': colour})
        C('set_track_input', {'track': new, 'source': 'No Input'})


def bus():
    C('set_track_input', {'track': SRC, 'source': 'No Input'})
    for new in NAMES.values():
        C('set_track_output', {'track': new, 'dest': SRC})
    C('set_track', {'track': SRC, 'monitoring': 'in'})
    C('set_device_on', {'track': SRC, 'device': 'Gate', 'on': False})


def guitar_only():
    C('set_track', {'track': NAMES['pad'], 'volume_db': -70.0})


if __name__ == '__main__':
    steps = {'place': place, 'bus': bus, 'guitar_only': guitar_only}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
    for t in (SRC, *NAMES.values()):
        print(t, {k: v for k, v in C('get_track', {'track': t}).items() if k in ('vol_db', 'pan', 'n_clips', 'devices')})
