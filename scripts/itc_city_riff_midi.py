"""In the City: the City synth riff as MIDI, so another sound can play it.

His note (2026-11-05): the separated guitar sounded chopped ("picotado"); "me faz o MIDI disso, exatamente como tá
lá, pra gente sintetizar outro que faz a mesma melodia". Every City synth file is the same 2-bar phrase repeated
exactly (repeats correlate 1.00), so the phrase was read once from the 16 repeats of 'City synth 65-96' folded on its
warp markers: spectral peaks per 16th, CQT tuned to the sample's own -27 cents (the sample sits 27 cents flat of A440;
this MIDI plays at A440, in tune with the bass). 57 of 58 peaks in the folded original are notes here.

Phrase (beats 0-8): E minor (B3 E4, the line in octaves D#->E up to E5), E5 again at 2.75 and 3.25, E5 -> D#5 -> D5
at 3.75-4, D at 4.75, C (C4 C5 C6) at 5.5, B3 passing at 6.25, then F add9 / Fmaj7 (F3 A3 C4 E4, G4 and F4 on the
hit, B3 under the E4) from 6.5 to the bar line. 'lead' is the top line, 'chords' the rest.

Every CITY SYNTH clip starts at the head of the phrase (start markers 0, 16 and 112 are all multiples of 8 beats),
so the phrase is tiled from each clip's start and cut at its end, one MIDI clip per City synth clip.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
SRC = 'CITY SYNTH'
T = 'CITY RIFF (MIDI)'
PRESET = 'sounds/Guitar & Plucked/Clean Chorus Guitar.adv'
OUT = Path('/Users/lukasgalhardo/Desktop/Projects 26:27/In the City  Project/MIDI City riff')
PHRASE = 8.0

CHORDS = [
    [59, 0.00, 2.25, 95], [62, 0.00, 0.25, 85], [64, 0.25, 2.00, 95],
    [59, 2.50, 0.25, 75], [62, 2.50, 0.25, 70], [64, 2.75, 0.25, 80], [64, 3.25, 0.50, 88],
    [63, 3.75, 0.25, 70], [62, 4.00, 0.25, 75], [62, 4.75, 0.25, 95], [57, 4.75, 0.25, 75],
    [60, 5.50, 0.75, 100], [59, 6.25, 0.25, 80],
    [53, 6.50, 1.50, 95], [57, 6.50, 1.50, 92], [60, 6.50, 1.50, 105], [65, 6.50, 0.25, 90], [67, 6.50, 0.25, 100],
    [59, 6.75, 0.50, 100], [64, 6.75, 1.25, 100],
]
LEAD = [
    [63, 0.50, 0.25, 90], [75, 0.50, 0.25, 92], [76, 0.75, 1.50, 100],
    [76, 2.75, 0.25, 92], [76, 3.25, 0.50, 100], [75, 3.75, 0.25, 85], [74, 4.00, 0.25, 100], [74, 4.75, 0.25, 100],
    [72, 5.50, 0.50, 110], [84, 5.50, 0.25, 80], [76, 6.50, 0.25, 70],
]


def tiled(length):
    notes = []
    k = 0.0
    while k < length - 1e-6:
        for p, b, d, v in CHORDS + LEAD:
            s = k + b
            if s < length - 1e-6:
                notes.append([p, s, min(d, length - s), float(v)])
        k += PHRASE
    return notes


def midi_files():
    import mido
    OUT.mkdir(parents=True, exist_ok=True)
    for name, notes in (('City riff - completo', CHORDS + LEAD), ('City riff - melodia', LEAD),
                        ('City riff - acordes', CHORDS)):
        mid = mido.MidiFile(ticks_per_beat=480)
        tr = mido.MidiTrack()
        mid.tracks.append(tr)
        tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(127)))
        tr.append(mido.MetaMessage('track_name', name=name))
        ev = []
        for rep in range(4):                                  # 8 bars
            for p, b, d, v in notes:
                ev += [(round((rep * PHRASE + b) * 480), 1, p, v), (round((rep * PHRASE + b + d) * 480), 0, p, 0)]
        t = 0
        for tick, on, p, v in sorted(ev, key=lambda e: (e[0], e[1])):
            tr.append(mido.Message('note_on' if on else 'note_off', note=p, velocity=int(v), time=tick - t))
            t = tick
        mid.save(OUT / f'{name}.mid')
    print('midi files in', OUT)


def place():
    names = [t['name'] for t in C('get_song', {})['tracks']]
    if T not in names:
        C('create_track', {'kind': 'midi', 'name': T, 'index': names.index('CITY PAD') + 1})
        C('load_device', {'track': T, 'path': PRESET}, timeout=40.0)
        colour = C('get_track', {'track': SRC}).get('color_index')
        if colour is not None:
            C('set_track', {'track': T, 'color_index': colour})
    C('set_track_output', {'track': T, 'dest': SRC})
    C('set_track', {'track': T, 'volume_db': 3.0})      # riff alone -20.9 LUFS in drop 1, the sample's -20.8
    if C('get_track', {'track': T, 'clips': True}).get('clips'):
        print('clips already there')
        return
    for c in C('get_track', {'track': SRC, 'clips': True})['clips']:
        length = c['end'] - c['start']
        C('create_midi_clip', {'track': T, 'beat': c['start'], 'length': length, 'name': 'City riff',
                               'notes': tiled(length)}, timeout=60.0)
    print(T, len(C('get_track', {'track': T, 'clips': True})['clips']), 'clips')


def midi_only():
    """The riff from MIDI alone: the separated guitar muted (not deleted)."""
    C('set_track', {'track': 'CITY GUITAR', 'mute': True})
    C('set_track', {'track': 'CITY PAD', 'volume_db': -70.0})


if __name__ == '__main__':
    steps = {'files': midi_files, 'place': place, 'midi_only': midi_only}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
