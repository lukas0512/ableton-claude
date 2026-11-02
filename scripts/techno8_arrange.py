"""TECHNO #8 (2026-11-02): finish the arrangement around the 64 bars he built.

Form, 192 bars at 128: intro 1-16 | grooves 17-56 | break 57-64 | DROP 1 65-96 | prepared exit
97-104 | main break 105-120 | build 121-128 | DROP 2 129-160 | outro A 161-176 | outro B 177-192.
Stages: python techno8_arrange.py fill | build | vox | fx | cues
"""
import json
from pathlib import Path
import sys

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server

KICK, BASS, TOP, PERC, HAT, OPEN, CLAP15, CLAP13, PING, LOOP, RIFF, VOX = 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14
FX16, FX11, FX6, FX3, FX10 = 16, 17, 18, 19, 20
PROJ = Path('/Users/lukasgalhardo/Desktop/Projects 26:27/TECHNO #8 Project/Samples')
CH = PROJ / 'Claude vox'
BASS_FILE = PROJ / 'Processed/Normalize/NCPZ1_BASSLOOP9_Fmin [2026-11-01 190524].wav'
LOOP_FILE = PROJ / 'Processed/Normalize/NCPZ1_SYNTHLOOP19_Gmin [2026-11-01 182738].wav'
VOX_FILE = '/Users/lukasgalhardo/Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs/Vox/Vox/Old school vox/Beatbox Female #20.wav'
B = lambda bar: (bar - 1) * 4.0


def C(cmd, **args):
    r = server._journaled(cmd, args)
    print(cmd, args.get('track', ''), str(r)[:120], flush=True)
    return r


def fill(track, a, b, c, d):
    C('fill_range', track=track, src_start_bar=a, src_end_bar=b, start_bar=c, end_bar=d)


def stage_fill():
    # the riff and the two drums that carry drop 1 return from bar 1 of drop 2
    fill(KICK, 65, 69, 129, 193)
    fill(BASS, 65, 81, 129, 169)
    fill(TOP, 65, 69, 129, 193)
    fill(PERC, 65, 67, 113, 128)
    fill(PERC, 65, 67, 129, 193)
    fill(HAT, 65, 69, 105, 117)
    fill(HAT, 65, 69, 133, 193)
    fill(OPEN, 65, 69, 129, 165)
    fill(CLAP15, 65, 66, 105, 193)
    fill(CLAP13, 65, 67, 125, 177)
    fill(PING, 65, 67, 141, 177)
    fill(LOOP, 97, 101, 161, 169)
    fill(RIFF, 65, 81, 129, 165)
    # subtraction: the build has its own synth, the drops keep their reserved layers
    C('mute_clips_in_range', track=LOOP, muted=True, start_bar=121, end_bar=129)
    C('mute_clips_in_range', track=OPEN, muted=True, start_bar=65, end_bar=73)
    for bar in (136, 152, 175, 176):
        C('mute_clips_in_range', track=KICK, muted=True, start_bar=bar, end_bar=bar + 1)


KICK_HP, BASS_B, SYNTH_B = 'KICK - build (HP)', 'BASS - build', 'SYNTH - build'
V_PHR, V_CALL, V_CHOP, V_THROW = 'VOX - phrases', 'VOX - calls', 'VOX - chops', 'VOX - throws'


def _names():
    return [t['name'] for t in client.call('get_song')['tracks']]


def _new(kind, name):
    if name not in _names():
        C('create_track', kind=kind, name=name)


def _ensure(track, path, name):
    if name not in [d['name'] for d in client.call('get_track', {'track': track})['devices']]:
        C('load_device', track=track, path=path)


def _hp_kick(a, b, last8):
    L = b - a
    notes, t = [], 0.0
    while t < L - 1e-3:
        step = .5 if t >= L - last8 else 1.0
        notes.append([60, t, step * .5, int(70 + 50 * t / L)])
        t += step
    C('create_midi_clip', track=KICK_HP, beat=a, length=L, notes=notes,
      name='build kick: HP 400 -> 150 Hz', envelopes=[
          {'param': '1 Frequency A', 'device': 'EQ Eight', 'unit': 'display',
           'points': [[0, 400], [L, 150]]}])


def stage_build():
    _new('midi', KICK_HP)
    _ensure(KICK_HP, 'samples/NCPZ1_KICK14.wav', 'NCPZ1_KICK14')
    _ensure(KICK_HP, 'audio_effects/EQ Eight', 'EQ Eight')
    C('set_param', track=KICK_HP, device='EQ Eight', param='1 Filter On A', value=1)
    C('set_param', track=KICK_HP, device='EQ Eight', param='1 Filter Type A', item='High Pass 48dB')
    _hp_kick(B(61), B(64) + 2, 4)
    _hp_kick(B(121), B(128) + 2, 8)

    # the bass stays through the build, its sub leaving over the last four bars
    _new('audio', BASS_B)
    _ensure(BASS_B, 'audio_effects/EQ Eight', 'EQ Eight')
    C('set_param', track=BASS_B, device='EQ Eight', param='1 Filter On A', value=1)
    C('set_param', track=BASS_B, device='EQ Eight', param='1 Filter Type A', item='High Pass 12dB')
    for bar, hz in ((121, (20, 20)), (125, (20, 200))):
        C('create_audio_clip', track=BASS_B, path=str(BASS_FILE), bar=bar, warp=True, beats=16,
          name='bass: sub leaving', envelopes=[
              {'param': '1 Frequency A', 'device': 'EQ Eight', 'unit': 'display',
               'points': [[0, hz[0]], [16, hz[1]]]}])
    C('trim_clip', track=BASS_B, clip={'at': B(125)}, end_beat=B(128) + 2)

    # the drop's synth, closed and opening: the track's own riser
    _new('audio', SYNTH_B)
    _ensure(SYNTH_B, 'audio_effects/Auto Filter', 'Auto Filter')
    C('set_param', track=SYNTH_B, device='Auto Filter', param='Filter Type', item='Low-pass')
    _ensure(SYNTH_B, 'audio_effects/Utility', 'Utility')
    for bar, hz, g in ((121, (450, 1400), (0, 3)), (125, (1400, 7000), (3, 6))):
        C('create_audio_clip', track=SYNTH_B, path=str(LOOP_FILE), bar=bar, warp=True, beats=16,
          name='synth opening', envelopes=[
              {'param': 'Frequency', 'device': 'Auto Filter', 'unit': 'display',
               'points': [[0, hz[0]], [16, hz[1]]]},
              {'param': 'Output', 'device': 'Utility', 'unit': 'db', 'points': [[0, g[0]], [16, g[1]]]}])
    C('trim_clip', track=SYNTH_B, clip={'at': B(125)}, end_beat=B(128) + 2)


def _chop(track, name, beat):
    # the file starts 4 ms before the attack: the attack lands on the beat
    d = sf.info(str(CH / f'{name}.wav')).duration
    C('create_audio_clip', track=track, path=str(CH / f'{name}.wav'), beat=beat - .0085, warp=False, name=name)


def _phrase(beat, marker, beats):
    C('create_audio_clip', track=V_PHR, path=VOX_FILE, beat=beat, warp=True, beats=32, name=f'phrase {marker}-{marker + beats}')
    C('set_clip', track=V_PHR, clip={'at': beat}, start_marker=marker + .009)
    C('trim_clip', track=V_PHR, clip={'at': beat}, end_beat=beat + beats)


def H1(b):
    return [(V_CHOP, 'tak', b + 4.25), (V_CALL, 'shout', b + 13.25), (V_CALL, 'tail', b + 14.75)]


def H2(b):
    return [(V_CHOP, 'dum', b + .25), (V_CALL, 'call', b + 12.5)]


def H3(b):
    return [(V_CHOP, 'dum', b + .25), (V_CHOP, 'tak', b + .75), (V_CHOP, 'dum2', b + 13.25),
            (V_CHOP, 'tak', b + 13.5), (V_CALL, 'resp_short', b + 14.75)]


def stage_vox():
    for n in (V_PHR, V_CALL, V_CHOP, V_THROW):
        _new('audio', n)
        _ensure(n, 'audio_effects/EQ Eight', 'EQ Eight')
        C('copy_device', src_track=VOX, src_device=0, track=n, device='EQ Eight')
    sends = {V_PHR: -19.4, V_CALL: -19.4, V_CHOP: -24, V_THROW: -14}
    level = {V_PHR: -17.3, V_CALL: -17.3, V_CHOP: -18, V_THROW: -20}
    for n in sends:
        C('set_send', track=n, send=0, db=sends[n])
        C('set_track', track=n, volume_db=level[n])
    # break 1: his eight bars of phrase become two statements with the riff answering
    C('trim_clip', track=VOX, clip={'at': 224.0085}, end_beat=B(59))
    _phrase(B(61), 8, 8)
    # main break: close, the synth loop answers in between
    _phrase(B(109), 0, 16)
    _phrase(B(117), 16, 16)
    B1, B2 = B(65), B(129)
    ev = [(V_CALL, 'resp_short', B(64)), (V_THROW, 'throw', B(60) + 2), (V_THROW, 'swell_2beats', B(64) + 2),
          (V_CALL, 'resp_short', B1)]
    ev += H1(B(73)) + H2(B(77)) + H1(B(89)) + H3(B(93))
    ev += [(V_THROW, 'throw', B(100) + 2)]
    # build: the call, the response, then the syllable faster until the breath
    ev += [(V_CALL, 'call', B(121)), (V_CALL, 'resp', B(123)), (V_CALL, 'shout', B(125)), (V_CALL, 'shout', B(126) + 1.5)]
    ev += [(V_CHOP, 'dum' if i % 2 == 0 else 'tak', B(127) + i * .5) for i in range(8)]
    ev += [(V_CHOP, 'dum' if i % 2 == 0 else 'tak', B(128) + i * .25) for i in range(8)]
    ev += [(V_THROW, 'swell_2beats', B(128) + 2), (V_CALL, 'resp_short', B2)]
    ev += H1(B2) + H2(B(133)) + [(V_CALL, 'shout', B(136) + 1), (V_THROW, 'throw', B(136) + 3)]
    ev += H1(B(137)) + H3(B(141)) + [(V_CALL, 'call', B(152))] + H2(B(153)) + H1(B(157))
    ev += [(V_THROW, 'throw', B(160) + 2)]
    for track, name, beat in sorted(ev, key=lambda e: e[2]):
        _chop(track, name, beat)


def stage_fx():
    C('duplicate_range', track=FX3, start_bar=60, end_bar=64, dest_bar=124)
    C('duplicate_range', track=FX10, start_bar=60, end_bar=66, dest_bar=124)
    C('duplicate_clip', track=FX6, clip={'at': B(65)}, bar=129)
    C('set_clip', track=FX6, clip={'at': B(129)}, gain_db=3)
    for bar in (57, 105, 161):
        C('duplicate_clip', track=FX16, clip={'at': B(17)}, bar=bar)
    for bar in (145, 177):
        C('duplicate_clip', track=FX16, clip={'at': B(33)}, bar=bar)
    fill_notes = client.call('get_notes', {'track': CLAP13, 'clip': {'at': B(64)}})
    fill_notes = fill_notes['notes'] if isinstance(fill_notes, dict) else fill_notes
    for bar in (96, 128, 160):
        C('add_notes', track=CLAP13, clip={'at': B(bar)}, notes=fill_notes, replace=True)
    C('mute_clips_in_range', track=LOOP, muted=True, start_bar=145, end_bar=153)


def stage_cues():
    for bar, n in ((1, 'INTRO - drums'), (17, 'GROOVE - bass'), (41, 'GROOVE - synth'), (57, 'BREAK 1'),
                   (65, 'DROP 1'), (73, 'DROP 1 - vocal answers'), (97, 'EXIT - kick, bass, synth'),
                   (105, 'MAIN BREAK'), (121, 'BUILD'), (129, 'DROP 2'), (145, 'DROP 2 - no loop'),
                   (153, 'DROP 2 - all back'), (161, 'OUTRO A'), (177, 'OUTRO B - drums')):
        C('set_cue', name=n, bar=bar)


if __name__ == '__main__':
    {'fill': stage_fill, 'build': stage_build, 'vox': stage_vox, 'fx': stage_fx, 'cues': stage_cues}[sys.argv[1]]()
