"""Build a genre profile from a folder of reference tracks.

    build_profile.py "/path/to/2026 Tracks/Deep House" "deep house"

Writes knowledge/genres/<genre>.profile.json. Per-track analyses are cached in
knowledge/cache.json (keyed by file content) and saved after every track, so a re-run
resumes where the last one stopped and overlapping folders are not analysed twice.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import knowledge, references  # noqa: E402

folder, genre = sys.argv[1], sys.argv[2]
cache_path = os.path.normpath(os.path.join(knowledge.KNOWLEDGE_DIR, "..", "cache.json"))
os.makedirs(knowledge.KNOWLEDGE_DIR, exist_ok=True)
cache = {}
if os.path.exists(cache_path):
    try:
        cache = json.load(open(cache_path))
    except ValueError:
        os.replace(cache_path, cache_path + ".broken")
        print("cache was unreadable; moved to cache.json.broken", flush=True)


def save(c):
    tmp = cache_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(c, f)
    os.replace(tmp, cache_path)


profile, cache = references.build_profile(folder, genre, cache=cache, on_track=save,
                                          log=lambda m: print(m, flush=True))
save(cache)
references.save_profile(profile, knowledge.profile_path(genre))
print("profile:", knowledge.profile_path(genre), "(%d tracks)" % profile["n_tracks"], flush=True)
