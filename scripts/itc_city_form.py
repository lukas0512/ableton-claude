"""In the City: the City stabs and guitar written as phrases A B C D in a repeating form, one groove for everyone.

His note (2026-11-05): "respeitar as melodias, tipo A B A C, A B A B, A B A C, A B C D ... não tem muita repetição,
às vezes você não pega o groove ... o stab pode melhorar no timbre e na melodia, acompanhar mais, fazer a harmonia,
o balanço e o movimento da música têm que estar nele ... a guitarra call & response com o stab, com a música, com os
vocais ... todo mundo tem que dançar na mesma".

The vocal gives no fixed accent to follow (its onsets per 16th of the 2-bar cycle are flat within 1-3 dB: the rap
fills every slot), so the shared groove is the drums' and the bass's: off-beat 8ths with the open hat, the bass's
tresillo (0, 0.75, 1.5 | 4, 4.75, 5.5). The STAB comps on the off-beats, lands with the bass on 1.5 and 5.5 and
pushes a 16th before each bar line; its top voice is a melody. Four 2-bar phrases:
  A  the groove: tops D5 D5 E5 D5 | C5 B4 A4 B4
  B  the line moves: D5 E5 D5 B4 | C5 B4 C5 B4, the guitar answers at 3.5 and 7.5
  C  the answer: displaced (0.75 1.5 2.25 3.0 | 4.5 5.25 6.5 7.5), the guitar fills 1.75 and 5.75
  D  the turnaround: driving 8ths, B7 (D#) at the end, the bass's own D-D#-E; the guitar's D#4 -> E4 slide
Form per 32 bars: A B A C  A B A B  A B A C  A B C D, restarting at each City section. Chords still come from the
bass root (E -> Em9, A -> Am9, B -> B7sus4); a voicing is picked for each top note, E4-E5. The guitar stays in the
mids (D4-G4) and stays out where a voice fills the bar (itc_vocal_map.py).
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_claude import client
from itc_city_bass_lock import BUS, STABS, GTR, bass, pocket, root_at
from itc_city_bounce import voiced_bars

C = client.call
FORM = 'ABACABABABACABCD'
STAB_LEN, PUSH_LEN = 0.23, 0.40
# voicings by bass root, keyed by the top note
VOICE = {
    4: {74: [66, 67, 71, 74], 76: [67, 71, 74, 76], 71: [64, 66, 67, 71], 78: [67, 71, 74, 78]},     # Em9
    9: {72: [64, 67, 71, 72], 71: [60, 64, 67, 71], 76: [67, 71, 72, 76], 69: [60, 64, 67, 69]},     # Am9
    11: {71: [64, 66, 69, 71], 69: [59, 64, 66, 69], 76: [66, 69, 71, 76], 75: [63, 66, 69, 75]},    # B7sus4 / B7
}
# (beat, top note, push?) per phrase
STAB = {
    'A': [(0.5, 74, 0), (1.5, 74, 0), (2.5, 76, 0), (3.25, 74, 1), (4.5, 72, 0), (5.5, 71, 0), (6.5, 69, 0), (7.25, 71, 1)],
    'B': [(0.5, 74, 0), (1.5, 76, 0), (2.5, 74, 0), (3.25, 71, 1), (4.5, 72, 0), (5.5, 71, 0), (6.5, 72, 0), (7.25, 71, 1)],
    'C': [(0.75, 76, 0), (1.5, 74, 0), (2.25, 71, 0), (3.0, 74, 1), (4.5, 72, 0), (5.25, 71, 0), (6.5, 69, 0), (7.5, 71, 0)],
    'D': [(0.5, 74, 0), (1.5, 76, 0), (2.5, 78, 0), (3.5, 76, 0), (4.5, 76, 0), (5.0, 72, 0), (5.5, 71, 0), (6.0, 71, 0),
          (6.5, 75, 0), (7.0, 75, 0)],
}
GUITAR = {
    'A': [],
    'B': [(3.5, 64, .30, 104), (3.75, 62, .12, 74), (7.5, 64, .30, 100)],
    'C': [(1.75, 67, .25, 100), (2.0, 64, .25, 90), (5.75, 62, .25, 98), (6.0, 64, .30, 96)],
    'D': [(3.75, 64, .25, 100), (7.5, 63, .10, 84), (7.75, 64, .30, 106)],
}


def voicing(root, top):
    table = VOICE.get(root, VOICE[4])
    if top in table:
        return table[top]
    return table[min(table, key=lambda t: abs(t - top))]


SECTION_BARS = (29, 65, 113, 121)       # the form restarts here: the City's entry, drop 1, break 2's tail, drop 2


def sections(spans):
    starts = [(b - 1) * 4.0 for b in SECTION_BARS]
    end = max(z for _, z in spans)
    return [(s, starts[k + 1] if k + 1 < len(starts) else end) for k, s in enumerate(starts)]


def write(a, z, section_start, notes, voiced):
    stabs, gtr = [], []
    cell = a
    while cell < z - 1e-6:
        letter = FORM[int(round((cell - section_start) / 8.0)) % 16]
        for b, top, push in STAB[letter]:
            s = cell + pocket(b)
            if s >= z - 1e-6:
                continue
            root = root_at(notes, s)
            if letter == 'D' and b >= 6.5 and root == 11:
                top = 75                                    # B7: the D# the bass's fill plays
            for k, p in enumerate(voicing(root, top)):
                vel = (100 if push else 92) + (6 if k == 3 else 0)
                stabs.append([p, s - a, min(PUSH_LEN if push else STAB_LEN, z - s), float(vel)])
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
    print('stab notes', n[0], 'guitar notes', n[1], 'guitar on a stab', clash, 'sections', [(s / 4 + 1, e / 4 + 1) for s, e in secs])


def stab_tone():
    """A little movement and body: Chorus-Ensemble and a soft Saturator before the filter."""
    have = [d['name'] for d in C('get_track', {'track': STABS})['devices']]
    if 'Saturator' not in have:
        C('load_device', {'track': STABS, 'path': 'audio_effects/Saturator'}, timeout=30.0)
    if 'Chorus-Ensemble' not in have:
        C('load_device', {'track': STABS, 'path': 'audio_effects/Chorus-Ensemble'}, timeout=30.0)
    order = ['Saturator', 'Chorus-Ensemble', 'Auto Filter', 'Utility', 'Echo']
    for pos, name in enumerate(order, start=1):
        names = [d['name'] for d in C('get_track', {'track': STABS})['devices']]
        if name in names and names.index(name) != pos:
            C('move_device', {'track': STABS, 'device': name, 'position': pos})
    for dev, name, kw in (('Saturator', 'Drive', {'display': '3.0 dB'}), ('Saturator', 'Dry/Wet', {'display': '35 %'}),
                          ('Chorus-Ensemble', 'Dry/Wet', {'display': '30 %'}), ('Chorus-Ensemble', 'Amount', {'display': '35 %'}),
                          ('Chorus-Ensemble', 'Warmth', {'display': '20 %'})):
        try:
            C('set_param', {'track': STABS, 'device': dev, 'param': name, **kw})
        except client.BridgeError as e:
            print(' ', dev, name, str(e).split('\n')[0][:100])
    print(STABS, [d['name'] for d in C('get_track', {'track': STABS})['devices']])


def level():
    # denser comping read 3 dB over the previous stabs (riff -20.7 vs -23.8 LUFS, bars 65-80): fader 6 -> 3
    C('set_track', {'track': STABS, 'volume_db': 3.0})


if __name__ == '__main__':
    steps = {'clips': clips, 'tone': stab_tone, 'level': level}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
