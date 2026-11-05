"""In the City: the running 16ths as a shaker, and a drier perc loop.

His note (2026-11-05): "hat 16ths muito estranho, fora da track ... era pra funcionar tipo um shaker,
dar velocidade, movimento" and "perc loop: uma secadinha, muita textura, mais contido".
Measured: the hat is the brightest part (centroid 8.0 kHz), almost mono (correlation .98) and a
58 ms tick, the same hit 16 times a bar. Two options, same bars as the hat, HAT 16ths left muted:
  A "SHAKER played"  the kit's played loop (real hands, wide), its 16ths warped onto the track's pocket
  B "SHAKER 16ths"   the kit's shaker one-shot on the hat's notes, small pan/pitch drift, shorter tail
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
KIT = 'user_library/Samples/Claude/Nobody Kit/'
LOOP = Path.home() / 'Music/Ableton/User Library/Samples/Claude/Nobody Kit/PMLxSVTxCioz_Shaker_Acti_Black_Far_Away_122bpm.wav'
A, B = 'SHAKER played', 'SHAKER 16ths'
SPANS = ((1, 64), (65, 84.5), (85, 89), (91, 127), (129, 185))    # where the hat plays (bars)
POCKET = 0.0225          # off-16ths +10.8 ms at 125 BPM
SEC_16TH = 60 / 122 / 4  # the loop's own 16th
ATTACK_LEAD = 0.0104     # the one-shot's attack comes at 5 ms: start it that much early


def hp(track, freq='300 Hz'):
    for name, kw in (('1 Filter On A', {'value': 1.0}), ('1 Filter Type A', {'value': 1.0}),
                     ('1 Frequency A', {'display': freq})):
        C('set_param', {'track': track, 'device': 'EQ Eight', 'param': name, **kw})


def has(track):
    return track in [t['name'] for t in C('get_song', {})['tracks']]


def option_a():
    if not has(A):
        C('create_track', {'kind': 'audio', 'name': A})
    C('set_track_input', {'track': A, 'source': 'No Input'})
    C('set_track_output', {'track': A, 'dest': 'TOPS'})
    tr = C('get_track', {'track': A, 'clips': True})
    if not any(d['class'] == 'Eq8' for d in tr['devices']):
        C('load_device', {'track': A, 'query': 'EQ Eight'}, timeout=30.0)
    hp(A)
    C('set_send', {'track': A, 'send': 3, 'db': -24.0})
    if not tr.get('clips'):
        markers = [[k * 0.25 + (POCKET if k % 2 else 0.0), k * SEC_16TH] for k in range(33)]  # [beat, seconds]
        C('create_audio_clip', {'track': A, 'path': str(LOOP), 'beat': 0.0, 'name': 'shaker played',
                                'warp': True, 'warp_mode': 'beats', 'beats': 8})
        C('set_warp_markers', {'track': A, 'clip': {'at': 0.0}, 'markers': markers})
        C('set_clip', {'track': A, 'clip': {'at': 0.0}, 'looping': False, 'loop_start': 0.0, 'loop_end': 8.0,
                       'start_marker': 0.0, 'end_marker': 8.0})
        for a, z in ((3, 64),) + SPANS[1:]:  # a looped clip keeps its 8 beats: copy the 2-bar phrase, never over itself
            C('fill_range', {'track': A, 'src_start_bar': 1, 'src_end_bar': 3, 'start_bar': a, 'end_bar': z},
              timeout=60.0)
    print(A, C('warp_markers', {'track': A, 'clip': {'at': 0.0}}).get('markers', [])[:3])


def option_b():
    if not has(B):
        C('create_track', {'kind': 'midi', 'name': B})
        C('load_device', {'track': B, 'path': KIT + 'KMRBI_AW_Shaker_One_Shot_Chuga.wav'}, timeout=40.0)
        C('load_device', {'track': B, 'query': 'EQ Eight'}, timeout=30.0)
    C('set_track_output', {'track': B, 'dest': 'TOPS'})
    hp(B)
    C('set_send', {'track': B, 'send': 3, 'db': -24.0})
    dev = 0
    for name, kw in (('Volume', {'display': '-12.0 dB'}), ('Vol < Vel', {'value': 0.35}),
                     ('Ve Decay', {'display': '120 ms'}), ('Ve Sustain', {'value': 0.0}),
                     ('Pan < Rnd', {'value': 0.18}),
                     ('L Wave', {'value': 5.0}), ('L Rate', {'display': '8.00 Hz'}),
                     ('Pitch < LFO', {'value': 0.03})):
        C('set_param', {'track': B, 'device': dev, 'param': name, **kw})
    if not C('get_track', {'track': B, 'clips': True}).get('clips'):
        hat = C('get_notes', {'track': 'HAT 16ths', 'clip': {'at': 0}})
        notes = [[60, max(0.0, n[1] - ATTACK_LEAD), n[2], n[3]] for n in hat if n[1] < 736]
        C('create_midi_clip', {'track': B, 'bar': 1, 'length': 736, 'name': 'shaker 16ths', 'notes': notes},
          timeout=120.0)
    C('set_track', {'track': B, 'mute': True})     # A plays first; swap the mutes to compare


def perc_loop():
    T = 'PERC LOOP'
    C('set_track', {'track': T, 'volume_db': -18.6})
    C('set_send', {'track': T, 'send': 3, 'db': -30.0})
    C('set_param', {'track': T, 'device': 'Auto Pan-Tremolo', 'param': 'Amount', 'value': 0.12})
    for name, kw in (('3 Filter On A', {'value': 1.0}), ('3 Filter Type A', {'value': 3.0}),
                     ('3 Frequency A', {'display': '700 Hz'}), ('3 Gain A', {'value': -2.0})):
        C('set_param', {'track': T, 'device': 'EQ Eight', 'param': name, **kw})


if __name__ == '__main__':
    perc_loop()
    option_a()
    option_b()
    print('done')
