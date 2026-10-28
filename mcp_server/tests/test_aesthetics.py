import numpy as np
import pytest
import soundfile as sf

pytest.importorskip("torch")

from ableton_claude.ear import aesthetics as aes  # noqa: E402


def fake_predict(level_of):
    """A stand-in model: every score is the window's RMS mapped through `level_of`."""
    def predict(batch):
        out = []
        for item in batch:
            r = float(item["path"].pow(2).mean().sqrt())
            out.append({k: level_of(r) for k in aes.AXES})
        return out
    return predict


def test_windows_cover_the_file_and_drop_a_short_tail():
    x = np.zeros(int(aes.SR * 34.0), dtype=np.float32)     # 3 windows and a 4 s tail
    w = aes.score_windows(x, predict=fake_predict(lambda r: 5.0))
    assert [v["t"] for v in w] == [0.0, 10.0, 20.0]
    short = aes.score_windows(np.zeros(aes.SR * 3, dtype=np.float32), predict=fake_predict(lambda r: 5.0))
    assert len(short) == 1


def test_score_file_and_bars(tmp_path):
    p = tmp_path / "r.wav"
    sig = np.concatenate([np.full(aes.SR * 10, 0.1), np.full(aes.SR * 10, 0.5)]).astype(np.float32)
    sf.write(p, np.stack([sig, sig], 1), aes.SR)
    res = aes.score_file(str(p), predict=fake_predict(lambda r: round(10 * r, 2)), cache=False)
    assert [w["CE"] for w in res["windows"]] == [1.0, 5.0] and res["mean"]["CE"] == 3.0
    bars = aes.with_bars(res["windows"], tempo=120.0, start_bar=65)
    assert [w["bar"] for w in bars] == [65.0, 70.0]


def _scored(values, bars=None):
    w = [dict({"t": 10.0 * i}, **{k: v for k in aes.AXES}) for i, v in enumerate(values)]
    if bars:
        w = [dict(x, bar=b) for x, b in zip(w, bars)]
    return {"mean": aes._mean(w), "windows": w}


def test_a_worse_section_is_flagged_and_noise_is_not():
    old = _scored([7.0, 7.2, 7.4], bars=[1, 6, 11])
    assert aes.compare(_scored([7.02, 7.15, 7.42], bars=[1, 6, 11]), old)["worse"] == []
    worse = aes.compare(_scored([7.0, 6.8, 7.4], bars=[1, 6, 11]), old)["worse"]
    assert {"axis": "CE", "where": "bar 6", "delta": -0.4} in worse
    assert any(w["where"] == "whole render" for w in worse)


def test_findings_against_references():
    refs = [{k: v for k in aes.AXES} for v in (7.0, 7.4, 7.6)]
    f = aes.findings(_scored([7.1, 7.2]), ref_means=refs)
    assert f[0]["severity"] == "info" and "refs 7.40" in f[0]["detail"]
    f = aes.findings(_scored([6.5, 6.6]), ref_means=refs)
    assert f[0]["severity"] == "warn" and "under every reference" in f[0]["detail"]
