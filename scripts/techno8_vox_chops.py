"""TECHNO #8: cuts the beatbox vocal into syllable chops for the call and response.

Unwarped chops start at a real onset (4 ms before it), 3 ms in, 15 ms out. Also bakes a
reversed swell of the shout and a 3/16 ping-pong throw of the phrase's last syllable.
"""
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SRC = Path('/Users/lukasgalhardo/Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs/Vox/Vox/Old school vox/Beatbox Female #20.wav')
OUT = Path('/Users/lukasgalhardo/Desktop/Projects 26:27/TECHNO #8 Project/Samples/Claude vox')
BPM = 128.0
CHOPS = {
    'dum': (0.615, 0.859), 'dum2': (2.554, 2.798), 'tak': (1.103, 1.219), 'rise': (1.219, 1.950),
    'call': (6.084, 7.779), 'shout': (6.966, 7.465), 'resp': (13.839, 15.418), 'resp_short': (13.839, 14.408),
    'tail': (14.408, 15.418),
}


def cut(y, sr, a, b):
    s = y[max(0, int((a - .004) * sr)):int(b * sr)].copy()
    n_in, n_out = int(.003 * sr), int(.015 * sr)
    s[:n_in] *= np.linspace(0, 1, n_in)[:, None]
    s[-n_out:] *= np.linspace(1, 0, n_out)[:, None]
    return s


def dark(x, sr, hz):
    return sosfilt(butter(2, hz, 'lp', fs=sr, output='sos'), x, axis=0)


def tail(x, sr, seconds=1.4, seed=8):
    """Soft plate-like tail: exponentially decaying noise, band-limited, convolved."""
    n = int(seconds * sr)
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal((n, 2)) * np.exp(-np.arange(n) / (.28 * sr))[:, None]
    ir = sosfilt(butter(2, [400, 6000], 'bp', fs=sr, output='sos'), ir, axis=0)
    out = np.stack([np.convolve(x[:, i], ir[:, i]) for i in (0, 1)], 1)
    return out / (np.abs(out).max() + 1e-9) * np.abs(x).max()


def main():
    y, sr = sf.read(SRC)
    OUT.mkdir(exist_ok=True)
    res = {}
    for name, (a, b) in CHOPS.items():
        s = cut(y, sr, a, b)
        sf.write(OUT / f'{name}.wav', s, sr, subtype='PCM_24')
        res[name] = s
    # swell: the shout reversed through its own tail, 2 beats long, ending on its attack
    wet = tail(res['shout'], sr)
    rev = wet[::-1]
    n = int(2 * 60 / BPM * sr)
    rev = rev[-n:] * np.linspace(.15, 1, n)[:, None] ** 2
    sf.write(OUT / 'swell_2beats.wav', rev, sr, subtype='PCM_24')
    # throw: the last syllable in 3/16 ping-pong, darker each repeat
    step = int(3 * 15 / BPM * sr)
    src = res['tail'][:int(.45 * sr)]
    src = src * np.linspace(1, 0, len(src))[:, None] ** .5
    out = np.zeros((step * 7 + len(src), 2))
    for i in range(7):
        g = .62 ** i
        e = dark(src, sr, 6000 * .72 ** i)
        L, R = (1, .25) if i % 2 == 0 else (.25, 1)
        out[i * step:i * step + len(e), 0] += e.mean(1) * g * L
        out[i * step:i * step + len(e), 1] += e.mean(1) * g * R
    sf.write(OUT / 'throw.wav', out, sr, subtype='PCM_24')
    for f in sorted(OUT.glob('*.wav')):
        print(f.name, round(sf.info(f).duration, 3))


main()
