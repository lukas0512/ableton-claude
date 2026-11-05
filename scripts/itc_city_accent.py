"""In the City: the City guitar as an accent in the mids, the delay doing the talking.

His note (2026-11-05, on itc_city_bounce.py): "o timbre da guitarra dá pra melhorar, abusar mais do delay, menos
notas, mas a conversa ainda prevalecer ... só um acento, um charmezinho, mais repetitivo ... mas timbre agudo muito
repetitivo cansa, enjoa, se destaca muito na track ... usar médio-agudo, mais médio, perto dos médios, que os stabs
estão bem fechados".

- Notes: from B4-E5 down to E4/D4 (330/294 Hz fundamentals), one figure per 2 bars: a ghost D4 into an E4 accent on
  the bass's G (1.5), a D4 on the bass's B (5.5). Phrase 3 lifts the accent to G4 once, phrase 4 closes with the
  record's D#4 -> E4 slide. Silent in the bars a voice fills (itc_vocal_map.py): the voice talks, the guitar and its
  echoes answer in the free bars.
- Delay: Echo at 1/4 and 3/8 (4 and 6 sixteenths: both even, so every echo keeps its note's place in the swing),
  feedback 50 %, 38 % wet, filtered 500 Hz-2.8 kHz (mid echoes, never bright), ducked so they bloom after the hit.
- Timbre: the guitar's own filter down to 4 kHz, Saturator 30 % wet; the CITY SYNTH bus loses the +3 dB shelf at
  4.5 kHz, its presence goes from +2.5 at 3 kHz to +1.5 at 1.8 kHz (added when the guitar read dark) and its mud
cut from -4.5 at 350 Hz to -2 at 250 Hz (the new notes live at 294-392 Hz).
The stabs' notes are untouched; no guitar note within a 16th of a stab.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_claude import client
from itc_city_bass_lock import BUS, GTR, ORIGIN, pocket
from itc_city_bounce import voiced_bars

C = client.call
BASE = [(1.25, 62, .12, 72), (1.5, 64, .30, 108), (5.5, 62, .30, 100)]


def cell(phrase):
    notes = list(BASE)
    if phrase == 2:
        notes = [(b, 67 if b == 1.5 else p, d, v) for b, p, d, v in notes]
    if phrase == 3:
        notes += [(7.5, 63, .10, 84), (7.75, 64, .22, 100)]
    return notes


def accents(a, z, voiced):
    out, k = [], a
    while k < z - 1e-6:
        phrase = int(round((k - ORIGIN) / 8.0)) % 4
        for b, p, d, v in cell(phrase):
            s = k + pocket(b)
            if s < z - 1e-6 and int(s // 4) not in voiced:
                out.append([p, s - a, min(d, z - s), float(v)])
        k += 8.0
    return out


def clips():
    voiced = voiced_bars()
    spans = [(c['start'], c['end']) for c in C('get_track', {'track': BUS, 'clips': True})['clips']]
    for c in reversed(C('get_track', {'track': GTR, 'clips': True}).get('clips', [])):
        C('delete_clip', {'track': GTR, 'clip': c['i']})
    n = 0
    for a, z in spans:
        ns = accents(a, z, voiced)
        C('create_midi_clip', {'track': GTR, 'beat': a, 'length': z - a, 'name': 'City Gtr Accent', 'notes': ns},
          timeout=60.0)
        n += len(ns)
    print('accent notes', n)


def p(track, device, name, **kw):
    C('set_param', {'track': track, 'device': device, 'param': name, **kw})


def sound():
    p(GTR, 0, 'Filter Cutoff', display='4.00 kHz')
    p(GTR, 0, 'Release', display='220 ms')
    p(GTR, 'Saturator', 'Dry/Wet', display='30 %')
    for name, kw in (('L 16th', {'value': 4.0}), ('R 16th', {'value': 6.0}), ('Feedback', {'display': '50 %'}),
                     ('Dry Wet', {'display': '38 %'}), ('HP Freq', {'display': '500 Hz'}), ('LP Freq', {'display': '2.80 kHz'}),
                     ('Duck Thr', {'display': '-20.0 dB'}), ('Duck Release', {'display': '200 ms'}),
                     ('Reverb Level', {'display': '18 %'}), ('Dly < Mod', {'display': '4.0 %'})):
        p(GTR, 'Echo', name, **kw)
    # the bus: no air shelf, a softer and lower presence
    p(BUS, 'EQ Eight', '7 Filter On A', value=0.0)
    p(BUS, 'EQ Eight', '3 Frequency A', display='1.80 kHz')
    p(BUS, 'EQ Eight', '3 Gain A', value=1.5)
    # the -4.5 dB at 350 Hz was for the guitar's body when it played B4-E5; its notes now sit there (E4 330 Hz)
    p(BUS, 'EQ Eight', '2 Frequency A', display='250 Hz')
    p(BUS, 'EQ Eight', '2 Gain A', value=-2.0)


def level(db=2.0):   # at +4 the riff read -23.7 LUFS in bars 65-80, 2 dB over the previous version
    C('set_track', {'track': GTR, 'volume_db': db})


if __name__ == '__main__':
    steps = {'clips': clips, 'sound': sound, 'level': level}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
