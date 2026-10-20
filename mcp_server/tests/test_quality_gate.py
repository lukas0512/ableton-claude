from ableton_claude import quality_gate as gate


def fake_set(**over):
    """A tiny set: kick, hats, a 909 rack, two voices, a master limiter."""
    hats = [[60, k / 4 + (0.0225 if k % 2 else 0), .1, 100] for k in range(32)]
    late = [[60, k / 4 + (0.04 if k % 2 else 0), .2, 90] for k in range(32)]
    s = {
        "song": {"tempo": 125.0, "cues": [{"name": "DROP 1"}, {"name": "DROP 2"}],
                 "master": {"devices": ["Limiter"]},
                 "tracks": [{"i": 0, "name": "HATS", "kind": "midi", "mute": False},
                            {"i": 1, "name": "CONGAS", "kind": "midi", "mute": False},
                            {"i": 2, "name": "RIDE 909", "kind": "midi", "mute": False},
                            {"i": 3, "name": "VOX A", "kind": "audio", "mute": False},
                            {"i": 4, "name": "VOX B", "kind": "audio", "mute": False}]},
        "tracks": {0: {"devices": [{"i": 0, "class": "OriginalSimpler"}],
                       "clips": [{"type": "midi", "start": 0}]},
                   1: {"devices": [], "clips": [{"type": "midi", "start": 0}]},
                   2: {"devices": [], "clips": [{"type": "midi", "start": 0}]},
                   3: {"devices": [], "clips": [], "sends_db": [-70.0, -14.0]},
                   4: {"devices": [], "clips": [], "sends_db": [-70.0, -14.0]}},
        "notes": {0: hats, 1: hats, 2: [[51, k, .5, 100] for k in range(8)]},
        "pads": {2: [51]}, "simpler_db": -12.0, "transport": {"re_enable_automation_enabled": False},
        "limiter": {"Mode": "True Peak", "Ceiling": "-1.0 dB"},
    }
    s.update(over)
    return s, late


def caller(s):
    def call(cmd, args=None):
        args = args or {}
        if cmd == "get_song":
            return s["song"]
        if cmd == "get_track":
            return s["tracks"][args["track"]]
        if cmd == "get_notes":
            return s["notes"].get(args["track"], [])
        if cmd == "drum_pads":
            pads = s["pads"].get(args["track"])
            return {"device": "909 Core Kit", "pads": pads} if pads is not None else {"device": None, "pads": []}
        if cmd == "get_device":
            if args["track"] == "master":
                return {"params": [{"name": k, "display": v} for k, v in s["limiter"].items()]}
            return {"params": [{"name": "Volume", "value": s["simpler_db"]}]}
        if cmd == "transport_state":
            return s["transport"]
        raise AssertionError(cmd)
    return call


def checks(result):
    return {f["check"] for f in result["findings"]}


def test_a_clean_set_passes():
    s, _ = fake_set()
    r = gate.run(caller(s))
    assert r["passed"] and checks(r) == set()


def test_each_past_mistake_is_caught():
    s, late = fake_set()
    s["song"]["tracks"].append({"i": 5, "name": "lvl LOOP CITY -", "kind": "audio", "mute": False})
    s["tracks"][5] = {"devices": [], "clips": [{"type": "audio", "start": 0,
                                                "file": "/x/Samples/Recorded/lvl 0001.wav"}]}
    s["transport"] = {"re_enable_automation_enabled": True}
    s["simpler_db"] = 0.0
    s["notes"][2] = [[60, k, .5, 100] for k in range(8)]       # the ride on an empty pad
    s["notes"][0] = late                                        # hats in another pocket
    s["notes"][6] = s["notes"][1]
    s["song"]["tracks"].append({"i": 6, "name": "BASS", "kind": "midi", "mute": False})
    s["tracks"][6] = {"devices": [], "clips": [{"type": "midi", "start": 0}]}
    s["tracks"][4]["sends_db"] = [-70.0, -70.0]                 # a voice outside the plate
    s["limiter"] = {"Mode": "Standard", "Ceiling": "-0.3 dB"}
    s["song"]["cues"] = [{"name": "DROP"}]
    r = gate.run(caller(s))
    assert not r["passed"]
    assert {"leftover track", "automation overridden", "gain staging", "empty drum pad",
            "swing pocket", "voices in different spaces", "master", "club form"} <= checks(r)
    assert r["findings"][0]["severity"] == "error"


def test_off16_offset_reads_the_swing():
    times = [k / 4 + (0.0225 if k % 2 else 0) for k in range(32)]
    assert abs(gate.off16_offset_ms(times, 125.0) - 10.8) < .1
    assert gate.off16_offset_ms([0, 1, 2], 125.0) is None


def test_the_producer_brief_carries_his_quality_bar():
    from ableton_claude import server
    brief = server._brief("producer") + server._brief("taste")
    assert "quality bar" in brief and "One pocket" in brief and "DROP 2" in brief
