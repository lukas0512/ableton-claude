import os

import pytest

from ableton_claude import study


def test_collect_links_files_and_refuses_non_audio(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "STUDIES_DIR", str(tmp_path / "studies"))
    src = tmp_path / "refs"
    src.mkdir()
    for n in ("a.wav", "b.flac", "notes.txt"):
        (src / n).write_bytes(b"x")
    folder = study.collect("My Track", folder=str(src))
    assert folder.endswith("my_track")
    assert [os.path.basename(p) for p in study.audio_files(folder)] == ["a.wav", "b.flac"]
    assert os.path.islink(os.path.join(folder, "a.wav"))
    study.collect("My Track", folder=str(src))  # idempotent
    with pytest.raises(ValueError):
        study.collect("Other", paths=[str(src / "notes.txt")])


def test_collect_caps_the_number_of_references(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "STUDIES_DIR", str(tmp_path / "studies"))
    for i in range(study.MAX_REFS + 1):
        (tmp_path / ("%02d.wav" % i)).write_bytes(b"x")
    with pytest.raises(ValueError, match="handful"):
        study.collect("Too many", folder=str(tmp_path))
