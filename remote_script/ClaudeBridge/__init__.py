"""ClaudeBridge: Ableton Live Remote Script.

Opens a TCP server on 127.0.0.1:9878 that accepts newline-delimited JSON
requests and runs them on Live's main thread. Command logic lives in
`handlers.py`, which can be hot-reloaded with the `reload` command so edits
don't require restarting Live.

Request:  {"id": 1, "cmd": "get_song", "args": {}}
Response: {"id": 1, "ok": true, "result": {...}}
          {"id": 1, "ok": false, "error": "...", "trace": "..."}
"""
import importlib
import json
import queue
import socket
import threading
import traceback

from _Framework.ControlSurface import ControlSurface

from . import handlers

HOST = "127.0.0.1"
PORT = 9878
REPLY_TIMEOUT = 60.0
MAX_PER_TICK = 64


def create_instance(c_instance):
    return ClaudeBridge(c_instance)


class ClaudeBridge(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._inbox = queue.Queue()
        self._running = True
        self._server = None
        self._ctx = handlers.Context(self)
        self._thread = threading.Thread(target=self._serve, name="ClaudeBridge", daemon=True)
        self._thread.start()
        self.log_message("ClaudeBridge: listening on %s:%d" % (HOST, PORT))
        self.show_message("ClaudeBridge ready on port %d" % PORT)

    # ---------- network thread ----------

    def _serve(self):
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind((HOST, PORT))
            self._server.listen(4)
            self._server.settimeout(1.0)
        except Exception as e:
            self.log_message("ClaudeBridge: bind failed: %s" % e)
            return
        while self._running:
            try:
                conn, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._client, args=(conn,), daemon=True).start()

    def _client(self, conn):
        conn.settimeout(None)
        buf = b""
        try:
            while self._running:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if line.strip():
                        conn.sendall(self._handle_line(line) + b"\n")
        except Exception as e:
            self.log_message("ClaudeBridge: client error: %s" % e)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _handle_line(self, line):
        req_id = None
        try:
            req = json.loads(line.decode("utf-8"))
            req_id = req.get("id")
            reply = queue.Queue(maxsize=1)
            self._inbox.put((req.get("cmd"), req.get("args") or {}, reply))
            ok, payload = reply.get(timeout=REPLY_TIMEOUT)
        except queue.Empty:
            ok, payload = False, {"error": "timeout waiting for Live main thread"}
        except Exception as e:
            ok, payload = False, {"error": "bad request: %s" % e}
        if ok:
            msg = {"id": req_id, "ok": True, "result": payload}
        else:
            msg = {"id": req_id, "ok": False}
            msg.update(payload)
        return json.dumps(msg, default=str).encode("utf-8")

    # ---------- Live main thread ----------

    def update_display(self):
        """Called by Live ~10x/s on its main thread. Everything past the reload command
        lives in handlers.py (dispatch, deferred commands, background jobs), so this
        file should almost never need to change."""
        global handlers
        ControlSurface.update_display(self)
        for _ in range(MAX_PER_TICK):
            try:
                cmd, args, reply = self._inbox.get_nowait()
            except queue.Empty:
                break
            if cmd == "reload":
                try:
                    handlers = importlib.reload(handlers)
                    self._ctx = handlers.Context(self, previous=self._ctx)
                    reply.put((True, {"reloaded": True, "handlers_version": handlers.VERSION}))
                except Exception as e:
                    reply.put((False, {"error": "reload failed: %s" % e,
                                       "trace": traceback.format_exc(limit=6)}))
                continue
            try:
                handlers.dispatch(self._ctx, cmd, args, reply)
            except Exception as e:
                reply.put((False, {"error": "%s: %s" % (type(e).__name__, e),
                                   "trace": traceback.format_exc(limit=6)}))
        try:
            handlers.tick(self._ctx)
        except Exception as e:
            self.log_message("ClaudeBridge: tick error: %s" % e)

    def disconnect(self):
        self._running = False
        try:
            if self._server:
                self._server.close()
        except Exception:
            pass
        self.log_message("ClaudeBridge: disconnected")
        ControlSurface.disconnect(self)
