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


def test_reload_swaps_handlers(bridge):
    r = _rpc(bridge.PORT, "reload")
    assert r["ok"] and r["result"]["handlers_version"]
    assert _rpc(bridge.PORT, "ping")["ok"]
