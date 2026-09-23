import numpy as np
import soundfile as sf

from ableton_claude import analysis

SR = 44100


def _write(tmp_path, name, x):
    p = tmp_path / name
    sf.write(p, x.astype(np.float32), SR)
    return str(p)


def _sine(freq, secs, amp, sr=SR):
    t = np.arange(int(secs * sr)) / sr
    return amp * np.sin(2 * np.pi * freq * t)


def test_loudness_and_peak_of_known_sine(tmp_path):
    # BS.1770 calibration: a full-scale 1 kHz sine in one channel reads -3.01 LUFS.
    # At -20 dBFS peak that is -23; identical stereo channels sum power (+3 dB) -> -20
    s = _sine(1000, 10, 10 ** (-20 / 20))
    p = _write(tmp_path, "sine.wav", np.stack([s, s], axis=1))
    r = analysis.analyze(p)
    assert abs(r["loudness"]["integrated_lufs"] - (-20.0)) < 0.2
    assert abs(r["loudness"]["sample_peak_dbfs"] - (-20.0)) < 0.1
    assert abs(r["loudness"]["crest_db"] - 3.0) < 0.3
    assert r["bands"]["mid"]["share_pct"] > 95


def test_true_peak_catches_intersample_overs(tmp_path):
    # fs/4 sine phased so samples land at +-0.707 of a full-scale waveform
    n = np.arange(SR * 2)
    s = np.sin(2 * np.pi * n / 4 + np.pi / 4)
    p = _write(tmp_path, "isp.wav", np.stack([s, s], axis=1) * 0.99)
    r = analysis.analyze(p)
    assert r["loudness"]["true_peak_dbtp"] > r["loudness"]["sample_peak_dbfs"] + 2.0


def test_sub_energy_lands_in_sub_band(tmp_path):
    s = _sine(45, 8, 0.5)
    r = analysis.analyze(_write(tmp_path, "sub.wav", np.stack([s, s], axis=1)))
    assert r["bands"]["sub"]["share_pct"] > 90


def test_out_of_phase_low_end_is_flagged(tmp_path):
    s = _sine(60, 8, 0.5)
    r = analysis.analyze(_write(tmp_path, "phase.wav", np.stack([s, -s], axis=1)))
    assert r["stereo"]["low_correlation_below_120hz"] < -0.9
    assert any("not mono" in f for f in r["flags"])


def test_sections_measure_each_part(tmp_path):
    tempo = 120.0          # 1 bar = 2 s
    quiet = _sine(200, 8, 0.05)
    loud = _sine(200, 8, 0.5)
    x = np.concatenate([quiet, loud])
    p = _write(tmp_path, "sec.wav", np.stack([x, x], axis=1))
    r = analysis.analyze(p, sections=[{"name": "A", "start_bar": 1, "end_bar": 5},
                                      {"name": "B", "start_bar": 5, "end_bar": 9}],
                         tempo=tempo)
    a, b = r["sections"]
    assert b["lufs"] - a["lufs"] > 18


def test_compare_matches_loudness_before_band_diff(tmp_path):
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.1, SR * 6)
    a = _write(tmp_path, "a.wav", np.stack([noise, noise], axis=1))
    b = _write(tmp_path, "b.wav", np.stack([noise, noise], axis=1) * 0.5)
    c = analysis.compare(a, b)
    assert abs(c["loudness_diff_lu"] - 6.0) < 0.3
    assert all(abs(v) < 0.5 for v in c["band_diff_db_loudness_matched"].values())
