"""Smoke test against a running Live with ClaudeBridge loaded.

Run it on an EMPTY Live Set: it creates tracks, a cue, clips, and renders 2 bars,
then deletes everything it created.

    cd mcp_server && uv run python ../scripts/smoke_live.py
"""
import glob
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from ableton_claude import analysis, client  # noqa: E402

results = []


def step(name):
    def wrap(fn):
        t0 = time.time()
        try:
            out = fn()
            results.append((name, True, out))
            print("PASS  %-34s %.2fs  %s" % (name, time.time() - t0, _short(out)))
            return out
        except Exception as e:
            results.append((name, False, e))
            print("FAIL  %-34s %s" % (name, e))
            traceback.print_exc(limit=2)
            return None
    return wrap


def _short(x, n=150):
    s = repr(x)
    return s if len(s) <= n else s[:n] + "..."


made_tracks = []

step("ping")(lambda: client.call("ping"))
song = step("get_song")(lambda: client.call("get_song"))
n0 = len(song["tracks"]) if song else 0
step("set_tempo 120")(lambda: client.call("set_tempo", {"bpm": 120}))


def _mk_midi():
    r = client.call("create_track", {"kind": "midi", "name": "CB MIDI"})
    made_tracks.append("CB MIDI")
    return r


step("create_track midi")(_mk_midi)

notes = [[43, 0, 4, 100], [50, 0, 4, 90], [55, 0, 4, 90], [58, 0, 4, 85],   # Gm
         [39, 4, 4, 100], [46, 4, 4, 90], [51, 4, 4, 90], [55, 4, 4, 85]]   # Eb
step("create_midi_clip (arrangement)")(lambda: client.call(
    "create_midi_clip", {"track": "CB MIDI", "bar": 1, "length": 8, "notes": notes,
                         "name": "Gm-Eb"}))
step("get_notes round-trip")(lambda: (
    lambda got: got if len(got) == 8 else (_ for _ in ()).throw(AssertionError(got)))(
    client.call("get_notes", {"track": "CB MIDI", "clip": 0})))

found = step("browse 'drift'")(lambda: client.call("browse", {"query": "drift", "limit": 5}))
if found:
    step("load_device")(lambda: client.call("load_device", {"track": "CB MIDI",
                                                            "path": found[0]}))
step("set_track volume -6 dB")(lambda: (
    lambda r: r if abs(r["vol_db"] + 6) < 0.3 else (_ for _ in ()).throw(AssertionError(r)))(
    client.call("set_track", {"track": "CB MIDI", "volume_db": -6})))
step("clip_envelope volume ramp")(lambda: client.call(
    "clip_envelope", {"track": "CB MIDI", "clip": 0, "param": "volume",
                      "points": [[0, 0.4], [8, 0.85]]}))
step("set_cue")(lambda: client.call("set_cue", {"name": "CB Test", "bar": 1}))


def _mk_audio():
    wav = sorted(glob.glob(os.path.expanduser(
        "~/Desktop/*/Ableton Projects/*/*/Samples/Imported/LG_riser_noise_4bar_123.wav")))
    if not wav:
        raise RuntimeError("no test wav found")
    client.call("create_track", {"kind": "audio", "name": "CB Audio"})
    made_tracks.append("CB Audio")
    return client.call("create_audio_clip", {"track": "CB Audio", "path": wav[0], "bar": 1,
                                             "name": "riser", "gain_db": -12})


step("create_audio_clip (arrangement)")(_mk_audio)
step("mute_clips_in_range")(lambda: client.call(
    "mute_clips_in_range", {"track": "CB Audio", "muted": True, "start_bar": 1, "end_bar": 5}))
step("batch x3")(lambda: client.batch([{"cmd": "ping"}, {"cmd": "get_song"},
                                       {"cmd": "ping"}]))


def _render():
    client.call("record_master", {"start_bar": 1, "end_bar": 3, "name": "CB Render"})
    made_tracks.append("CB Render")
    deadline = time.time() + 40
    st = client.call("record_status")
    while st["state"] in ("recording", "finalizing") and time.time() < deadline:
        time.sleep(0.5)
        st = client.call("record_status")
    if st["state"] != "done":
        raise RuntimeError(st)
    a = analysis.analyze(st["file"])
    return {"file": st["file"], "lufs": a["loudness"]["integrated_lufs"],
            "tp": a["loudness"]["true_peak_dbtp"], "dur": a["duration_s"]}


step("render 2 bars + analyze")(_render)

# cleanup
for name in reversed(made_tracks):
    try:
        client.call("delete_track", {"track": name})
    except Exception as e:
        print("cleanup: could not delete %s: %s" % (name, e))
try:
    client.call("delete_cue", {"name": "CB Test"})
except Exception as e:
    print("cleanup: could not delete cue: %s" % e)
left = len(client.call("get_song")["tracks"])
if left != n0:
    print("cleanup: track count %d, expected %d" % (left, n0))

fails = [n for n, ok, _ in results if not ok]
print("\n%d/%d passed" % (len(results) - len(fails), len(results)))
if fails:
    print("failed:", fails)
    sys.exit(1)
