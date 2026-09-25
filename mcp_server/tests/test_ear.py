"""The ear on synthetic music whose answers are known (no models needed)."""
import os
import re

import numpy as np
import pytest
from scipy import signal

from ableton_claude.ear import bass, drums, grid, groove_file, harmony, midi

SR = 44100
BPM = 123.0
P = 60.0 / BPM


def _grid(bars):
    return {"bpm": BPM, "period": P, "first_downbeat": 0.0, "n_bars": bars, "fit_ms": 0.0}


def test_grid_fit_survives_frame_quantized_and_half_beat_detections():
    rng = np.random.default_rng(0)
    t0, n = 0.35, 700
    beats = t0 + P * np.arange(n) + rng.normal(0, 0.004, n)
    beats = np.round(beats / 0.02) * 0.02                          # Beat This: 20 ms frames
    extra = t0 + P * (np.arange(300, 340) + 0.5)                   # half-beat detections in a break
    missing = np.ones(n, bool)
    missing[500:520] = False
    b = np.sort(np.concatenate([beats[missing], extra]))
    downbeats = beats[::4][:150]
    g = grid.fit(b, downbeats, duration_s=t0 + P * n)
    assert abs(g["bpm"] - BPM) < 0.02
    assert abs(g["first_downbeat"] - t0) < 0.01
    assert g["fit_ms"] < 10


def _drum_stem(bars=16, swing=0.60):
    rng = np.random.default_rng(1)
    y = np.zeros(int(bars * 4 * P * SR) + SR)
    tk = np.arange(int(0.25 * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(55 * (1 + 2 * np.exp(-tk / 0.01))) / SR) * np.exp(-tk / 0.08)
    sos_c = signal.butter(4, [1000, 4000], "bandpass", fs=SR, output="sos")
    tc = np.arange(int(0.12 * SR)) / SR
    clap = signal.sosfilt(sos_c, rng.standard_normal(len(tc))) * np.exp(-tc / 0.03) * 1.5
    sos_h = signal.butter(4, [8000, 13000], "bandpass", fs=SR, output="sos")
    th = np.arange(int(0.04 * SR)) / SR
    for b in range(bars):
        for k in range(16):
            t = (b * 16 + k) * P / 4 + ((swing - 0.5) * P / 2 if k % 2 else 0.0)
            i = int(t * SR)
            if k % 4 == 0:
                y[i:i + len(kick)] += kick
            if k in (4, 12):
                y[i:i + len(clap)] += clap
            hat = signal.sosfilt(sos_h, rng.standard_normal(len(th))) * np.exp(-th / 0.008)
            y[i:i + len(hat)] += hat * (0.4 if k % 2 == 0 else 0.15)
    return np.stack([y, y], axis=1) * 0.5


def test_drums_hear_four_on_the_floor_backbeat_and_swing():
    g = _grid(16)
    d = drums.transcribe(_drum_stem(), SR, g)
    typical = drums.section_patterns(d, list(range(1, 15)))
    assert [i for i, c in enumerate(typical["kick"]["pattern"]) if c != "."] == [0, 4, 8, 12]
    assert "backbeat on 2 and 4" in drums.describe_pattern(typical["clap"]["pattern"])
    assert typical["hats"]["pattern"].count(".") == 0                  # 16ths
    assert d["hats"]["swing_pct"] == pytest.approx(60, abs=2.5)
    assert abs(d["kick"]["template"][0]["offset_ms"]) < 5


def _bass_stem(bars=8):
    y = np.zeros(int(bars * 4 * P * SR) + SR)
    plan = [(2, 31, 0.9), (6, 31, 0.9), (10, 31, 0.9), (14, 38, 0.9)]     # G1, G1, G1, D2 on the "&"s
    for b in range(bars):
        for step, m, dur in plan:
            t0 = (b * 16 + step) * P / 4
            n = int(dur * P / 4 * 2 * SR)
            t = np.arange(n) / SR
            f0 = 440 * 2 ** ((m - 69) / 12)
            tone = sum(np.sin(2 * np.pi * h * f0 * t) / h ** 1.5 for h in range(1, 6))
            env = np.minimum(1, t / 0.004) * np.exp(-t / 0.3)
            i = int(t0 * SR)
            y[i:i + n] += tone * env * 0.4
    return np.stack([y, y], axis=1)


def test_bass_hears_notes_steps_and_no_octave_errors():
    g = _grid(8)
    b = bass.transcribe(_bass_stem(), SR, g)
    notes = [n for n in b["notes"] if 0 < n["bar"] < 7]
    assert {n["pitch"] for n in notes} == {31, 38}
    assert sorted({n["step"] for n in notes}) == [2, 6, 10, 14]
    assert b["offbeat_share"] == 1.0


def _chord_stem(chords, bars_each=2):
    y = np.zeros(int(len(chords) * bars_each * 4 * P * SR) + SR)
    for k, (root, iv) in enumerate(chords):
        a = int(k * bars_each * 4 * P * SR)
        n = int(bars_each * 4 * P * SR)
        t = np.arange(n) / SR
        for i in iv:
            m = 60 + (root + i) % 12 - (12 if (root + i) % 12 > 7 else 0)
            f0 = 440 * 2 ** ((m - 69) / 12)
            y[a:a + n] += sum(np.sin(2 * np.pi * h * f0 * t) / h for h in range(1, 4)) * 0.1
    return np.stack([y, y], axis=1)


def test_harmony_reads_a_minor_progression_and_its_key():
    prog = [(7, [0, 3, 7, 10]), (10, [0, 4, 7, 11]), (5, [0, 4, 7, 2]), (0, [0, 5, 7, 10])] * 2
    g = _grid(len(prog) * 2)
    h = harmony.analyze(_chord_stem(prog), SR, g)
    roots = [s.split()[0] for s in h["bars"][::2]]
    want = ["G", "Bb", "F", "C"] * 2
    hits = sum(r.startswith(w) and (len(w) == 2 or len(r) == 1 or r[1] not in "b#") for r, w in zip(roots, want))
    assert hits >= 6, roots
    # without a bass these notes (G A Bb C D F) fit four keys equally
    assert h["key"] in ("G minor", "Bb major", "D minor", "F major")


def test_key_follows_the_bass_that_stays_on_the_tonic():
    segs = [{"root": 7, "quality": "m7", "beats": 8}, {"root": 10, "quality": "maj7", "beats": 8},
            {"root": 5, "quality": "add9", "beats": 8}, {"root": 0, "quality": "7sus4", "beats": 8}]
    bass_line = [{"pitch": 31, "dur_steps": 12.0}] * 6 + [{"pitch": 38, "dur_steps": 4.0}] * 2
    tonic, mode, conf = harmony.key_of(segs, bass_line)
    assert (harmony.NAMES[tonic], mode) == ("G", "minor")


def test_midi_round_trip(tmp_path):
    notes = [[31, 0.5, 0.4, 100], [38, 3.5, 0.4, 90]]
    p = midi.write(str(tmp_path / "a.mid"), [("bass", 1, notes)], BPM)
    back = dict(midi.read_notes(p))["bass"]
    assert [[n[0], round(n[1], 3), round(n[2], 3), n[3]] for n in back] == notes


def test_groove_file_places_offbeats_late(tmp_path):
    if not os.path.exists(groove_file.CORE_GROOVE):
        pytest.skip("Live's core library is not installed here")
    tmpl = [{"step": s, "offset_ms": (20.0 if s % 2 else 0.0), "accent_db": (-12.0 if s % 2 else 0.0)} for s in range(16)]
    path = groove_file.write("test groove", groove_file.notes_from_template(tmpl, P), out_dir=str(tmp_path))
    xml = open(path, encoding="utf-8").read()
    times = [float(t) for t in re.findall(r'MidiNoteEvent Time="([\d.]+)"', xml)]
    assert len(times) == 16
    assert times[1] == pytest.approx(0.25 + 0.020 / P, abs=1e-4)
    assert "<SourceContext>" not in xml and '<Name Value="test groove" />' in xml


def test_sample_names_give_role_key_and_tempo():
    from ableton_claude import library as L
    assert L._key("Stab_Gm_124") == (7, "minor")
    assert L._key("DH_Chord_F#min_122bpm") == (6, "minor")
    assert L._key("EbMaj Pad") == (3, "major")
    assert L._key("Loop A 120") == (None, None)            # a lone letter is not a key
    assert L._bpm("DH_Chord_F#min_122bpm") == 122
    c = L.classify("/packs/Deep House/One Shots/Kicks/DH_Kick_03.wav", dur_s=0.6)
    assert c["role"] == "kick" and not c["loop"]
    c = L.classify("/packs/Deep House Drum Loops/Kick Loops/Kick_Loop_124.wav", dur_s=7.7)
    assert c["role"] == "kick" and c["loop"] and c["bpm"] == 124


def test_library_search_keeps_tonal_material_in_key():
    from ableton_claude import library as L
    idx = {"items": [
        {"path": "/p/Stab_Gm.wav", **L.classify("/p/Stab_Gm.wav", 1.0)},
        {"path": "/p/Stab_Bb.wav", **L.classify("/p/Stab_Bbmaj.wav", 1.0)},
        {"path": "/p/Stab_E.wav", **L.classify("/p/Stab_Emaj.wav", 1.0)},
        {"path": "/p/Stab_Dm.wav", **L.classify("/p/Stab_Dm.wav", 1.0)}]}
    got = [r["path"] for r in L.search(role="chord", key_pc=7, mode="minor", idx=idx)]
    assert got[0] == "/p/Stab_Gm.wav" and "/p/Stab_Bb.wav" in got and "/p/Stab_E.wav" not in got
