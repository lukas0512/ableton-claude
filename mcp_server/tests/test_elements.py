import numpy as np
import soundfile as sf

from ableton_claude import elements as el
from ableton_claude.ear import separate, tagging


def test_every_role_label_is_an_audioset_class():
    names = set(tagging.labels())
    assert len(names) == 527
    missing = [l for _, labs in tagging.ROLES for l in labs if l not in names]
    assert missing == []
    assert "Scratching (performance technique)" in names


def test_roles_of_a_window():
    names = tagging.labels()
    p = np.zeros(527, dtype=np.float32)
    p[names.index("Scratching (performance technique)")] = 0.6
    p[names.index("Speech")] = 0.3
    p[names.index("Organ")] = 0.05
    assert tagging.roles_of(p, names) == {"scratch": 0.6, "rap_or_speech": 0.3}


def test_stem_names_from_separator_files():
    names = separate.MODELS["drums"][1]
    assert separate._stem_of("city_(Kick)_MDX23C-DrumSep.wav", names) == "kick"
    assert separate._stem_of("city_(hh)_MDX23C-DrumSep.wav", names) == "hats"
    names = separate.MODELS["dereverb"][1]
    assert separate._stem_of("v_(noreverb)_x.wav", names) == "dry"
    assert separate._stem_of("v_(reverb)_x.wav", names) == "reverb"


def test_parts_replace_their_parents():
    files = {"vocals": "v", "drums": "d", "bass": "b", "other": "o", "kick": "k", "snare": "s",
             "lead_vocal": "l", "backing_vocal": "bv", "_seconds": {}}
    assert el.elements_of(files) == ["kick", "snare", "bass", "other", "lead_vocal",
                                     "backing_vocal"]
    assert el.elements_of({"vocals": "v", "bass": "b"}) == ["bass", "vocals"]


class FakeLive:
    def __init__(self):
        self.tracks = [{"name": "LOOP MURDER", "clips": []}]
        self.calls = []

    def __call__(self, cmd, args=None):
        args = args or {}
        self.calls.append((cmd, args))
        if cmd == "create_track":
            self.tracks.insert(args["index"], {"name": args["name"], "clips": []})
            return {"i": args["index"], "name": args["name"]}
        if cmd == "create_audio_clip":
            self.tracks[args["track"]]["clips"].append(
                {"start": args["beat"], "end": args["beat"] + 64.0, "file": args["path"]})
            return {}
        if cmd == "set_clip" and "muted" not in args:
            t = self.tracks[args["track"]]
            return dict(next(c for c in t["clips"] if c["start"] == args["clip"]["at"]))
        if cmd == "trim_clip":
            t = self.tracks[args["track"]]
            c = next(c for c in t["clips"] if c["start"] == args["clip"]["at"])
            assert not [o for o in t["clips"] if o["start"] > c["start"]], "trim before a later clip"
            c["end"] = args["end_beat"]
            return {}
        return {}


def test_place_puts_each_element_under_the_source_in_time_order():
    live = FakeLive()
    clip = {"warping": True, "warp_mode": 4, "pitch": 0, "detune": -10.0, "gain_db": 0.0,
            "looping": False, "loop_start": 0.0, "loop_end": 8.0, "start_marker": 0.0,
            "end_marker": 8.0, "markers": [{"beat": 0.0, "sample_s": 0.0},
                                           {"beat": 8.0, "sample_s": 3.9}]}
    by_file = {"/a.wav": [dict(clip, start=32.0, end=40.0, i=1)],
               "/b.wav": [dict(clip, start=0.0, end=8.0, i=0)]}
    res = {"/a.wav": {"elements": {"kick": {"file": "/a k.wav", "silent": False},
                                   "hats": {"file": "/a h.wav", "silent": True}}},
           "/b.wav": {"elements": {"kick": {"file": "/b k.wav", "silent": False}}}}
    info = {"name": "LOOP MURDER", "vol_db": -6.0, "pan": 0.0}
    batches = []

    def batch(cmds):
        batches.append(len(cmds))
        return [{"ok": True, "result": live(c["cmd"], c["args"])} for c in cmds]
    out = el.place(live, batch, "LOOP MURDER", 0, info, by_file, res)
    assert batches == [3, 1, 3, 1, 2]      # each clip, its trim, then the source mutes
    assert out == {"tracks": ["KICK - LOOP MURDER"], "problems": []}
    kick = live.tracks[1]
    assert [(c["start"], c["end"], c["file"]) for c in kick["clips"]] == \
        [(0.0, 8.0, "/b k.wav"), (32.0, 40.0, "/a k.wav")]
    wm = [a for c, a in live.calls if c == "set_warp_markers"]
    assert wm[0]["markers"] == [[0.0, 0.0], [8.0, 3.9]]
    mutes = [a for c, a in live.calls if c == "set_clip" and a.get("muted")]
    assert sorted(a["clip"]["at"] for a in mutes) == [0.0, 32.0]
    vol = [a for c, a in live.calls if c == "set_track"]
    assert vol[0]["volume_db"] == -6.0


def test_analyze_reuses_its_report(tmp_path, monkeypatch):
    src = tmp_path / "loop.wav"
    sf.write(src, np.zeros((4410, 2), dtype=np.float32), 44100)
    calls = []

    def fake_split(path, out_dir, **kw):
        calls.append(path)
        out = {}
        for n, amp in (("kick", 0.3), ("hats", 0.0), ("bass", 0.2), ("drums", 0.3)):
            p = tmp_path / ("%s.wav" % n)
            sf.write(p, np.full((4410, 2), amp, dtype=np.float32), 44100)
            out[n] = str(p)
        out["_seconds"] = {"stems": 1.0}
        return out
    monkeypatch.setattr(separate, "split", fake_split)
    r = el.analyze(src, tmp_path / "out", tag=False)
    assert list(r["elements"]) == ["kick", "hats", "bass"]
    assert r["elements"]["hats"]["silent"] and not r["elements"]["kick"]["silent"]
    assert el.analyze(src, tmp_path / "out", tag=False)["cached"] and len(calls) == 1
    assert any("KICK" in line for line in el.summary(r))


def test_taste_counts_kept_and_reverted_moves(tmp_path, monkeypatch):
    from ableton_claude import journal
    path = tmp_path / "journal.jsonl"
    monkeypatch.setattr(journal, "PATH", str(path))
    monkeypatch.setattr(journal, "_records", [])
    eq = {"track": "HATS", "device": "EQ Eight", "param": "4 Gain A"}
    for v in (0.6, 0.7, 0.8):
        journal.record("set_param", dict(eq, value=v), {"value": v}, {"value": 0.5})
    journal.record("set_track", {"track": "HATS", "volume_db": -12}, {"name": "HATS"},
                   {"volume_raw": 0.7})
    for _ in range(3):
        journal.record("set_track", {"track": "BASS", "volume_db": -3}, {"name": "BASS"},
                       {"volume_raw": 0.8})
    for rec in journal.find([1, 2]):
        journal.mark_reverted(rec)
    t = {f["family"]: f for f in journal.taste(min_changes=3)}
    assert t["EQ Eight: 4 Gain A up"] == {"family": "EQ Eight: 4 Gain A up", "changes": 3,
                                          "reverted": 2, "kept_pct": 33}
    assert t["level"]["changes"] == 4 and t["level"]["reverted"] == 0
    assert list(t)[0] == "EQ Eight: 4 Gain A up"      # most undone first
