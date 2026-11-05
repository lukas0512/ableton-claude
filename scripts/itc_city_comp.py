"""In the City: the City stabs back to accompaniment, the vocal is the lead.

His note (2026-11-05, on itc_city_form.py): "agora os stabs ficaram demais ... o lead é o vocal. Os stabs são só
para acompanhar o groove, o balanço, dar aquela marcada, criar corpo ... você colocou como lead, fazendo frases".

The stab loses its phrases and its top line: one fixed voicing per chord (Em9 top D5, Am9 top C5, B7sus4 top B4,
the smallest moves between them) and one pattern everywhere: two short off-beats a bar in the bass's holes
(0.5, 2.5 | 4.5, 6.5). Under a voice only the first of each bar. The only change is the 16th push into B7 at the end
of each 32-bar form (phrase D), where the bass plays its own D#. The guitar keeps its answers (itc_city_form.py).
taste.md: stabs short (~110 ms), off the beat, at most 2 changes per 8 bars.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_claude import client
from itc_city_bass_lock import BUS, STABS, GTR, bass, pocket, root_at
from itc_city_bounce import voiced_bars
from itc_city_form import FORM, GUITAR, sections

C = client.call
FIXED = {4: [66, 67, 71, 74], 9: [64, 67, 71, 72], 11: [64, 66, 69, 71]}
B7 = [63, 66, 69, 71]
HITS = [0.5, 2.5, 4.5, 6.5]
STAB_LEN = 0.23


def write(a, z, section_start, notes, voiced):
    stabs, gtr = [], []
    cell = a
    while cell < z - 1e-6:
        letter = FORM[int(round((cell - section_start) / 8.0)) % 16]
        hits = [(b, 0) for b in HITS] + ([(7.25, 1)] if letter == 'D' else [])
        for b, push in hits:
            s = cell + pocket(b)
            if s >= z - 1e-6:
                continue
            if int(s // 4) in voiced and (b % 4) != 0.5 and not push:
                continue                                   # under the voice: one mark a bar
            root = root_at(notes, s)
            chord = B7 if push and root == 11 else FIXED.get(root, FIXED[4])
            for p in chord:
                stabs.append([p, s - a, min(0.4 if push else STAB_LEN, z - s), 96.0 if push else 90.0])
        for b, p, d, v in GUITAR[letter]:
            s = cell + pocket(b)
            if s < z - 1e-6 and int(s // 4) not in voiced:
                gtr.append([p, s - a, min(d, z - s), float(v)])
        cell += 8.0
    return stabs, gtr


def clips():
    notes = bass()
    voiced = voiced_bars()
    spans = [(c['start'], c['end']) for c in C('get_track', {'track': BUS, 'clips': True})['clips']]
    secs = sections(spans)
    for t in (STABS, GTR):
        for c in reversed(C('get_track', {'track': t, 'clips': True}).get('clips', [])):
            C('delete_clip', {'track': t, 'clip': c['i']})
    n = [0, 0]
    clash = 0
    for a, z in spans:
        start = next(s for s, e in secs if s <= a < e)
        st, gt = write(a, z, start, notes, voiced)
        on = {round(b, 3) for _, b, _, _ in st}
        clash += sum(1 for _, b, _, _ in gt if any(abs(b - o) < 0.15 for o in on))
        for k, (t, ns) in enumerate(((STABS, st), (GTR, gt))):
            C('create_midi_clip', {'track': t, 'beat': a, 'length': z - a, 'name': 'City ' + ('Stabs' if k == 0 else 'Gtr'),
                                   'notes': ns}, timeout=60.0)
            n[k] += len(ns)
    print('stab notes', n[0], 'hits', n[0] // 4, 'guitar notes', n[1], 'guitar on a stab', clash)


if __name__ == '__main__':
    steps = {'clips': clips}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
