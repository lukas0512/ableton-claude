import json
import threading
import time

import pytest

from ableton_claude import genres, knowledge, library, references, server, storage, study


@pytest.fixture
def user_data(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path / "user"))
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DIR", str(tmp_path / "user" / "knowledge" / "genres"))
    monkeypatch.setattr(study, "STUDIES_DIR", str(tmp_path / "user" / "References"))
    monkeypatch.setattr(study, "CACHE_PATH", str(tmp_path / "user" / "knowledge" / "cache.json"))
    monkeypatch.setattr(genres, "_JOBS", {})
    return tmp_path


def wait_for_job(folder):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        result = genres.status(str(folder))
        if result["state"] not in ("queued", "running"):
            return result
        time.sleep(0.01)
    pytest.fail("learning job did not complete")


def test_training_handles_subfolders_without_study_cap_and_isolates_errors(user_data, monkeypatch):
    root = user_data / "source"
    nested = root / "Jazz" / "album"
    nested.mkdir(parents=True)
    for i in range(13):
        (nested / f"{i}.wav").write_bytes(b"audio")
    (root / "Empty").mkdir()
    (root / "root.wav").write_bytes(b"ignored")
    called = []

    def run(name, folder, **kwargs):
        called.append((name, len(study.audio_files(folder)), kwargs))
        references.save_profile({"genre": name, "n_tracks": 13}, knowledge.profile_path(name))
        return {"n_references": 13}

    monkeypatch.setattr(study, "run", run)
    genres.start(str(root))
    result = wait_for_job(root)
    assert result["state"] == "partial"
    assert result["completed"][0]["genre"] == "Jazz"
    assert result["errors"][0]["genre"] == "Empty"
    assert called[0][1] == 13
    assert called[0][2]["kind"] == "genre"
    assert called[0][2]["brief_folder"].startswith(str(user_data / "user"))
    assert not (root / "Jazz" / "study.json").exists()
    assert knowledge.load_profile("Jazz")["n_tracks"] == 13


def test_validation_rejects_missing_empty_and_colliding_folders(user_data):
    with pytest.raises(ValueError, match="not a folder"):
        genres.discover(str(user_data / "missing"))
    with pytest.raises(ValueError, match="no genre subfolders"):
        genres.discover(str(user_data))
    (user_data / "UKG").mkdir()
    (user_data / "garage").mkdir()
    with pytest.raises(ValueError, match="same profile"):
        genres.discover(str(user_data))


def test_repeated_call_reuses_running_job(user_data, monkeypatch):
    (user_data / "Jazz").mkdir()
    (user_data / "Jazz" / "song.wav").write_bytes(b"audio")
    entered, release = threading.Event(), threading.Event()
    calls = []

    def run(*args, **kwargs):
        calls.append(args)
        entered.set()
        release.wait(2)
        return {"n_references": 1}

    monkeypatch.setattr(study, "run", run)
    try:
        genres.start(str(user_data))
        assert entered.wait(1)
        assert genres.start(str(user_data))["state"] == "running"
        assert len(calls) == 1
    finally:
        release.set()
        wait_for_job(user_data)


def test_context_reads_user_profiles_on_every_prompt(user_data):
    assert "No genres trained" in server.producer_brief()
    references.save_profile({"genre": "Jazz", "n_tracks": 3}, knowledge.profile_path("Jazz"))
    bad = user_data / "user" / "knowledge" / "genres" / "broken.profile.json"
    bad.write_text("invalid json")
    assert [g["genre"] for g in server.list_genres()] == ["Jazz"]
    assert '"genre": "Jazz"' in server.producer_brief()
    assert '"genre": "Jazz"' in server.produce_prompt()
    server._refresh_genres()
    assert '"genre": "Jazz"' in server.mcp._mcp_server.instructions


def test_empty_or_all_failed_analysis_has_clear_error(user_data, monkeypatch):
    with pytest.raises(ValueError, match="no reference could be analysed"):
        references.build_profile(str(user_data), "empty", log=lambda _: None)
    (user_data / "bad.wav").write_bytes(b"bad")
    monkeypatch.setattr(references, "analyze_reference", lambda _: (_ for _ in ()).throw(ValueError("bad")))
    with pytest.raises(ValueError, match="no reference could be analysed"):
        references.build_profile(str(user_data), "bad", log=lambda _: None)


def test_study_saves_brief_outside_reference_source(user_data, monkeypatch):
    source = user_data / "source"
    source.mkdir()
    profile = {"genre": "Jazz", "n_tracks": 1}
    monkeypatch.setattr(references, "build_profile", lambda *a, **kw: (profile, {}))
    monkeypatch.setattr(references, "build_fingerprints", lambda *a, **kw: [])
    monkeypatch.setattr(study.timbre, "build_timbre", lambda *a, **kw: [])
    monkeypatch.setattr(study.timbre, "profile_stats", lambda _: {})
    monkeypatch.setattr(study.tension, "profile_stats", lambda _: {})
    monkeypatch.setattr(study, "make_brief", lambda *a: {"n_references": 1})
    destination = study.folder_of("Jazz")
    study.run("Jazz", str(source), ear=False, log=lambda _: None,
              brief_folder=destination, kind="genre")
    assert not (source / "study.json").exists()
    assert study.load_brief("Jazz") == {"n_references": 1}
    assert knowledge.load_profile("Jazz")["kind"] == "genre"
    assert json.loads((user_data / "user" / "knowledge" / "cache.json").read_text()) == {}


def test_learning_tool_refuses_active_render(user_data, monkeypatch):
    monkeypatch.setattr(server.client, "call", lambda _: {"state": "recording"})
    assert "render is running" in server.learn_genres(str(user_data))["error"]
    assert genres._JOBS == {}


def test_library_index_creates_fresh_user_directory(user_data, monkeypatch):
    target = user_data / "new-user" / "knowledge" / "samples_index.json"
    monkeypatch.setattr(library, "INDEX_PATH", str(target))
    library.build_index([])
    assert json.loads(target.read_text())["n"] == 0
