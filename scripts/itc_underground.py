"""In the City, the turn to older, underground tech house: the riff and the voice carry, not percussion.

His note (2026-11-05): "muito percussiva, groove forçado com percussão ... mais gangsta, menos tech house
mainstream, menos corneta ... muito efeito pra subida ... tensão e alívio com ausência: tirar o kick, filtrar o
bass ... o riffzinho pega muito". Measured in drop 2: non-kick drums -7.6 LU against the kick, all music -14.9,
the Murder riff -25.5 (only in drop 2, an octave up, high-passed at 500 Hz).

Everything here mutes clips rather than deleting them, so a layer can come back.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call


def clips(track):
    return C('get_track', {'track': track, 'clips': True}).get('clips', [])


def mute_where(track, test):
    n = 0
    for c in clips(track):
        if not c.get('muted') and test(c):
            C('set_clip', {'track': track, 'clip': {'at': c['start']}, 'muted': True})
            n += 1
    print(f'  {track}: muted {n}')


def bar(c):
    return c['start'] / 4 + 1


def percussion():
    # one running texture and one off-beat are enough; the fills and congas were forcing the groove
    mute_where('CONGAS', lambda c: not 105 <= bar(c) < 113)      # stays only in break 2, where the kick is out
    mute_where('TOM 909', lambda c: True)
    mute_where('HAT OFF - shaker shot', lambda c: True)          # doubled the persona's off-beat
    mute_where('BREAKBEAT', lambda c: bar(c) >= 113)             # keeps the break's sauce, out of build and drop
    mute_where('FX - transitions', lambda c: any(w in c['name'] for w in ('reversed', 'tom run', 'swell')))
    mute_where('FX - sub boom', lambda c: bar(c) < 60)
    C('set_track', {'track': 'FX - build tail', 'mute': True})


def riff():
    # the record's register, not the +12 layer, with its body back and at a level you can hear
    T = 'MURDER RIFF (drop 2)'
    C('set_clip', {'track': T, 'clip': {'at': 496.0}, 'pitch': 0})
    C('set_param', {'track': 'MURDER BUS - drop', 'device': 0, 'param': '1 Frequency A', 'display': '180 Hz'})
    C('set_param', {'track': 'MURDER BUS - drop', 'device': 0, 'param': '1 Filter Type A', 'value': 1.0})
    # drop 1: from its second 8 bars, the same phrase
    if not any(c['start'] < 480 for c in clips(T)):
        print(C('fill_range', {'track': T, 'src_start_bar': 125, 'src_end_bar': 153, 'start_bar': 73, 'end_bar': 97},
                timeout=60.0))
    print(T, [(round(bar(c), 1), round(c['end'] / 4 + 1, 1), c.get('pitch')) for c in clips(T)])




# --- second part: tension by absence, the bass filter, texture, room for the voice ---------------

TEXTURE = 'TEXTURE vinyl'
CRACKLE = ('/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Samples/Loops/Texture/'
           'Crackle Vinyl Pop.wav')
SWEEPS = {256.0: (65, 97, ((79, 81), (95, 97))),         # clip start, bars, (close, reopen) in bars
          480.0: (121, 169, ((135, 137), (151, 153)))}
KICK_OUT = {256.0: (65, 88), 512.0: (121, 144)}          # the whole bar; clip 512 has start marker 32, so its notes count from bar 121
BASE_FREQ = '300 Hz'                                     # the Simpler low-pass at velocity 0
VEL_OPEN, VEL_CLOSED = 110, 30                           # the velocity ramp across a sweep


def bass_filter():
    """Live drops clip envelopes on arrangement clips, so the sweep is written in velocity: the Simpler's
    own low-pass opens with velocity, stays open at the riff's 100-118, and closes as the notes fall."""
    C('set_device_on', {'track': 'BASS', 'device': 'Auto Filter', 'on': False})
    for name, kw in (('F On', {'value': 1.0}), ('Filter Type', {'value': 0.0}), ('Filter Slope', {'value': 1.0}),
                     ('Filter Freq', {'display': BASE_FREQ}), ('Filt < Vel', {'value': 1.0})):
        C('set_param', {'track': 'BASS', 'device': 0, 'param': name, **kw})
    for at, (first, _end, moves) in SWEEPS.items():
        notes = C('get_notes', {'track': 'BASS', 'clip': {'at': at}})
        out = []
        for pitch, start, dur, vel in notes:
            for a, z in moves:
                x, y = (a - first) * 4.0, (z - first) * 4.0
                if x <= start < y:
                    vel = min(vel, VEL_OPEN + (VEL_CLOSED - VEL_OPEN) * (start - x) / (y - x))
            out.append([pitch, start, dur, float(round(vel))])
        C('add_notes', {'track': 'BASS', 'clip': {'at': at}, 'notes': out, 'replace': True}, timeout=60.0)
        print(' bass', at, 'velocities', min(n[3] for n in out), max(n[3] for n in out))


def kick_out():
    for at, (first, out_bar) in KICK_OUT.items():
        a, z = (out_bar - first) * 4.0, (out_bar - first + 1) * 4.0
        notes = C('get_notes', {'track': 'KICK', 'clip': {'at': at}})
        kept = [n for n in notes if not a <= n[1] < z]
        C('add_notes', {'track': 'KICK', 'clip': {'at': at}, 'notes': kept, 'replace': True})
        print(' kick out bar', out_bar, 'removed', len(notes) - len(kept))


def texture():
    names = [t['name'] for t in C('get_song', {})['tracks']]
    if TEXTURE not in names:
        C('create_track', {'kind': 'audio', 'name': TEXTURE})
        C('set_track_input', {'track': TEXTURE, 'source': 'No Input'})
        C('set_track_output', {'track': TEXTURE, 'dest': 'MUSIC BUS'})
        C('set_track', {'track': TEXTURE, 'color_index': 21, 'volume_db': -16.0})
        C('create_audio_clip', {'track': TEXTURE, 'path': CRACKLE, 'beat': 0.0, 'name': 'vinyl', 'warp': True,
                                'warp_mode': 'texture', 'beats': 24})
        print(' texture', C('fill_range', {'track': TEXTURE, 'src_start_bar': 1, 'src_end_bar': 7, 'start_bar': 7,
                                           'end_bar': 185}, timeout=60.0))


def music_up():
    C('set_track', {'track': 'CITY SYNTH', 'volume_db': -7.1})
    C('set_track', {'track': 'MURDER BUS - drop', 'volume_db': -12.0})
    tr = C('get_track', {'track': 'MURDER BUS - drop'})
    if not any(d['class'] == 'Compressor2' for d in tr['devices']):
        C('load_device', {'track': 'MURDER BUS - drop', 'query': 'Compressor'}, timeout=30.0)
    for name, kw in (('Model', {'value': 0.0}), ('Expansion Ratio', {'value': 0.0}), ('Threshold', {'display': '-24.0 dB'}),
                     ('Ratio', {'display': '3.00 : 1'}), ('Attack', {'display': '10.00 ms'}), ('Release', {'display': '150 ms'}),
                     ('S/C EQ On', {'value': 0.0})):
        C('set_param', {'track': 'MURDER BUS - drop', 'device': 'Compressor', 'param': name, **kw})
    C('set_device_input', {'track': 'MURDER BUS - drop', 'device': 'Compressor', 'source': 'VOX BUS', 'channel': 'Post Mixer'})
    C('set_param', {'track': 'MURDER BUS - drop', 'device': 'Compressor', 'param': 'S/C On', 'value': 1.0})


if __name__ == '__main__':
    steps = {'percussion': percussion, 'riff': riff, 'bass': bass_filter, 'kick': kick_out, 'texture': texture, 'music': music_up}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
