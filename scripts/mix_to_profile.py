"""Bring a mix toward a genre profile: broad master EQ moves and limiter drive.

    mix_to_profile.py RENDER.wav "deep house" [--apply] [--ceiling -1.5]

Without --apply it only reports. See mixing.toward_profile for what --apply changes.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import mixing  # noqa: E402

a = sys.argv[1:]
ceil = float(a[a.index("--ceiling") + 1]) if "--ceiling" in a else -1.5
print(json.dumps(mixing.toward_profile(a[0], a[1], apply="--apply" in a, ceiling=ceil),
                 indent=1))
