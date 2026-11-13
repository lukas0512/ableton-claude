"""--http with ABLETON_MCP_TOKEN: served at /<token>/mcp and reachable through a tunnel Host."""
import pytest

from ableton_claude import server


@pytest.fixture(autouse=True)
def _restore():
    s = server.mcp.settings
    saved = (s.port, s.streamable_http_path, s.transport_security)
    yield
    s.port, s.streamable_http_path, s.transport_security = saved


def test_token_moves_path_and_drops_localhost_host_check():
    token = "a" * 16 + "B9_-" + "c" * 12
    assert server.configure_http({"ABLETON_MCP_TOKEN": token, "ABLETON_MCP_PORT": "8123"}) \
        == "/%s/mcp" % token
    assert server.mcp.settings.port == 8123
    assert server.mcp.settings.transport_security.enable_dns_rebinding_protection is False


def test_without_token_keeps_localhost_defaults():
    assert server.configure_http({}) == "/mcp"
    assert server.mcp.settings.transport_security.enable_dns_rebinding_protection is True


@pytest.mark.parametrize("bad", ["short", "x" * 30 + "/../"])
def test_weak_or_odd_tokens_are_refused(bad):
    with pytest.raises(SystemExit):
        server.configure_http({"ABLETON_MCP_TOKEN": bad})
