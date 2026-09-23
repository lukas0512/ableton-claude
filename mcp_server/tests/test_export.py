import numpy as np

from ableton_claude import analysis, export

SR = 44100
BPM = 120.0            # 1 bar = 2 s


def _bar_clicks(bars):
    """A click on every downbeat, with the bar number encoded in its amplitude."""
    x = np.zeros((int(bars * 2 * SR), 2), dtype=np.float32)
    for b in range(bars):
        i = int(b * 2 * SR)
        x[i:i + 64] = 0.01 * (b + 1)
    return x


def test_edit_keeps_the_bar_grid_across_splices():
    x = _bar_clicks(20)
    y = export.edit(x, SR, BPM, [(1, 5), (11, 13), (17, 19)], fade_in_ms=0)
    assert abs(len(y) - (4 + 2 + 2) * 2 * SR) <= 1
    # downbeats of the edit, in order: bars 1-4, 11-12, 17-18
    want = [1, 2, 3, 4, 11, 12, 17, 18]
    for k, bar in enumerate(want):
        i = int(k * 2 * SR)
        assert abs(float(y[i + 32, 0]) - 0.01 * bar) < 2e-3, (k, bar, float(y[i + 32, 0]))


def test_fade_out_reaches_silence():
    x = np.ones((SR * 8, 2), dtype=np.float32) * 0.5
    y = export.edit(x, SR, BPM, [(1, 5)], fade_out_bars=1)
    assert abs(float(y[-1, 0])) < 1e-3 and abs(float(y[0 + SR, 0]) - 0.5) < 1e-6


def test_mp3_true_peak_is_held_below_the_target(tmp_path):
    t = np.arange(SR * 3) / SR
    x = np.stack([np.sin(2 * np.pi * 997 * t)] * 2, axis=1).astype(np.float32) * 0.999
    r = export.encode_mp3(x, SR, str(tmp_path / "a.mp3"), tags={"title": "t"}, tp_target=-1.0)
    assert r["true_peak_dbtp"] <= -1.0 + 1e-6, r
    assert r["gain_applied_db"] < 0
