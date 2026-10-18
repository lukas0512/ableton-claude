"""Targeted, additive production pass on the saved Summer Groove copy."""
import json
from pathlib import Path
from ableton_claude import client

OUT = Path('/Users/lukasgalhardo/Music/Ableton/User Library/Samples/Codex/Summer Groove')
OUT.mkdir(parents=True, exist_ok=True)
song = client.call('get_song')
assert song['tempo'] == 123
resume = any(t['name'] == 'Summer Piano' for t in song['tracks'])
before = {name: client.call('get_track', {'track': name})
          for name in ['Theme', 'Hats', 'Pad', 'Stab', 'Perc Tops']}
if not resume:
    (OUT / 'before.json').write_text(json.dumps(before, indent=2))
log = json.loads((OUT / 'changes.json').read_text()) if resume else []

def call(cmd, **args):
    result = client.call(cmd, args)
    log.append({'cmd': cmd, 'args': args, 'result': result})
    (OUT / 'changes.json').write_text(json.dumps(log, indent=2))
    print(cmd, str(result)[:180], flush=True)
    return result

if not resume:
    call('create_track', kind='midi', name='Summer Piano')
    call('set_track', track='Summer Piano', volume_db=-15, pan=0.12, arm=False)
    call('load_device', track='Summer Piano', path='sounds/Piano & Keys/Grand Piano Single Sample.adv')
    call('load_device', track='Summer Piano', query='EQ Eight')
assert client.call('get_track', {'track':'Summer Piano'})['n_clips'] == 0
call('set_param', track='Summer Piano', device=1, param='1 Filter Type A', item='High Pass 12dB')
call('set_param', track='Summer Piano', device=1, param='1 Frequency A', display='160 Hz')
call('set_track_output', track='Summer Piano', dest='Music Bus')
call('set_send', track='Summer Piano', send=2, db=-19)
call('set_send', track='Summer Piano', send=1, db=-24)

# Rootless Cm9 -> Abmaj7 voicings follow the existing pad, not a new progression.
# Four-bar responses occupy the existing Theme's four-bar rests.
for bar in [61, 69, 109, 117, 125, 133, 141]:
    notes = []
    for beat, vel, duration in [(0.5,91,.34),(1.75,69,.20),(2.5,83,.38),
                               (4.5,85,.34),(5.75,66,.20),(7.25,78,.23),
                               (8.5,88,.34),(10.0,72,.28),(10.75,64,.20),
                               (12.5,84,.4),(14.5,77,.38)]:
        chord = [62,63,67,70] if beat < 7.5 else [60,63,67,68]
        if bar == 141:
            chord = [60,63,65,68]
        # Existing Swing 16ths 66 at 50% supplies the timing once.
        offset = 0
        for j, pitch in enumerate(chord):
            notes.append([pitch,beat+offset+j*.008,duration,vel-j*3])
    call('create_midi_clip', track='Summer Piano', bar=bar, length=16,
         notes=notes, name='Sunlit piano - Cm9 / Abmaj7', loop=False)
call('set_send', track='Theme', send=1, db=-13)
call('set_param', track='master', device='Limiter', param='Mode', item='True Peak')
call('set_param', track='master', device='Limiter', param='Ceiling', display='-1.1 dB')
call('set_clip', track='Bass', clip=17, muted=True)
for track, index in [('Clap',21), ('Ghost',18), ('Tops 2',9), ('Crash',3)]:
    call('set_clip', track=track, clip=index, gain_db=-3)
for track in ['Vox Chops', 'Vox Call', 'Hats', 'Perc Tops', 'FX 1', 'Riser']:
    for clip in client.call('get_track', {'track': track})['clips']:
        if 400 <= clip['start'] < 416:
            call('set_clip', track=track, clip=clip['i'], gain_db=clip['gain_db']-4)
for track, index in [('Pad', 3), ('Theme', 10), ('Theme', 11)]:
    notes = client.call('get_notes', {'track': track, 'clip': index})
    for note in notes:
        note[3] = max(1, round(note[3]*.8))
    call('add_notes', track=track, clip=index, notes=notes, replace=True)
(OUT / 'after.json').write_text(json.dumps(client.call('get_song'), indent=2))
