"""In the City: the City riff as a dialogue between long notes and a fingerpicked guitar, two different timbres.

His note (2026-11-05): "o call tem que ser de um timbre e o response no outro ... as notas longas num timbre
diferente, e o outro riffzinho, mais um dedilhado, notas trocando, com outro ... pra se encaixarem e falarem um com o
outro, como se estivessem um dentro do outro ... não precisa repetir o mesmo groove ... gostei de quando colocava só
a primeira e segunda nota, só a cabeça ... dá uma variação". Two guitars playing the same riff was not that.

Built on the riff read from the sample (itc_city_riff_midi.py): Em (0-3.75), D (3.75-5.5), C (5.5-6.5), F add9 (6.5-8).
LONG: the sample's top line E5 -> D5 -> C5 held, in open fifths (B4, A4, G4 under), entering at 0.75, 3.75, 5.5.
PICK: the guitar fingerpicks each chord in alternating notes and rests on every long-note attack, so each fills the
other's gaps. An 8-bar cycle: phrases 1 and 3 full (3 with a G4 colour and the long line rising to G5), 2 and 4 only
the head of each chord (its first two notes), 4 with a fill back into 1. The cycle runs on song position, so it
carries on across clips.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
BUS = 'CITY SYNTH'
OLD = {'CITY CALL (synth 1)': 'CITY LONG (notas longas)', 'CITY RESPONSE (synth 2)': 'CITY PICK (dedilhado)'}
LONG, PICK = OLD.values()
GROOVE = 'Swing 16ths 66'
ORIGIN = 112.0            # bar 29, the first City clip: the 8-bar cycle counts from here
CANDIDATES = {
    'epiano': 'sounds/Piano & Keys/E-Piano MKI Mellow.adv',
    'pad': 'sounds/Pad/Warm Analog Pad.adg',
    'organ': 'sounds/Piano & Keys/Organ Analog.adg',
}


def long_phrase(k):
    top = [[75, 0.50, 0.25, 80], [76, 0.75, 2.75, 100], [74, 3.75, 1.50, 96], [72, 5.50, 2.25, 100]]
    low = [[71, 0.75, 2.75, 85], [69, 3.75, 1.50, 82], [67, 5.50, 2.25, 85]]
    if k == 2:                                  # phrase 3: the line lifts to G5 before falling
        top = [[75, 0.50, 0.25, 80], [76, 0.75, 1.75, 100], [79, 2.50, 1.00, 100], [74, 3.75, 1.50, 96],
               [72, 5.50, 2.25, 100]]
    if k == 3:                                  # phrase 4: C5 leans on B4 back into the top
        top = [[75, 0.50, 0.25, 80], [76, 0.75, 2.75, 100], [74, 3.75, 1.50, 96], [72, 5.50, 1.50, 100],
               [71, 7.00, 0.75, 90]]
    return top + low


def pick_phrase(k):
    if k in (0, 2):
        em = [[59, 0.0], [64, 0.25], [62, 1.0], [64, 1.25], [59, 1.75], [64, 2.0],
              [67 if k == 2 else 62, 2.5], [64, 2.75], [59, 3.25], [64, 3.5]]
        d = [[57, 4.0], [62, 4.25], [62, 4.75], [57, 5.0], [62, 5.25]]
        c = [[60, 5.75], [64, 6.0], [59, 6.25]]
        f = [[53, 6.5], [60, 6.5], [57, 6.75], [64, 7.0], [60, 7.25], [57, 7.5], [60, 7.75]]
        notes = em + d + c + f
    else:                                       # only the head of each chord
        notes = [[59, 0.0], [64, 0.25], [57, 4.0], [62, 4.25], [60, 5.75], [64, 6.0], [53, 6.5], [60, 6.5], [57, 6.75]]
        if k == 3:
            notes += [[64, 7.25], [60, 7.5], [59, 7.75]]
    out = []
    for p, b in notes:
        accent = (b * 4) % 2 == 1                # the off 16ths speak a little louder: the bounce
        out.append([p, b, 0.5 if b == 6.5 else 0.25, 100 if accent else 84])
    return out


def cycle_notes(start, length, phrase_fn):
    notes = []
    k = 0.0
    while k < length - 1e-6:
        idx = int(round((start + k - ORIGIN) / 8.0)) % 4
        for p, b, d, v in phrase_fn(idx):
            if k + b < length - 1e-6:
                notes.append([p, k + b, min(d, length - k - b), float(v)])
        k += 8.0
    return notes


def tracks():
    names = [t['name'] for t in C('get_song', {})['tracks']]
    for old, new in OLD.items():
        if old in names:
            C('set_track', {'track': old, 'name': new})
    C('set_track', {'track': LONG, 'pan': -0.15})
    C('set_track', {'track': PICK, 'pan': 0.25})


def sound(name='epiano'):
    devs = C('get_track', {'track': LONG})['devices']
    for d in reversed(devs):
        if d['name'] != 'Delay':
            C('delete_device', {'track': LONG, 'device': d['i']})
    C('load_device', {'track': LONG, 'path': CANDIDATES[name]}, timeout=40.0)
    devs = C('get_track', {'track': LONG})['devices']
    inst = next(d for d in devs if d['name'] != 'Delay')
    if inst['i'] != 0:
        C('move_device', {'track': LONG, 'device': inst['i'], 'position': 0})
    print(LONG, [d['name'] for d in C('get_track', {'track': LONG})['devices']])


def clips():
    spans = [(c['start'], c['end']) for c in C('get_track', {'track': BUS, 'clips': True})['clips']]
    for t, fn in ((LONG, long_phrase), (PICK, pick_phrase)):
        for c in reversed(C('get_track', {'track': t, 'clips': True}).get('clips', [])):
            C('delete_clip', {'track': t, 'clip': c['i']})
        for a, z in spans:
            C('create_midi_clip', {'track': t, 'beat': a, 'length': z - a, 'name': t.split(' (')[0].title(),
                                   'notes': cycle_notes(a, z - a, fn)}, timeout=60.0)
        print(t, C('apply_groove', {'track': t, 'groove': GROOVE}))


LEVELS = {'epiano': 1.8, 'pad': -2.3, 'organ': -9.4}   # long notes 1.5 dB under the guitar, riff ~-24.5 LUFS in drop 1


def level(long_db=-9.4, pick_db=3.0):
    C('set_track', {'track': LONG, 'volume_db': long_db})
    C('set_track', {'track': PICK, 'volume_db': pick_db})


if __name__ == '__main__':
    steps = {'tracks': tracks, 'sound': sound, 'clips': clips, 'level': level}
    args = sys.argv[1:] or list(steps)
    for name in args:
        if name in CANDIDATES:
            sound(name)
            continue
        print(name)
        steps[name]()
