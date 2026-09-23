"""Export Club Mix, Radio Edit and Dub Mix MP3s from rendered masters.

    export_versions.py CLUB_RENDER.json DUB_RENDER.json OUT_DIR

The Radio Edit is cut from the club render on the bar grid: groove, call and dialogue
(17-65), the heart of the breakdown with the bells (105-121), the build (121-129), the
whole drop (129-161) and the drums-only ending (177-185) fading over its last 4 bars.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import export, references  # noqa: E402

BPM = 123.0
RADIO = [(17, 65), (105, 121), (121, 129), (129, 161), (177, 185)]
TAGS = {"album": "Drums Groove", "genre": "Deep House", "comment": "123 BPM, G minor"}


def main(club_json, dub_json, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    club = json.load(open(club_json))["file"]
    dub = json.load(open(dub_json))["file"] if dub_json != "-" else None
    x, sr = references.load_audio(club)
    beat = int(60.0 / BPM * sr)
    fade = np.linspace(1, 0, beat, dtype=np.float32)[:, None] ** 2
    results = []

    club_x = x.copy()
    club_x[-beat:] *= fade
    results.append(export.encode_mp3(club_x, sr, os.path.join(out_dir, "Drums Groove (Club Mix).mp3"),
                                     tags=dict(TAGS, title="Drums Groove (Club Mix)")))
    radio = export.edit(x, sr, BPM, RADIO, fade_out_bars=4)
    results.append(export.encode_mp3(radio, sr, os.path.join(out_dir, "Drums Groove (Radio Edit).mp3"),
                                     tags=dict(TAGS, title="Drums Groove (Radio Edit)")))
    if dub:
        d, dsr = references.load_audio(dub)
        d[-beat:] *= fade
        results.append(export.encode_mp3(d, dsr, os.path.join(out_dir, "Drums Groove (Dub Mix).mp3"),
                                         tags=dict(TAGS, title="Drums Groove (Dub Mix)")))
    for r in results:
        print("%-38s %5.1f s  %6.1f LUFS  TP %+.2f dBTP  gain %+.2f dB" % (
            os.path.basename(r["file"]), r["duration_s"], r["integrated_lufs"],
            r["true_peak_dbtp"], r["gain_applied_db"]), flush=True)
    json.dump(results, open(os.path.join(out_dir, "exports.json"), "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:4])
