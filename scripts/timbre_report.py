"""Element timbre of a render against a genre's references.

    timbre_report.py RENDER.json|AUDIO [genre] [--json OUT.json]

Segments and the beat grid come from the same analysis the references went through, so
both sides are measured in the same windows.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import knowledge, references, timbre  # noqa: E402


def main(src, genre="deep house", out=None):
    bpm = None
    if src.endswith(".json"):
        d = json.load(open(src))
        src, bpm = d["file"], d.get("render", {}).get("tempo")
    a = references.analyze_reference(src, bpm=bpm)
    ours = timbre.timbre_file(src, a["bpm"], a["first_beat_s"], a["segments"], a["bars_matrix"])
    prof = knowledge.load_profile(genre).get("timbre", {})
    rows = timbre.compare(ours, prof)
    print("%-20s %9s   %9s  %9s..%-9s  %s" % ("element", "ours", "median", "p25", "p75", ""))
    for k, r in rows.items():
        mark = "" if r["verdict"] == "ok" else r["verdict"].upper()
        print("%-20s %9s   %9s  %9s..%-9s  %-4s %s" % (k, r["ours"], r["median"], r["p25"], r["p75"],
                                                   mark, r["what"]))
    if out:
        json.dump({"file": src, "timbre": ours, "compare": rows,
                   "segments": a["segments"]}, open(out, "w"), indent=1)


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[args.index("--json") + 1] if "--json" in args else None
    pos = [x for i, x in enumerate(args) if x != "--json" and (i == 0 or args[i - 1] != "--json")]
    main(pos[0], pos[1] if len(pos) > 1 else "deep house", out)
