import json

import pytest

from ableton_claude import desktop, groove_maker as gm, knowledge, storage
from ableton_claude.desktop_agent import read_only
from ableton_claude.production_session import ProductionSession


class FakeLive:
    """Records commands; answers get_song with a set that is empty or holds a song."""

    def __init__(self, occupied=False, fail=()):
        self.calls = []
        self.fail = set(fail)
        tracks = [{"name": "KICK", "clips_active": 3 if occupied else 0}]
        self.song = {"tempo": 127.0, "signature": "4/4", "tracks": tracks,
                     "song_length_beats": 400.0 if occupied else 0.0}

    def __call__(self, cmd, args):
        self.calls.append((cmd, args))
        if cmd in self.fail or (cmd, args.get("path")) in self.fail:
            raise ValueError("refused: %s" % cmd)
        return self.song if cmd == "get_song" else {"ok": True}

    def of(self, cmd):
        return [a for c, a in self.calls if c == cmd]


@pytest.mark.parametrize("vibe", list(gm.VIBES))
@pytest.mark.parametrize("bars", [4, 8, 16])
def test_every_vibe_plans_valid_notes_on_real_pads(vibe, bars):
    groove = gm.make(vibe, bars=bars)
    pads = set(gm.PADS_909.values()) | set(gm.PADS_PERC.values())
    for track, notes in groove["notes"].items():
        assert notes, track
        assert notes == sorted(notes, key=lambda n: (n[1], n[0]))
        for pitch, start, dur, vel in notes:
            assert 0 <= start < bars * 4 and 0 < dur and 1 <= vel <= 127
            if track != "BASS":
                assert pitch in pads
            else:
                assert 16 <= pitch <= 52        # bass register
    # The kick is the grid: never swung.
    assert all(abs(n[1] * 4 - round(n[1] * 4)) < 1e-6 for n in groove["notes"]["KICK"])
    assert len(groove["grid"]["kick"]) == 16


def test_offbeat_bass_stays_off_the_kick_and_swing_moves_offbeats():
    groove = gm.make("house", bass="offbeat")
    kicks = {n[1] for n in groove["notes"]["KICK"]}
    assert not kicks & {n[1] for n in groove["notes"]["BASS"]}
    straight = gm.make("house", feel="reto")
    hard = gm.make("house", feel="forte")
    assert straight["swing"] < groove["swing"] < hard["swing"] <= 66
    hat = lambda g: [n[1] for n in g["notes"]["HATS"] if n[0] == gm.PADS_909["closed_hat"]][1]
    assert hat(straight) < hat(hard)      # the 2nd 16th lands later with more swing


def test_seed_varies_and_same_inputs_repeat():
    assert gm.make("tech_house", seed=3) == gm.make("tech_house", seed=3)
    assert gm.make("tech_house", seed=3)["id"] != gm.make("tech_house", seed=4)["id"]


def test_key_and_mode_move_the_bass():
    g = gm.make("house", tonic="C", mode="major")
    assert min(n[0] for n in g["notes"]["BASS"]) % 12 in {0, 7, 11, 10}
    assert g["key"] == "C major"
    assert gm.make("house", tonic="Db")["tonic"] == "C#"
    with pytest.raises(ValueError):
        gm.make("house", tonic="H")
    with pytest.raises(ValueError):
        gm.make("polka")


@pytest.fixture
def profile(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DIR", str(tmp_path))
    steps = [{"step": i, "offset_ms": 12.0 if i % 2 else 0.0, "accent_db": -10.0 if i % 2 else -1.0,
              "spread_ms": 1.0, "share": 1.0} for i in range(16)]
    prof = {"genre": "minha ref", "n_tracks": 5, "bpm": {"median": 124.0}, "swing_pct": {"median": 59.0},
            "keys": {"E minor": 3, "C major": 1}, "structure": {"main_break_bars": {"median": 20}},
            "ear": {"hat_swing_pct": 58.0, "four_on_floor_share": 1.0,
                    "drums": {"hats": {"template": {"n": 5, "steps": steps}, "step_presence": [0.9] * 16}},
                    "bass": {"rhythms": [[".x-x..x-.x-x..x-", 2], ["..x-..x-..x-.xx-", 1]],
                             "degrees": {"1": 0.5, "b7": 0.2, "5": 0.15, "b3": 0.1}}}}
    (tmp_path / "minha_ref.profile.json").write_text(json.dumps(prof))
    return prof


def test_inspiration_takes_tempo_key_swing_hats_and_bass(profile):
    g = gm.make("house", inspired_by="minha ref")
    assert (g["bpm"], g["tonic"], g["mode"], g["swing"]) == (124.0, "E", "minor", 58.0)
    assert g["bass"] == "referencia" and g["break_bars"] == 24
    hats = [n for n in g["notes"]["HATS"] if n[0] == gm.PADS_909["closed_hat"] and n[1] < 1]
    assert len(hats) == 4
    assert hats[1][1] == pytest.approx(0.25 + 12.0 * 124 / 60000, abs=1e-3)
    assert hats[0][3] > hats[1][3]        # their accents, not ours
    assert "Inspirado em minha ref" in g["why"][0]
    # The person's own choices still win over the reference.
    assert gm.make("house", inspired_by="minha ref", tonic="G", bpm=128)["key"] == "G minor"
    with pytest.raises(ValueError):
        gm.make("house", inspired_by="nada")


def test_apply_loop_in_an_empty_set_sets_tempo_and_builds_five_tracks():
    live = FakeLive()
    g = gm.make("tech_house")
    receipt = gm.apply(g, live)
    assert live.of("set_tempo") == [{"bpm": 126.0}]
    assert receipt["tracks"] == ["G1 · %s" % t for t in gm.TRACKS]
    assert receipt["start_bar"] == 1 and receipt["end_bar"] == 9
    clips = live.of("create_midi_clip")
    assert len(clips) == 5 and all(c["bar"] == 1 and c["length"] == 32.0 for c in clips)
    kits = [a["path"] for a in live.of("load_device") if a.get("path", "").startswith("drums/")]
    assert kits.count(gm.KIT_909) == 3 and kits.count(gm.KIT_PERC) == 1
    side = live.of("set_device_input")
    assert side == [{"track": "G1 · BASS", "device": "Compressor", "source": "G1 · KICK"}]
    assert live.of("set_loop") == [{"on": True, "start_bar": 1, "end_bar": 9}]
    assert not receipt["warnings"]


def test_apply_after_existing_music_keeps_tempo_and_names():
    live = FakeLive(occupied=True)
    live.song["tracks"].append({"name": "G1 · KICK"})
    receipt = gm.apply(gm.make("house"), live, layout="pista")
    assert not live.of("set_tempo")
    assert receipt["start_bar"] == 109 and receipt["number"] == 2
    assert receipt["warnings"] and "127.0 BPM" in receipt["warnings"][0]
    assert len(live.of("set_cue")) == len(gm.DANCEFLOOR)
    # Drums alone at both ends; the kick is out of break and build, its last beat cut before.
    starts = {(c["track"], c["bar"]) for c in live.of("create_midi_clip")}
    assert ("G2 · BASS", 109) not in starts and ("G2 · KICK", 109) in starts
    before_break = [c for c in live.of("create_midi_clip") if c["track"] == "G2 · KICK" and c["name"] == "Groove 2"][0]
    assert max(n[1] for n in before_break["notes"]) < before_break["length"] - 1


def test_apply_falls_back_on_bass_sounds_and_reports_polish_failures():
    g = gm.make("ukg")
    live = FakeLive(fail={("load_device", p) for p in g["bass_presets"]} | {"set_device_input"})
    receipt = gm.apply(g, live)
    assert receipt["bass_sound"] == "Drift"
    assert any("Sidechain" in w for w in receipt["warnings"])
    with pytest.raises(ValueError):
        gm.apply(g, FakeLive(fail={"create_track"}))


def test_remove_deletes_tracks_cues_and_restores_tempo():
    live = FakeLive()
    receipt = gm.apply(gm.make("deep_house"), live, layout="pista")
    undo = FakeLive()
    out = gm.remove(receipt, undo)
    assert out["removed"] == list(reversed(receipt["tracks"]))
    assert len(undo.of("delete_cue")) == len(gm.DANCEFLOOR)
    assert undo.of("set_tempo") == [{"bpm": 127.0}]


def test_assistant_reviews_building_and_ideas_keep_their_tracks(tmp_path):
    assert read_only("quick_groove", {"vibe": "house"})
    assert not read_only("quick_groove", {"apply": True})
    assert not read_only("quick_groove_remove", {})
    flow = ProductionSession(tmp_path, lambda p, v: None)
    flow.begin({"signature": "4/4", "tracks": []}, 8, copy_confirmed=True)
    flow.check("quick_groove", {"vibe": "house"})
    with pytest.raises(ValueError):
        flow.check("quick_groove", {"apply": True})


@pytest.fixture
def desktop_data(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(desktop, "producer_agent", lambda: type("A", (), {"status": lambda s: {"state": "idle", "pending": []}})())
    monkeypatch.setattr(desktop.client, "call", lambda *a, **kw: {"state": "idle"})
    live = FakeLive()

    class Connection:
        def call(self, name, args):
            assert name == "ableton_command"
            return live(args["cmd"], args["args"])

    monkeypatch.setattr(desktop, "mcp_connection", lambda: Connection())
    return live


def test_desktop_applies_only_the_previewed_groove_and_removes_it(desktop_data):
    options = desktop.dispatch("groove_options", {})
    assert {v["id"] for v in options["vibes"]} == set(gm.VIBES) and options["last"] is None
    preview = desktop.dispatch("groove_preview", {"vibe": "afro_house", "seed": 2})
    assert "notes" not in preview and preview["grid"]["kick"]
    with pytest.raises(ValueError):
        desktop.dispatch("groove_apply", {"id": "old"})
    receipt = desktop.dispatch("groove_apply", {"id": preview["id"], "layout": "loop"})
    assert receipt["label"].startswith("Afro house")
    assert desktop.dispatch("groove_options", {})["last"]["tracks"] == receipt["tracks"]
    with pytest.raises(ValueError):
        desktop.dispatch("groove_remove", {})
    assert desktop.dispatch("groove_remove", {"confirmed": True})["removed"]
    assert desktop.dispatch("groove_options", {})["last"] is None
