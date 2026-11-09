"""From The Streets v30: vocals re-cut at the words, placed less predictably, echoes thrown.

His notes: "os vocais cortados na forma certa... entrando e saindo mais na boa... pra não
parecer que foi cortado", "o vocal corta no meio" (build 2 -> drop), "às vezes os vocais
tão em lugares bem óbvios".

  prepare   re-cuts the City phrases from the htdemucs vocal stem: start at the breath
            before the first word, end where the last word has decayed (-38 dB), 8 ms fade
            in, 90 ms fade out. Writes "<phrase> - clean.wav" (+ a radio variant) and, for
            every throw, "<phrase> - last word echo.wav": the last word with a 3/16 ping-pong
            echo at 125 BPM, darker each repeat (played unwarped, so the echo stays in time).
  apply     replaces the cut clips by the clean ones (same syllable warp, the clip moved
            earlier by the pre-roll so every word keeps its beat), moves the calls off the
            obvious pick-ups, and lays the echoes on a new track VOX - throws.
"""
import json
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server

R = Path.home() / 'Desktop/TRACKS 2027/From the streets/Remix 122'
STEM = (Path.home() / 'Desktop/TRACKS 2027/From the streets/stems/htdemucs'
        / '02. B-Legit - City 2 City (Original Mix)/vocals.wav')
OUT = R / 'vocals v30'
LOG_PATH = R / 'live-changes-v30_vocals.json'
SRC_BPM, BPM = 92.0, 125.0
LOG = []
CUT_AT = {'City trade 1': 2.93}    # seconds of the file the clip plays (pre-drop 2)
PHRASES = {   # phrase file -> clean name
    'City call - src 20-20.wav': 'City call',
    'City hook B - src 40-47.wav': 'City hook B',
    'City trade 1 - src 40-41.wav': 'City trade 1',
    'City hook B tail - src 44-47.wav': 'City hook B tail',
}


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    LOG_PATH.write_text(json.dumps(LOG, indent=2, default=str))
    print(cmd, args.get('track', ''), str(r)[:110], flush=True)
    return r


def mono(x):
    return x.mean(1) if x.ndim > 1 else x


def env_db(x, sr, win=.02):
    n = max(1, round(win * sr))
    e = np.sqrt(signal.lfilter(np.ones(n) / n, 1, mono(x) ** 2) + 1e-12)
    return 20 * np.log10(e / e.max())


def locate(phrase, stem, sr):
    """Sample offset of the phrase inside the stem (envelope cross-correlation, then refine)."""
    hop = 256
    def e(y):
        y = mono(y)
        return np.sqrt(np.add.reduceat(y ** 2, np.arange(0, len(y), hop)))
    a, b = e(phrase[:sr * 4]), e(stem)
    c = signal.correlate(b - b.mean(), a - a.mean(), mode='valid')
    coarse = int(np.argmax(c)) * hop
    lo = max(0, coarse - hop * 2)
    seg = mono(stem[lo:lo + sr * 2 + hop * 4])
    fine = signal.correlate(seg, mono(phrase[:sr * 2]), mode='valid')
    return lo + int(np.argmax(fine))


def fade(x, a, b, sr):
    x = x.copy()
    na, nb = min(len(x), round(a * sr)), min(len(x), round(b * sr))
    if na: x[:na] *= np.linspace(0, 1, na)[:, None]
    if nb: x[-nb:] *= np.linspace(1, 0, nb)[:, None]
    return x


def radio(x, sr):
    y = signal.sosfilt(signal.butter(2, [450, 3200], 'bandpass', fs=sr, output='sos'), x, axis=0)
    return np.tanh(2.0 * y) / 2.0


def _held(mask, k, n):
    return mask[k:k + n].all()


def clean_cut(phrase, stem, sr, max_pre=.35, max_tail=.45, off=None):
    """Move each edge to the nearest gap between words: forward from the phrase end to where
    the last word has fallen 26 dB under the phrase peak, back from the start to before the
    first word's attack (30 dB down). Rap leaves no silence, so the gap is the boundary."""
    off = locate(phrase, stem, sr) if off is None else off
    ev = env_db(stem, sr, .015)
    ref = ev[off:off + len(phrase)].max()
    ev = ev - ref
    end = off + len(phrase)
    low_end, low_pre = ev < -26, ev < -30
    tail = 0
    if not _held(low_end, end, round(.015 * sr)):
        win = range(end, min(len(stem) - 1, end + round(max_tail * sr)))
        hit = next((k for k in win if _held(low_end, k, round(.015 * sr))), None)
        tail = (hit if hit is not None else end + int(np.argmin(ev[end:end + round(max_tail * sr)]))) - end
    pre, fin = 0, .008
    head = env_db(phrase, sr, .015)[:round(.03 * sr)].max()
    if head > -25:                                        # the phrase opens mid-word
        win = range(off, max(0, off - round(max_pre * sr)), -1)
        hit = next((k for k in win if _held(ev < -26, k, round(.01 * sr))), None)
        pre, fin = (off - hit, .008) if hit is not None else (0, .03)
    y = fade(stem[off - pre:end + tail], fin, .04, sr)
    return y, pre / sr, tail / sr


def last_word(y, sr):
    """Onset (s) of the last word: back from the last loud frame to the previous gap."""
    ev = env_db(y, sr, .015)
    loud = np.where(ev > -22)[0]
    k = loud[-1]
    while k > 0 and ev[k] > -26:
        k -= 1
    return k / sr


def echo(word, sr, repeats=5):
    d = round(.75 * 60 / BPM * sr)
    out = np.zeros((len(word) + d * repeats + sr, 2))
    out[:len(word)] += word
    rep = word.copy()
    for k in range(1, repeats + 1):
        rep = signal.sosfilt(signal.butter(2, 3800 - 450 * k, 'lowpass', fs=sr, output='sos'), rep, axis=0)
        rep = signal.sosfilt(signal.butter(2, 220 + 50 * k, 'highpass', fs=sr, output='sos'), rep, axis=0)
        side = np.array([1, .3]) if k % 2 else np.array([.3, 1])
        out[k * d:k * d + len(rep)] += rep * side * .5 ** k
    return fade(out, .004, .3, sr)


def prepare():
    OUT.mkdir(exist_ok=True)
    stem, sr = sf.read(STEM, always_2d=True)
    info = {}
    for f, name in PHRASES.items():
        ph, psr = sf.read(R / f, always_2d=True)
        assert psr == sr
        if name in CUT_AT:                   # the set plays only the start of this file
            ph = ph[:round(CUT_AT[name] * sr)]
        o = locate(ph, stem, sr) if name != 'City trade 1' else hook_off
        if name == 'City hook B':
            hook_off = o
        a_, b_ = mono(ph[:sr * 2]), mono(stem[o:o + sr * 2])
        print(name, 'match r =', round(float(np.corrcoef(a_, b_)[0, 1]), 3))
        y, pre, tail = clean_cut(ph, stem, sr, off=o)
        sf.write(OUT / f'{name} - clean.wav', y, sr, subtype='PCM_24')
        sf.write(OUT / f'{name} - clean radio.wav', radio(y, sr), sr, subtype='PCM_24')
        w = last_word(y, sr)
        word = fade(y[round(w * sr):], .004, .05, sr)
        sf.write(OUT / f'{name} - last word echo.wav', echo(word, sr), sr, subtype='PCM_24')
        info[f] = dict(name=name, pre_s=pre, tail_s=tail, last_word_s=w, length_s=len(y) / sr)
        print(name, {k: round(v, 3) for k, v in info[f].items() if k != 'name'})
    (OUT / 'clean.json').write_text(json.dumps(info, indent=2))


B = lambda bar: (bar - 1) * 4.0
# (track clip start bar to replace or move, new start bar or None to delete, throw?)
PLAN = [
    (31.875, 31.875, False), (35.875, None, False), (39.875, 42.375, True),
    (59.875, 59.875, False), (63.875, 63.875, True),
    (64.875, 72.875, True),                      # hook B enters in the 2nd 8 of drop 1
    (79.875, None, False), (87.875, 90.375, False), (95.875, 95.875, True),
    (118.875, 118.875, True),                    # the pre-drop 2 trade, whole, into the echo
    (120.875, 120.875, True),
    (135.875, 135.875, False), (143.875, 146.375, True),
    (160.875, 160.875, False),
]


def apply():
    assert not LOG_PATH.exists(), 'inspect the partial receipt before a retry'
    info = json.loads((OUT / 'clean.json').read_text())
    track = 'VOX CITY'
    clips = {round(c['start'], 3): c for c in
             client.call('get_track', {'track': track, 'markers': True, 'max_clips': 200})['clips']}
    # the City tape-stop glitch at 72.5 would sit under the hook's new entry
    C('delete_clips_in_range', track='FX - glitches', start_bar=72.5, end_bar=73)

    names = [t['name'] for t in client.call('get_song')['tracks']]
    C('create_track', kind='audio', name='VOX - throws', index=names.index('VOX BUS'))
    C('set_track_input', track='VOX - throws', source='No Input')
    C('set_track_output', track='VOX - throws', dest='VOX BUS')
    C('set_track', track='VOX - throws', volume_db=-9.0)
    C('set_send', track='VOX - throws', send=4, db=-12.0)       # the voices' plate
    C('set_send', track='VOX - throws', send=2, db=-18.0)       # the shared atmos tail

    plan = []
    for old_bar, new_bar, throw in PLAN:
        c = clips[round(B(old_bar), 3)]
        plan.append((c, new_bar, throw))
    for c, _, _ in plan:                     # clear first: moved clips may land on old spots
        C('delete_clip', track=track, clip={'at': c['start']})
    for c, new_bar, throw in plan:
        if new_bar is None:
            continue
        src = Path(c['file']).name.replace(' - radio', '')
        meta = info.get(src)
        radio_v = ' - radio' in Path(c['file']).name or '[radio]' in c['name']
        if meta is None:                     # not a re-cut phrase: put the original back
            C('create_audio_clip', track=track, path=c['file'], beat=B(new_bar), name=c['name'],
              warp=True, gain_db=c.get('gain_db', 0))
            continue
        path = OUT / f"{meta['name']} - clean{' radio' if radio_v else ''}.wav"
        pre_b = meta['pre_s'] * SRC_BPM / 60
        old = client  # noqa: keep the old syllable map, shifted by the pre-roll
        ms = c['_markers']
        body = [[b + pre_b, s + meta['pre_s']] for b, s in ms if b > 1e-6]
        last_b, last_s = ms[-1]
        end_s = meta['length_s']
        body.append([last_b + pre_b + (end_s - last_s - meta['pre_s']) * SRC_BPM / 60, end_s])
        start = B(new_bar) - pre_b
        C('create_audio_clip', track=track, path=str(path), beat=start,
          name=c['name'].replace('[throw]', '').replace('[dry]', '').strip() + ' (clean)',
          warp=True, beats=body[-1][0], gain_db=c.get('gain_db', 0),
          warp_mode=c.get('warp_mode', 4))
        C('set_warp_markers', track=track, clip={'at': start}, markers=[[0.0, 0.0]] + body)
        if throw:
            wb = np.interp(meta['last_word_s'], [0.0] + [s for _, s in body],
                           [0.0] + [b for b, _ in body])
            C('create_audio_clip', track='VOX - throws',
              path=str(OUT / f"{meta['name']} - last word echo.wav"),
              beat=start + float(wb), name=f"echo {meta['name']} {new_bar:g}", warp=False)


def attach_markers():
    """Read every VOX CITY clip's warp markers once (the bridge returns them separately)."""
    out = {}
    for c in client.call('get_track', {'track': 'VOX CITY', 'markers': True, 'max_clips': 200})['clips']:
        if c['type'] == 'audio' and c.get('warping'):
            wm = client.call('warp_markers', {'track': 'VOX CITY', 'clip': {'at': c['start']}})
            out[round(c['start'], 3)] = [[m['beat'], m['sample_s']] for m in wm['markers']]
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    else:
        # apply needs the markers; fetch them before anything is deleted
        _m = attach_markers()
        _orig = client.call

        def call(cmd, args=None, **kw):
            r = _orig(cmd, args, **kw)
            if cmd == 'get_track' and (args or {}).get('track') == 'VOX CITY' and 'clips' in r:
                for c in r['clips']:
                    c['_markers'] = _m.get(round(c['start'], 3), [[0.0, 0.0]])
            return r
        client.call = call
        apply()
