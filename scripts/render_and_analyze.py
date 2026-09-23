"""Render the master through ClaudeBridge and measure it, section by section.

Sections come from the Set's locators. Runs in real time.

    render_and_analyze.py START_BAR END_BAR OUT.json [--target club|streaming] [--keep]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import analysis, client  # noqa: E402


def main(start, end, out, target="club", keep=False):
    song = client.call("get_song")
    tempo = song["tempo"]
    cues = [c for c in song["cues"] if start <= c["bar"] < end]
    sections = []
    for i, c in enumerate(cues):
        b = cues[i + 1]["bar"] if i + 1 < len(cues) else end
        sections.append({"name": c["name"], "start_bar": c["bar"] - start + 1,
                         "end_bar": b - start + 1})
    name = "Claude Render"
    r = client.call("record_master", {"start_bar": start, "end_bar": end, "name": name})
    print("recording %.0f s ..." % r["expected_seconds"], flush=True)
    deadline = time.time() + r["expected_seconds"] + 90
    st = client.call("record_status")
    while st["state"] in ("recording", "finalizing") and time.time() < deadline:
        time.sleep(2)
        st = client.call("record_status")
    if st["state"] != "done":
        print("render failed:", st, flush=True)
        sys.exit(1)
    res = analysis.analyze(st["file"], target=target, sections=sections, tempo=tempo)
    res["render"] = {"start_bar": start, "end_bar": end, "tempo": tempo}
    with open(out, "w") as f:
        json.dump(res, f, indent=1)
    if not keep:
        client.call("delete_track", {"track": name})
    print("ok", st["file"], flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    tgt = a[a.index("--target") + 1] if "--target" in a else "club"
    main(float(a[0]), float(a[1]), a[2], target=tgt, keep="--keep" in a)
