"""Everything we measure about a render, against a genre's references, in one report.

    validate_render.py RENDER.json|AUDIO [genre] [--json OUT.json]

Structure, loudness and bands, groove/harmony/timbre fingerprint, element timbre and
tension/release, each against the references' middle half (ableton_claude.validate).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import validate  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[args.index("--json") + 1] if "--json" in args else None
    pos = [x for i, x in enumerate(args) if x != "--json" and (i == 0 or args[i - 1] != "--json")]
    validate.report(pos[0], pos[1] if len(pos) > 1 else "deep house", out)
