"""Measure element timbre (kick, bass, hats, clap, breakdown) on a genre's cached
references and store its distribution in the genre profile.

    build_timbre.py "/path/to/2026 Tracks/Deep House" "deep house"
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import knowledge, references, timbre  # noqa: E402

folder, genre = sys.argv[1], sys.argv[2]
cache_path = os.path.normpath(os.path.join(knowledge.KNOWLEDGE_DIR, "..", "cache.json"))
cache = json.load(open(cache_path))


def save(c):
    tmp = cache_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(c, f)
    os.replace(tmp, cache_path)


refs = timbre.build_timbre(folder, cache, log=lambda m: print(m, flush=True), on_track=save)
save(cache)
prof = knowledge.load_profile(genre)
prof["timbre"] = timbre.profile_stats(refs)
references.save_profile(prof, knowledge.profile_path(genre))
print("timbre: %d references, %d measures" % (len(refs), len(prof["timbre"])), flush=True)
for k, v in prof["timbre"].items():
    print("  %-22s median %8s   middle half %s .. %s   (n=%d)" % (k, v["median"], v["p25"], v["p75"], v["n"]))
