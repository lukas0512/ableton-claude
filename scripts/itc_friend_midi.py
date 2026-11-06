"""In the City: the final City riff as MIDI for his friend (stabs, guitar and bass, one track each).

Reads the arrangement clips as Live plays them (start marker, loop, muted clips skipped) into song beats and writes:
- "Final - drop 2 (comp 113-152, o original dele).mid": his hand-made stretch, from bar 113 = beat 0;
- "Final - musica inteira (do compasso 1).mid": the whole song, dropped at bar 1.
The bass Simpler sounds three octaves under its notes (E4 plays E1), so the bass is written -36, in its real register.
The clips carry the 'Swing 16ths 66' groove from the pool: the files hold the notes, not the groove.
"""
from pathlib import Path
import sys

import mido

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_claude import client
from itc_city_bass_lock import GTR, STABS

C = client.call
OUT = Path('/Users/lukasgalhardo/Desktop/Projects 26:27/In the City  Project/MIDI pro amigo - In the City')
PARTS = [('City Stabs', STABS, 0), ('City Guitarra', GTR, 0), ('Baixo', 'BASS', -36)]


def song_notes(track, shift):
    out = []
    for cl in C('get_track', {'track': track, 'clips': True})['clips']:
        if cl.get('muted') or cl.get('type') != 'midi':
            continue
        info = C('set_clip', {'track': track, 'clip': cl['i'], 'name': cl['name']})
        sm, ls, le = info['start_marker'], info['loop_start'], info['loop_end']
        notes = C('get_notes', {'track': track, 'clip': cl['i']})
        if info.get('looping'):
            span = le - ls
            # first pass from the start marker to the loop end, then the loop repeated
            pos, first = cl['start'], True
            while pos < cl['end'] - 1e-6:
                a = sm if first else ls
                for p, b, d, v in notes:
                    if a - 1e-6 <= b < le - 1e-6:
                        s = pos + b - a
                        if s < cl['end'] - 1e-6:
                            out.append((p + shift, s, min(d, cl['end'] - s), v))
                pos += le - a
                first = False
                if span <= 0:
                    break
        else:
            em = info.get('end_marker', le)
            for p, b, d, v in notes:
                if sm - 1e-6 <= b < em - 1e-6:
                    s = cl['start'] + b - sm
                    if s < cl['end'] - 1e-6:
                        out.append((p + shift, s, min(d, cl['end'] - s), v))
    return sorted(out, key=lambda n: n[1])


def write(name, parts, origin, until=None):
    mid = mido.MidiFile(type=1, ticks_per_beat=480)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(127)))
    meta.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))
    mid.tracks.append(meta)
    for ch, (tname, notes) in enumerate(parts):
        tr = mido.MidiTrack()
        tr.append(mido.MetaMessage('track_name', name=tname))
        ev = []
        for p, s, d, v in notes:
            if s < origin - 1e-6 or (until is not None and s >= until - 1e-6):
                continue
            e = s + d if until is None else min(s + d, until)
            ev.append((round((s - origin) * 480), 1, p, int(v)))
            ev.append((round((e - origin) * 480), 0, p, 0))
        ev.sort(key=lambda x: (x[0], x[1]))
        t = 0
        for tick, on, p, v in ev:
            tr.append(mido.Message('note_on' if on else 'note_off', channel=ch, note=p, velocity=v, time=tick - t))
            t = tick
        mid.tracks.append(tr)
    mid.save(OUT / f'{name}.mid')
    return sum(len(n) for _, n in parts)


if __name__ == '__main__':
    parts = [(n, song_notes(t, sh)) for n, t, sh in PARTS]
    for n, notes in parts:
        print(n, len(notes), 'notes, bars', round(notes[0][1] / 4 + 1, 2), '-', round(notes[-1][1] / 4 + 1, 2),
              'pitch', min(x[0] for x in notes), max(x[0] for x in notes))
    write('Final - drop 2 (comp 113-152, o original dele)', parts, origin=112 * 4.0, until=152 * 4.0)
    write('Final - musica inteira (do compasso 1)', parts, origin=0.0)
    print(sorted(p.name for p in OUT.glob('*.mid')))
