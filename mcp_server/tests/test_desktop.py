import json
from pathlib import Path

import pytest

from ableton_claude import desktop, storage


@pytest.fixture
def desktop_data(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setattr(desktop, "DATA_DIR", str(data))
    monkeypatch.setattr(storage, "DATA_DIR", str(data))
    monkeypatch.setattr(desktop.client, "call", lambda *a, **kw: (_ for _ in ()).throw(desktop.client.BridgeOffline("test offline")))
    return data


def test_configure_claude_preserves_other_connectors_and_backs_up(desktop_data, tmp_path, monkeypatch):
    config = tmp_path / "Claude" / "config.json"
    config.parent.mkdir()
    old = {"mcpServers": {"other": {"command": "other-server"}}, "preferences": {"theme": "dark"}}
    config.write_text(json.dumps(old))
    monkeypatch.setattr(desktop, "backend_command", lambda: {"command": "/Applications/Ableton Claude.app/backend", "args": ["--mcp"]})
    result = desktop.configure_claude(config)
    new = json.loads(config.read_text())
    assert new["mcpServers"]["other"] == old["mcpServers"]["other"]
    assert new["preferences"] == old["preferences"]
    assert new["mcpServers"]["ableton-claude"]["args"] == ["--mcp"]
    assert json.loads(Path(result["backup"]).read_text()) == old
    assert config.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("content", ["bad json", "[]", '{"mcpServers": []}'])
def test_invalid_config_is_preserved(desktop_data, tmp_path, content):
    config = tmp_path / "config.json"
    config.write_text(content)
    with pytest.raises(ValueError):
        desktop.configure_claude(config)
    assert config.read_text() == content


def test_bridge_installs_only_into_selected_library_with_backup(desktop_data, tmp_path, monkeypatch):
    resources = tmp_path / "resources"
    source = resources / "ClaudeBridge"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text("new init")
    (source / "handlers.py").write_text("new handlers")
    library = tmp_path / "Custom User Library"
    target = library / "Remote Scripts" / "ClaudeBridge"
    target.mkdir(parents=True)
    (target / "handlers.py").write_text("old handlers")
    monkeypatch.setattr(desktop, "resources", lambda: resources)
    result = desktop.install_bridge(str(library))
    assert (target / "handlers.py").read_text() == "new handlers"
    assert (Path(result["backup"]) / "handlers.py").read_text() == "old handlers"
    assert desktop.load_settings()["user_library"] == str(library)


def test_missing_library_is_not_created(desktop_data, tmp_path):
    library = tmp_path / "not-the-library"
    with pytest.raises(ValueError, match="User Library"):
        desktop.install_bridge(str(library))
    assert not library.exists()


def test_training_refuses_render_in_progress(desktop_data, monkeypatch):
    monkeypatch.setattr(desktop.client, "call", lambda *a, **kw: {"state": "finalizing"})
    with pytest.raises(ValueError, match="render"):
        desktop.dispatch("learn", {"folder": "/unused"})


def test_nested_analysis_lock_is_reentrant(desktop_data):
    @storage.serialized_analysis
    def inner():
        return 42

    @storage.serialized_analysis
    def outer():
        return inner()

    assert outer() == 42
    assert (desktop_data / "analysis.lock").exists()


def test_onboarding_organizes_references_and_handles_duplicate_names(desktop_data, tmp_path):
    (tmp_path / "album-a").mkdir()
    (tmp_path / "album-b").mkdir()
    files = [tmp_path / "album-a" / "track.wav", tmp_path / "album-b" / "track.wav"]
    for index, file in enumerate(files):
        file.write_bytes(bytes([index]))
    result = desktop.prepare_genre("Indie Dance", [str(p) for p in files])
    assert result["total_files"] == 2
    assert result["genres"][0]["genre"] == "Indie Dance"
    dest = Path(result["genres"][0]["folder"])
    assert all(p.is_symlink() for p in dest.iterdir())
    desktop.prepare_genre("Indie Dance", [str(p) for p in files])
    assert len(list(dest.iterdir())) == 2
    assert files[0].read_bytes() == b"\x00"


def test_onboarding_rejects_invalid_genre_before_creating_files(desktop_data, tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"audio")
    with pytest.raises(ValueError, match="nome"):
        desktop.prepare_genre("../elsewhere", [str(audio)])
    assert not desktop_data.exists()


def test_detects_custom_library_from_ableton_preferences(tmp_path):
    library = tmp_path / "Music" / "Custom Library"
    library.mkdir(parents=True)
    prefs = tmp_path / "Library" / "Preferences" / "Ableton" / "Live 12.4"
    prefs.mkdir(parents=True)
    (prefs / "Library.cfg").write_text('<Ableton><ContentLibrary><UserLibrary><LibraryProject>'
                                    f'<ProjectPath Value="{library.parent}"/><ProjectName Value="{library.name}"/>'
                                    '</LibraryProject></UserLibrary></ContentLibrary></Ableton>')
    assert desktop.detect_library(tmp_path) == str(library)


def test_preferences_never_persist_api_credentials(desktop_data):
    desktop.dispatch("save_settings", {"api_key": "private", "key": "private", "provider": "anthropic", "onboarding_step": 2})
    assert desktop.load_settings() == {"provider": "anthropic", "onboarding_step": 2}


def test_live_silence_values_are_valid_native_json():
    value = {"sends_db": [float('-inf'), 0.0], "invalid": float('nan')}
    encoded = json.dumps(storage.json_safe(value), allow_nan=False)
    assert json.loads(encoded) == {"sends_db": ["-Infinity", 0.0], "invalid": None}


def test_resume_allows_unfinished_arrangement_and_checks_saved_tracks(desktop_data, monkeypatch):
    from ableton_claude.production_session import ProductionSession
    flow = ProductionSession(desktop_data, desktop.write_json)
    flow.begin({'tracks': []}, copy_confirmed=True)
    flow.value.update(stage='arrangement', tracks=['Ideia · Motivo'], approvals=['loop', 'groove'], needs_resume=True)
    monkeypatch.setattr(desktop, '_PRODUCTION', flow)
    monkeypatch.setattr(desktop, 'producer_agent', lambda: type('Agent', (), {'status': lambda self: {'state': 'idle', 'pending': []}, 'reset': lambda self: {}})())
    monkeypatch.setattr(desktop.client, 'call', lambda *a, **kw: {'state': 'idle'})
    calls = []
    class Connection:
        def call(self, name, args):
            calls.append((name, args))
            return {'name': 'Ideia · Motivo'}
    monkeypatch.setattr(desktop, 'mcp_connection', lambda: Connection())
    with pytest.raises(ValueError, match='Confirme'):
        desktop.dispatch('production_resume', {})
    result = desktop.dispatch('production_resume', {'project_confirmed': True})
    assert not result['needs_resume'] and result['stage'] == 'arrangement'
    assert calls == [('ableton_command', {'cmd': 'get_track', 'args': {'track': 'Ideia · Motivo', 'clips': False}})]


def test_stage_cannot_change_during_pending_proposal(desktop_data, monkeypatch):
    monkeypatch.setattr(desktop, 'producer_agent', lambda: type('Agent', (), {'status': lambda self: {'state': 'review', 'pending': [{}]}})())
    with pytest.raises(ValueError, match='descarte'):
        desktop.dispatch('production_approve', {})


def test_saved_project_restoration_requires_confirmation_and_missing_track_preserves_selection(desktop_data, monkeypatch):
    from ableton_claude.production_session import ProductionSession
    flow = ProductionSession(desktop_data, desktop.write_json)
    first = flow.begin({'tracks': []}, copy_confirmed=True)
    flow.observe('ableton_command', {'cmd': 'create_track'}, {'name': 'Ideia · Hook'})
    flow.end()
    monkeypatch.setattr(desktop, '_PRODUCTION', flow)
    monkeypatch.setattr(desktop, 'producer_agent', lambda: type('Agent', (), {'status': lambda self: {'state': 'idle', 'pending': []}, 'reset': lambda self: {}})())
    monkeypatch.setattr(desktop.client, 'call', lambda *a, **kw: {'state': 'idle'})
    class Connection:
        def call(self, *args):
            raise ValueError('Faixa não encontrada')
    monkeypatch.setattr(desktop, 'mcp_connection', lambda: Connection())
    with pytest.raises(ValueError, match='Confirme'):
        desktop.dispatch('production_restore', {'project_id': first['id']})
    with pytest.raises(ValueError, match='Faixa'):
        desktop.dispatch('production_restore', {'project_id': first['id'], 'project_confirmed': True})
    assert flow.status() == {'active': False}
    assert len(flow.projects()) == 1
    assert desktop.dispatch('production_end', {}) == {'active': False}
def test_development_resources_resolve_the_checkout_bridge():
    from ableton_claude.desktop import resources
    assert (resources() / 'remote_script' / 'ClaudeBridge' / 'handlers.py').is_file()


def test_claude_status_reads_installed_app_and_this_backend(desktop_data, tmp_path, monkeypatch):
    config = tmp_path / "claude.json"
    app = tmp_path / "Claude.app"
    monkeypatch.setattr(desktop, "backend_command", lambda: {"command": "/backend", "args": ["--mcp"]})
    assert desktop.claude_status(config, apps=[app]) == {"installed": False, "configured": False}
    app.mkdir()
    desktop.configure_claude(config)
    assert desktop.claude_status(config, apps=[app]) == {"installed": True, "configured": True}
    monkeypatch.setattr(desktop, "backend_command", lambda: {"command": "/other", "args": ["--mcp"]})
    assert desktop.claude_status(config, apps=[app])["configured"] is False


def test_index_samples_saves_folders_and_count(desktop_data, tmp_path, monkeypatch):
    from ableton_claude import library
    folder = tmp_path / "Samples"
    folder.mkdir()
    monkeypatch.setattr(library, "build_index", lambda roots: {"n": 3, "roots": roots})
    result = desktop.index_samples([str(folder), str(tmp_path / "missing")])
    assert result["n"] == 3 and result["roots"] == [str(folder)]
    assert desktop.load_settings()["sample_count"] == 3
    monkeypatch.setattr(library, "build_index", lambda roots: {"n": 0, "roots": roots})
    with pytest.raises(ValueError):
        desktop.index_samples([str(folder)])
    with pytest.raises(ValueError):
        desktop.index_samples([str(tmp_path / "missing")])
