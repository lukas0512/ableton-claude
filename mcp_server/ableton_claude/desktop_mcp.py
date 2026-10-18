"""A persistent local MCP session owned by the desktop app, with reconnection."""
import asyncio
import concurrent.futures
import json
import os
import threading

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def unpack(result):
    text = "\n".join(c.text for c in result.content if getattr(c, "type", None) == "text")
    if result.isError:
        raise ValueError(text or "A ferramenta não conseguiu executar o pedido.")
    structured = result.structuredContent
    if structured is not None:
        if set(structured) == {"result"}:
            return structured["result"]
        return structured
    try:
        return json.loads(text)
    except ValueError:
        return text


class LocalMCP:
    def __init__(self, command, data_dir):
        self.command = command
        self.data_dir = data_dir
        self.state = "connecting"
        self.error = None
        self.tools = []
        self._thread = None
        self._loop = None
        self._queue = None
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                self._thread = threading.Thread(target=lambda: asyncio.run(self._serve()), daemon=True,
                                                name="desktop-mcp")
                self._thread.start()
        return self.status()

    def status(self):
        return {"state": self.state, "error": self.error, "tools": len(self.tools)}

    async def _serve(self):
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        while not self._stop.is_set():
            self.state, self.error = "connecting", None
            try:
                env = dict(os.environ, ABLETON_CLAUDE_DATA=self.data_dir)
                params = StdioServerParameters(command=self.command["command"], args=self.command["args"], env=env)
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await asyncio.wait_for(session.initialize(), 20)
                        catalog = await session.list_tools()
                        self.tools = [{"name": t.name, "description": t.description or "",
                                       "parameters": t.inputSchema} for t in catalog.tools]
                        self.state = "ready"
                        self._ready.set()
                        last_ping = self._loop.time()
                        while not self._stop.is_set():
                            try:
                                name, args, future = await asyncio.wait_for(self._queue.get(), 0.5)
                            except asyncio.TimeoutError:
                                if self._loop.time() - last_ping >= 5:
                                    await asyncio.wait_for(session.send_ping(), 5)
                                    last_ping = self._loop.time()
                                continue
                            if future.cancelled():
                                continue
                            try:
                                result = await asyncio.wait_for(session.call_tool(name, args), 180)
                                value = unpack(result)
                                if not future.done():
                                    future.set_result(value)
                            except Exception as e:
                                if not future.done():
                                    future.set_exception(e)
                                # Protocol/timeout failures need a fresh session; tool errors do not.
                                if not isinstance(e, ValueError):
                                    raise
            except Exception:
                self.state = "reconnecting"
                self.error = "Reconectando o serviço local automaticamente."
            finally:
                self._ready.clear()
            if not self._stop.is_set():
                await asyncio.sleep(1)
        self.state = "stopped"

    def call(self, name, args=None, timeout=190):
        self.start()
        if not self._ready.wait(22):
            raise ValueError("A conexão MCP está sendo preparada. Tente novamente em alguns segundos.")
        if name not in {t["name"] for t in self.tools}:
            raise ValueError("Ferramenta MCP desconhecida: %s" % name)
        future = concurrent.futures.Future()
        self._loop.call_soon_threadsafe(self._queue.put_nowait, (name, args or {}, future))
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise ValueError("A operação demorou demais. Verifique o Live antes de repetir.") from None

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
