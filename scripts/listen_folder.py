"""Listen to every track in a folder (cached per file): stems, grid, drums, bass, chords,
arrangement and mix balance, as ear reports in knowledge/ear/<id>/report.json.

    listen_folder.py FOLDER
"""
import glob
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import references  # noqa: E402
from ableton_claude.ear import listen  # noqa: E402

folder = sys.argv[1]
files = sorted(p for p in glob.glob(os.path.join(folder, "**", "*"), recursive=True)
               if p.lower().endswith(references.AUDIO_EXT))
for i, p in enumerate(files, 1):
    t = time.time()
    try:
        rep = listen.listen(p)
        print("%2d/%d %-50s %5.1fs  %s BPM %s" % (i, len(files), os.path.basename(p)[:50], time.time() - t,
                                                rep["grid"]["bpm"], rep["key"]), flush=True)
    except Exception as e:  # keep going; report what failed
        print("%2d/%d %-50s FAILED %s" % (i, len(files), os.path.basename(p)[:50], e), flush=True)
