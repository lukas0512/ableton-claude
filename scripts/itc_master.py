"""In the City: the club master, tried on drop 2 (bars 121-129) before the whole song.

He (2026-11-05): "tem que fazer a mix e master depois no detalhe e preparar ela pra eu tocar". v7: integrated
-11.6 LUFS, drops -10.4/-10.6, breaks 5-7 LU under them, true peak -1.0. The references (dub_house_streets):
integrated -8.5, drops (full_lufs) -7.75, true peak ~0, crest 10.1, break depth 4.3 LU, low width -43 dB.
Before the limiter, drop 2 sat at -21.2 LUFS with peaks at -7.9 (PLR 13.3), the 20-120 Hz band carrying the peaks
(the kick); the low end is already mono (-43.5 dB side). The limiter got +13 dB and took up to 6 dB off the kicks.

Each config is applied, the 8 bars recorded, and measured: LUFS, true peak, the kick's low-band crest (punch),
and the pump (how far the 300 Hz-3 kHz band dips 10-80 ms after each beat against the same beat's tail), next to
the unlimited pass and v7.
usage: itc_master.py <config> [<config> ...] | itc_master.py apply <config>
"""
from pathlib import Path
import sys
import time

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
BPM = 127.0
A, Z = 121, 129
PROJ = Path('/Users/lukasgalhardo/Desktop/Projects 26:27/In the City  Project')
V7 = PROJ / 'Versoes/In the City v7.wav'

# Saturator first used as a clipper on the kick's peaks: Drive raises, Output takes it back, so the limiter sees the
# same level with the tallest few dB of the kick rounded off.
SAT_TYPES = ['Analog Clip', 'Soft Sine', 'Bass Shaper', 'Medium Curve', 'Hard Curve', 'Sinoid Fold', 'Digital Clip',
             'Waveshaper']
CONFIGS = {
    'v7': dict(sat=None, gain=13.0, ceiling=-1.0),
    'push': dict(sat=None, gain=16.0, ceiling=-0.5),
    'clip3': dict(sat=('Analog Clip', 7.0), gain=16.0, ceiling=-0.5),
    'clip3soft': dict(sat=('Soft Sine', 7.0), gain=16.0, ceiling=-0.5),
    'clip3hot': dict(sat=('Analog Clip', 7.0), gain=17.0, ceiling=-0.5),
    'clip5': dict(sat=('Analog Clip', 9.0), gain=17.0, ceiling=-0.5),
    'clip7': dict(sat=('Analog Clip', 11.0), gain=17.0, ceiling=-0.5),
}
# Chosen (2026-11-06, drop 2): clip7 = -7.77 LUFS (refs' drops -7.75), true peak -0.48, the kick's low-band crest
# 10.0 dB (v7 9.6, the limiter alone at this level 8.7) and the pump 2.3 dB (v7 2.4, limiter alone 0.7): the
# Analog Clip rounds the kick's peaks so the limiter hardly works; band balance within 0.5 dB of the unlimited pass.
CONFIGS['club'] = CONFIGS['clip7']
# v8 (club) measured the sub at 46 % of the energy (refs 35, p75 41) and crest 9.2 (p25 9.9): a wide bell under the
# kick's 66 Hz on the master's free band 6, so the clipper gets less sub to round off.
CONFIGS['sub2'] = dict(CONFIGS['club'], sub=(45.0, -2.0, 0.8))
CONFIGS['sub3'] = dict(CONFIGS['club'], sub=(45.0, -3.0, 0.8))
CONFIGS['sub2g'] = dict(CONFIGS['sub2'], gain=18.0)
CONFIGS['sub3g'] = dict(CONFIGS['sub3'], gain=18.0)
# Drop 2: club -7.78 LUFS / sub 44 %; sub2 -8.47 / 39 %, punch 10.6, pump 2.4; making the level back up (+1 dB)
# gave only +0.3 LU and the pump fell to 1.8 (the limiter starts working). v8b = the middle, for his A/B with v8.
CONFIGS['v8b'] = dict(CONFIGS['sub2'], gain=17.5)


def p(dev, name, **kw):
    C('set_param', {'track': 'master', 'device': dev, 'param': name, **kw})


def apply(cfg):
    sat = cfg['sat']
    if sat:
        kind, drive = sat
        p('Saturator', 'Type', value=float(SAT_TYPES.index(kind)))
        p('Saturator', 'Drive', display=f'{drive:.1f} dB')
        p('Saturator', 'Output', display=f'{-drive:.1f} dB')
        p('Saturator', 'Dry/Wet', display='100 %')
        p('Saturator', 'Post Clip Mode', value=0.0)
        p('Saturator', 'Color On', value=0.0)
    C('set_device_on', {'track': 'master', 'device': 'Saturator', 'on': bool(sat)})
    freq, gain, q = cfg.get('sub', (45.0, 0.0, 0.71))
    p('EQ Eight', '6 Filter Type A', value=3.0)                       # Bell
    p('EQ Eight', '6 Frequency A', display=f'{freq:.1f} Hz')
    p('EQ Eight', '6 Gain A', value=gain)
    p('EQ Eight', '6 Q A', display=f'{q:.2f}')
    C('set_device_on', {'track': 'master', 'device': 'Limiter', 'on': True})
    p('Limiter', 'Input Gain', display=f'{cfg["gain"]:.0f} dB')
    p('Limiter', 'Ceiling', display=f'{cfg["ceiling"]:.1f} dB')
    p('Limiter', 'Mode', value=2.0)                 # True Peak (enums take the index)


def render(name):
    C('record_master', {'start_bar': A, 'end_bar': Z, 'name': name})
    time.sleep(2)
    for _ in range(90):
        st = C('record_status')
        if st['state'] not in ('recording', 'finalizing'):
            break
        time.sleep(1)
    if st['state'] != 'done':
        raise SystemExit(st)
    C('delete_track', {'track': st['name']})
    return st['file']


def band(x, sr, lo, hi):
    sos = butter(4, [lo, hi], 'band', fs=sr, output='sos')
    return sosfilt(sos, x.mean(1) if x.ndim > 1 else x)


def env(y, sr, ms=10):
    n = int(sr * ms / 1000)
    return np.sqrt(np.convolve(y ** 2, np.ones(n) / n, 'same'))


def measure(x, sr):
    m = pyln.Meter(sr)
    L = m.integrated_loudness(x)
    tp = 20 * np.log10(np.abs(resample_poly(x, 4, 1, axis=0)).max())
    lo = band(x, sr, 30, 120)
    punch = 20 * np.log10(np.abs(lo).max() / np.sqrt((lo ** 2).mean()))
    mid = env(band(x, sr, 300, 3000), sr)
    beat = 60 / BPM
    dips = []
    for k in range(int(len(x) / sr / beat) - 1):
        b = int(k * beat * sr)
        early = mid[b + int(0.01 * sr): b + int(0.08 * sr)].mean()
        late = mid[b + int(0.2 * sr): b + int(0.4 * sr)].mean()
        dips.append(20 * np.log10(early / late))
    mono = x.mean(1)
    spec = np.abs(np.fft.rfft(mono)) ** 2
    fr = np.fft.rfftfreq(len(mono), 1 / sr)
    sub = spec[(fr >= 20) & (fr < 60)].sum() / spec[fr >= 20].sum()
    return dict(lufs=round(L, 2), tp=round(tp, 2), plr=round(tp - L, 2), punch=round(punch, 2),
                pump=round(float(np.median(dips)), 2), sub_pct=round(100 * sub, 1))


def v7_slice():
    x, sr = sf.read(V7)
    bar = 4 * 60 / BPM
    return x[int((A - 1) * bar * sr): int((Z - 1) * bar * sr)], sr


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[:1] == ['apply']:
        apply(CONFIGS[args[1]])
        print('applied', args[1])
        raise SystemExit
    print('v7 file', measure(*v7_slice()))
    for name in args:
        apply(CONFIGS[name])
        f = render(f'ITC master {name}')
        print(name, measure(*sf.read(f)), Path(f).name)
