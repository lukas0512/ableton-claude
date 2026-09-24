"""Tension and release of a render against a genre's references.

    tension_report.py RENDER.json|AUDIO [genre] [--json OUT.json]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import knowledge, references, tension  # noqa: E402


def main(src, genre="deep house", out=None):
    bpm = None
    if src.endswith(".json"):
        d = json.load(open(src))
        src, bpm = d["file"], d.get("render", {}).get("tempo")
    a = references.analyze_reference(src, bpm=bpm)
    ours = tension.for_track(a["bars_matrix"], a["segments"])
    rows = tension.compare(ours or {}, knowledge.load_profile(genre).get("tension", {}))
    print("break bars %s, drop at bar %s" % (ours and ours["break_bars"], ours and ours["drop_bar"]))
    for k, r in rows.items():
        mark = "" if r["verdict"] == "ok" else r["verdict"].upper()
        print("%-24s %8.2f   refs %7.2f .. %-7.2f (median %6.2f)  %s" % (k, r["ours"], r["p25"], r["p75"], r["median"], mark))
    if out:
        json.dump({"file": src, "tension": ours, "compare": rows, "segments": a["segments"],
                   "bars_matrix": a["bars_matrix"]}, open(out, "w"), indent=1)


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[args.index("--json") + 1] if "--json" in args else None
    pos = [x for i, x in enumerate(args) if x != "--json" and (i == 0 or args[i - 1] != "--json")]
    main(pos[0], pos[1] if len(pos) > 1 else "deep house", out)
