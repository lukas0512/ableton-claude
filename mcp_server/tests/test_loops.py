"""Loops from one-shots land where the references' groove says (no Live, no models)."""
import numpy as np
import pytest
import soundfile as sf

from ableton_claude import loops
from ableton_claude.ear import why

BPM = 123.0
SR = 44100


def _click(tmp_path, name="click.wav", n=400, first=1.0):
    x = np.zeros((n, 2))
    x[0] = first
    x[1:40] = np.linspace(0.5, 0.0, 39)[:, None]
    p = tmp_path / name
    sf.write(str(p), x, SR, subtype="FLOAT")
    return str(p)


def _template(late_ms=20.0):
    return {"n": 1, "steps": [{"step": s, "offset_ms": late_ms if s % 2 else 0.0,
                               "accent_db": 0.0 if s % 4 == 2 else -12.0, "spread_ms": 0.0}
                              for s in range(16)]}


def test_template_hits_land_on_their_offsets_with_their_accents(tmp_path):
    y = loops.from_template({"default": _click(tmp_path)}, _template(), BPM, bars=1, humanize=False)
    assert len(y) == int(round(4 * 60 / BPM * SR))
    six = 60 / BPM / 4
    for s in range(16):
        want = s * six + (0.020 if s % 2 else 0.0)
        a = int(round(want * SR))
        assert abs(y[a, 0]) > 0.2 and (a == 0 or abs(y[a - 2:a, 0]).max() < 1e-9), s
        level = 1.0 if s % 4 == 2 else 10 ** (-12 / 20)
        assert y[a, 0] == pytest.approx(level, rel=1e-6)


def test_steps_and_per_step_shots(tmp_path):
    click, other = _click(tmp_path), _click(tmp_path, "other.wav", first=0.5)
    y = loops.from_template({"default": click, 2: other}, _template(), BPM, bars=1,
                            steps=[0, 2], humanize=False)
    six = 60 / BPM / 4
    a2 = int(round(2 * six * SR))
    assert y[0, 0] == pytest.approx(10 ** (-12 / 20), rel=1e-6)      # step 0: default shot
    assert y[a2, 0] == pytest.approx(0.5, rel=1e-6)                  # step 2: its own shot
    for st in [1] + list(range(3, 16)):                               # nothing on other steps
        a = int(round((st * six + (0.020 if st % 2 else 0.0)) * SR))
        assert y[a, 0] == 0.0, st


def test_four_on_the_floor_is_exactly_the_loop_length(tmp_path):
    y = loops.four_on_floor(_click(tmp_path), BPM, bars=2)
    beat = int(round(60 / BPM * SR))
    assert len(y) == int(round(8 * 60 / BPM * SR))
    assert all(y[int(round(k * 60 / BPM * SR)), 0] == 1.0 for k in range(8))
    assert abs(y[beat // 2, 0]) < 1e-9


def test_groove_template_pools_the_references():
    def rep(late, acc):
        return {"drums": {"hats": {"template": [
            {"step": s, "offset_ms": late if s % 2 else 0.0, "accent_db": acc if s % 2 else 0.0,
             "spread_ms": 2.0} for s in range(16)]}}}
    t = why.groove_template([rep(10.0, -12.0), rep(20.0, -10.0), rep(30.0, -14.0)], "hats")
    assert t["n"] == 3
    assert t["steps"][1]["offset_ms"] == 20.0 and t["steps"][1]["accent_db"] == -12.0
    assert t["steps"][0]["offset_ms"] == 0.0 and t["steps"][3]["spread_ms"] == 2.0
    none = why.groove_template([{"drums": {}}], "hats")
    assert none["n"] == 0 and none["steps"][0]["offset_ms"] is None


def test_swing_moves_the_offbeats_and_keeps_their_lean():
    t = {"steps": [{"step": s, "offset_ms": (10.0 + (4.0 if s in (3, 7) else 0.0)) if s % 2 else 0.0,
                    "accent_db": 0.0, "spread_ms": 0.0} for s in range(16)]}
    eighth_ms = 60000 / BPM / 2
    sw = loops.with_swing(t, 60.0, BPM)["steps"]
    odd = [s["offset_ms"] for s in sw if s["step"] % 2]
    assert np.median(odd) == pytest.approx(0.10 * eighth_ms, abs=0.1)
    assert sw[3]["offset_ms"] - sw[1]["offset_ms"] == pytest.approx(4.0, abs=0.11)
    assert sw[0]["offset_ms"] == 0.0 and t["steps"][1]["offset_ms"] == 10.0     # input untouched


def test_stretch_and_reverse(tmp_path):
    src = _click(tmp_path, "fx.wav", n=SR, first=0.8)       # 1 s (write() only scales >0.999)
    out = loops.stretch_to(src, str(tmp_path / "s.wav"), BPM, 1)
    y, sr = sf.read(out)
    assert sr == SR and len(y) == int(round(4 * 60 / BPM * SR))
    rev = loops.reverse_to(src, str(tmp_path / "r.wav"))
    z, _ = sf.read(rev)
    assert len(z) == SR and abs(z[-1, 0]) == pytest.approx(0.8) and abs(z[0, 0]) < 1e-6


def test_trim_hit_cuts_and_fades(tmp_path):
    src = _click(tmp_path, "open.wav", n=SR, first=0.8)
    out = loops.trim_hit(src, str(tmp_path / "short.wav"), 0.09, fade_ms=10)
    y, sr = sf.read(out)
    assert len(y) == int(0.09 * SR) and abs(y[-1, 0]) < 1e-6 and y[0, 0] == pytest.approx(0.8)


def test_from_notes_scales_by_velocity_and_chokes(tmp_path):
    src = _click(tmp_path, "sn.wav", n=SR, first=1.0)
    y = loops.from_notes(src, [[39, 0.0, 0.5, 127], [39, 1.0, 0.5, 64]], BPM, 1)
    beat = int(round(60 / BPM * SR))
    assert y[0, 0] == pytest.approx(0.999, abs=1e-3) or y[0, 0] == pytest.approx(1.0)
    assert y[beat, 0] == pytest.approx(64 / 127, rel=1e-3)
    assert abs(y[beat - 1, 0]) < 1e-6                     # the first hit is choked at the second


def test_gaps_and_slices(tmp_path):
    ones = np.ones((int(4 * 60 / BPM * SR), 2)) * 0.5            # one bar of DC
    src = str(tmp_path / "bar.wav")
    sf.write(src, ones, SR, subtype="FLOAT")
    out = loops.with_gaps(src, str(tmp_path / "gap.wav"), BPM, [(2.0, 4.0)], fade_ms=0)
    y, _ = sf.read(out)
    beat = int(round(60 / BPM * SR))
    assert y[beat, 0] == pytest.approx(0.5) and y[2 * beat + 10, 0] == 0.0 and y[-1, 0] == 0.0
    sl = loops.slice_beats(src, str(tmp_path / "s.wav"), BPM, 3.0, 4.0, reverse=True)
    z, _ = sf.read(sl)
    assert abs(len(z) - beat) <= 1
