"""TECHNO #8 v4 (2026-11-02), after his notes on v3: chops square and out of warp, break without
movement, build without tension, repetitive.

The voice is a 123.6 BPM record whose 4-beat cell hits 0, .75, 1.25, 1.75, 2.25, 3: pinned to 32
beats it sits in the same off-16ths as the riff (1.75, 2.25, 2.75, 3.25). So nothing unwarped: every
piece is a warped slice placed on its own beat phase, and the riff leaves room where the voice answers.
Stages: python techno8_v4.py riff | voice | break | build | holes | top
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server
from techno8_arrange import (_ensure, _names, B, BASS, BASS_B, BASS_FILE, CH, CLAP13, CLAP15, HAT, KICK, KICK_HP, LOOP,
                             LOOP_FILE, OPEN, PERC, RIFF, SYNTH_B, TOP, V_CALL, V_CHOP, V_PHR, V_THROW,
                             VOX_FILE, C)

PAD = 10
TOP_B = 'TOP - build'
TOP_FILE = '/Users/lukasgalhardo/Desktop/Projects 26:27/TECHNO #8 Project/Samples/Imported/91V_SGR_135_drum_top_loop_all_in.wav'
RIFF_NOTES = json.loads((Path(__file__).parent / 'techno8_riff.json').read_text())
EDGE = .03     # a slice opens this many beats before the attack, in the gap


def riff(keep=lambda n: True, lift=False):
    out = []
    for p, t, d, v in RIFF_NOTES:
        if not keep(t):
            continue
        if lift and 8 <= t < 12:
            p = {74: 77, 67: 70}.get(p, p)
        out.append([p, t, d, int(v)])
    return out


def ans(t):
    return t < 12.6


def stage_riff():
    d1 = [(riff(), None), (riff(), None), (riff(ans), 12), (riff(), None), (riff(ans), None), (riff(ans), None),
          (riff(lift=True), None), (riff(lambda t: t < 8, lift=True), 8)]
    d2 = [(riff(ans), 12), (riff(ans), 12), (riff(), None), (riff(lambda t: t < 8), 8),
          (riff(lambda t: t < 4 or 8 <= t < 12), None), (riff(lambda t: t < 4 or 8 <= t < 12), None),
          (riff(ans, lift=True), 12), (riff(ans, lift=True), 12)]
    # the audio loop doubles the riff: it has to leave the same room or the voice answers nothing
    loop_on = {65: 1, 69: 1, 73: 1, 77: 1, 93: 1, 129: 1, 133: 1, 137: 1, 141: 1, 153: 1, 157: 1}
    for first, cycles in ((65, d1), (129, d2)):
        last = first + 4 * len(cycles)
        C('delete_clips_in_range', track=RIFF, start_bar=first, end_bar=last)
        C('delete_clips_in_range', track=LOOP, start_bar=first, end_bar=last)
        for i, (notes, cut) in enumerate(cycles):
            bar = first + 4 * i
            C('create_midi_clip', track=RIFF, beat=B(bar), length=16, notes=notes, name=f'riff {bar}')
            if bar in loop_on:
                C('create_audio_clip', track=LOOP, path=str(LOOP_FILE), bar=bar, warp=True, beats=16, name='loop')
                if cut:
                    C('trim_clip', track=LOOP, clip={'at': B(bar)}, end_beat=B(bar) + cut)


def piece(track, song, src, length, pitch=0):
    """The voice from source beat `src` (attack time on its own grid) at song beat `song`."""
    at = song - EDGE
    C('create_audio_clip', track=track, path=VOX_FILE, beat=at, warp=True, beats=32, name=f'vox {src}',
      warp_mode='complex_pro', pitch=pitch)
    C('set_clip', track=track, clip={'at': at}, start_marker=src - EDGE)
    C('trim_clip', track=track, clip={'at': at}, end_beat=song + length)


def cell(b):
    # the whole cell, its last syllable ringing into the next beat
    return [(V_CHOP, b, 4, 4)]


def half(b):
    # the cell from its off-16ths on; b is where the whole cell would have started
    return [(V_CHOP, b + 1.25, 5.25, 2.75)]


def shout(b):
    # 12.5 / 28.5 keep the off-8th they have on the record
    return [(V_CALL, b, 12.5, 3.5)]


def resp(b):
    return [(V_CALL, b, 28.5, 1.5)]


def stage_voice():
    for t in (V_CALL, V_CHOP, V_THROW):
        C('delete_clips_in_range', track=t, start_bar=1, end_bar=193)
    for t, l in ((V_CALL, -12.3), (V_CHOP, -11), (V_THROW, -20)):
        C('set_send', track=t, send=0, db=-19.4)
        C('set_track', track=t, volume_db=l)
    b = B
    ev = shout(b(64) + .5)
    ev += cell(b(73) + 12) + shout(b(77) + 8.5) + half(b(81) + 12) + cell(b(85) + 12)
    ev += shout(b(89) + 12.5) + cell(b(93) + 8) + cell(b(93) + 12)
    ev += resp(b(129) + .5) + half(b(129) + 12) + cell(b(133) + 12) + shout(b(137) + 8.5)
    ev += cell(b(141) + 8) + cell(b(141) + 12) + cell(b(145) + 4) + cell(b(145) + 12)
    ev += shout(b(149) + 4.5) + cell(b(149) + 12) + half(b(153) + 12) + cell(b(157) + 12)
    ev += cell(b(37) + 12)
    # main break: the voice grows between its two phrases
    ev += half(b(113) + 8) + cell(b(115) + 4)
    # build: its own syllable, slower than the riff, then 8ths, then 16ths climbing, one bar alone
    ev += shout(b(122) + .5) + half(b(121) + 12)
    ev += [(V_CHOP, b(125) + i * .5, 5.75, .48, 0) for i in range(8)]
    ev += [(V_CHOP, b(126) + i * .5, 5.75, .48, 1) for i in range(8)]
    ev += [(V_CHOP, b(127) + i * .25 + (.04 if i % 2 else 0), 5.75, .21, 2 + i // 4 * 2 - (i // 12)) for i in range(16)]
    ev += shout(b(128) + .5)
    for e in sorted(ev, key=lambda e: e[1]):
        piece(*(e if len(e) == 5 else (*e, 0)))
    # the delays and swells are baked at 128, the only unwarped pieces left
    for name, at in (('throw', b(60) + 2), ('throw', b(100) + 2), ('swell_2beats', b(64) + 2),
                     ('swell_2beats', b(128) + 2), ('throw', b(136) + 3), ('throw', b(160) + 2)):
        C('create_audio_clip', track=V_THROW, path=str(CH / f'{name}.wav'), beat=at - .0085, warp=False, name=name)


def stage_break():
    # the bass and the loop leave the break: the ear had 16 bars at -14.1 LUFS with the sub on
    C('delete_clips_in_range', track=BASS, start_bar=105, end_bar=121)
    C('delete_clips_in_range', track=LOOP, start_bar=105, end_bar=129)
    C('delete_clips_in_range', track=SYNTH_B, start_bar=105, end_bar=129)
    C('delete_clips_in_range', track=BASS_B, start_bar=105, end_bar=129)
    # the drop's riff dissolving into the break, then breathing: each 4 bars open further and close less
    moves = ((105, (3000, 800, 500), (3, -3)), (109, (500, 1300, 700), (-3, -2)), (113, (700, 1800, 1000), (-2, 0)),
             (117, (1000, 2500, 1400), (0, 1)), (121, (1400, 2200, 3000), (1, 4)), (125, (3000, 6000, 10000), (4, 8)))
    for bar, (a, m, z), (g0, g1) in moves:
        C('create_audio_clip', track=SYNTH_B, path=str(LOOP_FILE), bar=bar, warp=True, beats=16,
          name='synth breathing', envelopes=[
              {'param': 'Frequency', 'device': 'Auto Filter', 'unit': 'display', 'points': [[0, a], [10, m], [16, z]]},
              {'param': 'Output', 'device': 'Utility', 'unit': 'db', 'points': [[0, g0], [16, g1]]}])
    C('trim_clip', track=SYNTH_B, clip={'at': B(125)}, end_beat=B(128))
    # harmony moves over the G pedal of the riff; no bass under it, so nothing fights
    C('delete_clips_in_range', track=PAD, start_bar=105, end_bar=129)
    GM, EB, CM, F = [55, 58, 62, 67], [51, 58, 63, 67], [48, 55, 60, 63], [53, 57, 60, 65]
    seq = [GM, EB, CM, F, GM, EB, CM, F, CM, CM, EB, EB, F, F]
    for i, ch in enumerate(seq):
        bar = 105 + i * 2 if i < 8 else 121 + (i - 8)
        L = 8 if i < 8 else 4
        vel = int(60 + i * 3)
        # his band-pass opens with the phrase; the last clip returns it to his 581 Hz for what follows
        f0, f1 = 400 * 1.17 ** i, 400 * 1.17 ** (i + 1)
        C('create_midi_clip', track=PAD, beat=B(bar), length=L, notes=[[p, 0, L - .25, vel] for p in ch],
          name='break harmony', envelopes=[{'param': 'Frequency', 'device': 'Auto Filter', 'unit': 'display',
                                            'points': [[0, f0], [L - .25, f1]] + ([[L, 581]] if i == len(seq) - 1 else [])}])
    # the bass without its sub keeps the pulse from the break's second half into the build
    for bar, hz in ((113, (350, 250)), (117, (250, 350)), (121, (350, 500)), (125, (500, 1500))):
        C('create_audio_clip', track=BASS_B, path=str(BASS_FILE), bar=bar, warp=True, beats=16,
          name='bass: no sub', envelopes=[
              {'param': '1 Frequency A', 'device': 'EQ Eight', 'unit': 'display', 'points': [[0, hz[0]], [16, hz[1]]]}])
    C('trim_clip', track=BASS_B, clip={'at': B(125)}, end_beat=B(128))
    C('set_track', track=SYNTH_B, volume_db=-9)


def stage_build():
    C('delete_clips_in_range', track=KICK_HP, start_bar=121, end_bar=129)
    notes, t = [], 0.0
    while t < 28 - 1e-3:
        step = .25 if t >= 24 else .5 if t >= 16 else 1.0
        notes.append([60, t, step * .5, int(70 + 50 * t / 28)])
        t += step
    C('create_midi_clip', track=KICK_HP, beat=B(121), length=28, notes=notes, name='build kick: HP 400 -> 150 Hz',
      envelopes=[{'param': '1 Frequency A', 'device': 'EQ Eight', 'unit': 'display', 'points': [[0, 400], [28, 150]]}])
    # highs climb: the open hat on the off-beats, rising, only in the last 3 bars
    n = [[60, .5 + i, .25, int(45 + 6 * i)] for i in range(12)]
    C('create_midi_clip', track=OPEN, beat=B(125), length=12, notes=n, name='open hat rising')
    # the last bar is the voice alone
    for t_ in (HAT, CLAP15, CLAP13, PERC):
        C('mute_clips_in_range', track=t_, muted=True, start_bar=128, end_bar=129)
    C('trim_clip', track=TOP, clip={'at': B(125)}, end_beat=B(128))


def stage_top():
    # highs must climb +0.3-0.6 dB a bar (taste 2): his top loop again, high-passed, rising to the breath
    if TOP_B not in _names():
        C('create_track', kind='audio', name=TOP_B)
    _ensure(TOP_B, 'audio_effects/EQ Eight', 'EQ Eight')
    C('set_param', track=TOP_B, device='EQ Eight', param='1 Filter On A', value=1)
    C('set_param', track=TOP_B, device='EQ Eight', param='1 Filter Type A', item='High Pass 48dB')
    C('set_param', track=TOP_B, device='EQ Eight', param='1 Frequency A', display=2500)
    _ensure(TOP_B, 'audio_effects/Utility', 'Utility')
    C('set_track', track=TOP_B, volume_db=-14)
    C('delete_clips_in_range', track=TOP_B, start_bar=121, end_bar=129)
    for bar, g in ((121, (-18, -8)), (125, (-8, 4))):
        C('create_audio_clip', track=TOP_B, path=TOP_FILE, bar=bar, warp=True, beats=16, name='top rising', envelopes=[
            {'param': 'Output', 'device': 'Utility', 'unit': 'db', 'points': [[0, g[0]], [16, g[1]]]}])
    C('trim_clip', track=TOP_B, clip={'at': B(125)}, end_beat=B(128))


def stage_holes():
    # (track, first bar, last bar + 1): one change every few bars, by absence (taste 2: monotony)
    holes = [(HAT, 23, 25), (PERC, 37, 39), (HAT, 39, 41), (KICK, 40, 41), (KICK, 47, 49), (CLAP13, 49, 53),
             (OPEN, 49, 53), (HAT, 53, 55), (OPEN, 81, 85), (HAT, 85, 87), (KICK, 88, 89), (HAT, 88, 89),
             (CLAP15, 88, 89), (CLAP13, 88, 89), (PERC, 92, 93), (KICK, 143, 145), (HAT, 150, 151),
             (CLAP13, 156, 157), (KICK, 160, 161)]
    for track, a, z in holes:
        C('mute_clips_in_range', track=track, muted=True, start_bar=a, end_bar=z)


if __name__ == '__main__':
    {'riff': stage_riff, 'voice': stage_voice, 'break': stage_break, 'build': stage_build,
     'holes': stage_holes, 'top': stage_top}[sys.argv[1]]()
