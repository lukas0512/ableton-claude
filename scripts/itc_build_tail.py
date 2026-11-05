"""In the City: a pressure tail for each build, in the spirit of Endless Smile (not installed here).

His note (2026-11-05): "os drops, os builds ... Endless Smile, ou um efeito parecido, aquela cauda da pressão".
Made from the build's own render, not a stock riser: a wide 2.5 s stereo reverb of the build, under a high-pass
rising 300 Hz -> 5 kHz and a level rising 24 dB, that cuts dead 10 ms before the drop so the first kick lands
alone (taste.md). Written to the project's Samples folder and placed on one FX channel.
"""
import glob
from pathlib import Path
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
PROJECT = Path.home() / 'Desktop/Projects 26:27/In the City  Project'
OUT = PROJECT / 'Samples/Processed'
TRACK = 'FX - build tail'
BUILDS = (('ITC src build 1', 'build tail 1.wav', 57), ('ITC src build 2', 'build tail 2.wav', 113))
BEATS = 32
SEED = 64


def tail(src):
    x, sr = sf.read(src, always_2d=True)
    tempo = C('get_song', {})['tempo']
    n = int(round(BEATS * 60 / tempo * sr))
    x = x[:n]
    if len(x) < n:
        x = np.vstack([x, np.zeros((n - len(x), x.shape[1]))])
    rng = np.random.default_rng(SEED)
    ir_len = int(2.5 * sr)
    decay = np.exp(-np.arange(ir_len) / (0.55 * sr))
    wet = np.zeros((n, 2))
    for ch in range(2):                    # different noise each side: wide, not a stereo copy
        ir = rng.standard_normal(ir_len) * decay
        size = n + ir_len
        wet[:, ch] = np.fft.irfft(np.fft.rfft(x[:, ch], size) * np.fft.rfft(ir, size), size)[:n]
    # a rising high-pass, frame by frame
    win = 4096
    hop = win // 2
    w = np.hanning(win)
    out = np.zeros((n + win, 2))
    fr = np.fft.rfftfreq(win, 1 / sr)
    for start in range(0, n, hop):
        pos = min(1.0, start / n)
        cut = 300 * (5000 / 300) ** pos
        mask = 1 / np.sqrt(1 + (cut / np.maximum(fr, 1)) ** 8)
        for ch in range(2):
            seg = wet[start:start + win, ch]
            seg = np.pad(seg, (0, win - len(seg)))
            out[start:start + win, ch] += np.fft.irfft(np.fft.rfft(seg * w) * mask, win) * w
    out = out[:n] / 0.75
    pos = np.arange(n) / n
    out *= (10 ** ((-24 + 24 * pos ** 1.5) / 20))[:, None]
    stop = n - int(0.010 * sr)              # dead before the downbeat, 3 ms fade
    fade = int(0.003 * sr)
    out[stop:] = 0
    out[stop - fade:stop] *= np.linspace(1, 0, fade)[:, None]
    out *= 10 ** (-6 / 20) / np.abs(out).max()
    return out, sr


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = [t['name'] for t in C('get_song', {})['tracks']]
    if TRACK not in names:
        C('create_track', {'kind': 'audio', 'name': TRACK})
    C('set_track_input', {'track': TRACK, 'source': 'No Input'})
    C('set_track_output', {'track': TRACK, 'dest': 'FX BUS'})
    C('set_track', {'track': TRACK, 'color_index': 26, 'volume_db': -14.0})
    have = {c['start'] for c in C('get_track', {'track': TRACK, 'clips': True}).get('clips', [])}
    for pattern, name, bar in BUILDS:
        src = sorted(g for g in glob.glob(str(PROJECT / 'Samples/Recorded' / (pattern + '*'))) if g.endswith('.wav'))[-1]
        y, sr = tail(src)
        path = OUT / name
        sf.write(path, y, sr, subtype='PCM_24')
        print(name, 'peak', round(20 * np.log10(np.abs(y).max()), 1), 'seconds', round(len(y) / sr, 2))
        beat = (bar - 1) * 4.0
        if beat not in have:
            C('create_audio_clip', {'track': TRACK, 'path': str(path), 'beat': beat, 'name': name[:-4],
                                    'warp': True, 'warp_mode': 'complex_pro', 'beats': BEATS})


if __name__ == '__main__':
    main()
