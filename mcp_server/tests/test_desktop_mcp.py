import sys
import time

import pytest

from ableton_claude.desktop_mcp import LocalMCP


def test_local_session_recovers_after_server_exit_without_replaying_changes(tmp_path):
    script = tmp_path / 'server.py'
    script.write_text('''import os
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("reconnect-test")
@mcp.tool()
def read() -> dict:
    return {"ok": True}
@mcp.tool()
def crash() -> dict:
    os._exit(1)
mcp.run()
''')
    connection = LocalMCP({'command': sys.executable, 'args': [str(script)]}, str(tmp_path))
    try:
        assert connection.call('read') == {'ok': True}
        with pytest.raises(Exception):
            connection.call('crash', timeout=10)
        end = time.monotonic() + 10
        while connection.status()['state'] != 'ready' and time.monotonic() < end:
            time.sleep(0.05)
        assert connection.call('read') == {'ok': True}
        assert connection.status()['tools'] == 2
    finally:
        connection.stop()
    assert connection.status()['state'] == 'stopped'
