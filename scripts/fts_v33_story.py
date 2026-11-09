"""From The Streets v33: the vocal story, with the theme present and drop 2 as the climax.

His notes: "o drop 2 ainda tá caindo um pouquinho fraquinho... polida na parte de história e
versos... onde repetir e onde colocar coisas novas, principalmente os vocais, o tema tem que
ser bem presente". Measured v32: every kick phrase -8.2..-8.9 LUFS, drop 2 = drop 1; the
references' drop sits ~1.3 LU over the integrated. Drop 2 lands harder by bringing what has
not been heard yet:

  16.875    the City call on the radio: the theme first, far away (intro B)
  121       the call on the downbeat (his one-bar cut), like drop 1 at 65
  128.875   hook B (known by now: the repeat is the singalong)
  136.875   City hook C: new lines, never heard before (re-cut clean from the stem)
  145-152   City and Murder answer each other: City call / Murder verse line / City call /
            Murder verse line (the two records meet)
  121-152   a layer only drop 2 has: the Murder guitar an octave up, low, on the music bus
"""
import json
from pathlib import Path
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ableton_claude import client, server
import fts_v30_vocals as v

R = v.R
LOG_PATH = R / 'live-changes-v33_story.json'
LOG = []
B = lambda bar: (bar - 1) * 4.0
PH = json.load(open(R / 'phrases.json'))


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    LOG_PATH.write_text(json.dumps(LOG, indent=2, default=str))
    print(cmd, args.get('track', ''), str(r)[:110], flush=True)
    return r


def clips(track):
    return client.call('get_track', {'track': track, 'markers': True, 'max_clips': 400})['clips']


def markers_for(name, path):
    L = sf.info(str(path)).duration
    src_bpm = v.SRC_BPM if PH[name]['source'] == 'CITY' else 86.0
    ms = [[b, s] for b, s in PH[name]['markers'] if b > 1e-6 and s < L - 0.003]
    lb, ls = ms[-1]
    ms.append([lb + (L - ls) * src_bpm / 60, L])
    return [[0.0, 0.0]] + ms


def place(track, path, beat, markers, name, gain=0.0, envelopes=None):
    args = dict(track=track, path=str(path), beat=beat, name=name, warp=True,
                beats=markers[-1][0], gain_db=gain, warp_mode='complex_pro')
    if envelopes:
        args['envelopes'] = envelopes
    C('create_audio_clip', **args)
    C('set_warp_markers', track=track, clip={'at': beat}, markers=markers)
    C('set_clip', track=track, clip={'at': beat}, looping=False,
      loop_end=markers[-1][0], end_marker=markers[-1][0])


def prepare_hook_c():
    stem, sr = sf.read(v.STEM, always_2d=True)
    ph, _ = sf.read(R / 'City hook C - src 56-63.wav', always_2d=True)
    off = v.locate(ph, stem, sr)
    r = np.corrcoef(v.mono(ph[:sr * 2]), v.mono(stem[off:off + sr * 2]))[0, 1]
    assert r > .95, r
    y, pre, tail = v.clean_cut(ph, stem, sr, off=off)
    n = round(.15 * sr)
    y[-n:] *= np.linspace(1, 0, n)[:, None]
    out = v.OUT / 'City hook C - clean.wav'
    sf.write(out, y, sr, subtype='PCM_24')
    print('hook C', dict(match=round(float(r), 3), pre=pre, tail=tail, length=len(y) / sr))
    return out


def main():
    assert not LOG_PATH.exists(), 'inspect the partial receipt before a retry'
    hook_c = prepare_hook_c()
    T, M, TH = 'VOX CITY', 'VOX MURDER', 'VOX - throws'
    his = next(c for c in clips(T) if abs(c['start'] - B(40)) < .01)      # his one-bar call

    # the theme on the radio at the top of intro B
    radio = v.OUT / 'City call - clean radio.wav'
    place(T, radio, B(16.875), markers_for('City call', radio), 'City call [radio] - the theme, far', -6.0)

    # drop 2: the call on the downbeat
    C('duplicate_clip', track=T, clip={'at': his['start']}, beat=B(121))
    C('set_clip', track=T, clip={'at': B(121)}, name='City call on drop 2 (his bar-40 cut)')

    # hook C (new lines) in the third 8; the old call at 143.875 and its echo make room
    for c in clips(T):
        if B(136.8) <= c['start'] < B(153) and 'hook B' not in c['name']:
            C('delete_clip', track=T, clip={'at': c['start']})
    for c in clips(TH):
        if B(136.5) <= c['start'] < B(153):
            C('delete_clip', track=TH, clip={'at': c['start']})
    place(T, hook_c, B(136.875), markers_for('City hook C', hook_c), 'City hook C (clean) - new lines, drop 2')

    # 145-152: City and Murder answer each other
    open_filter = [{'param': 'Frequency', 'device': 'Auto Filter', 'points': [[0, 0.984], [8, 0.984]],
                    'unit': 'raw'}]
    C('duplicate_clip', track=T, clip={'at': his['start']}, beat=B(145))
    C('duplicate_clip', track=T, clip={'at': his['start']}, beat=B(149))
    for bar, f, name in [(146.875, 'Murder trade 1 - src 9-10.wav', 'Murder trade 1'),
                         (150.875, 'Murder trade 2 - src 11-12.wav', 'Murder trade 2')]:
        place(M, R / f, B(bar), markers_for(name, R / f), f'{name} - answers the City', 0.0,
              envelopes=open_filter)

    # a layer only drop 2 has: the Murder guitar an octave up, low
    src = next(c for c in clips('LOOP MURDER - guitar riff') if abs(c['start'] - B(121)) < .01)
    names = [t['name'] for t in client.call('get_song')['tracks']]
    L = 'LOOP MURDER +12 (drop 2 only)'
    C('create_track', kind='audio', name=L, index=names.index('LOOP MURDER - guitar riff') + 1)
    C('set_track_input', track=L, source='No Input')
    C('set_track_output', track=L, dest='MUSIC BUS')
    C('set_track', track=L, volume_db=-24.0, pan=0.3)
    C('set_send', track=L, send=4, db=-20.0)
    C('create_audio_clip', track=L, path=src['file'], beat=B(121), name='Murder guitar +12',
      warp=True, beats=src['end'] - src['start'], pitch=12, warp_mode='complex_pro')
    C('load_device', track=L, query='EQ Eight')
    for prm, kw in [('1 Filter On A', {'value': 1}), ('1 Filter Type A', {'item': 'High Pass 48dB'}),
                    ('1 Frequency A', {'display': '500'})]:
        C('set_param', track=L, device='EQ Eight', param=prm, **kw)


if __name__ == '__main__':
    main()
