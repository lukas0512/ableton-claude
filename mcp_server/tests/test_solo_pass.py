import pytest

from ableton_claude import solo_pass as sp


class FakeLive:
    """Tracks with solo states, a master limiter, and renders that leave a track named
    with a trailing space (Live strips it)."""

    def __init__(self, fail_render=None, fail_solo=None):
        self.tracks = [{"i": 0, "name": "KICK", "solo": False}, {"i": 1, "name": "BASS", "solo": False},
                       {"i": 2, "name": "VOX", "solo": True}, {"i": 3, "name": "CLAP", "solo": False},
                       {"i": 4, "name": "LOOP CITY - orig synth", "solo": False}]
        self.limiter_on = True
        self.fail_render, self.fail_solo = fail_render, fail_solo
        self.calls, self.job = [], None

    def soloed(self):
        return {t["name"] for t in self.tracks if t["solo"]}

    def __call__(self, cmd, args=None):
        args = args or {}
        self.calls.append((cmd, args))
        if cmd == "get_song":
            return {"tempo": 125.0, "tracks": [dict(t) for t in self.tracks],
                    "master": {"devices": ["EQ Eight", "Limiter"]}}
        if cmd == "set_device_on":
            before = {"on": self.limiter_on}
            self.limiter_on = args["on"]
            return {"before": before}
        if cmd == "set_track":
            if args.get("solo") and args["track"] == self.fail_solo:
                raise RuntimeError("no such track")
            next(t for t in self.tracks if t["name"] == args["track"])["solo"] = args["solo"]
            return {}
        if cmd == "record_master":
            solo = sorted(self.soloed())
            # Live drops trailing spaces from a track name
            self.tracks.append({"i": len(self.tracks), "name": args["name"].rstrip(), "solo": False})
            self.job = {"state": "done", "file": "/r/%s.wav" % "+".join(solo)}
            if solo == [self.fail_render]:
                self.job = {"state": "idle"}
            return {"state": "recording"}
        if cmd == "track_routing":
            return {"output": "DRUMS" if args["track"] == "CLAP" else "Main"}
        if cmd == "record_tracks":
            names = ["%s %s" % (args["prefix"], t) for t in args["tracks"]]
            for n in names:
                self.tracks.append({"i": len(self.tracks), "name": n[:31].rstrip(), "solo": False})
            self.job = {"state": "done", "files": {t: "/r/%s.wav" % t for t in args["tracks"]}}
            return {"state": "recording", "tracks": names}
        if cmd == "record_status":
            return self.job
        if cmd == "delete_track":
            self.tracks = [t for t in self.tracks if t["i"] != args["track"]]
            for i, t in enumerate(self.tracks):
                t["i"] = i
            return {}
        raise AssertionError(cmd)


LEVELS = {"KICK": -16.5, "BASS": -19.8, "CLAP": -28.7}


def fake_measure(path):
    name = path.split("/")[-1][:-4]
    lufs = LEVELS.get(name, float("-inf"))
    third = [-60.0] * len(sp.THIRD_OCTAVES)
    if name == "KICK":
        third[3] = -10.0                         # 63 Hz
        third[12] = -20.0                        # 500 Hz: the box
    if name == "BASS":
        third[3] = -14.0
        third[12] = -22.0
    return lufs, -3.0, third


def run(live, tracks=("BASS", "CLAP", "LOOP CITY - orig synth")):
    return sp.run(live, list(tracks), 81, 89, sleep=lambda s: None, measure_fn=fake_measure,
                  timeout_s=5)


def test_levels_against_the_kick_and_everything_restored():
    live = FakeLive()
    r = run(live)
    e = r["elements"]
    assert list(e) == ["KICK", "BASS", "CLAP", "LOOP CITY - orig synth"]
    assert e["KICK"]["vs_kick_lu"] == 0 and e["BASS"]["vs_kick_lu"] == -3.3
    assert e["CLAP"]["vs_kick_lu"] == -12.2
    assert live.limiter_on and live.soloed() == {"VOX"}
    assert [t["name"] for t in live.tracks] == ["KICK", "BASS", "VOX", "CLAP",
                                                "LOOP CITY - orig synth"]   # no leftovers
    renders = [a["name"] for c, a in live.calls if c == "record_master"]
    assert renders == ["lvl KICK", "lvl BASS", "lvl CLAP", "lvl LOOP CITY -"]
    m = {b["hz"]: b for b in r["masking"]}
    assert m[63]["loudest"] == "KICK" and m[63]["within"] == [["BASS", 4.0]]
    assert m[500]["within"] == [["BASS", 2.0]] and 1000 not in m


def test_a_silent_element_and_a_failed_render_do_not_stop_the_pass():
    live = FakeLive(fail_render="BASS")
    LEVELS_SAVE = dict(LEVELS)
    r = run(live, ("BASS", "CLAP", "VOX"))
    assert "BASS" in r["failed"] and r["elements"]["CLAP"]["vs_kick_lu"] == -12.2
    assert r["elements"]["VOX"]["silent"] and r["elements"]["VOX"]["vs_kick_lu"] is None
    assert live.limiter_on and live.soloed() == {"VOX"}
    assert not [t for t in live.tracks if t["name"].startswith("lvl")]
    assert LEVELS == LEVELS_SAVE


def test_an_error_mid_pass_still_restores_solo_and_limiter():
    live = FakeLive(fail_solo="CLAP")
    with pytest.raises(RuntimeError):
        run(live)
    assert live.limiter_on and live.soloed() == {"VOX"}


def test_limiter_left_off_stays_off():
    live = FakeLive()
    live.limiter_on = False
    run(live)
    assert live.limiter_on is False


def test_masking_ignores_quiet_bands():
    spectra = {"A": [-10.0, -60.0], "B": [-12.0, -61.0]}
    sp_hz = sp.THIRD_OCTAVES
    sp.THIRD_OCTAVES = [63, 8000]
    try:
        out = sp.masking(spectra)
    finally:
        sp.THIRD_OCTAVES = sp_hz
    assert out == [{"hz": 63, "loudest": "A", "within": [["B", 2.0]]}]


def test_solo_levels_tool_runs_in_the_background(monkeypatch):
    from ableton_claude import client, server
    live = FakeLive()
    real = live

    def call(cmd, args=None):
        if cmd == "record_status" and (real.job is None):
            return {"state": "idle"}
        return real(cmd, args)
    monkeypatch.setattr(client, "call", call)
    monkeypatch.setattr(sp, "measure", fake_measure)
    monkeypatch.setattr(sp, "POLL_S", 0.0)
    server._SOLO.clear()
    r = server.solo_levels(["BASS"], 81, 89)
    assert r["state"] == "running" and r["expected_s"] == round(2 * (8 * 4 * 60 / 125 + 6))
    st = server.solo_levels_status(wait_s=10)
    assert st["state"] == "done", st
    assert st["result"]["elements"]["BASS"]["vs_kick_lu"] == -3.3
    assert live.limiter_on and live.soloed() == {"VOX"}


def test_one_pass_taps_every_track_at_once_and_cleans_up():
    live = FakeLive()
    r = sp.run(live, ["BASS", "CLAP", "VOX"], 81, 89, sleep=lambda s: None,
               measure_fn=fake_measure, timeout_s=5, one_pass=True)
    assert r["mode"] == "one_pass_post_fader" and r["via_bus"] == {"CLAP": "DRUMS"}
    taps = [a for c, a in live.calls if c == "record_tracks"]
    assert len(taps) == 1 and taps[0]["tracks"] == ["KICK", "BASS", "CLAP", "VOX"]
    assert not [c for c, a in live.calls if c in ("record_master", "set_track", "set_device_on")]
    assert "warning" in r
    assert r["elements"]["BASS"]["vs_kick_lu"] == -3.3 and r["elements"]["VOX"]["silent"]
    assert [t["name"] for t in live.tracks] == ["KICK", "BASS", "VOX", "CLAP",
                                                "LOOP CITY - orig synth"]
    assert sp.expected_seconds(4, 81, 89, 125, one_pass=True) == round(8 * 4 * 60 / 125 + 6)


def test_two_limiters_are_each_restored():
    class TwoLimiters(FakeLive):
        def __init__(self):
            super().__init__()
            self.on = {"Limiter#0": True, "Limiter#1": True}

        def __call__(self, cmd, args=None):
            if cmd == "get_song":
                r = super().__call__(cmd, args)
                r["master"]["devices"] = ["Utility", "Limiter", "Limiter"]
                return r
            if cmd == "set_device_on":
                self.calls.append((cmd, args))
                assert args["device"] in self.on, args["device"]
                before = {"on": self.on[args["device"]]}
                self.on[args["device"]] = args["on"]
                return {"before": before}
            return super().__call__(cmd, args)
    live = TwoLimiters()
    run(live)
    assert live.on == {"Limiter#0": True, "Limiter#1": True}
