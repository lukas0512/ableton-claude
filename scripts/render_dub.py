"""Render a Dub Mix of the open Set: the toplines muted, the call-and-response stabs
thrown into the delay, then everything put back exactly as it was.

    render_dub.py OUT.json
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import client  # noqa: E402

C = client.call
MUTE = ["Claude Call (Bells)", "Claude Response (EP)", "29 Vox Shot Cm", "30-ny_vox124_yagota",
        "31-SAM_FELDT", "32-oss_ip1", "18 Guitar"]
DELAY_SENDS = {"20 Stab Rhytm": -11.0, "16 Synth resp": -11.0}   # send A = A-Delay

saved = {}
for tr in MUTE + list(DELAY_SENDS):
    t = C("get_track", {"track": tr, "clips": False})
    saved[tr] = {"mute": t["mute"], "send_a": t["sends_db"][0]}
try:
    for tr in MUTE:
        C("set_track", {"track": tr, "mute": True})
    for tr, db in DELAY_SENDS.items():
        C("set_send", {"track": tr, "send": 0, "db": db})
    here = os.path.dirname(__file__)
    subprocess.run([sys.executable, os.path.join(here, "render_and_analyze.py"), "1", "185",
                    sys.argv[1]], check=True)
finally:
    for tr, st in saved.items():
        C("set_track", {"track": tr, "mute": st["mute"]})
        C("set_send", {"track": tr, "send": 0, "db": st["send_a"] if st["send_a"] is not None
                       else -70})
    print("restored:", json.dumps(saved), flush=True)
