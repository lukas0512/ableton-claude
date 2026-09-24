import numpy as np

from ableton_claude import tension


def _song(kick_in_build=False):
    rows = []
    for b in range(64):
        if b < 32 or b >= 56:                        # groove, then the drop
            rows.append([-10.0 if b < 32 else -9.5, -7.0, -10.0, -25.0])
        else:                                        # break; its last 8 bars build
            ramp = max(0, b - 48)
            kick = -7.0 if (kick_in_build and b >= 48) else -50.0
            rows.append([-14.0 + 0.3 * ramp, kick, -50.0, -30.0 + 0.8 * ramp])
    segs = [{"start": 0, "end": 32, "label": "full"}, {"start": 32, "end": 56, "label": "break"},
            {"start": 56, "end": 64, "label": "full"}]
    return np.array(rows), segs


def test_finds_the_break_and_the_drop():
    bars, segs = _song()
    assert tension.main_break(segs) == (32, 56, 56)
    m = tension.for_track(bars, segs)
    assert m["break_bars"] == [33, 57] and m["drop_bar"] == 57
    assert m["kick_out_db"] > 40 and m["bass_out_db"] > 30
    assert m["build_lu_per_bar"] > 0.2 and m["build_high_db_per_bar"] > 0.5
    assert m["drop_jump_lu"] > 2 and m["drop_jump_kick_db"] > 40


def test_a_kick_back_in_the_build_takes_the_release_away_from_the_drop():
    bars, segs = _song(kick_in_build=True)
    m = tension.for_track(bars, segs)
    assert abs(m["drop_jump_kick_db"]) < 1
    prof = {"drop_jump_kick_db": {"median": 26.0, "p25": 11.3, "p75": 37.0}}
    assert tension.compare(m, prof)["drop_jump_kick_db"]["verdict"] == "low"


def test_profile_stats_over_references():
    refs = []
    for k in range(5):
        bars, segs = _song(kick_in_build=(k == 0))
        refs.append({"bars_matrix": bars.tolist(), "segments": segs})
    st = tension.profile_stats(refs)
    assert st["drop_jump_kick_db"]["n"] == 5 and st["drop_jump_kick_db"]["median"] > 40
