import json

import numpy as np
import pytest
import soundfile as sf

from ableton_claude import client, journal, server
from ableton_claude import stem_remix as sr

SR = 22050
BPM = 92.0
DOWN = 0.25


def burst(n_s, at, sr=SR, f=900.0, dur=.06, amp=.5):
    """A syllable-like tone burst (sharp attack, decay) added at `at` seconds."""
    x = np.zeros(int(n_s * sr))
    t = np.arange(int(dur * sr)) / sr
    seg = amp * np.sin(2 * np.pi * f * t) * np.exp(-t / (dur / 3))
    i = int(at * sr)
    x[i:i + len(seg)] += seg[: len(x) - i]
    return x


def stereo(x):
    return np.repeat(x[:, None], 2, axis=1).astype(np.float32)


# ---------------------------------------------------------------- the grid and markers
def test_source_sixteenths_follow_detected_beats_only_near_the_grid():
    six = sr.source_sixteenths(BPM, DOWN, 3, 2)
    period = 60 / BPM
    assert len(six) == 2 * 16 + 1
    assert six[0] == pytest.approx(DOWN + 8 * period)
    assert np.allclose(np.diff(six), period / 4)
    near = DOWN + 9 * period + .02          # beat 2 of bar 3, 20 ms late: used
    far = DOWN + 10 * period + .08          # beat 3, 80 ms off: ignored
    six = sr.source_sixteenths(BPM, DOWN, 3, 1, detected=[near, far])
    assert six[4] == pytest.approx(near)
    assert six[8] == pytest.approx(DOWN + 10 * period)
    assert six[5] == pytest.approx(near + (six[8] - near) / 4)


def _script_quantized_markers(sixteenths, file_start, onsets, swing, q=.6, preroll=.5):
    """scripts/build_from_the_streets.py before the extraction (the reference)."""
    six = np.asarray(sixteenths)
    targets = {}
    for o in onsets:
        k = int(np.argmin(np.abs(six - o)))
        if k == 0 or k == len(six) - 1:
            continue
        step = (six[min(k + 1, len(six) - 1)] - six[max(k - 1, 0)]) / 2
        dev = (o - six[k]) / step
        if abs(dev) < .35 and k not in targets:
            targets[k] = (o, dev)
    m = [[0.0, 0.0]]
    for k, t in enumerate(six):
        beat_k = preroll + k / 4 + (swing if k % 2 else 0.0)
        if k in targets:
            o, dev = targets[k]
            m.append([beat_k + (1 - q) * dev / 4, o - file_start])
        else:
            m.append([beat_k, t - file_start])
    return m


def test_onset_markers_move_syllables_part_way_onto_the_swung_16th():
    six = sr.source_sixteenths(BPM, DOWN, 1, 1)
    step = six[1] - six[0]
    a = six[0] - .5 * 60 / BPM
    swing = sr.swing_beats(11, 125)
    onsets = [six[4] + .2 * step,          # 0.2 of a 16th late: pulled 60 % in
              six[6] - .1 * step,          # early, on an off-beat: swing still applies
              six[9] + .45 * step,         # too far from any 16th: left on the grid
              six[0] + .01]                # the first 16th stays on the grid
    m = sr.onset_markers(six, a, onsets, swing)
    assert m[0] == [0.0, 0.0] and m[1] == [pytest.approx(.5), pytest.approx(six[0] - a)]
    assert m[5][0] == pytest.approx(.5 + 1 + .4 * .2 / 4)
    assert m[5][1] == pytest.approx(onsets[0] - a)
    assert m[7][0] == pytest.approx(.5 + 1.5 - .4 * .1 / 4)       # step 6: even, no swing
    assert m[10][0] == pytest.approx(.5 + 9 / 4 + swing) and m[10][1] == pytest.approx(six[9] - a)
    ref = _script_quantized_markers(six, a, onsets, swing)
    assert np.allclose(np.array(m), np.array(ref), atol=1e-5)
    beats = [b for b, _ in m]
    assert all(b1 > b0 for b0, b1 in zip(beats, beats[1:]))


def test_grid_markers_have_no_duplicate_zero():
    six = sr.source_sixteenths(BPM, DOWN, 1, 2)
    m = sr.grid_markers(six, six[0], .02)
    assert m[0] == [0.0, 0.0] and m[1][0] == pytest.approx(.25 + .02)
    assert len(m) == len(six) and m[-1][0] == pytest.approx(8.0)


def test_syllable_onsets_find_the_attacks():
    times = [.30, .62, .95, 1.31]
    x = sum(burst(1.8, t) for t in times) + 1e-4 * np.random.default_rng(0).standard_normal(int(1.8 * SR))
    ons = sr.syllable_onsets(x, SR, 0, 1.8)
    assert len(ons) == len(times)
    assert np.all(np.abs(ons - np.array(times)) < .02)


def test_filter_raw_matches_lives_auto_filter():
    assert sr.filter_raw(300) == pytest.approx(.3918)
    assert sr.filter_raw(600) - sr.filter_raw(300) == pytest.approx(.1003, abs=1e-4)


# ---------------------------------------------------------------- phrases and chops
@pytest.fixture
def vocal_stem(tmp_path):
    rng = np.random.default_rng(1)
    six = sr.source_sixteenths(BPM, DOWN, 1, 6)
    n = DOWN + 7 * 4 * 60 / BPM
    x = np.zeros(int(n * SR))
    for k in range(16, 5 * 16, 3):                      # a flow from bar 2, slightly loose
        x += burst(n, six[k] + rng.uniform(-.012, .012), f=700 + 30 * (k % 5))
    p = tmp_path / "vocals.wav"
    sf.write(p, stereo(x), SR)
    return p


def test_cut_phrase_writes_the_take_and_its_markers(vocal_stem, tmp_path):
    m = sr.cut_phrase(vocal_stem, tmp_path / "out/phrase.wav", BPM, DOWN, 2, 2, swing=.02)
    info = sf.info(m["path"])
    assert info.duration == pytest.approx((8 + .5) * 60 / BPM, abs=.002)
    assert m["beats"] == 8 and m["clip_beats"] == 8.5 and m["source_bar"] == 2
    assert m["n_syllables"] >= 8
    beats = [b for b, _ in m["markers"]]
    secs = [s for _, s in m["markers"]]
    assert beats[1] == .5 and beats[-1] == pytest.approx(8.5)
    assert all(b1 > b0 for b0, b1 in zip(beats, beats[1:]))
    assert all(s1 > s0 for s0, s1 in zip(secs, secs[1:]))
    assert secs[-1] == pytest.approx(info.duration, abs=.002)
    with pytest.raises(ValueError):
        sr.cut_phrase(vocal_stem, tmp_path / "x.wav", BPM, DOWN, 40, 2, swing=0)


def test_onset_chop_starts_at_the_attack(tmp_path):
    n = 4.0
    six = sr.source_sixteenths(BPM, DOWN, 2, 1)
    x = burst(n, six[0] + .045, amp=.6) + burst(n, six[0] + .5, amp=.2)
    p = tmp_path / "v.wav"
    sf.write(p, stereo(x), SR)
    files, lead = sr.onset_chops(p, tmp_path, BPM, DOWN, 2, lengths={"long": .5})
    assert lead == pytest.approx(.045, abs=.015)
    y, _ = sf.read(files["long"])
    first = np.argmax(np.abs(y[:, 0]) > .05 * np.abs(y).max()) / SR
    assert first < .02                                # the attack is the file's start


# ---------------------------------------------------------------- loops from the 'other' stem
def test_loop_candidates_prefer_the_typical_window_without_vocal(tmp_path):
    rng = np.random.default_rng(2)
    bar_s = 4 * 60 / BPM
    n = DOWN + 12 * bar_s
    t = np.arange(int(n * SR)) / SR
    other = .2 * np.sin(2 * np.pi * 220 * t) + .1 * np.sin(2 * np.pi * 330 * t)
    a, b = int((DOWN + 6 * bar_s) * SR), int((DOWN + 8 * bar_s) * SR)
    other[a:b] = .3 * rng.standard_normal(b - a)          # a noise fill: atypical (bars 7-8)
    vocals = np.zeros_like(other)
    v0 = int((DOWN + 0 * bar_s) * SR)
    vocals[v0:int((DOWN + 4 * bar_s) * SR)] = .2 * np.sin(2 * np.pi * 500 * t[v0:int((DOWN + 4 * bar_s) * SR)])
    rows = sr.loop_candidates(other, SR, BPM, DOWN, 2, vocals=vocals)
    best = rows[0]["bar"]
    assert best >= 5 and best not in (6, 7, 8)               # no vocal, not the fill
    assert {"bar", "vocal_db", "typical_db", "level_db", "score"} <= set(rows[0])
    m = sr.cut_loop(stereo(other), SR, tmp_path / "loop.wav", BPM, DOWN, best, 2, swing=.02)
    assert sf.info(m["path"]).duration == pytest.approx(2 * bar_s, abs=.002)
    assert m["beats"] == 8 and len(m["markers"]) == 33


def test_section_file_tiles_the_loop_and_gates_bars(tmp_path):
    bar_s = 4 * 60 / BPM
    x = stereo(.3 * np.ones(int(2 * bar_s * SR)))
    sf.write(tmp_path / "l.wav", x, SR)
    six = sr.source_sixteenths(BPM, 0.0, 1, 2)
    loop = {"path": str(tmp_path / "l.wav"), "beats": 8, "markers": sr.grid_markers(six, 0, .02)}
    path, mk = sr.section_file(loop, 8, tmp_path / "sec.wav", gate=lambda k: k % 2 == 1)
    y, _ = sf.read(path)
    assert len(y) == 4 * len(x)
    mid = lambda bar: np.abs(y[int((bar + .5) * bar_s * SR), 0])
    assert mid(0) == 0 and mid(1) > .2 and mid(2) == 0 and mid(3) > .2
    assert mk[-1][0] == pytest.approx(32.0) and len(mk) == 1 + 4 * 32
    beats = [b for b, _ in mk]
    assert all(b1 > b0 for b0, b1 in zip(beats, beats[1:]))


# ---------------------------------------------------------------- breakbeats
def _script_break_markers(x, sr_, ons, swing, bpm=120.0, q=.7):
    six = np.arange(0, 8 * 4 + 1) * 60 / bpm / 4
    targets = {}
    for o in ons:
        k = int(np.argmin(np.abs(six - o)))
        if 0 < k < len(six) - 1 and abs(o - six[k]) < .4 * (six[1] - six[0]) and k not in targets:
            targets[k] = o
    mk = [[0.0, 0.0]]
    for k, t in enumerate(six[1:], start=1):
        b = k / 4 + (swing if k % 2 else 0)
        if k in targets:
            dev = (targets[k] - t) / (six[1] - six[0]) / 4
            mk.append([b + (1 - q) * dev, targets[k]])
        else:
            mk.append([b, min(t, len(x) / sr_ - .001)])
    return mk


def test_break_loop_pulls_the_hits_into_the_pocket():
    step = .125                                          # 16ths at 120 BPM
    n = 32 * step
    hits = [k * step + (.008 if k % 2 else .004) for k in range(0, 32, 2)]
    x = stereo(sum(burst(n, h, f=2000, dur=.04) for h in hits))
    swing = sr.swing_beats(10.8, 125)
    mk, beats = sr.break_loop(x, SR, 120, swing)
    assert beats == 8.0 and len(mk) == 33 and mk[-1][0] == pytest.approx(8.0)
    ons = sr.syllable_onsets(x, SR, 0, n)
    assert np.allclose(np.array(mk), np.array(_script_break_markers(x, SR, ons, swing)), atol=1e-5)
    k = 2                                                 # the hit 4 ms late on 16th 2
    assert mk[k][0] == pytest.approx(.5 + .3 * (mk[k][1] - .25) / step / 4, abs=1e-4)
    assert sr.loop_bpm_from_name("adt_120_drum_break_smash.wav") == 120
    assert sr.loop_bpm_from_name("Shaker_Far_Away_122bpm.wav") == 122
    assert sr.loop_bpm_from_name("break.wav") is None


# ---------------------------------------------------------------- placing in Live (fake bridge)
class FakeLive:
    def __init__(self, clip_len=None, devices=()):
        self.calls, self.clip_len = [], clip_len
        self.devices = list(devices)
        self.clips = []

    def __call__(self, cmd, args=None):
        args = args or {}
        self.calls.append((cmd, args))
        if cmd == "create_audio_clip":
            self.clips.append({"start": args["beat"], "end": args["beat"] + (self.clip_len or 4)})
            return {"start": args["beat"]}
        if cmd == "get_track":
            return {"devices": [{"i": i, "name": d} for i, d in enumerate(self.devices)],
                    "clips": self.clips}
        if cmd == "load_device":
            self.devices.append("Auto Filter")
        if cmd == "get_song":
            return {"tempo": 125.0, "tracks": [], "master": {"devices": []}}
        return {}

    def cmds(self):
        return [c for c, _ in self.calls]


def test_place_warped_sets_markers_and_trims_a_clip_live_made_too_long(tmp_path):
    p = tmp_path / "a.wav"
    sf.write(p, stereo(np.zeros(SR)), SR)
    live = FakeLive(clip_len=20)
    r = sr.place_warped(live, "VOX", str(p), 63.5, 8.5, [[0, 0], [.5, .1], [8.5, 5.0]])
    assert live.cmds() == ["create_audio_clip", "set_warp_markers", "set_clip", "get_track", "trim_clip"]
    marks = live.calls[1][1]["markers"]
    assert marks[-1][1] == pytest.approx(1.0 - .001)       # clamped inside the 1 s file
    sc = live.calls[2][1]
    assert sc["warping"] and sc["warp_mode"] == "complex_pro" and sc["end_marker"] == 8.5
    assert live.calls[4][1]["end_beat"] == 72.0 and r["trimmed"]
    live = FakeLive(clip_len=8.5)
    assert not sr.place_warped(live, "VOX", str(p), 0, 8.5, [[0, 0]])["trimmed"]


def test_set_pocket_ms_reads_the_midi_parts():
    hats = [[60, k / 4 + (.0225 if k % 2 else 0), .1, 100] for k in range(32)]

    def call(cmd, args=None):
        if cmd == "get_song":
            return {"tempo": 125.0, "tracks": [{"i": 0, "kind": "midi"}, {"i": 1, "kind": "midi"},
                                               {"i": 2, "kind": "audio"}]}
        if cmd == "get_track":
            return {"clips": [{"type": "midi", "start": 0}]}
        if cmd == "get_notes":
            return hats
        raise AssertionError(cmd)
    assert sr.set_pocket_ms(call) == pytest.approx(10.8, abs=.05)


@pytest.fixture
def bridge(monkeypatch, tmp_path):
    monkeypatch.setattr(journal, "PATH", str(tmp_path / "journal.jsonl"))
    live = FakeLive(clip_len=40)
    monkeypatch.setattr(client, "call", live)
    return live


def test_place_loop_tool_tiles_filters_and_ramps(bridge, tmp_path):
    bar_s = 4 * 60 / BPM
    sf.write(tmp_path / "l.wav", stereo(.3 * np.ones(int(2 * bar_s * SR))), SR)
    six = sr.source_sixteenths(BPM, 0.0, 1, 2)
    loop = {"path": str(tmp_path / "l.wav"), "beats": 8, "markers": sr.grid_markers(six, 0, .02)}
    r = server.place_loop("LOOP CITY", loop, 33, 41, play_bars="even", filter_from_hz=400,
                          filter_to_hz=3000, ramp_db=[-12, -6], end_gap_beats=2,
                          out_dir=str(tmp_path))
    assert r["beat"] == 128 and r["beats"] == 30 and r["trimmed"]
    assert "load_device" in bridge.cmds()                   # Auto Filter was missing
    create = next(a for c, a in bridge.calls if c == "create_audio_clip")
    env = {e["param"]: e for e in create["envelopes"]}
    assert env["Frequency"]["points"][0][1] == sr.filter_raw(400)
    assert env["Frequency"]["points"][-1] == [30, sr.filter_raw(3000)]
    assert env["volume"]["points"] == [[0, -12], [30, -6]]
    assert sf.info(create["path"]).duration == pytest.approx(8 * bar_s, abs=.01)
    assert any(r["cmd"] == "create_audio_clip" for r in journal.recent(50))


def test_rap_phrase_tool_cuts_and_places_with_the_set_pocket(bridge, vocal_stem, tmp_path):
    r = server.rap_phrase(str(vocal_stem), 2, 2, source_bpm=BPM, source_downbeat=DOWN,
                          out_dir=str(tmp_path / "o"), track="VOX CITY", bar=17, name="City call")
    assert r["placed"]["beat"] == 64 - .5 and r["placed"]["beats"] == 8.5
    assert r["swing_ms"] == 0.0 and r["n_markers"] > 30 and "markers" not in r
    saved = json.loads(open(r["meta"]).read())["City call"]
    assert saved["markers"][1][0] == .5
    with pytest.raises(ValueError):
        server.rap_phrase(str(vocal_stem), 2, 2)


def test_remix_tools_are_registered():
    names = {t.name for t in server.mcp._tool_manager.list_tools()}
    assert {"rap_phrase", "onset_chop", "stem_loop", "breakbeat_loop", "place_loop",
            "solo_levels"} <= names


def test_stem_loop_onset_chop_and_breakbeat_tools(bridge, tmp_path):
    bar_s = 4 * 60 / BPM
    t = np.arange(int((DOWN + 8 * bar_s) * SR)) / SR
    other = stereo(.2 * np.sin(2 * np.pi * 220 * t))
    sf.write(tmp_path / "other.wav", other, SR)
    r = server.stem_loop(str(tmp_path / "other.wav"), bars=2, source_bpm=BPM, source_downbeat=DOWN,
                         out_dir=str(tmp_path / "o"), swing_ms=11)
    assert r["candidates"] and r["source_bar"] == r["candidates"][0]["bar"]
    assert r["beats"] == 8 and r["markers"][1][0] == pytest.approx(.25 + sr.swing_beats(11, 125), abs=1e-5)

    six = sr.source_sixteenths(BPM, DOWN, 2, 1)
    sf.write(tmp_path / "v.wav", stereo(burst(4.0, six[0] + .03)), SR)
    c = server.onset_chop(str(tmp_path / "v.wav"), 2, source_bpm=BPM, source_downbeat=DOWN,
                          out_dir=str(tmp_path / "o"), track="VOX", at_beats=[448.0])
    assert c["attack_vs_grid_s"] == pytest.approx(.03, abs=.015)
    assert c["placed"] == [round(448 - sr.CHOP_LEAD_S * 125 / 60, 4)]

    sf.write(tmp_path / "adt_120_break.wav", stereo(sum(burst(4.0, k * .25, f=2000) for k in range(16))), SR)
    b = server.breakbeat_loop(str(tmp_path / "adt_120_break.wav"), swing_ms=0, out_dir=str(tmp_path / "o"))
    assert b["loop_bpm"] == 120 and b["beats"] == 8
    assert "error" in server.breakbeat_loop(str(tmp_path / "v.wav"), swing_ms=0)
