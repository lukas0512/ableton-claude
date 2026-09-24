"""Store the tension/release distribution of a genre's cached references in its profile.
Needs no audio: it reads the per-bar matrices build_profile.py cached.

    build_tension.py "deep house"
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import knowledge, references, tension  # noqa: E402

genre = sys.argv[1]
cache = json.load(open(os.path.normpath(os.path.join(knowledge.KNOWLEDGE_DIR, "..", "cache.json"))))
prof = knowledge.load_profile(genre)
names = {t["file"] for t in prof.get("tracks", [])}
refs = [r for r in cache.values() if not names or r["file"] in names]
prof["tension"] = tension.profile_stats(refs)
references.save_profile(prof, knowledge.profile_path(genre))
print("tension: %d references" % len(refs))
for k, v in prof["tension"].items():
    print("  %-22s median %7s   middle half %7s .. %-7s (n=%d)" % (k, v["median"], v["p25"], v["p75"], v["n"]))
