"""Pool the ear reports of a genre's references into principles (what they share and why
it works) and store them in the genre profile under "ear".

    build_principles.py "deep house"      (after listen_folder.py on the references)
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import knowledge, references  # noqa: E402
from ableton_claude.ear import why  # noqa: E402

genre = sys.argv[1]
prof = knowledge.load_profile(genre)
names = {t["file"] for t in prof.get("tracks", [])}
reports = [r for r in why.load_reports() if not names or r["file"] in names]
P = why.principles(reports)
prof["ear"] = references.analysis._plain(P)
references.save_profile(prof, knowledge.profile_path(genre))
print("principles from %d references" % len(reports))
for line in P["why"]:
    print(" -", line)
print(json.dumps({k: P[k] for k in ("bpm", "minor_share", "main_break_bars", "break_keeps", "hat_swing_pct")}, indent=1))
print("drums:", {k: v["typical"] for k, v in P["drums"].items()})
print("bass rhythms:", P["bass"]["rhythms"][:5])
print("harmony:", P["harmony"])
