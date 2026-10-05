from ableton_claude import journal


def setup_function():
    journal._records.clear()
    journal.PATH = "/dev/null"


def test_param_change_reverts_to_raw_value():
    journal.record("set_param", {"track": "Bass", "device": "EQ Eight", "param": "1 Gain A",
                                 "db": -3}, {"value": 0.4, "before": {"value": 0.5}})
    rec = journal.find()[0]
    assert journal.inverse(rec) == [("set_param", {"track": "Bass", "device": "EQ Eight",
                                                   "param": "1 Gain A", "value": 0.5})]


def test_renamed_track_is_addressed_by_its_new_name():
    journal.record("set_track", {"track": "Bass", "name": "Sub", "volume_db": -6},
                   {"name": "Sub", "before": {"name": "Bass", "volume_raw": 0.85}})
    inv = journal.inverse(journal.find()[0])
    assert inv[0] == ("set_raw", {"track": "Sub", "target": "volume", "value": 0.85})
    assert inv[1] == ("set_track", {"track": "Sub", "name": "Bass"})


def test_reads_are_not_journaled_and_deletes_are_not_reversible():
    assert journal.record("get_song", {}, {}) is None
    journal.record("delete_clips_in_range", {"track": 1, "start_bar": 1, "end_bar": 9}, {})
    assert journal.inverse(journal.find()[0]) is None


def test_find_skips_reverted_and_returns_newest_first():
    for v in (1, 2, 3):
        journal.record("set_send", {"track": 0, "send": 0, "db": -v}, {"before": {"raw": v}})
    journal.mark_reverted(journal.find()[0])
    assert [r["id"] for r in journal.find(last=5)] == [2, 1]


def test_clip_gain_and_created_clip():
    journal.record("set_clip", {"track": "Kick", "clip": 3, "gain_db": -2},
                   {"start": 32.0, "before": {"gain_raw": 0.4}})
    assert journal.inverse(journal.find()[0]) == [
        ("set_raw", {"track": "Kick", "target": "clip_gain", "device": {"at": 32.0},
                     "value": 0.4})]
    journal.record("create_midi_clip", {"track": "Bass", "length": 16}, {"start": 64.0})
    assert journal.inverse(journal.find()[0]) == [
        ("delete_clip", {"track": "Bass", "clip": {"at": 64.0}})]
