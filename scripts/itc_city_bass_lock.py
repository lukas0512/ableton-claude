"""In the City: the City riff rebuilt on the bass, stabs in its holes and a guitar riding its rhythm.

His note (2026-11-05): "ainda tá ruim ... uma parada mais interessante, mais no groove da música, mais parecido com
o baixo, pra encaixar no baixo". The riff read from the sample played D, C and F add9 in its second bar while the bass
plays A then B: C over B is a semitone, F over B a tritone. Everything here is derived bar by bar from the BASS notes:

- harmony from the bass root: E -> Em9, G (passing in the E bar) stays Em9, A -> Am9, B -> B7sus4, D/D# (fills) ->
  no chord change. Rootless voicings around G4-F#5 (the references' stabs ~780 Hz), moving by step.
- STABS (taste.md: short ~110 ms, 74 % off the beat, in the bass's holes): candidates on the off 8ths/16ths of the
  bass's rests (0.5, 2.25, 2.75 | 4.5, 6.25, 6.75, 7.25 of each 2-bar cell), dropped when a bass note starts within
  a 16th. Phrases 2 and 4 of each 8 bars add a pickup at 3.25.
- GUITAR: on every bass hit the chord's fifth, a 16th later the root an octave up (alternating notes), two octaves
  over the bass. Phrases 1 and 3 of each 8 bars ride every hit; 2 and 4 only the first two hits of each bar (the head).
- Pocket: the bass carries its swing in the notes (off 16ths at +0.0225 beat): every written part gets the same
  offset, and no pool groove on top (taste.md: one pocket, never counted twice).
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
BUS = 'CITY SYNTH'
RENAME = {'CITY LONG (notas longas)': 'CITY STABS', 'CITY PICK (dedilhado)': 'CITY GTR (riff)'}
STABS, GTR = RENAME.values()
ORIGIN = 112.0
POCKET = 0.0225
STAB_LEN = 0.23                       # ~110 ms at 127 BPM
VOICING = {4: [67, 71, 74, 78],      # Em9 rootless: G4 B4 D5 F#5
           9: [67, 71, 72, 76],      # Am9 rootless: G4 B4 C5 E5
           11: [69, 71, 76, 78]}     # B7sus4: A4 B4 E5 F#5
FIFTH_ROOT = {4: (71, 76), 7: (74, 67), 9: (76, 69), 11: (66, 71), 2: (69, 74), 3: (75, 75)}
STAB_SLOTS = [0.5, 2.25, 2.75, 4.5, 6.25, 6.75, 7.25]
SOUNDS = {'organ': 'sounds/Piano & Keys/Organ Analog.adg', 'epiano': 'sounds/Piano & Keys/E-Piano MKI Mellow.adv'}
STAB_DB = {'organ': -4.0, 'epiano': 4.0}          # level-matched riff in drop 1 (E-piano at +7.2 read 2.8 dB over)
GUITAR = 'sounds/Guitar & Plucked/Guitar Electric Clean.adg'


def bass():
    tr = C('get_track', {'track': 'BASS', 'clips': True})
    out = []
    for cl in tr['clips']:
        if cl.get('muted'):
            continue
        sm = C('set_clip', {'track': 'BASS', 'clip': cl['i'], 'name': cl['name']}).get('start_marker') or 0.0
        for p, b, d, v in C('get_notes', {'track': 'BASS', 'clip': cl['i']}):
            s = cl['start'] + b - sm
            if cl['start'] <= s < cl['end']:
                out.append((round(s, 4), p % 12))
    return sorted(out)


def pocket(b):
    k = round(b * 4)
    return k / 4 + (POCKET if k % 2 else 0.0)


def root_at(notes, beat):
    """The bass root that holds at `beat`: the last E, A or B struck at or before it in the same bar."""
    bar0 = beat - (beat - ORIGIN) % 4
    roots = [p for s, p in notes if bar0 <= s <= beat + 1e-3 and p in VOICING]
    if roots:
        return roots[-1]
    prev = [p for s, p in notes if s < bar0 and p in VOICING]
    return prev[-1] if prev else 4


def parts(a, z, notes):
    stabs, gtr = [], []
    cell = a
    while cell < z - 1e-6:
        phrase = int(round((cell - ORIGIN) / 8.0)) % 4
        inside = [(s - cell, p) for s, p in notes if cell - 1e-3 <= s < cell + 8 - 1e-3]
        slots = STAB_SLOTS + ([3.25] if phrase in (1, 3) else [])
        for slot in slots:
            b = cell + slot
            if b >= z - 1e-6 or any(abs(s - slot) < 0.2 for s, _ in inside):
                continue
            root = root_at(notes, b)
            for k, p in enumerate(VOICING[root]):
                stabs.append([p, pocket(slot) + cell - a, STAB_LEN, 92.0 + (6 if k == 3 else 0)])
        per_bar = {}
        for s, p in inside:
            bar = int(s // 4)
            per_bar.setdefault(bar, []).append((s, p))
        for bar, hits in per_bar.items():
            if phrase in (1, 3):
                hits = hits[:2]
            for s, p in hits:
                if p not in FIFTH_ROOT or cell + s >= z - 1e-6:
                    continue
                fifth, root = FIFTH_ROOT[p]
                gtr.append([fifth, s + cell - a, 0.25, 100.0])
                if cell + s + 0.25 < z - 1e-6 and p != 3:
                    gtr.append([root, pocket(round(s * 4) / 4 + 0.25) + cell - a, 0.2, 74.0])
        cell += 8.0
    return stabs, gtr


def tracks(stab_sound='organ'):
    names = [t['name'] for t in C('get_song', {})['tracks']]
    for old, new in RENAME.items():
        if old in names:
            C('set_track', {'track': old, 'name': new})
    sound(stab_sound)
    devs = C('get_track', {'track': GTR})['devices']
    if not devs or devs[0]['name'] != 'Guitar Electric Clean':
        for d in reversed(devs):
            if d['name'] != 'Delay':
                C('delete_device', {'track': GTR, 'device': d['i']})
        C('load_device', {'track': GTR, 'path': GUITAR}, timeout=40.0)
    C('set_param', {'track': GTR, 'device': 0, 'param': 'Release', 'display': '300 ms'})
    C('set_track', {'track': STABS, 'pan': 0.0})
    C('set_track', {'track': GTR, 'pan': 0.2})
    # stabs: dry and wide, movement from a slow filter (taste.md)
    for t in (STABS,):
        have = [d['name'] for d in C('get_track', {'track': t})['devices']]
        if 'Delay' in have:
            C('delete_device', {'track': t, 'device': 'Delay'})
        if 'Auto Filter' not in have:
            C('load_device', {'track': t, 'path': 'audio_effects/Auto Filter'}, timeout=30.0)
        if 'Utility' not in have:
            C('load_device', {'track': t, 'query': 'Utility'}, timeout=30.0)
        C('set_param', {'track': t, 'device': 'Utility', 'param': 'Stereo Width', 'display': '140 %'})
    C('set_send', {'track': STABS, 'send': 4, 'db': -24.0})
    C('set_send', {'track': STABS, 'send': 2, 'db': -26.0})
    C('set_send', {'track': STABS, 'send': 0, 'db': -70.0})


def sound(name='organ'):
    devs = C('get_track', {'track': STABS})['devices']
    inst = [d for d in devs if d['name'] not in ('Delay', 'Auto Filter', 'Utility')]
    if inst and inst[0]['name'] == Path(SOUNDS[name]).stem:
        return
    for d in reversed(inst):
        C('delete_device', {'track': STABS, 'device': d['i']})
    C('load_device', {'track': STABS, 'path': SOUNDS[name]}, timeout=40.0)
    first = C('get_track', {'track': STABS})['devices'][0]['name']
    if first != Path(SOUNDS[name]).stem:          # Live puts an instrument first already
        C('move_device', {'track': STABS, 'device': Path(SOUNDS[name]).stem, 'position': 0})
    print(STABS, [d['name'] for d in C('get_track', {'track': STABS})['devices']])


def filter_lfo():
    # a slow sweep, not a wobble: Live's floor is 0.10 Hz (a cycle every ~5 bars), so a shallow one
    for name, kw in (('Frequency', {'display': '3.20 kHz'}), ('Resonance', {'display': '15 %'}),
                     ('LFO Amount', {'display': '12 %'}), ('LFO Freq', {'display': '0.10 Hz'})):
        try:
            C('set_param', {'track': STABS, 'device': 'Auto Filter', 'param': name, **kw})
        except client.BridgeError as e:
            print(' auto filter', name, str(e).split('\n')[0][:80])


def clips():
    notes = bass()
    spans = [(c['start'], c['end']) for c in C('get_track', {'track': BUS, 'clips': True})['clips']]
    for t in (STABS, GTR):
        for c in reversed(C('get_track', {'track': t, 'clips': True}).get('clips', [])):
            C('delete_clip', {'track': t, 'clip': c['i']})
    n = [0, 0]
    for a, z in spans:
        st, gt = parts(a, z, notes)
        for k, (t, ns) in enumerate(((STABS, st), (GTR, gt))):
            C('create_midi_clip', {'track': t, 'beat': a, 'length': z - a, 'name': t.title(), 'notes': ns}, timeout=60.0)
            n[k] += len(ns)
    print('stab notes', n[0], 'guitar notes', n[1])


def level(stab_db=-4.0, gtr_db=2.0):   # riff -26.6 LUFS at -6/0 in drop 1; aim ~-24.5
    C('set_track', {'track': STABS, 'volume_db': stab_db})
    C('set_track', {'track': GTR, 'volume_db': gtr_db})


def dump():
    notes = bass()
    st, gt = parts(256.0, 264.0, notes)
    print('bass', [(round(s - 256, 3), p) for s, p in notes if 256 <= s < 264])
    print('stabs', sorted({round(b, 3) for p, b, d, v in st}))
    print('gtr', [(round(b, 3), p) for p, b, d, v in gt])


if __name__ == '__main__':
    steps = {'tracks': tracks, 'filter': filter_lfo, 'clips': clips, 'level': level, 'dump': dump}
    for name in sys.argv[1:] or ['tracks', 'filter', 'clips', 'level']:
        if name in SOUNDS:
            sound(name)
            continue
        print(name)
        steps[name]()
