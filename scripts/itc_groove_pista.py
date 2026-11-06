"""In the City: the grooves move ("ta meio quadrado ainda e mt travada ... precisa de mais groove e um pouco mais de
movimento", "quero ela bem pista bem forte", 2026-11-06).

What made it square (v8b against dub_house_streets): in the drops every drum sat on the 8th grid (kick on the beat,
clap + snare on 2/4, open hat and ride both on the off-beat 8ths); nothing played an off-16th, so the 'Swing 16ths 66'
on every clip had nothing to swing. offbeat_16th_share 0.46 (refs 0.51-0.56), clap 13.9 dB over the backbeat (refs
8.2), hats -21.6 dB and dark (refs -17.5, 6.4 kHz). The congas (syncopated: 16ths 2, 7, 8, 10, 12 of each bar) were
muted in every groove since the underground pass. He rejected three continuous 16th hat layers: no 16th hat here.

Moves:
- CONGAS back in the grooves (25-48, 65-96, 121-168), humanized, a run into every 8-bar phrase that does not end in a
  transition, a pickup into the 4th bar, every 2nd bar the low tone moves (slot 15 instead of 7): the conversation;
- clap and snare -2.5 dB (the backbeat stops dominating), a ghost clap on the 'a' of 4 every 2nd bar (low velocity);
- open hat +2.5 dB, PERC LOOP +4 dB (its 16ths now carry), TOPS high shelf +2 dB at 8 kHz;
- the ride drops the off-beat it doubles with the hat on the 2nd bar of each pair and plays the 'a' of 2 and 4 there;
- the pool groove 'Swing 16ths 66' Timing 16 -> 45 %: at 16 % the off-16ths landed ~8 ms late (nearly straight, the
  "travada"); at 45 % every band's 'e' and 'a' land ~18 ms late (swing ~58 %, refs 57), one pocket for all MIDI parts.
Drop 2 (121-137) measured on the real grid: off-16th onset energy 0.41 -> 0.47, percussion band 0.44 -> 0.49.
Backup of every note it rewrites: 'groove pista - antes 06-11.json' in the project.
usage: itc_groove_pista.py [--restore]
"""
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
PROJ = Path('/Users/lukasgalhardo/Desktop/Projects 26:27/In the City  Project')
BACKUP = PROJ / 'groove pista - antes 06-11.json'
LOW, MID, HIGH = 38, 40, 43
GROOVE = 'Swing 16ths 66'
# phrase ends (last bar of an 8-bar phrase) that lead into a transition FX: no fill there
NO_FILL = {48, 96, 120, 168}
LEVELS = {'CLAP': -9.7, 'SNARE': -15.5, 'HAT OFF - persona': -12.5, 'PERC LOOP': -17.6}


def clips(track):
    return C('get_track', {'track': track, 'clips': True})['clips']


def backup():
    if BACKUP.exists():
        return json.loads(BACKUP.read_text())
    data = {'levels': {t: C('get_track', {'track': t})['vol_db'] for t in LEVELS}, 'notes': {}}
    for t in ('CONGAS', 'CLAP', 'RIDE 909'):
        for c in clips(t):
            if c.get('type') == 'midi':
                data['notes'][f'{t}|{c["start"]}'] = {'muted': bool(c.get('muted')),
                                                     'notes': C('get_notes', {'track': t, 'clip': c['i']})}
    BACKUP.write_text(json.dumps(data))
    return data


def restore(data):
    for key, v in data['notes'].items():
        t, start = key.split('|')
        C('add_notes', {'track': t, 'clip': {'at': float(start)}, 'notes': v['notes'], 'replace': True})
        C('set_clip', {'track': t, 'clip': {'at': float(start)}, 'muted': v['muted']})
    for t, db in data['levels'].items():
        C('set_track', {'track': t, 'volume_db': db})
    C('set_groove', {'name': GROOVE, 'timing': 16.0})
    C('set_param', {'track': 'TOPS', 'device': 'EQ Eight', 'param': '4 Frequency A', 'display': '5.00 kHz'})
    C('set_param', {'track': 'TOPS', 'device': 'EQ Eight', 'param': '4 Gain A', 'value': 0.0})


def conga_bar(bar, rng):
    """One bar of congas (beats relative to the bar), the kit's own cell with a conversation every 2nd bar."""
    odd = bar % 2 == 0                      # the answering bar
    cell = [(LOW, 0.25), (MID, 1.5), (LOW, 3.75 if odd else 1.75), (MID, 2.25), (HIGH, 2.75)]
    if bar % 4 == 3:                        # pickup into the 4th bar
        cell += [(HIGH, 3.5), (MID, 3.75)]
    if bar % 8 == 0 and bar not in NO_FILL:  # run into the next phrase
        cell = [n for n in cell if n[1] < 2.0] + [(HIGH, 2.0), (HIGH, 2.25), (MID, 2.5), (MID, 2.75),
                                                  (LOW, 3.0), (LOW, 3.25), (MID, 3.5), (HIGH, 3.75)]
    out = []
    for p, b in cell:
        accent = 84 if b in (0.25, 3.0) else 72
        if bar % 8 == 0 and b >= 2.0:
            accent = 60 + int((b - 2.0) * 16)   # the run grows
        out.append([p, b, 0.2, max(40, min(110, accent + rng.randint(-8, 8)))])
    return out


def congas():
    rng = random.Random(611)
    for c in clips('CONGAS'):
        a, z = int(c['start'] // 4) + 1, int(c['end'] // 4) + 1
        if not (25 <= a <= 121) or a in (105,):
            continue                         # 105-112 keeps its own part
        info = C('set_clip', {'track': 'CONGAS', 'clip': c['i'], 'muted': False})
        sm = info['start_marker']
        notes = []
        for bar in range(a, z):
            rel = (bar - a) * 4.0 + sm
            notes += [[p, rel + b, d, v] for p, b, d, v in conga_bar(bar, rng)]
        C('add_notes', {'track': 'CONGAS', 'clip': c['i'], 'notes': notes, 'replace': True})
        print('congas', a, z - 1, len(notes), 'notes')


def clap_ghosts(data):
    for c in clips('CLAP'):
        if c.get('type') != 'midi':
            continue
        a, z = int(c['start'] // 4) + 1, int(round(c['end'] / 4)) + 1
        if a < 9 or 49 <= a < 57 or 97 <= a < 121:
            continue                          # breaks and builds keep theirs
        info = C('set_clip', {'track': 'CLAP', 'clip': c['i'], 'name': c['name']})
        sm = info['start_marker']
        orig = data['notes'][f'CLAP|{c["start"]}']['notes']
        ghosts = []
        for bar in range(a, z):
            if bar % 2 == 0 and bar % 8 != 0 and not 57 <= bar < 65:
                ghosts.append([60, sm + (bar - a) * 4.0 + 3.75, 0.2, 46])
        keep = [n for n in orig if not any(abs(n[1] - g[1]) < 0.05 for g in ghosts)]
        C('add_notes', {'track': 'CLAP', 'clip': c['i'], 'notes': keep + ghosts, 'replace': True})
        print('clap ghosts', a, z - 1, len(ghosts))


def ride(data):
    for c in clips('RIDE 909'):
        a, z = int(c['start'] // 4) + 1, int(round(c['end'] / 4)) + 1
        info = C('set_clip', {'track': 'RIDE 909', 'clip': c['i'], 'name': c['name']})
        sm = info['start_marker']
        orig = data['notes'][f'RIDE 909|{c["start"]}']['notes']
        out = []
        for p, b, d, v in orig:
            bar = a + int((b - sm) // 4)
            pos = (b - sm) % 4
            if bar % 2 == 0 and abs(pos - 1.5) < 0.05:
                out.append([p, b + 0.25, d * 0.5, v * 0.85])    # off-beat of 2 -> 'a' of 2
            elif bar % 2 == 0 and abs(pos - 3.5) < 0.05:
                out.append([p, b + 0.25, d * 0.5, v * 0.85])
            else:
                out.append([p, b, d, v])
        C('add_notes', {'track': 'RIDE 909', 'clip': c['i'], 'notes': out, 'replace': True})
        print('ride', a, z - 1, len(out))


def mix():
    for t, db in LEVELS.items():
        C('set_track', {'track': t, 'volume_db': db})
    # band 4 is already the bus's (flat) high shelf at 5 kHz
    C('set_param', {'track': 'TOPS', 'device': 'EQ Eight', 'param': '4 Frequency A', 'display': '8.00 kHz'})
    C('set_param', {'track': 'TOPS', 'device': 'EQ Eight', 'param': '4 Gain A', 'value': 2.0})
    C('set_groove', {'name': GROOVE, 'timing': 45.0})
    # the congas' body added +3 dB at 315 Hz to the drops (the mud zone): their bell -3 -> -7 dB, Q 1.2 leaves +1.5
    C('set_param', {'track': 'CONGAS', 'device': 'EQ Eight', 'param': '2 Gain A', 'value': -7.0})
    C('set_param', {'track': 'CONGAS', 'device': 'EQ Eight', 'param': '2 Q A', 'display': '1.20'})


if __name__ == '__main__':
    data = backup()
    if sys.argv[1:] == ['--restore']:
        restore(data)
        print('restored')
        raise SystemExit
    congas()
    clap_ghosts(data)
    ride(data)
    mix()
