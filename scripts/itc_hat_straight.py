"""In the City: the running 16th hat played like a hat, not like a velocity graph.

His note (2026-11-05): "o que você fez com o velocity não existe ... subindo até 125, 127 ...
tem que ser mais reto, mais orgânico, parecer um hat, um shaker". Measured before: velocity 19-125,
89 distinct values, Vol<Vel 100 %, so neighbouring 16ths read -53 / -31 / -20 / -27 dBFS,
33 dB apart, with the off-beat only 4.4 dB under the kick's peak.

Now: every 16th within a small range under 100, one accent map played by a steady hand
(the "and" a little up), +-2 of scatter, 32nd flutters a touch softer. No note moves: the holes,
pockets and swing stay. The old notes are kept in the project folder (--restore puts them back).
"""
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

TRACK = 'HAT 16ths'
BACKUP = Path.home() / 'Desktop/Projects 26:27/In the City  Project/hat 16ths - notas antes 05-11.json'
ACCENT = {0: 80, 1: 76, 2: 92, 3: 80}      # on the beat, e, and, a
FLUTTER = 68                                # 32nds between the 16ths
SCATTER = 2
SEED = 16


def humanised(notes):
    rng = random.Random(SEED)
    out = []
    for pitch, start, dur, _vel in notes:
        slot = start * 4
        on_16th = abs(slot - round(slot)) < 0.2          # swing moves the off-16ths by 0.09 of a 16th
        base = ACCENT[round(slot) % 4] if on_16th else FLUTTER
        out.append([pitch, start, dur, float(base + rng.randint(-SCATTER, SCATTER))])
    return out


def clips():
    return client.call('get_track', {'track': TRACK, 'clips': True})['clips']


def main():
    if '--restore' in sys.argv:
        saved = json.loads(BACKUP.read_text())
        for start, notes in saved.items():
            client.call('add_notes', {'track': TRACK, 'clip': {'at': float(start)}, 'notes': notes,
                                      'replace': True}, timeout=120.0)
        print('restored', {k: len(v) for k, v in saved.items()})
        return
    saved = {str(c['start']): client.call('get_notes', {'track': TRACK, 'clip': {'at': c['start']}})
             for c in clips()}
    if not BACKUP.exists():                         # never overwrite the original take
        BACKUP.write_text(json.dumps(saved))
    for start, notes in saved.items():
        new = humanised(notes)
        client.call('add_notes', {'track': TRACK, 'clip': {'at': float(start)}, 'notes': new,
                                  'replace': True}, timeout=120.0)
        v = [n[3] for n in new]
        print(start, 'notes', len(new), 'vel', min(v), max(v), 'distinct', len(set(v)))


if __name__ == '__main__':
    main()
