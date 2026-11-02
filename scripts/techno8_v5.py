"""TECHNO #8 v5 (2026-11-02), after his notes on v4: the riff's high notes from 129, synth and voice
conversing, delay and reverb on the voice, a break and build with real pressure into a strong drop.

Drop 2's high notes become the voice's own cell (0, .75, 1.25, 1.75, 2.25, 3), so the synth and the voice
trade one phrase. The audio loop doubles the old high notes, so it plays low-passed under them.
Stages: python techno8_v5.py drop2 | fx | pressure
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from techno8_arrange import (_ensure, B, BASS_B, BASS_FILE, CLAP13, KICK_HP, LOOP, LOOP_FILE, PERC, RIFF, SYNTH_B,
                             V_CALL, V_CHOP, V_PHR, C, fill)
from techno8_v4 import RIFF_NOTES, TOP_B, TOP_FILE, ans, cell, piece, resp, shout

CELL = (0, .75, 1.25, 1.75, 2.25, 3)
LOOP_LOW = 450    # above it the loop's D5 is gone, its pulse stays
LOOP_OPEN = 1780  # his own setting on the loop's EQ


def synth_cell(at, top=65):
    # in the voice's register, the same phrase; off-16ths late as in his riff, rising to its open note
    pitches = (62, 62, 62, 62, 63, top)
    return [[p, at + t + (.011 if t % .5 else 0), .24 if t < 3 else .7, 78 + 3 * i]
            for i, (t, p) in enumerate(zip(CELL, pitches))]


def low(keep=lambda t: True):
    return [[p, t, d, int(v)] for p, t, d, v in RIFF_NOTES if p < 60 and keep(t)]


def stage_drop2():
    C('delete_clips_in_range', track=RIFF, start_bar=129, end_bar=161)
    C('delete_clips_in_range', track=LOOP, start_bar=129, end_bar=161)
    C('delete_clips_in_range', track=V_CHOP, start_bar=129, end_bar=161)
    C('delete_clips_in_range', track=V_CALL, start_bar=129, end_bar=161)
    # bar: riff notes, source cell beats of the voice, shout beats, does the audio loop play
    plan = [(129, low(ans) + synth_cell(8), [12], [], True),
            (133, low(ans) + synth_cell(8), [12], [], True),
            (137, low(lambda t: t < 12) + synth_cell(12, 67), [4], [], True),
            (141, low(lambda t: t < 8) + synth_cell(8, 67), [4, 12], [], True),
            (145, low() + synth_cell(0) + synth_cell(8), [4, 12], [], False),
            (149, low() + synth_cell(0) + synth_cell(8), [12], [4.5], False),
            (153, low(ans) + synth_cell(8, 67), [12], [], True),
            (157, low(ans) + synth_cell(8, 67), [12], [], True)]
    for bar, notes, cells, shouts, loop in plan:
        C('create_midi_clip', track=RIFF, beat=B(bar), length=16, notes=notes, name=f'riff + cell {bar}')
        ev = [e for c in cells for e in cell(B(bar) + c)] + [e for s in shouts for e in shout(B(bar) + s)]
        if bar == 129:
            ev += resp(B(129) + .5)
        for e in sorted(ev, key=lambda e: e[1]):
            piece(*e)
        if loop:
            pts = [[0, LOOP_LOW], [15.75, LOOP_LOW]] if bar != 157 else [[0, LOOP_LOW], [11.75, LOOP_LOW], [12, LOOP_OPEN]]
            C('create_audio_clip', track=LOOP, path=str(LOOP_FILE), bar=bar, warp=True, beats=16, name='loop low-passed',
              envelopes=[{'param': '8 Frequency A', 'device': 'EQ Eight', 'unit': 'display', 'points': pts}])
    C('trim_clip', track=LOOP, clip={'at': B(157)}, end_beat=B(157) + 12)


def stage_fx():
    # the voice's space: light on the chops, the calls carry his own Echo and go further
    for t, rev, dly in ((V_CHOP, -20, -24), (V_PHR, -13, -16), (V_CALL, -11, -12)):
        C('set_send', track=t, send=0, db=rev)
        C('set_send', track=t, send=1, db=dly)
    _ensure(V_CALL, 'audio_effects/Echo', 'Echo')
    C('copy_device', src_track=14, src_device='Echo', track=V_CALL, device='Echo')
    C('set_clip', track=V_CALL, clip={'at': B(128) + .47}, gain_db=4)  # the bar it has alone
    C('set_device_on', track=V_CALL, device='Echo', on=True)
    C('set_param', track=V_CALL, device='Echo', param='Dry Wet', display=25)
    C('set_param', track=V_CALL, device='Echo', param='Feedback', display=38)


def stage_pressure():
    # drums keep going through the break: the perc comes back at its second phrase, the clap with the build
    fill(PERC, 65, 67, 109, 113)
    fill(CLAP13, 65, 67, 121, 125)

    C('delete_clips_in_range', track=KICK_HP, start_bar=113, end_bar=129)
    C('create_midi_clip', track=KICK_HP, beat=B(113), length=32, name='break kick, far away',
      notes=[[60, float(i), .5, int(55 + i * .8)] for i in range(32)],
      envelopes=[{'param': '1 Frequency A', 'device': 'EQ Eight', 'unit': 'display', 'points': [[0, 800], [32, 450]]}])
    notes, t = [], 0.0
    while t < 28 - 1e-3:
        step = .25 if t >= 24 else .5 if t >= 16 else 1.0
        notes.append([60, t, step * .5, int(80 + 47 * t / 28)])
        t += step
    C('create_midi_clip', track=KICK_HP, beat=B(121), length=28, notes=notes, name='build kick, gaining weight',
      envelopes=[{'param': '1 Frequency A', 'device': 'EQ Eight', 'unit': 'display', 'points': [[0, 450], [28, 110]]}])

    C('delete_clips_in_range', track=SYNTH_B, start_bar=113, end_bar=129)
    for bar, (a, m, z), (g0, g1) in ((113, (800, 1800, 1100), (0, 2)), (117, (1100, 2500, 1500), (2, 4)),
                                     (121, (1500, 2500, 3500), (4, 8)), (125, (3500, 7000, 12000), (8, 13))):
        C('create_audio_clip', track=SYNTH_B, path=str(LOOP_FILE), bar=bar, warp=True, beats=16, name='synth opening',
          envelopes=[{'param': 'Frequency', 'device': 'Auto Filter', 'unit': 'display', 'points': [[0, a], [10, m], [16, z]]},
                     {'param': 'Output', 'device': 'Utility', 'unit': 'db', 'points': [[0, g0], [16, g1]]}])
    C('trim_clip', track=SYNTH_B, clip={'at': B(125)}, end_beat=B(128))

    C('delete_clips_in_range', track=BASS_B, start_bar=113, end_bar=129)
    for bar, hz in ((113, (350, 250)), (117, (250, 220)), (121, (220, 180)), (125, (180, 180))):
        C('create_audio_clip', track=BASS_B, path=str(BASS_FILE), bar=bar, warp=True, beats=16, name='bass: no sub',
          envelopes=[{'param': '1 Frequency A', 'device': 'EQ Eight', 'unit': 'display', 'points': [[0, hz[0]], [16, hz[1]]]}])
    C('trim_clip', track=BASS_B, clip={'at': B(125)}, end_beat=B(128))

    # the riff returns under the build, then climbs G minor in 16ths into the breath
    scale = [55, 57, 58, 60, 62, 63, 65]
    up = [scale[i % 7] + 12 * (i // 7) for i in range(36)]
    run = up[up.index(91) - 15:up.index(91) + 1]
    build = [[p, t, d, int(v * (.7 + .3 * t / 16))] for p, t, d, v in low()]
    C('create_midi_clip', track=RIFF, beat=B(121), length=16, notes=build, name='riff returning')
    press = [[55, i * .5, .24, 95 + i] for i in range(16)] + [[67 + (i // 8) * 2, i * .5 + .25, .2, 80 + i] for i in range(16)]
    C('create_midi_clip', track=RIFF, beat=B(125), length=8, notes=press, name='riff pressing')
    C('create_midi_clip', track=RIFF, beat=B(127), length=4, name='riff climbing',
      notes=[[p, i * .25, .22, 80 + 3 * i] for i, p in enumerate(run)])

    # highs climb hard and do not fall away at the drop
    C('set_track', track=TOP_B, volume_db=-12)
    C('delete_clips_in_range', track=TOP_B, start_bar=121, end_bar=137)
    for bar, g in ((121, (-14, -4)), (125, (-4, 6)), (129, (0, 0)), (133, (0, -8))):
        C('create_audio_clip', track=TOP_B, path=TOP_FILE, bar=bar, warp=True, beats=16, name='top rising', envelopes=[
            {'param': 'Output', 'device': 'Utility', 'unit': 'db', 'points': [[0, g[0]], [16, g[1]]]}])
        if bar == 125:
            C('trim_clip', track=TOP_B, clip={'at': B(125)}, end_beat=B(128))


if __name__ == '__main__':
    {'drop2': stage_drop2, 'fx': stage_fx, 'pressure': stage_pressure}[sys.argv[1]]()
