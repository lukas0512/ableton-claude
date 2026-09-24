"""Element timbre on synthetic four-on-the-floor tracks whose answers are known."""
import numpy as np
import pytest

from ableton_claude import timbre

SR = 44100
BPM = 120.0                    # beat 0.5 s, bar 2 s
BEAT = 60.0 / BPM


def _track(bars=24, intro=8, kick_hz=55.0, kick_tau=0.09, bass="sine", bass_db=-6.0,
           clap=True, hats=True, seed=0):
    rng = np.random.default_rng(seed)
    n = int(bars * 4 * BEAT * SR)
    y = np.zeros(n)
    t_k = np.arange(int(0.45 * SR)) / SR
    # pitch drops from 3x to the body pitch in ~10 ms, then holds: the body is kick_hz
    f_inst = kick_hz * (1 + 2 * np.exp(-t_k / 0.004))
    kick = np.sin(2 * np.pi * np.cumsum(f_inst) / SR) * np.exp(-t_k / kick_tau)
    t_b = np.arange(int(0.2 * SR)) / SR
    f0 = 49.0
    if bass == "sine":
        tone = np.sin(2 * np.pi * f0 * t_b)
    else:                       # saw: every harmonic at 1/k
        tone = sum(np.sin(2 * np.pi * k * f0 * t_b) / k for k in range(1, 30))
    bass_note = tone * np.hanning(len(t_b)) * 10 ** (bass_db / 20)
    t_c = np.arange(int(0.25 * SR)) / SR
    from scipy import signal
    sos = signal.butter(4, [1000, 4000], "bandpass", fs=SR, output="sos")
    clap_hit = signal.sosfilt(sos, rng.standard_normal(len(t_c))) * np.exp(-t_c / 0.05) * 0.8
    sos_h = signal.butter(4, [7000, 12000], "bandpass", fs=SR, output="sos")
    t_h = np.arange(int(0.05 * SR)) / SR
    for b in range(bars):
        for k in range(4):
            a = int((b * 4 + k) * BEAT * SR)
            y[a:a + len(kick)] += kick[: n - a]
            if b >= intro:
                o = a + int(0.5 * BEAT * SR)
                y[o:o + len(bass_note)] += bass_note[: max(0, n - o)]
                if clap and k in (1, 3):
                    y[a:a + len(clap_hit)] += clap_hit[: n - a]
            if hats:
                for s in range(4):
                    h = a + int(s * BEAT / 4 * SR)
                    hit = signal.sosfilt(sos_h, rng.standard_normal(len(t_h))) * np.exp(-t_h / 0.012) * 0.3
                    y[h:h + len(hit)] += hit[: max(0, n - h)]
    x = np.stack([y, y], axis=1).astype(np.float32) * 0.5
    segs = [{"start": 0, "end": intro, "label": "intro"},
            {"start": intro, "end": bars, "label": "full"}]
    return x, segs


def _measure(**kw):
    x, segs = _track(**kw)
    return timbre.element_timbre(x, SR, BPM, 0.0, segs)


def test_kick_pitch_is_the_body_not_the_click():
    assert _measure(kick_hz=55.0)["kick_pitch_hz"] == pytest.approx(55.0, abs=3.0)
    assert _measure(kick_hz=72.0)["kick_pitch_hz"] == pytest.approx(72.0, abs=3.0)


def test_kick_length_follows_its_decay():
    short, long_ = _measure(kick_tau=0.04)["kick_decay_ms"], _measure(kick_tau=0.12)["kick_decay_ms"]
    assert short is not None and long_ is not None
    assert long_ > short * 2


def test_saw_bass_reads_richer_than_sine_bass():
    sine = _measure(bass="sine")["bass_harmonics_db"]
    saw = _measure(bass="saw")["bass_harmonics_db"]
    assert saw > sine + 10


def test_kick_over_bass_tracks_the_bass_level():
    quiet, loud = _measure(bass_db=-18.0)["kick_over_bass_db"], _measure(bass_db=0.0)["kick_over_bass_db"]
    assert quiet > loud + 8


def test_backbeat_clap_is_detected():
    assert _measure(clap=True)["clap_backbeat_db"] > 6
    assert abs(_measure(clap=False)["clap_backbeat_db"]) < 3


def test_compare_flags_outside_the_middle_half():
    rows = timbre.compare({"kick_pitch_hz": 80.0, "hat_decay_ms": 30.0},
                          {"kick_pitch_hz": {"median": 55, "p25": 52, "p75": 60},
                           "hat_decay_ms": {"median": 28, "p25": 20, "p75": 40}})
    assert rows["kick_pitch_hz"]["verdict"] == "high"
    assert rows["hat_decay_ms"]["verdict"] == "ok"


def test_rank_samples_prefers_the_closest_in_genre_units():
    targets = {"brightness_hz": {"median": 6400, "p25": 5800, "p75": 7300},
               "hat_decay_ms": {"median": 60, "p25": 44, "p75": 84}}
    rows = [{"name": "808 maracas", "brightness_hz": 10167, "hat_decay_ms": 2},
            {"name": "groove shaker", "brightness_hz": 6908, "hat_decay_ms": 76},
            {"name": "dark long", "brightness_hz": 4152, "hat_decay_ms": 124},
            {"name": "unmeasured", "brightness_hz": 6400, "hat_decay_ms": None}]
    ranked = timbre.rank_samples(rows, targets)
    assert [r["name"] for r in ranked] == ["groove shaker", "dark long", "808 maracas"]
    assert ranked[0]["distance"] < 1


def test_oneshot_measures_a_short_bright_tick_and_a_long_dark_hit(tmp_path):
    import soundfile as sf
    from scipy import signal
    rng = np.random.default_rng(1)
    t = np.arange(int(0.4 * SR)) / SR

    def hit(lo, hi, tau):
        sos = signal.butter(4, [lo, hi], "bandpass", fs=SR, output="sos")
        return (signal.sosfilt(sos, rng.standard_normal(len(t))) * np.exp(-t / tau) * 0.5).astype(np.float32)
    sf.write(tmp_path / "tick.wav", hit(9000, 14000, 0.002), SR)
    sf.write(tmp_path / "soft.wav", hit(5000, 8000, 0.03), SR)
    a, b = timbre.oneshot(str(tmp_path / "tick.wav")), timbre.oneshot(str(tmp_path / "soft.wav"))
    assert a["brightness_hz"] > b["brightness_hz"] + 2000
    assert b["decay_ms"] > a["decay_ms"] * 3
    rows = timbre.measure_folder(str(tmp_path), cache_path=str(tmp_path / "cache.json"))
    assert {r["name"] for r in rows} == {"tick.wav", "soft.wav"}
    prof = {"hat_brightness_hz": {"median": 6400, "p25": 5800, "p75": 7300},
            "hat_decay_ms": {"median": 60, "p25": 44, "p75": 84}}
    assert timbre.find_samples(rows, prof, "hat")[0]["name"] == "soft.wav"
