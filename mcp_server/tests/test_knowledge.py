import json

import pytest

from ableton_claude import knowledge


def test_aliases_map_folder_names_to_genres():
    assert knowledge.key_of("Deep House") == "deep_house"
    assert knowledge.key_of("UKG") == "uk_garage"
    assert knowledge.key_of("Real Deep Tech") == "minimal_tech"
    assert knowledge.key_of("Psy techno") == "psy_techno"      # unknown: slugged


def test_every_convention_entry_is_complete():
    need = {"bpm", "keys", "harmony", "drums", "bass", "arrangement", "palette", "mix"}
    for g, c in knowledge.CONVENTIONS.items():
        assert need <= set(c), g
        assert c["bpm"][0] < c["bpm"][1], g


def test_plan_from_conventions_fills_the_duration(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DIR", str(tmp_path))
    p = knowledge.plan_structure("deep house", 6, bpm=123)
    assert p["source"] == "conventions"
    assert sum(s["bars"] for s in p["sections"]) == p["total_bars"] == 184
    assert all(s["bars"] % 8 == 0 for s in p["sections"])


def test_plan_uses_the_measured_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DIR", str(tmp_path))
    prof = {"bpm": {"median": 122}, "structure": {
        "intro_bars": {"median": 31}, "outro_bars": {"median": 33},
        "main_break_bars": {"median": 25}, "main_break_at": {"median": 0.6}}}
    (tmp_path / "deep_house.profile.json").write_text(json.dumps(prof))
    p = knowledge.plan_structure("Deep House", 7)
    names = {s["name"]: s for s in p["sections"]}
    assert p["source"] == "measured profile" and p["bpm"] == 122
    assert names["Intro"]["bars"] == 32 and names["Outro"]["bars"] == 32
    assert names["Breakdown"]["bars"] == 24
    assert abs(names["Breakdown"]["start_bar"] / p["total_bars"] - 0.6) < 0.05


def test_too_short_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        knowledge.plan_structure("deep house", 1.5, bpm=123)
