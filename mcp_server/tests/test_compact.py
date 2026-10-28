import json

from mcp.server.fastmcp.utilities import func_metadata as fm

from ableton_claude import compact, server  # noqa: F401  (server installs the converter)
from ableton_claude.desktop_mcp import unpack


def test_tables_go_toon_and_round_trip():
    clips = {"name": "RIFF", "clips": [{"i": k, "start": k * 16.0, "end": k * 16.0 + 16,
                                        "name": "Murder riff", "muted": False} for k in range(8)]}
    text = compact.render(clips)
    assert "clips[8]{" in text
    assert len(text) < len(json.dumps(clips, indent=2)) * 0.5
    assert compact.parse(text) == clips


def test_nested_data_stays_compact_json_and_floats_are_cut():
    data = {"song_length_beats": 799.9900001040626, "master": {"devices": [{"a": {"b": [1]}}]}}
    text = compact.render(data)
    assert "799.99," in text and " " not in text
    assert compact.parse(text)["song_length_beats"] == 799.99


def test_plain_text_is_left_alone():
    brief = server.producer_brief()
    assert compact.parse(brief) == brief
    assert fm._convert_to_content(brief)[0].text == brief


def test_fastmcp_writes_tool_results_compact():
    out = fm._convert_to_content({"tracks": [{"i": 0, "name": "KICK"}, {"i": 1, "name": "BASS"}]})
    assert len(out) == 1 and out[0].text == "tracks[2]{i,name}:\n  0,KICK\n  1,BASS"


def test_desktop_unpacks_toon():
    class Text:
        type = "text"
        text = compact.render([{"i": 0, "name": "KICK"}, {"i": 1, "name": "BASS"}])

    class Result:
        content = [Text()]
        isError = False
        structuredContent = None
    assert unpack(Result()) == [{"i": 0, "name": "KICK"}, {"i": 1, "name": "BASS"}]
