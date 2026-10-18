import pytest

from ableton_claude.music import kits


def test_kit_is_shipped_and_loads():
    assert "let_the_rhythm" in kits.names()
    kit = kits.load("Let The Rhythm")
    assert kit["bpm"] == 127.0
    for key in ("kick", "clap", "snare", "hat_16ths", "congas", "tom_909", "rim_909"):
        assert key in kit["parts"]


def test_steps_capture_the_producers_patterns():
    parts = kits.load("let_the_rhythm")["parts"]
    assert parts["kick"]["steps"][0] == "X...X...X...X..."
    # syncopated backbeat: 2 and 4 plus a 16th pickup before 4, and the '& of 1' in bar 2
    assert parts["clap"]["steps"][0][4] == "X" and parts["clap"]["steps"][0][15] == "X"
    assert parts["clap"]["steps"][1][2] == "X"
    assert parts["clap"]["steps"] == parts["snare"]["steps"]          # layered
    assert all(row == "..X...X...X...X." for row in parts["hat_off_persona"]["steps"])


def test_micro_timing_keeps_the_early_shaker():
    off = kits.load("let_the_rhythm")["parts"]["hat_off_shaker_shot"]["offset_ms"]
    assert off and all(-8 < v < -3 for v in off.values())             # ~5 ms early


def test_tile_repeats_and_cuts():
    notes = [[60, 0.0, 1.0, 100], [60, 3.5, 1.0, 90]]
    out = kits.tile(notes, 4, 3, pitch=36)
    assert len(out) == 6 and all(n[0] == 36 for n in out)
    assert out[-1][1] == 11.5 and out[-1][2] == 0.5                  # cut at the end
    assert kits.tile([[60, 0.0, 0.25, 90]], 32, 2) == [[60, 0.0, 0.25, 90]]


def test_pattern_and_summary():
    pat = kits.pattern("let_the_rhythm", bars=4, parts=["kick", "clap"], pitch_map={"kick": 36})
    assert set(pat) == {"kick", "clap"}
    assert len(pat["kick"]) == 16 and pat["kick"][0][0] == 36
    assert all(n[1] < 16 for n in pat["clap"])
    s = kits.summary(kits.load("let_the_rhythm"))
    assert "notes" not in s["parts"]["kick"] and s["parts"]["kick"]["fader_db"] == -2.3


def test_unknown_kit():
    with pytest.raises(ValueError):
        kits.load("nope")
