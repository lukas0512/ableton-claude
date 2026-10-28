"""Tool results as few tokens as they can be, for the model that reads them.

FastMCP turns a returned dict into JSON indented by two spaces. Measured on the Murder
set (2026-10-28): get_song 15,095 characters indented, 8,618 compact (-43 %); a track's
clip list 1,304 indented, 546 in TOON (-58 %). TOON (toon-format, MIT) writes a list of
like objects as one header and one CSV row each, which wins on clips, levels and arcs;
compact JSON wins on nested data. `render` returns the shorter of the two, with floats cut
to 4 decimals (799.9900001040626 beats -> 799.99).

No tool here declares an output schema, so the text is the whole result: the desktop app
reads it back with `parse` (JSON or TOON).
"""
import json

DECIMALS = 4


def _round(x):
    if isinstance(x, float):
        return round(x, DECIMALS)
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v) for v in x]
    return x


def _jsonable(x):
    import pydantic_core
    return pydantic_core.to_jsonable_python(x, fallback=str)


def render(result):
    data = _round(_jsonable(result))
    best = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    try:
        from toon_format import encode
        toon = encode(data)
    except Exception:       # not installed, or a shape it refuses: compact JSON
        return best
    return toon if len(toon) < len(best) else best


def parse(text):
    """The value `render` wrote (JSON or TOON); text that is neither comes back as is."""
    try:
        return json.loads(text)
    except ValueError:
        pass
    try:
        from toon_format import decode, encode
        value = decode(text)
    except Exception:
        return text
    # plain text (a brief, a message) can happen to parse as TOON: only a round trip proves
    # it was written by `render`
    return value if encode(value) == text else text


def install():
    """Make FastMCP write every non-text tool result with `render`."""
    from mcp.server.fastmcp.utilities import func_metadata as fm
    original = getattr(fm, "_convert_to_content", None)
    if original is None or getattr(original, "_compact", False):
        return False

    def convert(result):
        if result is None or isinstance(result, str):
            return original(result)
        try:
            from mcp.types import ContentBlock
            from mcp.server.fastmcp.utilities.types import Audio, Image
            if isinstance(result, (ContentBlock, Image, Audio)) or (
                    isinstance(result, (list, tuple))
                    and any(isinstance(r, (ContentBlock, Image, Audio)) for r in result)):
                return original(result)
        except ImportError:
            pass
        return original(render(result))

    convert._compact = True
    fm._convert_to_content = convert
    return True
