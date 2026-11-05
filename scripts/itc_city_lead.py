"""In the City: the City guitar riff as a lead, the stabs moved out of its way.

His note (2026-11-05) on itc_city_bass_lock.py: "o City GTR riff ficou bem legal ... encaixar mais no groove, com os
delays ... um pouco mais complexo, mais lead ... a melodia ficou legal, dar um tapa. O stab fica muito fora com a
guitarra ... trocar o timbre, algo um pouco diferente".

Why the stab clashed: the guitar (F#4-E5) and the stab voicings (G4-F#5) shared one register. Now:
- STABS move down to E4-D5 (Em9 F#4 G4 B4 D5, Am9 E4 G4 B4 C5, B7sus4 E4 F#4 A4 B4), and give the holes to the lead
  on phrases 2 and 4 (only their heads at 0.5 and 4.5 there).
- LEAD: the alternating fifth/root on every bass hit, a step higher (B4-G5), plus its own answers in the bass's holes:
  phrase 2 a run G5-F#5-E5-D5-B4 and A5 falling to the D#5 leading tone, phrase 3 single answers at 3.0 and 7.0,
  phrase 4 a longer fall from B5. Same pocket as the bass written in.
- ECHO instead of the 3/16 Delay: 3/16 swaps on- and off-16ths, so every echo fell on an unswung 16th. 1/8 and 1/4
  keep each note's place in the swing. Ping-pong, ducked while the guitar plays, filtered 400 Hz-4.5 kHz.
- A soft Saturator before it: the sampled guitar read 7 dB dark at 3-6 kHz against the reference guitar.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_claude import client
from itc_city_bass_lock import BUS, STABS, GTR, ORIGIN, STAB_LEN, STAB_SLOTS, bass, pocket, root_at

C = client.call
VOICING = {4: [66, 67, 71, 74], 9: [64, 67, 71, 72], 11: [64, 66, 69, 71]}
PAIRS = {4: (71, 76), 7: (74, 79), 9: (72, 76), 11: (71, 78), 2: (69, 74), 3: (75, 75)}
FILLS = {
    1: [(2.0, 79, .25), (2.25, 78, .25), (2.5, 76, .5), (3.0, 74, .25), (3.25, 71, .25),
        (6.0, 76, .25), (6.25, 78, .25), (6.5, 81, .5), (7.0, 78, .25), (7.25, 76, .25), (7.5, 75, .25)],
    2: [(3.0, 76, .5), (7.0, 78, .5)],
    3: [(2.25, 76, .25), (2.5, 79, .5), (3.0, 78, .25), (3.25, 76, .25),
        (6.0, 83, .5), (6.5, 81, .25), (6.75, 79, .25), (7.0, 78, .25), (7.25, 76, .25), (7.5, 74, .25), (7.75, 75, .25)],
}
STAB_SOUNDS = {'epiano': 'sounds/Piano & Keys/E-Piano MKI Mellow.adv',
               'synth': 'sounds/Synth Keys/Stab Twice for Murder.adv'}


def parts(a, z, notes):
    stabs, lead = [], []
    cell = a
    while cell < z - 1e-6:
        phrase = int(round((cell - ORIGIN) / 8.0)) % 4
        inside = [(s - cell, p) for s, p in notes if cell - 1e-3 <= s < cell + 8 - 1e-3]
        per_bar = {}
        for s, p in inside:
            per_bar.setdefault(int(s // 4), []).append((s, p))
        for bar, hits in per_bar.items():
            if phrase in (1, 3):
                hits = hits[:2]                       # the head; the answers take the rest
            for s, p in hits:
                if p not in PAIRS or cell + s >= z - 1e-6:
                    continue
                hi, lo = PAIRS[p]
                lead.append([hi, s + cell - a, 0.25, 100.0])
                nxt = pocket(round(s * 4) / 4 + 0.25)
                if p != 3 and cell + nxt < z - 1e-6:
                    lead.append([lo, nxt + cell - a, 0.2, 78.0])
        for b, p, d in FILLS.get(phrase, []):
            if cell + b < z - 1e-6:
                accent = 98.0 if b in (2.5, 6.5, 6.0, 3.0, 7.0) else 88.0
                lead.append([p, pocket(b) + cell - a, min(d, z - cell - b), accent])
        here = [b - (cell - a) for _, b, _, _ in lead if cell - a <= b < cell - a + 8]
        slots = STAB_SLOTS if phrase in (0, 2) else [0.5, 4.5]
        for slot in slots:
            if cell + slot >= z - 1e-6 or any(abs(s - slot) < 0.2 for s, _ in inside) \
                    or any(abs(h - pocket(slot)) < 0.15 for h in here):
                continue                              # the bass's hole, and not under the lead
            for k, p in enumerate(VOICING[root_at(notes, cell + slot)]):
                stabs.append([p, pocket(slot) + cell - a, STAB_LEN, 90.0 + (6 if k == 3 else 0)])
        cell += 8.0
    return stabs, lead


def p(track, device, name, **kw):
    C('set_param', {'track': track, 'device': device, 'param': name, **kw})


def echo(track, wet, feedback, duck=True):
    have = [d['name'] for d in C('get_track', {'track': track})['devices']]
    if 'Delay' in have:
        C('delete_device', {'track': track, 'device': 'Delay'})
    if 'Echo' not in have:
        C('load_device', {'track': track, 'path': 'audio_effects/Echo'}, timeout=30.0)
    for name, kw in (('Link', {'value': 0.0}), ('L Sync', {'value': 1.0}), ('R Sync', {'value': 1.0}),
                     ('L Sync Mode', {'value': 3.0}), ('R Sync Mode', {'value': 3.0}),       # '16th' mode
                     ('L 16th', {'value': 2.0}), ('R 16th', {'value': 4.0}),                 # 1/8 and 1/4
                     ('Channel Mode', {'value': 1.0}), ('Feedback', {'display': f'{feedback} %'}),  # ping pong
                     ('Filter On', {'value': 1.0}), ('HP Freq', {'display': '400 Hz'}), ('LP Freq', {'display': '4.50 kHz'}),
                     ('Duck On', {'value': 1.0 if duck else 0.0}), ('Duck Thr', {'display': '-24.0 dB'}),
                     ('Duck Release', {'display': '120 ms'}), ('Reverb Level', {'display': '12 %'}),
                     ('Dly < Mod', {'display': '3.0 %'}), ('Dry Wet', {'display': f'{wet} %'})):
        try:
            p(track, 'Echo', name, **kw)
        except client.BridgeError as e:
            print(' echo', name, str(e).split('\n')[0][:90])


def lead_chain():
    have = [d['name'] for d in C('get_track', {'track': GTR})['devices']]
    if 'Saturator' not in have:
        C('load_device', {'track': GTR, 'path': 'audio_effects/Saturator'}, timeout=30.0)
    for name, kw in (('Drive', {'display': '4.0 dB'}), ('Dry/Wet', {'display': '45 %'})):
        p(GTR, 'Saturator', name, **kw)
    echo(GTR, 24, 35)
    if [d['name'] for d in C('get_track', {'track': GTR})['devices']].index('Echo') < \
            [d['name'] for d in C('get_track', {'track': GTR})['devices']].index('Saturator'):
        C('move_device', {'track': GTR, 'device': 'Echo', 'position': 9})
    C('set_track', {'track': GTR, 'pan': 0.1})
    print(GTR, [d['name'] for d in C('get_track', {'track': GTR})['devices']])


def stab_sound(name='epiano'):
    devs = C('get_track', {'track': STABS})['devices']
    inst = [d for d in devs if d['name'] not in ('Echo', 'Auto Filter', 'Utility')]
    if not (inst and inst[0]['name'] == Path(STAB_SOUNDS[name]).stem):
        for d in reversed(inst):
            C('delete_device', {'track': STABS, 'device': d['i']})
        C('load_device', {'track': STABS, 'path': STAB_SOUNDS[name]}, timeout=40.0)
        if C('get_track', {'track': STABS})['devices'][0]['name'] != Path(STAB_SOUNDS[name]).stem:
            C('move_device', {'track': STABS, 'device': Path(STAB_SOUNDS[name]).stem, 'position': 0})
    # dub chord: darker, a little resonance, its own echo in the groove (not ducked: the tail is the dub)
    for n, kw in (('Frequency', {'display': '1.80 kHz'}), ('Resonance', {'display': '25 %'})):
        p(STABS, 'Auto Filter', n, **kw)
    echo(STABS, 18, 30, duck=False)
    print(STABS, [d['name'] for d in C('get_track', {'track': STABS})['devices']])


def clips():
    notes = bass()
    spans = [(c['start'], c['end']) for c in C('get_track', {'track': BUS, 'clips': True})['clips']]
    for t in (STABS, GTR):
        for c in reversed(C('get_track', {'track': t, 'clips': True}).get('clips', [])):
            C('delete_clip', {'track': t, 'clip': c['i']})
    n = [0, 0]
    for a, z in spans:
        st, ld = parts(a, z, notes)
        for k, (t, ns) in enumerate(((STABS, st), (GTR, ld))):
            C('create_midi_clip', {'track': t, 'beat': a, 'length': z - a, 'name': t.title(), 'notes': ns}, timeout=60.0)
            n[k] += len(ns)
    print('stab notes', n[0], 'lead notes', n[1])


def level(stab_db=4.0, lead_db=3.5):   # riff -25.5 LUFS at +2 in drop 1
    C('set_track', {'track': STABS, 'volume_db': stab_db})
    C('set_track', {'track': GTR, 'volume_db': lead_db})


def dump():
    notes = bass()
    for start in (256.0, 264.0, 272.0, 280.0):
        st, ld = parts(start, start + 8, notes)
        print(int((start - ORIGIN) / 8) % 4, 'stabs', sorted({round(b, 2) for _, b, _, _ in st}),
              '\n   lead', [(round(b, 2), n) for n, b, _, _ in sorted(ld, key=lambda x: x[1])])


if __name__ == '__main__':
    steps = {'lead_chain': lead_chain, 'stabs': stab_sound, 'clips': clips, 'level': level, 'dump': dump}
    for name in sys.argv[1:] or ['lead_chain', 'stabs', 'clips', 'level']:
        if name in STAB_SOUNDS:
            stab_sound(name)
            continue
        print(name)
        steps[name]()
