"""In the City: the City guitar contained, bouncing and gangsta; the stabs as they were.

His note (2026-11-05) on itc_city_lead.py: "gostei dos stabs agora, mas o City GTR pode ser mais contido em questão
de melodia, fazer algo mais bounce e gangsta". The lead ran B4-B5 with runs in every other phrase. Now three notes
(B4 D5 E5, the minor pentatonic's top), short and staccato, an accent/ghost figure on the swung 16ths that rides
the bass's tresillo (0, 0.75, 1.5 | 4, 4.75, 5.5) plus an off-beat hiccup at 1.0 and 5.0, and rests through the
bass's holes so the stabs answer there. Variation over 8 bars: phrase 2 a D5-E5 hiccup at 3.5, phrase 3 the
1.5 note lifted to G5, phrase 4 the record's D#5 -> E5 slide into the next cycle.

The stabs' notes are not touched: their clips stay as itc_city_lead.py wrote them, and no lead note lands within a
16th of a stab slot.

Next note (same night): "a guitarra tá um pouco alta ... o stab tá meio escondido, lá no fundo, pode fazer mais
parte do bounce ... às vezes com o vocal fica muita coisa ... fazer uma conversa". The hooks are a dense rap (8 bars
between -17 and -30 dB, no breaths), so the conversation is per bar: itc_vocal_map.py marks the bars a voice fills;
there the guitar only nods on the one (velocity 70), in the bars without voice it bounces. Guitar -3 dB; stabs out
of the back: filter 1.8 -> 2.8 kHz, resonance 25 -> 15 %, echo 18 -> 11 %, width 140 -> 115 %, plate/atmos -4 dB,
+3.5 dB.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_claude import client
from itc_city_bass_lock import BUS, GTR, ORIGIN, pocket

C = client.call
# (beat in the 2-bar cell, pitch, length in beats, velocity)
BASE = [(0.0, 71, .20, 105), (0.75, 71, .14, 80), (1.0, 74, .18, 94), (1.5, 76, .32, 108),
        (3.5, 74, .18, 90),
        (4.0, 76, .20, 100), (4.75, 76, .14, 80), (5.0, 74, .18, 92), (5.5, 71, .32, 106)]
EXTRA = {1: [(3.75, 76, .18, 96)],                                   # hiccup D5-E5
         3: [(7.5, 75, .10, 86), (7.75, 76, .22, 100)]}              # D#5 -> E5 slide into the top


def cell(phrase):
    notes = list(BASE)
    if phrase == 2:
        notes = [(b, 79 if b == 1.5 else p, d, v) for b, p, d, v in notes]   # lift to G5 once
    return notes + EXTRA.get(phrase, [])


def voiced_bars(min_slots=8):
    """Bars where a vocal sounds at least half the bar (itc_vocal_map.py)."""
    import json
    v = {int(k) for k in json.loads((Path(__file__).resolve().parent / 'vocal_map.json').read_text())}
    bars = {s // 16 for s in v}
    return {b for b in bars if sum(1 for s in range(b * 16, b * 16 + 16) if s in v) >= min_slots}


def lead(a, z, voiced=frozenset()):
    """The bounce in the bars without voice; under the voice only a quiet nod on each bar's one."""
    out, k = [], a
    while k < z - 1e-6:
        phrase = int(round((k - ORIGIN) / 8.0)) % 4
        for b, p, d, v in cell(phrase):
            s = k + pocket(b)
            if s >= z - 1e-6:
                continue
            if int(s // 4) in voiced:
                if abs(s - round(s / 4) * 4) > 1e-3:
                    continue
                v = 70
            out.append([p, s - a, min(d, z - s), float(v)])
        k += 8.0
    return out


def clips():
    spans = [(c['start'], c['end']) for c in C('get_track', {'track': BUS, 'clips': True})['clips']]
    for c in reversed(C('get_track', {'track': GTR, 'clips': True}).get('clips', [])):
        C('delete_clip', {'track': GTR, 'clip': c['i']})
    n = 0
    voiced = voiced_bars()
    for a, z in spans:
        ns = lead(a, z, voiced)
        C('create_midi_clip', {'track': GTR, 'beat': a, 'length': z - a, 'name': 'City Gtr Bounce', 'notes': ns},
          timeout=60.0)
        n += len(ns)
    print('lead notes', n)


def chain():
    # tighter echo for a staccato part; the release short so the hits stay hits
    C('set_param', {'track': GTR, 'device': 'Echo', 'param': 'Dry Wet', 'display': '18 %'})
    C('set_param', {'track': GTR, 'device': 'Echo', 'param': 'Feedback', 'display': '28 %'})
    C('set_param', {'track': GTR, 'device': 0, 'param': 'Release', 'display': '180 ms'})
    C('set_track', {'track': GTR, 'volume_db': 2.5})     # "um pouco alto" at +5.5 (riff -24.7 LUFS in drop 1)


def stabs_forward():
    """"O stab tá de boa mas meio escondido, lá no fundo, pode fazer mais parte do bounce": less dub, more front."""
    S = 'CITY STABS'
    for dev, name, kw in (('Auto Filter', 'Frequency', {'display': '2.80 kHz'}), ('Auto Filter', 'Resonance', {'display': '15 %'}),
                          ('Echo', 'Dry Wet', {'display': '11 %'}), ('Utility', 'Stereo Width', {'display': '115 %'}),
                          ('Utility', 'Output', {'display': '1.5 dB'})):
        C('set_param', {'track': S, 'device': dev, 'param': name, **kw})
    C('set_send', {'track': S, 'send': 4, 'db': -28.0})    # E-Plate
    C('set_send', {'track': S, 'send': 2, 'db': -30.0})    # C-Atmos
    C('set_track', {'track': S, 'volume_db': 6.0})


if __name__ == '__main__':
    steps = {'clips': clips, 'chain': chain, 'stabs': stabs_forward}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
