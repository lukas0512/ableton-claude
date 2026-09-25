"""Exercise the Remote Script's server and dispatch outside Live, with stub modules.

This does not test Live's API; it tests that requests reach the main-thread tick,
errors come back as errors, batch works, and reload swaps the handlers module.
"""
import importlib
import json
import socket
import sys
import threading
import time
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "remote_script"


class FakeControlSurface:
    def __init__(self, c_instance):
        self.messages = []

    def log_message(self, m):
        self.messages.append(m)

    def show_message(self, m):
        pass

    def update_display(self):
        pass

    def disconnect(self):
        pass

    def song(self):
        return types.SimpleNamespace(tempo=123.0)

    def application(self):
        return types.SimpleNamespace(get_major_version=lambda: 12, get_minor_version=lambda: 4,
                                     get_bugfix_version=lambda: 2)


@pytest.fixture()
def bridge(monkeypatch):
    fw = types.ModuleType("_Framework")
    cs = types.ModuleType("_Framework.ControlSurface")
    cs.ControlSurface = FakeControlSurface
    monkeypatch.setitem(sys.modules, "_Framework", fw)
    monkeypatch.setitem(sys.modules, "_Framework.ControlSurface", cs)
    monkeypatch.setitem(sys.modules, "Live", types.ModuleType("Live"))
    monkeypatch.syspath_prepend(str(ROOT))
    for m in [m for m in sys.modules if m.startswith("ClaudeBridge")]:
        del sys.modules[m]
    pkg = importlib.import_module("ClaudeBridge")
    pkg.PORT = _free_port()
    b = pkg.create_instance(None)
    stop = threading.Event()

    def main_thread():          # stands in for Live calling update_display
        while not stop.is_set():
            b.update_display()
            time.sleep(0.01)

    t = threading.Thread(target=main_thread, daemon=True)
    t.start()
    _wait_listening(pkg.PORT)
    yield pkg
    stop.set()
    b.disconnect()


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _wait_listening(port):
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
            return
        except OSError:
            time.sleep(0.02)
    raise RuntimeError("bridge never started listening")


def _rpc(port, cmd, args=None):
    with socket.create_connection(("127.0.0.1", port), timeout=5) as s:
        s.sendall(json.dumps({"id": 7, "cmd": cmd, "args": args or {}}).encode() + b"\n")
        buf = b""
        while b"\n" not in buf:
            buf += s.recv(65536)
    return json.loads(buf.split(b"\n")[0])


def test_ping_runs_on_main_thread_and_returns(bridge):
    r = _rpc(bridge.PORT, "ping")
    assert r["ok"] and r["id"] == 7
    assert r["result"]["live"] == "12.4.2"


def test_unknown_command_is_an_error_with_the_command_list(bridge):
    r = _rpc(bridge.PORT, "does_not_exist")
    assert not r["ok"]
    assert "ping" in r["available"]


def test_handler_exception_comes_back_as_error(bridge):
    r = _rpc(bridge.PORT, "set_tempo", {})          # missing bpm
    assert not r["ok"] and "TypeError" in r["error"]


def test_batch_runs_each_command_independently(bridge):
    r = _rpc(bridge.PORT, "batch", {"commands": [{"cmd": "ping"}, {"cmd": "nope"},
                                                 {"cmd": "ping"}]})
    assert r["ok"]
    assert [x["ok"] for x in r["result"]] == [True, False, True]


def test_generator_command_waits_ticks_then_replies(bridge):
    handlers = sys.modules["ClaudeBridge.handlers"]

    def slow(ctx, n=3):
        for _ in range(n):
            yield
        return {"waited": n}

    handlers.COMMANDS["slow"] = slow
    r = _rpc(bridge.PORT, "slow", {"n": 4})
    assert r["ok"] and r["result"] == {"waited": 4}


def test_generator_error_is_reported(bridge):
    handlers = sys.modules["ClaudeBridge.handlers"]

    def boom(ctx):
        yield
        raise ValueError("late failure")

    handlers.COMMANDS["boom"] = boom
    r = _rpc(bridge.PORT, "boom")
    assert not r["ok"] and "late failure" in r["error"]


def test_batch_refuses_waiting_commands(bridge):
    handlers = sys.modules["ClaudeBridge.handlers"]

    def slow(ctx):
        yield
        return 1

    handlers.COMMANDS["slow"] = slow
    r = _rpc(bridge.PORT, "batch", {"commands": [{"cmd": "slow"}, {"cmd": "ping"}]})
    assert [x["ok"] for x in r["result"]] == [False, True]
    assert "cannot run inside a batch" in r["result"][0]["error"]


def test_reload_swaps_handlers(bridge):
    r = _rpc(bridge.PORT, "reload")
    assert r["ok"] and r["result"]["handlers_version"]
    assert _rpc(bridge.PORT, "ping")["ok"]


def test_display_units_convert_to_base_units(bridge):
    """Live shows one parameter in ms below a second and in s above it; mixing the two
    once set a 2.2 s reverb to 60 s."""
    h = sys.modules["ClaudeBridge.handlers"]
    assert h._to_base("800 ms") == pytest.approx(0.8)
    assert h._to_base("2.20 s") == pytest.approx(2.2)
    assert h._to_base("1.50 kHz") == pytest.approx(1500)
    assert h._to_base("830 Hz") == pytest.approx(830)
    assert h._to_base("−3.00 dB") == pytest.approx(-3.0)
    assert h._to_base("-inf dB") == float("-inf")

    class Param:                     # a decay knob that switches from ms to s at 1 s
        min, max = 0.0, 1.0

        def str_for_value(self, v):
            secs = 0.2 + v * 59.8
            return "%.0f ms" % (secs * 1000) if secs < 1 else "%.2f s" % secs

    p = Param()
    raw = h._raw_for_display(p, "2.2 s")
    assert abs((0.2 + raw * 59.8) - 2.2) < 0.01
    raw = h._raw_for_display(p, "500 ms")
    assert abs((0.2 + raw * 59.8) - 0.5) < 0.01


def test_display_target_lands_on_the_reading_not_one_step_under(bridge):
    """A coarse display ('7.9 dB' in 0.1 dB steps) must read the target, not the step
    below it: the limiter drive asked for 7.9 dB came back as 7.8."""
    h = sys.modules["ClaudeBridge.handlers"]

    class Gain:
        min, max = 0.0, 1.0

        def str_for_value(self, v):
            return "%.1f dB" % (round(v * 12.0, 1))

    raw = h._raw_for_display(Gain(), "7.9 dB")
    assert Gain().str_for_value(raw) == "7.9 dB"


def test_warp_modes_and_audio_shaping(bridge):
    h = sys.modules["ClaudeBridge.handlers"]
    assert h._warp_mode("complex_pro") == 6 and h._warp_mode("Beats") == 0 and h._warp_mode(3) == 3
    with pytest.raises(ValueError):
        h._warp_mode("granular")

    class Clip:
        warping, warp_mode, pitch_coarse, pitch_fine = False, 0, 0, 0.0

    c = Clip()
    h._shape_audio(c, warp=True, warp_mode="texture", pitch=5, detune=-80)
    assert (c.warping, c.warp_mode, c.pitch_coarse, c.pitch_fine) == (True, 2, 5, -50.0)


def test_render_refuses_playback_that_starts_away_from_the_render_start(bridge):
    """Live starts playback at its start marker; once that sat at bar 125 and a render of
    97-145 silently recorded only 125-145."""
    h = sys.modules["ClaudeBridge.handlers"]

    class Track:
        arm = True

    class Song:
        is_playing, current_song_time, record_mode, metronome, loop = True, 496.0, True, False, False
        start_time = 496.0

        def stop_playing(self):
            self.is_playing = False

    ctx = types.SimpleNamespace(song=Song(), pending=[], record_job={
        "state": "recording", "start": 384.0, "end": 576.0, "track": Track(), "ticks": 0,
        "saved": {"arm": [], "metronome": False, "loop": False, "record_mode": False}})
    h.tick(ctx)
    job = ctx.record_job
    assert "instead of 384.00" in job["error"] and not ctx.song.is_playing
