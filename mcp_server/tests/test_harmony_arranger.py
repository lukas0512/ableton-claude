import pytest

from ableton_claude.arranger import Arranger, energy
from ableton_claude.music import harmony, melody, theory


def test_progression_anticipates_changes_by_an_eighth():
    notes, vs = harmony.progression_notes(["Gm7", "C7sus4"], bars_per_chord=1,
                                          anticipate=0.5, legato=1.0)
    starts = sorted({n[1] for n in notes})
    assert starts == [0.0, 3.5]                    # second chord lands on the "and" of 4
    first = [n for n in notes if n[1] == 0.0]
    assert all(n[1] + n[2] == 3.5 for n in first)  # and the first chord makes room for it
    assert {p % 12 for p in vs[1]} <= theory.chord_pcs("C7sus4")


def test_hold_last_bars_extends_final_chord():
    notes, _ = harmony.progression_notes(["Gm7", "C7sus4"], bars_per_chord=2,
                                         hold_last_bars=8, legato=1.0)
    # two chords x 2 bars = 16 beats, plus 8 held bars = 32 beats
    assert max(n[1] + n[2] for n in notes) == pytest.approx(48.0)


def test_swing_moves_only_offbeat_sixteenths():
    notes = [[60, 0.0, 0.2, 90], [60, 0.25, 0.2, 90], [60, 0.5, 0.2, 90], [60, 0.75, 0.2, 90]]
    out = harmony.swing(notes, 60)
    assert [n[1] for n in out] == [0.0, 0.3, 0.5, 0.8]


def test_call_opens_with_a_leap_and_fills_the_gap():
    out = melody.call_and_response("G", "minor_hexatonic",
                                   ["Gm7", "Gm7", "Bbmaj7", "Bbmaj7"], seed=11)
    c = [n[0] for n in out["call"]]
    assert 5 <= c[1] - c[0] <= 7                  # opening leap up
    assert c[2] < c[1]                            # then back down into the gap
    r = [n[0] for n in out["response"]]
    assert -7 <= r[1] - r[0] <= -5                # the answer mirrors it downward


def test_no_ping_pong_trills():
    for seed in range(20):
        out = melody.call_and_response("G", "minor_hexatonic",
                                       ["Gm7", "Gm7", "Bbmaj7", "Bbmaj7"], seed=seed)
        for part in (out["call"], out["response"]):
            p = [n[0] for n in part]
            trills = sum(1 for i in range(3, len(p))
                         if p[i] == p[i - 2] and p[i - 1] == p[i - 3] and p[i] != p[i - 1])
            assert trills <= 1, (seed, [theory.note_name(x) for x in p])


class FakeLive:
    """Records bridge calls; answers like ClaudeBridge would."""

    def __init__(self):
        self.calls = []

    def __call__(self, cmd, args=None):
        self.calls.append((cmd, args))
        if cmd == "duplicate_range":
            return {"copied": 3}
        if cmd == "delete_clips_in_range":
            return {"deleted": 5, "left_in_range": 0}
        return {}


def test_arranger_stashes_into_separate_slots_and_fills():
    live = FakeLive()
    arr = Arranger(call=live, library_bar=601, slot_bars=24, log=lambda *a: None)
    a = arr.stash("Kick", 165, 169)
    b = arr.stash("Kick", 1, 3)
    c = arr.stash("Bass", 165, 169)
    assert (a.start_bar, b.start_bar, c.start_bar) == (601, 625, 601)
    arr.fill(a, 1, 32)
    assert live.calls[-1] == ("fill_range", {"track": "Kick", "src_start_bar": 601,
                                             "src_end_bar": 605, "start_bar": 1,
                                             "end_bar": 32})
    arr.drop_library()
    dropped = [args["track"] for cmd, args in live.calls if cmd == "delete_clips_in_range"]
    assert sorted(dropped) == ["Bass", "Kick"]


def test_arranger_refuses_phrases_longer_than_a_slot():
    arr = Arranger(call=FakeLive(), slot_bars=8, log=lambda *a: None)
    with pytest.raises(ValueError):
        arr.stash("Pad", 1, 20)


def test_energy_counts_overlapping_parts():
    curve = energy([("Kick", 1, 5), ("Bass", 3, 5)], bars=6)
    assert curve == [1, 1, 2, 2, 0, 0]
