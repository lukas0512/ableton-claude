import numpy as np
import soundfile as sf

from ableton_claude import references

SR = 44100


def _bars(blocks):
    """Per-bar [lufs, kick, bass, high] from (n, lufs, kick, bass, high) blocks + noise."""
    rng = np.random.default_rng(1)
    rows = []
    for n, lu, k, b, hi in blocks:
        for _ in range(n):
            rows.append([lu + rng.normal(0, 0.3), k + rng.normal(0, 0.5), b + rng.normal(0, 0.5),
                         hi + rng.normal(0, 0.5)])
    return np.array(rows)


def test_segment_finds_a_classic_club_structure():
    bars = _bars([(16, -12, -14, -38, -30),     # DJ intro: kick, no bass
                  (32, -9, -14, -18, -28),      # full
                  (16, -15, -40, -45, -32),     # breakdown: no kick, no bass
                  (32, -8.5, -13, -17, -27),    # drop
                  (16, -12, -14, -36, -30)])    # outro: kick, bass gone
    segs = references.segment(bars)
    s = references.structure_summary(segs, len(bars))
    assert abs(s["intro_bars"] - 16) <= 4, segs
    assert abs(s["main_break_bars"] - 16) <= 4, segs
    assert abs(s["main_break_at"] - 48 / 112) < 0.06, segs
    assert s["break_depth_lu"] > 5, s
    assert abs(s["outro_bars"] - 16) <= 4, segs


def test_third_octave_shape_is_loudness_independent():
    t = np.arange(SR * 4) / SR
    x = 0.3 * np.sin(2 * np.pi * 100 * t) + 0.05 * np.sin(2 * np.pi * 4000 * t)
    a = references.third_octave_db(x, SR)
    b = references.third_octave_db(x * 0.1, SR)
    assert np.allclose(a, b, atol=1e-6)
    i100 = references.THIRD_OCTAVES.index(100)
    assert a[i100] == max(a)


def test_beat_grid_finds_the_kick_phase():
    bpm, offset = 123.0, 0.21
    n = SR * 12
    x = np.zeros(n, dtype=np.float32)
    beat = 60 / bpm
    k = np.sin(2 * np.pi * 55 * np.arange(int(0.12 * SR)) / SR) * np.exp(-np.arange(int(0.12 * SR)) / (0.03 * SR))
    t = offset
    while t < 11.5:
        i = int(t * SR)
        x[i:i + k.size] += k.astype(np.float32)
        t += beat
    t0 = references.beat_grid(x, SR, bpm)
    assert abs(t0 - offset) < 0.02, t0


def test_load_audio_decodes_through_ffmpeg_when_needed(tmp_path):
    t = np.arange(SR) / SR
    x = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    wav = tmp_path / "a.wav"
    sf.write(wav, x, SR)
    m4a = tmp_path / "a.m4a"
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "aac", str(m4a)],
                   check=True)
    y, sr = references.load_audio(str(m4a))
    assert sr == SR and y.shape[1] == 2 and abs(len(y) / SR - 1.0) < 0.1


def test_key_follows_the_bass_not_the_kick():
    """G minor groove: bass G on the off-beats, a kick tuned to G#1 on every beat,
    and Gm chords above. Krumhansl on full-range chroma gets pulled by the kick."""
    from ableton_claude.music import samples
    bpm, secs = 123.0, 24
    beat = 60 / bpm
    t = np.arange(int(secs * SR)) / SR
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    x = np.zeros_like(t)
    for c in (55, 58, 62, 65):                     # Gm7 pad: G3 Bb3 D4 F4
        x += 0.05 * np.sin(2 * np.pi * hz(c) * t)
    kick_len = int(0.15 * SR)
    env = np.exp(-np.arange(kick_len) / (0.04 * SR))
    kick = 0.9 * np.sin(2 * np.pi * hz(32) * np.arange(kick_len) / SR) * env    # G#1
    bass_len = int(0.45 * beat * SR)
    bass = 0.5 * np.sin(2 * np.pi * hz(31) * np.arange(bass_len) / SR)           # G1
    for k in range(int(secs / beat) - 1):
        i = int(k * beat * SR)
        x[i:i + kick_len] += kick
        j = int((k + 0.5) * beat * SR)
        x[j:j + bass_len] += bass
    key = samples.estimate_key_bass_anchored(x.astype(np.float32), SR, bpm)
    assert (key["tonic"], key["mode"]) == ("G", "minor"), key


def test_refine_tempo_reaches_hundredths():
    bpm = 122.4
    beat = 60 / bpm
    n = SR * 40
    x = np.zeros(n, dtype=np.float32)
    k = (np.sin(2 * np.pi * 50 * np.arange(int(0.1 * SR)) / SR)
         * np.exp(-np.arange(int(0.1 * SR)) / (0.02 * SR))).astype(np.float32)
    t = 0.1
    while t < 39.5:
        i = int(t * SR)
        x[i:i + k.size] += k
        t += beat
    assert abs(references.refine_tempo(x, SR, 123.8) - bpm) <= 0.05


def test_segment_matches_a_known_arrangement():
    """The structure of the example track, bar for bar: DJ intro (kick, no bass), a short
    break, a breakdown whose hats return halfway, an 8-bar build (kick, no bass), and the
    bass leaving for the last 8 bars."""
    bars = _bars([(16, -13, -9, -73, -30),     # intro
                  (48, -11.7, -9, -18, -28),   # grooves
                  (8, -23.6, -63, -63, -35),   # break
                  (24, -11.7, -9, -18, -28),   # groove B
                  (16, -15.5, -48, -48, -40),  # breakdown
                  (8, -14.7, -51, -51, -30),   # breakdown, hats back
                  (8, -11.0, -9, -54, -29),    # build
                  (48, -11.6, -9, -18, -28),   # drop
                  (8, -13.1, -9, -73, -30)])   # outro
    segs = references.segment(bars)
    got = [(s["start"], s["end"], s["label"]) for s in segs]
    assert got == [(0, 16, "intro"), (16, 64, "full"), (64, 72, "break"), (72, 96, "full"),
                   (96, 120, "break"), (120, 128, "partial"), (128, 176, "full"),
                   (176, 184, "outro")], got
    s = references.structure_summary(segs, len(bars))
    assert (s["main_break_bars"], s["intro_bars"], s["outro_bars"]) == (24, 16, 8)



def test_self_referenced_swing_ignores_where_the_kick_grid_lands():
    """Hats at 58 % swing measured against a grid 29 ms late (a slow kick attack): the
    kick-referenced reading drops, the self-referenced one stays at 58."""
    sr, bpm = 44100, 123.0
    beat = 60.0 / bpm
    bars = 24
    x = np.zeros((int(bars * 4 * beat * sr) + sr, 2), dtype=np.float32)
    rng = np.random.default_rng(3)
    hit = (rng.standard_normal(int(0.01 * sr)) * np.exp(-np.arange(int(0.01 * sr)) / (0.002 * sr))).astype(np.float32)
    from scipy import signal
    hit = signal.sosfilt(signal.butter(4, 7000, "highpass", fs=sr, output="sos"), hit).astype(np.float32)
    for k in range(bars * 16):
        pair, second = divmod(k, 2)
        t = pair * beat / 2 + (0.58 * beat / 2 if second else 0.0)
        i = int(t * sr)
        x[i:i + len(hit)] += hit[:, None] * 0.5
    t0_late = 0.029
    fp = references.fingerprint(x, sr, bpm, t0_late, [{"start": 0, "end": bars - 1, "label": "full"}])
    assert fp["swing_pct"] < 50
    assert abs(fp["swing_self_pct"] - 58) < 2
