"""In the City: the bass fills its hole and varies, in the drops only.

His note (2026-11-05): "um pouco vazio ... mais presença, mais algumas notas ... esse timbre e o groove estão
legais". Measured: silent from beat 2.75 to 4 of every bar, about 3 notes a bar (his references ~5.4).
The riff stays. Additions sit off the kick, inside E minor, and rotate over 8 bars:
  cell 0  a pick-up into the A
  cell 1  a pick-up + the record's own turn
  cell 2  an octave answer, then a reply in bar 2
  cell 3  a pick-up + the record's own turn
The grooves keep the plain riff, so the drops have something to arrive with. Bars with a planned rest stay empty.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
TRACK = 'BASS'
BACKUP = Path.home() / 'Desktop/Projects 26:27/In the City  Project/baixo - notas antes 05-11.json'
E4, G4, A4, B4, D5, E5 = 64, 67, 69, 71, 74, 76
PICKUP = [[E4, 3.5, 0.3, 100.0]]
ANSWER = [[E5, 2.5, 0.25, 96.0], [D5, 3.2725, 0.25, 92.0], [B4, 3.5, 0.3, 100.0]]
REPLY = [[G4, 6.5, 0.3, 96.0], [E4, 7.5, 0.3, 92.0]]
CELLS = (PICKUP, PICKUP, ANSWER + REPLY, PICKUP)
RESTS = {72, 76, 84, 96, 132, 136, 140, 152}    # absolute bars: bass breaths, kick-outs, stops, last bar of a drop
DROPS = ((256.0, 65, 97), (480.0, 121, 153))    # clip start, first bar, end bar


def main():
    saved = {str(at): C('get_notes', {'track': TRACK, 'clip': {'at': at}}) for at, _, _ in DROPS}
    if not BACKUP.exists():
        BACKUP.write_text(json.dumps(saved))
    else:
        saved = json.loads(BACKUP.read_text())       # rerun from the original riff, never on top of itself
    for at, first, end in DROPS:
        notes = saved[str(at)]
        added = 0
        new = list(notes)
        for i, bar in enumerate(range(first, end, 2)):
            if {bar, bar + 1} & RESTS:
                continue
            base = (bar - first) * 4.0
            for pitch, start, dur, vel in CELLS[i % 4]:
                new.append([pitch, base + start, dur, vel])
                added += 1
        C('add_notes', {'track': TRACK, 'clip': {'at': at}, 'notes': new, 'replace': True}, timeout=60.0)
        print(at, 'notes', len(notes), '->', len(new), 'added', added)


if __name__ == '__main__':
    main()
