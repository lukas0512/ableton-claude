"""TECHNO #8 v6 (2026-11-02), after his notes: channel 13's riff sounds hard, too much repetition.

Soloed against the loop it came from, the riff had one resonance at 1.6-1.8 kHz 13 dB over everything,
a nearly mono image (-21 dB side, loop -8) and notes held to their full 16th (loop decays in 18 ms).
Stages: python techno8_v6.py timbre | notes | thin | cut | restore | riff | drops | final | landing | first_kick (each once: notes shortens what it reads)
"""
from pathlib import Path
import random
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client
from techno8_arrange import (_ensure, _hp_kick, B, BASS, BASS_B, BASS_FILE, C, CH, CLAP13, CLAP15, HAT, KICK_HP, LOOP, LOOP_FILE,
                             PERC, RIFF, SYNTH_B, V_CALL)
from techno8_v4 import PAD, TOP_B, TOP_FILE

EQ = 'EQ Eight'
BOOM = 'FX - boom'
ACID = 13


def stage_timbre():
    for p, v in (('5 Filter On A', 1), ('6 Filter On A', 1)):
        C('set_param', track=RIFF, device=EQ, param=p, value=v)
    C('set_param', track=RIFF, device=EQ, param='5 Frequency A', display=1700)
    C('set_param', track=RIFF, device=EQ, param='5 Q A', display=3)
    C('set_param', track=RIFF, device=EQ, param='5 Gain A', display=-11)
    C('set_param', track=RIFF, device=EQ, param='6 Frequency A', display=450)
    C('set_param', track=RIFF, device=EQ, param='6 Gain A', display=2)
    C('set_param', track=RIFF, device='A Bit Warmer', param='Drive', display=3)
    C('set_param', track=RIFF, device='A Bit Warmer', param='Dry/Wet', display=45)
    _ensure(RIFF, 'audio_effects/Chorus-Ensemble', 'Chorus-Ensemble')
    C('set_param', track=RIFF, device='Chorus-Ensemble', param='Dry/Wet', display=30)
    C('set_send', track=RIFF, send=0, db=-24)
    C('set_send', track=RIFF, send=1, db=-26)


def stage_notes():
    # a played part: shorter than the 16th, its length and accent moving, on-beats leaning in
    rng = random.Random(8)
    tr = client.call('get_track', {'track': RIFF, 'clips': True})
    for c in tr['clips']:
        if c['type'] != 'midi' or c['start'] < B(41) or B(105) <= c['start'] < B(129):
            continue
        r = client.call('get_notes', {'track': RIFF, 'clip': {'at': c['start']}})
        ns = r['notes'] if isinstance(r, dict) else r
        out = []
        for p, t, d, v in ns:
            onbeat = abs(t * 2 - round(t * 2)) < .06
            nd = max(.08, min(d, .25) * rng.uniform(.5, .8))
            nv = max(40, min(127, v + (6 if onbeat else -6) + rng.randint(-5, 5)))
            out.append([p, t, nd, nv])
        C('add_notes', track=RIFF, clip={'at': c['start']}, notes=out, replace=True)


def stage_thin():
    # the riff ran 64 bars straight from 41: before the break only its low pulse, so the drop brings the rest
    C('set_param', track=RIFF, device=EQ, param='5 Frequency A', display=1660)
    C('set_param', track=RIFF, device=EQ, param='5 Gain A', display=-14)
    tr = client.call('get_track', {'track': RIFF, 'clips': True})
    for c in tr['clips']:
        if B(41) <= c['start'] < B(49) and c['type'] == 'midi':
            r = client.call('get_notes', {'track': RIFF, 'clip': {'at': c['start']}})
            ns = r['notes'] if isinstance(r, dict) else r
            C('add_notes', track=RIFF, clip={'at': c['start']}, notes=[n for n in ns if n[0] < 60], replace=True)


# 168 bars: 8 less of bass groove, the exit (drop 1 goes straight into the break), 8 less of outro
CUTS = ((169, 177), (97, 105), (25, 33))
CUES = ((1, 'INTRO - drums'), (17, 'GROOVE - bass'), (25, 'GROOVE - open hat'), (33, 'GROOVE - riff pulse'),
        (41, 'GROOVE - riff'), (49, 'BREAK 1'), (57, 'DROP 1'), (65, 'DROP 1 - vocal answers'), (89, 'MAIN BREAK'),
        (105, 'BUILD'), (113, 'DROP 2'), (129, 'DROP 2 - synth and voice trade'), (137, 'DROP 2 - all back'),
        (145, 'OUTRO A'), (153, 'OUTRO B - drums'))


def stage_cut():
    C('create_audio_clip', track='VOX - throws', path=str(CH / 'throw.wav'), beat=B(96) + 2 - .0085, warp=False, name='throw')
    song = client.call('get_song')
    tracks = [i for i, t in enumerate(song['tracks']) if i != 0 and t['kind'] != 'group']
    for a, z in CUTS:
        for i in tracks:
            # his vocal pick-up at bar 32 survives the cut, moved with the bars after it
            first = 32 if a == 25 and i == 14 else z
            C('delete_clips_in_range', track=i, start_bar=a, end_bar=first)
            C('shift_clips', track=i, from_bar=first, bars=a - z)
    C('clear_cues')
    for bar, name in CUES:
        C('set_cue', name=name, bar=bar)


def _param_env(param, device, points, unit='display'):
    return {'param': param, 'device': device, 'unit': unit, 'points': points}


def stage_restore():
    # shift_clips moved these clips without their device envelopes: rebuilt at the new bars
    # (main break 89, build 105, drop 2 113)
    for track, a, z in ((SYNTH_B, 89, 113), (BASS_B, 89, 113), (KICK_HP, 53, 57), (KICK_HP, 89, 113), (TOP_B, 105, 121),
                        (PAD, 89, 113), (LOOP, 113, 129), (LOOP, 137, 145)):
        C('delete_clips_in_range', track=track, start_bar=a, end_bar=z)
    for bar, (a, m, z), (g0, g1) in ((89, (3000, 800, 500), (3, -3)), (93, (500, 1300, 700), (-3, -2)),
                                     (97, (800, 1800, 1100), (0, 2)), (101, (1100, 2500, 1500), (2, 4)),
                                     (105, (1500, 2500, 3500), (4, 8)), (109, (3500, 7000, 12000), (8, 13))):
        C('create_audio_clip', track=SYNTH_B, path=str(LOOP_FILE), bar=bar, warp=True, beats=16, name='synth opening', envelopes=[
            _param_env('Frequency', 'Auto Filter', [[0, a], [10, m], [16, z]]), _param_env('Output', 'Utility', [[0, g0], [16, g1]], 'db')])
    C('trim_clip', track=SYNTH_B, clip={'at': B(109)}, end_beat=B(112))
    for bar, hz in ((97, (350, 250)), (101, (250, 220)), (105, (220, 180)), (109, (180, 180))):
        C('create_audio_clip', track=BASS_B, path=str(BASS_FILE), bar=bar, warp=True, beats=16, name='bass: no sub',
          envelopes=[_param_env('1 Frequency A', EQ, [[0, hz[0]], [16, hz[1]]])])
    C('trim_clip', track=BASS_B, clip={'at': B(109)}, end_beat=B(112))
    _hp_kick(B(53), B(56) + 2, 4)
    C('create_midi_clip', track=KICK_HP, beat=B(97), length=32, name='break kick, far away',
      notes=[[60, float(i), .5, int(55 + i * .8)] for i in range(32)],
      envelopes=[_param_env('1 Frequency A', EQ, [[0, 800], [32, 450]])])
    notes, t = [], 0.0
    while t < 28 - 1e-3:
        step = .25 if t >= 24 else .5 if t >= 16 else 1.0
        notes.append([60, t, step * .5, int(80 + 47 * t / 28)])
        t += step
    C('create_midi_clip', track=KICK_HP, beat=B(105), length=28, notes=notes, name='build kick, gaining weight',
      envelopes=[_param_env('1 Frequency A', EQ, [[0, 450], [28, 110]])])
    for bar, g in ((105, (-14, -4)), (109, (-4, 6)), (113, (0, 0)), (117, (0, -8))):
        C('create_audio_clip', track=TOP_B, path=TOP_FILE, bar=bar, warp=True, beats=16, name='top rising',
          envelopes=[_param_env('Output', 'Utility', [[0, g[0]], [16, g[1]]], 'db')])
        if bar == 109:
            C('trim_clip', track=TOP_B, clip={'at': B(109)}, end_beat=B(112))
    GM, EB, CM, F = [55, 58, 62, 67], [51, 58, 63, 67], [48, 55, 60, 63], [53, 57, 60, 65]
    seq = [GM, EB, CM, F, GM, EB, CM, F, CM, CM, EB, EB, F, F]
    for i, ch in enumerate(seq):
        bar, L = (89 + i * 2, 8) if i < 8 else (105 + (i - 8), 4)
        f0, f1 = 400 * 1.17 ** i, 400 * 1.17 ** (i + 1)
        C('create_midi_clip', track=PAD, beat=B(bar), length=L, notes=[[p, 0, L - .25, int(60 + i * 3)] for p in ch],
          name='break harmony', envelopes=[_param_env('Frequency', 'Auto Filter',
                                                      [[0, f0], [L - .25, f1]] + ([[L, 581]] if i == len(seq) - 1 else []))])
    for bar in (113, 117, 121, 125, 137, 141):
        pts = [[0, 450], [15.75, 450]] if bar != 141 else [[0, 450], [11.75, 450], [12, 1780]]
        C('create_audio_clip', track=LOOP, path=str(LOOP_FILE), bar=bar, warp=True, beats=16, name='loop low-passed',
          envelopes=[_param_env('8 Frequency A', EQ, pts)])
    C('trim_clip', track=LOOP, clip={'at': B(141)}, end_beat=B(141) + 12)


def stage_riff():
    # the MIDI came from audio-to-MIDI: its D5 accents ring A6 (1758 Hz, this patch's strong 3rd partial)
    # where the loop has D5 and G5 (581, 778 Hz). Accents down an octave, the patch shaped towards the
    # loop's bands, and the loop itself comes back open: it holds the real melody
    tr = client.call('get_track', {'track': RIFF, 'clips': True})
    for c in tr['clips']:
        if c['type'] != 'midi':
            continue
        r = client.call('get_notes', {'track': RIFF, 'clip': {'at': c['start']}})
        ns = r['notes'] if isinstance(r, dict) else r
        if any(n[0] >= 60 for n in ns):
            C('add_notes', track=RIFF, clip={'at': c['start']}, replace=True,
              notes=[[n[0] - 12 if n[0] >= 60 else n[0], n[1], n[2], n[3]] for n in ns])
    C('delete_clips_in_range', track=RIFF, start_bar=109, end_bar=112)
    C('create_midi_clip', track=RIFF, beat=B(109), length=8, name='riff pressing',
      notes=[[55, i * .5, .2, 95 + i] for i in range(16)] + [[62 + (i // 8) * 2, i * .5 + .25, .18, 80 + i] for i in range(16)])
    scale = [55, 57, 58, 60, 62, 63, 65]
    up = [scale[i % 7] + 12 * (i // 7) for i in range(30)]
    run = up[up.index(79) - 15:up.index(79) + 1]
    C('create_midi_clip', track=RIFF, beat=B(111), length=4, name='riff climbing',
      notes=[[p, i * .25, .2, 80 + 3 * i] for i, p in enumerate(run)])
    C('set_param', track=RIFF, device=EQ, param='6 Gain A', display=0)
    C('set_param', track=RIFF, device=EQ, param='5 Gain A', display=-8)
    C('set_param', track=RIFF, device=EQ, param='8 Frequency A', display=1500)
    C('set_param', track=RIFF, device=EQ, param='8 Q A', display=.7)
    for a, z in ((113, 129), (137, 145)):
        C('delete_clips_in_range', track=LOOP, start_bar=a, end_bar=z)
    C('set_param', track=LOOP, device=EQ, param='8 Frequency A', display=1780)
    for bar in (113, 117, 121, 125, 137, 141):
        C('create_audio_clip', track=LOOP, path=str(LOOP_FILE), bar=bar, warp=True, beats=16, name='loop')
        if bar in (113, 117, 137, 141):
            C('trim_clip', track=LOOP, clip={'at': B(bar)}, end_beat=B(bar) + 12)


def _bake_boom():
    # the drop's first hit: a sub falling onto the key's root, from the song's own G
    sr, n = 44100, int(2 * 60 / 128 * 44100)
    t = np.arange(n) / sr
    hz = 49 + 30 * np.exp(-t / .05)
    y = np.tanh(1.6 * np.sin(2 * np.pi * np.cumsum(hz) / sr)) * np.exp(-t / .32)
    y[-400:] *= np.linspace(1, 0, 400)
    path = CH / 'boom_G.wav'
    sf.write(path, np.stack([y, y], 1) * .7, sr, subtype='PCM_24')
    return path


def stage_drops():
    boom = _bake_boom()
    if BOOM not in [t['name'] for t in client.call('get_song')['tracks']]:
        C('create_track', kind='audio', name=BOOM)
    C('set_track', track=BOOM, volume_db=-9)
    C('delete_clips_in_range', track=BOOM, start_bar=1, end_bar=169)
    for bar in (57, 113):
        C('create_audio_clip', track=BOOM, path=str(boom), bar=bar, warp=False, name='boom')

    # drop 1 gets the build's highs too, smaller than drop 2's
    C('delete_clips_in_range', track=TOP_B, start_bar=53, end_bar=65)
    for bar, g, cut in ((53, (-14, 4), 12), (57, (-5, -5), None), (61, (-5, -12), None)):
        C('create_audio_clip', track=TOP_B, path=TOP_FILE, bar=bar, warp=True, beats=16, name='top rising',
          envelopes=[_param_env('Output', 'Utility', [[0, g[0]], [16, g[1]]], 'db')])
        if cut:
            C('trim_clip', track=TOP_B, clip={'at': B(bar)}, end_beat=B(bar) + cut)

    # each drop turns over halfway: the loop dives through its filter and comes back open
    for bar in (69, 121):
        C('delete_clips_in_range', track=LOOP, start_bar=bar, end_bar=bar + 4)
        C('create_audio_clip', track=LOOP, path=str(LOOP_FILE), bar=bar, warp=True, beats=16, name='loop diving',
          envelopes=[_param_env('8 Frequency A', EQ, [[0, 1780], [8, 1780], [14, 350], [15.75, 350], [16, 1780]])])

    # the voice reversed into each phrase of the drops, under the music
    for bar in (65, 73, 81, 121, 129, 137):
        at = B(bar) - 2 - .0085
        C('create_audio_clip', track='VOX - throws', path=str(CH / 'swell_2beats.wav'), beat=at, warp=False, name='swell', gain_db=-5)

    # his acid, muted in the sketch, as drop 2's sauce where the loop rests; its first clips stay muted
    C('mute_clips_in_range', track=ACID, muted=True, start_bar=57, end_bar=59)
    # two octaves up: at F1/G1 it would sit on the bass's sub
    a = client.call('get_notes', {'track': ACID, 'clip': {'at': B(57)}})
    a = a['notes'] if isinstance(a, dict) else a
    C('delete_clips_in_range', track=ACID, start_bar=129, end_bar=137)
    C('create_midi_clip', track=ACID, beat=B(129), length=32, name='acid sauce',
      notes=[[n[0] + 24, n[1] + 4 * k, n[2], n[3]] for k in range(8) for n in a if n[1] + 4 * k < 32])
    C('set_track', track=ACID, mute=False, volume_db=-13)

    # the opening synth pumps from the build's kick: the faster it hits, the harder it pushes
    _ensure(SYNTH_B, 'audio_effects/Compressor', 'Compressor')
    C('set_device_input', track=SYNTH_B, device='Compressor', source=KICK_HP)
    C('set_param', track=SYNTH_B, device='Compressor', param='Threshold', display=-30)
    C('set_param', track=SYNTH_B, device='Compressor', param='Ratio', display=4)
    C('set_param', track=SYNTH_B, device='Compressor', param='Attack', display='1.00 ms')
    C('set_param', track=SYNTH_B, device='Compressor', param='Release', display='90.0 ms')


def stage_final():
    # break 1 sat flat at -14 with the sub on, so drop 1 had no climb: the same arc as the main build, shorter
    C('delete_clips_in_range', track=BASS, start_bar=49, end_bar=57)
    C('delete_clips_in_range', track=KICK_HP, start_bar=49, end_bar=57)
    C('delete_clips_in_range', track=TOP_B, start_bar=53, end_bar=57)
    C('delete_clips_in_range', track=BASS_B, start_bar=49, end_bar=57)
    C('delete_clips_in_range', track=SYNTH_B, start_bar=49, end_bar=57)
    for bar, hz, (a, m, z), (g0, g1) in ((49, (300, 220), (700, 1500, 1200), (-1, 3)), (53, (220, 180), (1200, 4000, 9000), (3, 11))):
        C('create_audio_clip', track=BASS_B, path=str(BASS_FILE), bar=bar, warp=True, beats=16, name='bass: no sub',
          envelopes=[_param_env('1 Frequency A', EQ, [[0, hz[0]], [16, hz[1]]])])
        C('create_audio_clip', track=SYNTH_B, path=str(LOOP_FILE), bar=bar, warp=True, beats=16, name='synth opening', envelopes=[
            _param_env('Frequency', 'Auto Filter', [[0, a], [10, m], [16, z]]), _param_env('Output', 'Utility', [[0, g0], [16, g1]], 'db')])
    for t in (BASS_B, SYNTH_B):
        C('trim_clip', track=t, clip={'at': B(53)}, end_beat=B(56))
    notes = [[60, float(i), .5, int(75 + i * 2)] for i in range(16)] + [[60, 16 + i * .5, .25, int(105 + i)] for i in range(8)] \
        + [[60, 20 + i * .25, .12, int(112 + i)] for i in range(14)]
    C('create_midi_clip', track=KICK_HP, beat=B(49), length=28, notes=notes, name='build 1 kick',
      envelopes=[_param_env('1 Frequency A', EQ, [[0, 500], [28, 130]])])
    C('create_audio_clip', track=TOP_B, path=TOP_FILE, bar=53, warp=True, beats=16, name='top rising',
      envelopes=[_param_env('Output', 'Utility', [[0, -10], [16, 6]], 'db')])
    C('trim_clip', track=TOP_B, clip={'at': B(53)}, end_beat=B(56))
    # the build's end lost 2 dB to the pump: give it back
    C('set_param', track=SYNTH_B, device='Compressor', param='Output', display='3.00 dB')
    C('set_track', track=SYNTH_B, volume_db=-7)
    # drop 1's highs were 4 dB under the reference
    C('delete_clips_in_range', track=TOP_B, start_bar=57, end_bar=61)
    C('create_audio_clip', track=TOP_B, path=TOP_FILE, bar=57, warp=True, beats=16, name='top rising',
      envelopes=[_param_env('Output', 'Utility', [[0, -2], [16, -2]], 'db')])
    # the acid added 3.3 dB at 120-250 Hz; the riff and loop hold the 250-500 Hz excess
    C('set_track', track=ACID, volume_db=-18)
    C('set_param', track=RIFF, device=EQ, param='2 Frequency A', display=380)
    C('set_param', track=RIFF, device=EQ, param='2 Gain A', display=-5)
    C('set_param', track=LOOP, device=EQ, param='3 Filter On A', value=1)
    C('set_param', track=LOOP, device=EQ, param='3 Filter Type A', item='Bell')
    C('set_param', track=LOOP, device=EQ, param='3 Frequency A', display=380)
    C('set_param', track=LOOP, device=EQ, param='3 Gain A', display=-4)


def stage_landing():
    # the synth stood 12-13 dB over the drop at 250-1000 Hz and all of it vanished on the downbeat: it now
    # thins out as it opens, so the drop's body is what returns. Drop 1's last two bars also match drop 2's:
    # drums carry on through bar 55, then bar 56 is the voice alone
    C('delete_clips_in_range', track=SYNTH_B, start_bar=49, end_bar=57)
    C('delete_clips_in_range', track=SYNTH_B, start_bar=105, end_bar=113)
    for bar, (a, m, z), (g0, g1), hp in ((49, (700, 1500, 1200), (-1, 3), (40, 120)), (53, (1200, 4000, 9000), (3, 11), (120, 650)),
                                         (105, (1500, 2500, 3500), (4, 7), (40, 150)), (109, (3500, 7000, 12000), (7, 13), (150, 800))):
        C('create_audio_clip', track=SYNTH_B, path=str(LOOP_FILE), bar=bar, warp=True, beats=16, name='synth opening', envelopes=[
            _param_env('Frequency', 'Auto Filter', [[0, a], [10, m], [16, z]]), _param_env('Output', 'Utility', [[0, g0], [16, g1]], 'db'),
            _param_env('1 Frequency A', EQ, [[0, hp[0]], [16, hp[1]]])])
    for bar in (53, 109):
        C('trim_clip', track=SYNTH_B, clip={'at': B(bar)}, end_beat=B(bar + 3))
    for t in (HAT, CLAP15):
        C('mute_clips_in_range', track=t, muted=False, start_bar=55, end_bar=56)
        C('mute_clips_in_range', track=t, muted=True, start_bar=56, end_bar=57)
    C('mute_clips_in_range', track=CLAP13, muted=True, start_bar=56, end_bar=57)
    C('set_clip', track=V_CALL, clip={'at': B(56) + .47}, gain_db=4)


def stage_first_kick():
    # his notes: the first kick lands wrong. Three causes: an FX hit a 16th early ringing over it, the baked
    # sub bending its waveform (correlation with the next kicks .89 -> .53), and no bass under that kick
    for bar in (57, 113):
        C('delete_clip', track=20, clip={'at': B(bar) - .25})
        C('delete_clips_in_range', track=BOOM, start_bar=bar, end_bar=bar + 1)
        r = client.call('get_notes', {'track': 1, 'clip': {'at': B(bar)}})
        ns = r['notes'] if isinstance(r, dict) else r
        C('add_notes', track=1, clip={'at': B(bar)}, replace=True,
          notes=[[n[0], n[1], n[2], 127 if n[1] < .01 else n[3]] for n in ns])


if __name__ == '__main__':
    {'first_kick': stage_first_kick, 'landing': stage_landing, 'final': stage_final, 'drops': stage_drops, 'riff': stage_riff, 'timbre': stage_timbre, 'notes': stage_notes, 'thin': stage_thin, 'cut': stage_cut,
     'restore': stage_restore}[sys.argv[1]]()
