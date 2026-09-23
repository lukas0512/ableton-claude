"""Add groove/harmony/timbre/width/movement fingerprints to a genre's cached references,
and store their distribution in the genre profile.

    build_fingerprints.py "/path/to/2026 Tracks/Deep House" "deep house"
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import knowledge, references  # noqa: E402

folder, genre = sys.argv[1], sys.argv[2]
cache_path = os.path.normpath(os.path.join(knowledge.KNOWLEDGE_DIR, "..", "cache.json"))
cache = json.load(open(cache_path))


def save(c):
    tmp = cache_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(c, f)
    os.replace(tmp, cache_path)


refs = references.build_fingerprints(folder, cache, log=lambda m: print(m, flush=True),
                                     on_track=save)
save(cache)
prof = knowledge.load_profile(genre)
keys = sorted({k for r in refs for k in (r.get("fingerprint") or {})})
prof["fingerprint"] = {}
for k in keys:
    vals = [r["fingerprint"][k] for r in refs if r.get("fingerprint") and r["fingerprint"].get(k) is not None]
    if vals:
        v = np.array(vals, float)
        prof["fingerprint"][k] = {"median": round(float(np.median(v)), 3),
                                  "p25": round(float(np.percentile(v, 25)), 3),
                                  "p75": round(float(np.percentile(v, 75)), 3), "n": len(vals)}
references.save_profile(prof, knowledge.profile_path(genre))
print("fingerprints: %d references, %d measures" % (len(refs), len(keys)), flush=True)
