import numpy as np
import soundfile as sf

from ableton_claude import setcut


def _track(sr, bpm, bars, kick_steps, hat_steps, freq, seed):
    rng = np.random.default_rng(seed)
    step = int(sr * 15 / bpm)
    x = np.zeros(bars * 16 * step, dtype=np.float32)
    t = np.arange(int(0.12 * sr)) / sr
    kick = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 30)
    hat = rng.normal(0, 1, int(0.03 * sr)) * np.exp(-np.arange(int(0.03 * sr)) / sr * 150)
    for b in range(bars):
        for k in range(16):
            a = (b * 16 + k) * step
            if k in kick_steps:
                x[a:a + len(kick)] += kick
            if k in hat_steps:
                x[a:a + len(hat)] += 0.3 * hat
    tt = np.arange(len(x)) / sr
    x += 0.15 * np.sin(2 * np.pi * freq * tt) + 0.1 * np.sin(2 * np.pi * freq * 1.5 * tt)
    return x


def test_alone_stretch_excludes_neighbours(tmp_path):
    sr, bpm = 44100, 125.0
    a = _track(sr, bpm, 32, {0, 4, 8, 12}, {2, 6, 10, 14}, 220.0, 1)
    b = _track(sr, bpm, 64, {0, 1, 4, 5, 8, 9, 12}, set(range(16)), 293.7, 2)
    step = int(sr * 15 / bpm)
    b[24 * 16 * step: 40 * 16 * step] *= 0.05      # a 16-bar break inside the track
    c = _track(sr, bpm, 32, {0, 4, 8, 12, 14}, {1, 3, 5, 7, 9, 11, 13, 15}, 174.6, 3)
    mix = np.concatenate([a, b, c])
    path = tmp_path / "set.wav"
    sf.write(path, np.stack([mix, mix], axis=1), sr)
    bar_s = 240 / bpm
    r = setcut.isolate(str(path), at_s=32 * bar_s, offset_s=600, bpm=bpm)
    alone = r["alone"]
    assert abs(alone["start_s"] - 32 * bar_s) <= 4 * bar_s + 0.5
    assert abs(alone["end_s"] - 96 * bar_s) <= 4 * bar_s + 0.5
    assert alone["set_start"] == setcut.clock(600 + alone["start_s"])


def test_times():
    assert setcut.seconds("17:10") == 1030
    assert setcut.seconds("1:02:03") == 3723
    assert setcut.url_start("https://www.youtube.com/watch?v=x&list=RD&t=1097s") == 1097
    assert setcut.url_start("https://youtu.be/x?t=18m17s") == 1097
    assert setcut.url_start("https://youtu.be/x") is None
    assert setcut.clock(1030) == "17:10"
