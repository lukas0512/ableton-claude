"""From The Streets v28: glitches from the track's own material (the City call, the Murder
riff, the hook B chop). prepare renders them at 125 BPM into Remix 122/glitch/.

  City stutter      'Ci-' in 16ths, then 32nds falling in pitch and level (2 beats)
  City tape stop    'City to' slowing to a stop (2 beats)
  Riff crush        the Murder riff's attack in 32nds, bit-crush rising (1 beat)
  Hook rev cut      the hook B chop reversed, then gated forward in 32nds (2 beats)
"""
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

SR, BPM = 44100, 125
BEAT = 60 / BPM
R = Path.home() / 'Desktop/TRACKS 2027/From the streets/Remix 122'
OUT = R / 'glitch'


def read(name):
    x, sr = sf.read(R / name, always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    return signal.resample_poly(x, SR, sr, axis=0) if sr != SR else x


def seg(x, a, b):
    return x[round(a * SR):round(b * SR)].copy()


def fade(x, a=.002, b=.01):
    x = x.copy()
    na, nb = min(len(x), round(a * SR)), min(len(x), round(b * SR))
    if na: x[:na] *= np.linspace(0, 1, na)[:, None]
    if nb: x[-nb:] *= np.linspace(1, 0, nb)[:, None]
    return x


def pitch(x, semis):
    """Repitch (tape style): shorter and higher, or longer and lower."""
    r = 2 ** (semis / 12)
    return signal.resample_poly(x, 1000, max(1, round(1000 * r)), axis=0)


def crush(x, hold):
    if hold <= 1:
        return x
    idx = (np.arange(len(x)) // hold) * hold
    y = x[idx]
    return np.round(y * 64) / 64


def clean(x, db=-10):
    x = signal.sosfilt(signal.butter(2, 160, 'highpass', fs=SR, output='sos'), x, axis=0)
    x = signal.sosfilt(signal.butter(2, 9000, 'lowpass', fs=SR, output='sos'), x, axis=0)
    return fade(x * 10 ** (db / 20) / max(float(np.abs(x).max()), 1e-9), .001, .02)


def canvas(beats):
    return np.zeros((round(beats * BEAT * SR), 2))


def put(y, x, t, g=1.0):
    a = round(t * BEAT * SR)
    n = min(len(x), len(y) - a)
    if n > 0:
        y[a:a + n] += x[:n] * g


def city_stutter(call):
    ci = fade(seg(call, .04, .20), .001, .015)
    y = canvas(2)
    for k in range(4):
        put(y, ci[:round(.25 * BEAT * SR)], k * .25, .9)
    for k in range(8):
        put(y, fade(pitch(ci, -1.5 * k))[:round(.125 * BEAT * SR)], 1 + k * .125, .85 - .07 * k)
    return clean(y)


def city_tapestop(call):
    w = seg(call, .04, .70)
    n = round(2 * BEAT * SR)
    rate = np.clip(1 - np.linspace(0, 1, n) ** .8, 0, 1)
    pos = np.cumsum(rate)
    pos = pos[pos < len(w) - 1]
    y = np.stack([np.interp(pos, np.arange(len(w)), w[:, c]) for c in range(2)], 1)
    out = canvas(2)
    put(out, fade(y, .002, .05), 0)
    return clean(out)


def riff_crush(riff):
    hit = fade(seg(riff, 2.06, 2.06 + .125 * BEAT), .001, .008)
    y = canvas(1)
    for k in range(8):
        put(y, crush(hit, 1 + 2 * k), k * .125, .95 - .05 * k)
    return clean(y, -12)


def hook_revcut(chop):
    y = canvas(2)
    r = fade(chop[::-1], .02, .005)
    put(y, r, 1 - len(r) / SR / BEAT)
    for k in range(8):
        if k % 2 == 0:
            put(y, fade(chop[:round(.125 * BEAT * SR)], .001, .006), 1 + k * .125, .9)
    return clean(y)


def prepare():
    OUT.mkdir(exist_ok=True)
    call = read('City call - src 20-20.wav')
    riff = read('Murder keys loop - src 3-4.wav')
    chop = read('Hook B chop - short (onset-aligned).wav')
    for name, y in [('City stutter', city_stutter(call)), ('City tape stop', city_tapestop(call)),
                    ('Riff crush', riff_crush(riff)), ('Hook rev cut', hook_revcut(chop))]:
        sf.write(OUT / f'Glitch - {name}.wav', y, SR, subtype='PCM_24')
        print(name, round(len(y) / SR / BEAT, 2), 'beats')


if __name__ == '__main__':
    {'prepare': prepare}[sys.argv[1]]()
