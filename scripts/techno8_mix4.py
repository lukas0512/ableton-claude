"""TECHNO #8 mix pass (2026-11-02): channels named and coloured by family, then cleaned and balanced.
Stages: python techno8_mix4.py names | balance | tilt | space | human | fx
"""
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server
from techno8_arrange import _ensure, B

RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, GREY = 14, 1, 4, 61, 26, 49, 69
NAMES = {0: ('REF - Rules Of The Groove', GREY),
         1: ('KICK', RED), 21: ('KICK - build', RED), 3: ('DRUMS', RED), 4: ('TOP loop', RED), 5: ('PERC loop', RED),
         6: ('HAT', RED), 7: ('OPEN HAT', RED), 8: ('CLAP A', RED), 9: ('CLAP B', RED), 28: ('TOP - build', RED),
         2: ('BASS', ORANGE), 22: ('BASS - build', ORANGE), 13: ('ACID', ORANGE),
         10: ('PAD', GREEN), 11: ('SYNTH loop', GREEN), 12: ('RIFF', GREEN), 23: ('SYNTH - build', GREEN),
         14: ('VOX - main', PURPLE), 24: ('VOX - phrases', PURPLE), 25: ('VOX - calls', PURPLE), 26: ('VOX - chops', PURPLE),
         27: ('VOX - throws', PURPLE), 15: ('FX', BLUE), 16: ('FX wash', BLUE), 17: ('FX hit', BLUE), 18: ('FX crash', BLUE),
         19: ('FX reverse', BLUE), 20: ('FX roll', BLUE)}


def C(cmd, **a):
    r = server._journaled(cmd, a)
    print(cmd, a.get('track', ''), str(r)[:90], flush=True)


def stage_names():
    for i, (name, color) in NAMES.items():
        C('set_track', track=i, name=name, color_index=color)


def eq(track, band, ftype=None, hz=None, db=None, q=None):
    C('set_param', track=track, device='EQ Eight', param=f'{band} Filter On A', value=1)
    if ftype:
        C('set_param', track=track, device='EQ Eight', param=f'{band} Filter Type A', item=ftype)
    if hz:
        C('set_param', track=track, device='EQ Eight', param=f'{band} Frequency A', display=hz)
    if db is not None:
        C('set_param', track=track, device='EQ Eight', param=f'{band} Gain A', display=db)
    if q:
        C('set_param', track=track, device='EQ Eight', param=f'{band} Q A', display=q)


def stage_balance():
    # measured against the kick in drop 2: the theme at -20/-22 LU under tops at -4/-6
    for t in ('CLAP A', 'CLAP B', 'OPEN HAT'):
        _ensure(t, 'audio_effects/EQ Eight', 'EQ Eight')
    eq('CLAP A', 1, 'High Pass 12dB', 180)
    eq('CLAP B', 1, 'High Pass 12dB', 200)
    eq('CLAP B', 3, 'Bell', 300, -4, 1.2)   # most of the low-mid excess against the reference
    eq('OPEN HAT', 1, 'High Pass 12dB', 500)
    eq('HAT', 1, 'High Pass 12dB', 500)
    eq('PERC loop', 1, 'High Pass 12dB', 200)
    eq('TOP loop', 1, 'High Pass 12dB', 250)
    eq('TOP loop', 5, 'Bell', 1000, -3.5, .8)  # clears the theme's register, keeps its air
    eq('BASS', 3, 'Bell', 290, -3, 1.2)
    eq('SYNTH loop', 3, 'Bell', 380, -1, .8)
    eq('RIFF', 2, 'Bell', 380, -2, .8)
    for t, db in (('SYNTH loop', -13.5), ('RIFF', -9), ('TOP loop', -23.7), ('TOP - build', -17), ('PAD', -2.9),
                  ('PERC loop', -24), ('OPEN HAT', -15.5), ('VOX - chops', -11.5), ('VOX - calls', -11)):
        C('set_track', track=t, volume_db=db)
    # drop 2 is the song's peak: the theme 2 dB over drop 1
    tr = client.call('get_track', {'track': 'SYNTH loop', 'clips': True})
    for c in tr['clips']:
        if B(113) <= c['start'] < B(145):
            C('set_clip', track='SYNTH loop', clip={'at': c['start']}, gain_db=2)


def stage_tilt():
    # with the theme up: 250-500 Hz +5.5 dB, 2-8 kHz -3 dB against the reference in drop 2
    eq('RIFF', 2, 'Bell', 380, -5, .8)
    eq('SYNTH loop', 3, 'Bell', 380, -4, .8)
    for t, db in (('TOP - build', -14.5), ('HAT', -15), ('OPEN HAT', -14)):
        C('set_track', track=t, volume_db=db)


def stage_space():
    # rooms: drums in a short sense of place, the theme and pad further back, low end dry
    sends = {'CLAP A': (-24, -70), 'CLAP B': (-22, -32), 'HAT': (-34, -70), 'OPEN HAT': (-26, -34), 'PERC loop': (-24, -28),
             'TOP loop': (-34, -70), 'PAD': (-14, -18), 'SYNTH loop': (-22, -26), 'RIFF': (-20, -20), 'SYNTH - build': (-14, -18),
             'FX wash': (-16, -24), 'FX hit': (-18, -14), 'FX crash': (-18, -70), 'FX reverse': (-20, -70), 'FX roll': (-20, -14),
             'VOX - throws': (-14, -70), 'KICK': (-70, -70), 'BASS': (-70, -70), 'KICK - build': (-30, -70), 'BASS - build': (-70, -70)}
    for t, (rev, dly) in sends.items():
        C('set_send', track=t, send=0, db=rev)
        C('set_send', track=t, send=1, db=dly)
    for t, pan in (('PERC loop', -.14), ('OPEN HAT', .1), ('FX hit', -.3), ('FX reverse', .2), ('FX roll', .3), ('CLAP B', .05)):
        C('set_track', track=t, pan=pan)
    # the delay filtered and ping-pong: spreads without muddying; the reverb ducks from the kick
    C('set_param', track='return:1', device='Delay', param='Ping Pong', value=1)
    C('set_param', track='return:1', device='Delay', param='Filter On', value=1)
    C('set_param', track='return:1', device='Delay', param='Filter Freq', display='1.50 kHz')
    C('set_param', track='return:1', device='Delay', param='Filter Width', display=6)
    _ensure('return:0', 'audio_effects/Compressor', 'Compressor')
    C('set_device_input', track='return:0', device='Compressor', source='KICK')
    C('set_param', track='return:0', device='Compressor', param='Threshold', display=-30)
    C('set_param', track='return:0', device='Compressor', param='Ratio', display=3)
    C('set_param', track='return:0', device='Compressor', param='Attack', display='5.00 ms')
    C('set_param', track='return:0', device='Compressor', param='Release', display='160 ms')


def stage_human():
    # hats and claps sat dead straight against a top loop whose off-16ths lag ~19 ms: one pocket, and no two bars alike
    rng = random.Random(28)
    for t, spread in (('HAT', 8), ('OPEN HAT', 6), ('CLAP A', 4), ('CLAP B', 5)):
        tr = client.call('get_track', {'track': t, 'clips': True})
        batch = []
        for c in tr['clips']:
            if c['type'] != 'midi':
                continue
            r = client.call('get_notes', {'track': t, 'clip': {'at': c['start']}})
            ns = r['notes'] if isinstance(r, dict) else r
            out = []
            for p, st, d, v in ns:
                off = abs((st * 2) % 1 - .5) < .01
                out.append([p, st + (.03 if off else 0) + rng.uniform(-.004, .004) if st > .01 else st, d,
                            max(30, min(127, v + rng.randint(-spread, spread)))])
            batch.append({'cmd': 'add_notes', 'args': {'track': t, 'clip': {'at': c['start']}, 'notes': out, 'replace': True}})
        for i in range(0, len(batch), 40):
            for b in batch[i:i + 40]:
                server._journaled(b['cmd'], b['args'])
        print(t, len(batch), flush=True)


def stage_fx():
    # his effects spread over the phrase turns instead of the same few spots
    tr = client.call('get_track', {'track': 'FX hit', 'clips': True})
    first = tr['clips'][0]
    for bar in (33, 41, 65, 81, 121, 137):
        C('duplicate_clip', track='FX hit', clip={'at': first['start']}, bar=bar)
        C('set_clip', track='FX hit', clip={'at': B(bar)}, muted=False)
    tr = client.call('get_track', {'track': 'FX wash', 'clips': True})
    have = {round(c['start']) for c in tr['clips']}
    first = tr['clips'][0]
    for bar in (73, 129):
        if B(bar) not in have:
            C('duplicate_clip', track='FX wash', clip={'at': first['start']}, bar=bar)


if __name__ == '__main__':
    {'names': stage_names, 'tilt': stage_tilt, 'balance': stage_balance, 'space': stage_space, 'human': stage_human, 'fx': stage_fx}[sys.argv[1]]()
