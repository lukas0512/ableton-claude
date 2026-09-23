"""Smoke test against a running Live with ClaudeBridge loaded.

Runs on an empty Set, or on any Set with --force: it creates its own tracks, a cue on
bar 3, clips, and renders bars 1-3, then deletes everything it created.

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
tempo0 = song["tempo"] if song else 120.0
busy = n0 and any(t["clips"] for t in song["tracks"])
if busy and "--force" not in sys.argv:
    print("\nThe open Set has clips on its tracks. Open an empty Live Set, or pass --force "
          "(everything the test creates is deleted afterwards).")
    sys.exit(2)
step("set_tempo round-trip")(lambda: client.call("set_tempo", {"bpm": tempo0 + 1}))


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

def _env_clip():
    r = client.call("create_midi_clip", {
        "track": "CB MIDI", "bar": 5, "length": 8, "notes": notes, "name": "with fade-in",
        "envelopes": [{"param": "volume", "unit": "db", "points": [[0, -30], [8, 0]]}]})
    assert r["method"] == "session_dup" and r["n_envelopes"] == 1, r
    assert abs(r["start"] - 16.0) < 1e-3, r
    slots = client.call("get_track", {"track": "CB MIDI"})
    assert slots["n_clips"] == 2, slots
    return r


step("arrangement clip with envelope")(_env_clip)


def _refused():
    try:
        client.call("clip_envelope", {"track": "CB MIDI", "clip": 0, "points": [[0, 0.5]]})
    except client.BridgeError as e:
        assert "Session" in str(e), e
        return "refused with a clear message"
    raise AssertionError("clip_envelope on an Arrangement clip should be refused")


step("clip_envelope refuses Arrangement")(_refused)
step("set_cue")(lambda: client.call("set_cue", {"name": "CB Test", "bar": 3}))


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


def _preset_and_filter_env():
    client.call("create_track", {"kind": "midi", "name": "CB Pad"})
    made_tracks.append("CB Pad")
    found = client.call("browse", {"query": "analog soft pad", "roots": ["sounds"]})
    assert found, "no pad preset found"
    client.call("load_device", {"track": "CB Pad", "path": found[0]})
    client.call("load_device", {"track": "CB Pad", "path": "audio_effects/Auto Filter"})
    r = client.call("create_midi_clip", {
        "track": "CB Pad", "bar": 1, "length": 8, "notes": [[55, 0, 8, 90], [58, 0, 8, 90]],
        "envelopes": [{"device": "Auto Filter", "param": "Frequency", "unit": "display",
                       "points": [[0, 500], [8, 5000]]}]})
    assert r["n_envelopes"] == 1 and r["method"] == "session_dup", r
    return {"preset": found[0], "clip": r["name"] or "ok"}


step("preset + filter envelope in Hz")(_preset_and_filter_env)


def _fill_trim_delete():
    # a 1-bar phrase at bar 1 on CB MIDI's neighbour: reuse the Gm-Eb clip as source
    r = client.call("fill_range", {"track": "CB MIDI", "src_start_bar": 1, "src_end_bar": 3,
                                   "start_bar": 41, "end_bar": 46})
    clips = [c for c in client.call("get_track", {"track": "CB MIDI"})["clips"]
             if c["start"] >= 40 * 4 - 1e-3]
    spans = [(round(c["start"] / 4 + 1, 2), round(c["end"] / 4 + 1, 2)) for c in clips]
    assert spans == [(41.0, 43.0), (43.0, 45.0), (45.0, 46.0)], spans
    # trim the last clip: trim_clip overwrites what follows the cut, so never mid-row
    t = client.call("trim_clip", {"track": "CB MIDI", "clip": {"at": 44 * 4},
                                  "end_bar": 45.5})
    assert abs(t["end"] - 44.5 * 4) < 1e-3, t
    d = client.call("delete_clips_in_range", {"track": "CB MIDI", "start_bar": 41,
                                              "end_bar": 50})
    assert d["deleted"] == 3 and d["left_in_range"] == 0, d
    return {"fill": r, "trimmed_end_bar": t["end"] / 4 + 1}


step("fill_range + trim_clip + delete range")(_fill_trim_delete)


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
client.call("set_tempo", {"bpm": tempo0})
left = len(client.call("get_song")["tracks"])
if left != n0:
    print("cleanup: track count %d, expected %d" % (left, n0))

fails = [n for n, ok, _ in results if not ok]
print("\n%d/%d passed" % (len(results) - len(fails), len(results)))
if fails:
    print("failed:", fails)
    sys.exit(1)
