#!/usr/bin/env python3
"""Exercise one-pass taps against a running Live, on a scratch set only (docs/one-pass-crash.md).

Each loop makes a burst of structural changes (create, rename, delete, optional bridge reload)
and then taps two tracks through solo_pass.render_taps, the path solo_levels(one_pass=True) uses.

    cd mcp_server && uv run python ../scripts/smoke_taps.py --loops 20
"""
import argparse
import sys
import time

from ableton_claude import client, solo_pass

MAX_SCRATCH_TRACKS = 6      # a new Live set has 4; a producer's set has far more


def call(cmd, args=None):
    return client.call(cmd, args or {})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--loops", type=int, default=20)
    ap.add_argument("--reload", action="store_true", help="send a bridge reload in every burst")
    a = ap.parse_args()

    song = call("get_song")
    if len(song["tracks"]) > MAX_SCRATCH_TRACKS:
        sys.exit("refusing: %d tracks looks like a real set. Open a new empty Live set first."
                 % len(song["tracks"]))
    if call("record_status").get("state") in ("recording", "finalizing"):
        sys.exit("refusing: a render is running.")

    print("bridge", call("ping"))
    for name in ("smoke A", "smoke B"):
        call("create_track", {"kind": "audio", "name": name})
    try:
        for i in range(a.loops):
            call("create_track", {"kind": "audio", "name": "burst"})
            call("set_track", {"track": "burst", "name": "burst renamed"})
            call("delete_track", {"track": "burst renamed"})
            if a.reload:
                call("reload")
            t0 = time.time()
            files = solo_pass.render_taps(call, ["smoke A", "smoke B"], 1, 2, timeout_s=30)
            print("loop %d/%d ok in %.1f s: %s" % (i + 1, a.loops, time.time() - t0, sorted(files)))
    finally:
        for name in ("smoke A", "smoke B"):
            call("delete_track", {"track": name})
    print("done: Live survived %d loops" % a.loops)


if __name__ == "__main__":
    main()
