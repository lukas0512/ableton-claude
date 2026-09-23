"""Socket client for the ClaudeBridge Remote Script running inside Ableton Live."""
import itertools
import json
import socket

HOST = "127.0.0.1"
PORT = 9878

_ids = itertools.count(1)


class BridgeError(RuntimeError):
    pass


class BridgeOffline(BridgeError):
    pass


def call(cmd, args=None, timeout=70.0):
    """Send one command and return its result. Raises BridgeError on failure."""
    req = {"id": next(_ids), "cmd": cmd, "args": args or {}}
    try:
        with socket.create_connection((HOST, PORT), timeout=5.0) as s:
            s.settimeout(timeout)
            s.sendall(json.dumps(req).encode("utf-8") + b"\n")
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(1 << 20)
                if not chunk:
                    break
                buf += chunk
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        raise BridgeOffline(
            "ClaudeBridge is not reachable on %s:%d (%s). Is Live open with ClaudeBridge "
            "selected as a Control Surface?" % (HOST, PORT, e)) from e
    msg = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
    if not msg.get("ok"):
        raise BridgeError(msg.get("error", "unknown error") +
                          ("\n" + msg["trace"] if msg.get("trace") else ""))
    return msg.get("result")


def batch(commands):
    """commands: [{"cmd": ..., "args": {...}}, ...] run in one main-thread tick."""
    return call("batch", {"commands": commands}, timeout=120.0)
