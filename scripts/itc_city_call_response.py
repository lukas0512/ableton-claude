"""In the City: the City riff as call & response between two synths.

His note (2026-11-05): "podemos fazer tipo um call response com 2 synths, pra encaixar mais, usar a mesma ideia mas
adaptar". The riff (itc_city_riff_midi.py) already asks and answers: beats 0-3.75 hold E minor under the D#->E5
line (the call), beats 3.75-8 answer D, C, F add9 (the response). The call stays long; the response is played
shorter (at most half a beat, the closing F three quarters) so air is left before the next call.

Timbre measured against the original riff isolated in drop 1 (set minus the set with the City muted), 1.6-6.4 kHz
bands and centroid: original -4.5/-6.2 dB, 3.75 kHz; Buzz Overtones Lead -6.9/-10.1, 2.5 kHz, narrow (side -3.2) and
the closest; Poly Saw 2.2 kHz and Dynamic Buzz Keys 2.1 kHz both too wide (side +8, +9); Clean Chorus Guitar 1.7 kHz.
The response gets Munster Funk keys (1.8 kHz, narrow, sustains): a different voice on the other side.

Both play into CITY SYNTH (their bus: EQ, compressor, sends, fader); the bus goes to the centre and each synth
takes a side. The separated stems (CITY GUITAR, CITY PAD) stay muted.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

sys.path.insert(0, str(Path(__file__).resolve().parent))
from itc_city_riff_midi import CHORDS, LEAD, PHRASE

C = client.call
BUS = 'CITY SYNTH'
CALL, RESP = 'CITY CALL (synth 1)', 'CITY RESPONSE (synth 2)'
OLD = 'CITY RIFF (MIDI)'
SOUNDS = {CALL: 'sounds/Synth Lead/Buzz Overtones Lead.adv', RESP: 'sounds/Synth Keys/Munster Funk.adv'}
PANS = {CALL: -0.35, RESP: 0.3}
SPLIT = 3.75


def parts():
    notes = CHORDS + LEAD
    call = [n for n in notes if n[1] < SPLIT]
    resp = [[p, b, min(d, 0.75 if b >= 6.5 else 0.5), v] for p, b, d, v in notes if b >= SPLIT]
    return {CALL: call, RESP: resp}


def tiled(phrase, length):
    out, k = [], 0.0
    while k < length - 1e-6:
        out += [[p, k + b, min(d, length - k - b), float(v)] for p, b, d, v in phrase if k + b < length - 1e-6]
        k += PHRASE
    return out


def tracks():
    names = [t['name'] for t in C('get_song', {})['tracks']]
    if OLD in names and CALL not in names:
        C('set_track', {'track': OLD, 'name': CALL})          # the riff track becomes synth 1
        names = [t['name'] for t in C('get_song', {})['tracks']]
    if RESP not in names:
        C('create_track', {'kind': 'midi', 'name': RESP, 'index': names.index(CALL) + 1})
    colour = C('get_track', {'track': BUS}).get('color_index')
    for t, preset in SOUNDS.items():
        devs = C('get_track', {'track': t})['devices']
        if not devs or devs[0]['name'] != Path(preset).stem:
            for d in reversed(devs):
                C('delete_device', {'track': t, 'device': d['i']})
            C('load_device', {'track': t, 'path': preset}, timeout=40.0)
        C('set_track_output', {'track': t, 'dest': BUS})
        C('set_track', {'track': t, 'pan': PANS[t], 'volume_db': -3.0, 'mute': False,
                        **({'color_index': colour} if colour is not None else {})})
    C('set_track', {'track': BUS, 'pan': 0.0})       # riff -15.1 LUFS at +3: -3 brings it to the sample's -20.8


def clips():
    spans = [(c['start'], c['end']) for c in C('get_track', {'track': BUS, 'clips': True})['clips']]
    for t, phrase in parts().items():
        have = C('get_track', {'track': t, 'clips': True}).get('clips', [])
        for c in reversed(have):
            C('delete_clip', {'track': t, 'clip': c['i']})
        for a, z in spans:
            C('create_midi_clip', {'track': t, 'beat': a, 'length': z - a, 'name': t.split(' (')[0].title(),
                                   'notes': tiled(phrase, z - a)}, timeout=60.0)
        print(t, len(C('get_track', {'track': t, 'clips': True})['clips']), 'clips')


if __name__ == '__main__':
    steps = {'tracks': tracks, 'clips': clips}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
