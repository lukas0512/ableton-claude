import numpy as np
import pytest
import soundfile as sf

from ableton_claude.music import groove, melody, samples, theory

# ---------------------------------------------------------------- theory


def test_scale_degrees_and_steps():
    g = theory.Scale("G", "minor")
    assert [theory.NOTE_NAMES[p] for p in g.pcs] == ["G", "A", "Bb", "C", "D", "Eb", "F"]
    assert g.degree(58) == 3                    # Bb3
    assert g.step(67, 1) == 69                  # G4 -> A4
    assert g.step(67, -1) == 65                 # G4 -> F4
    hexa = theory.Scale("G", "minor_hexatonic")
    assert not hexa.contains(63) and not hexa.contains(64)   # no Eb, no E


def test_chord_symbols():
    assert theory.chord_pcs("Gm7") == {7, 10, 2, 5}
    assert theory.chord_pcs("C7sus4") == {0, 5, 7, 10}
    assert theory.chord_pcs("Bbmaj7/A") == {10, 2, 5, 9}
    with pytest.raises(ValueError):
        theory.parse_chord("Gxyz")


def test_roman_numerals_in_g_minor():
    g = theory.Scale("G", "minor")
    assert theory.roman(g, "i7") == "Gm7"
    assert theory.roman(g, "III") == "Bb"
    assert theory.roman(g, "IIImaj7".replace("maj7", "7")) == "Bbmaj7"
    assert theory.roman(g, "VII") == "F"
    assert theory.roman(g, "iv9") == "Cm9"
    assert theory.roman(g, "IV7sus4") == "C7sus4"
    assert theory.roman(theory.Scale("G", "dorian"), "IV7") == "C7"


def test_voice_leading_keeps_chord_tones_and_moves_little():
    prog = ["Gm7", "Bbmaj7", "Fadd9", "C7sus4"]
    vs = theory.voice_lead(prog, low=55, high=79, voices=4)
    for sym, v in zip(prog, vs):
        assert {p % 12 for p in v} <= theory.chord_pcs(sym), (sym, v)
        assert len(v) == 4 and all(55 <= p <= 79 for p in v)
    # each change moves at most a few semitones in total: common tones held
    for a, b in zip(vs, vs[1:]):
        assert sum(abs(x - y) for x, y in zip(a, b)) <= 8, (a, b)
    # block chords in root position (what a beginner plays) jump around far more
    def root_position(sym):
        root, ivs, _ = theory.parse_chord(sym)
        base = 60 + (root - 60) % 12
        return tuple(base + i for i in ivs[:4])
    naive = [root_position(s) for s in prog]
    assert theory.movement(vs) * 3 < theory.movement(naive)


def test_low_register_voicings_avoid_mud():
    vs = theory.voice_lead(["Gm7", "C7sus4"], low=40, high=64, voices=4)
    for v in vs:
        for a, b in zip(v, v[1:]):
            if a < 48:
                assert b - a >= 7
            elif a < 55:
                assert b - a >= 3

# ---------------------------------------------------------------- groove


def test_swing_moves_only_offbeat_16ths():
    assert groove.swing_offset(0, 60) == 0
    assert groove.swing_offset(1, 50) == 0
    assert groove.swing_offset(1, 66) == pytest.approx(0.08)


def test_pattern_places_kick_on_every_beat():
    p = groove.pattern(bars=2, humanize=0)
    starts = [n[1] for n in p["kick"]]
    assert starts == [0, 1, 2, 3, 4, 5, 6, 7]
    assert all(n[3] == 115 for n in p["kick"])


def test_build_roll_accelerates_and_rises():
    r = groove.build_roll(bars=8)
    gaps = [b[1] - a[1] for a, b in zip(r, r[1:])]
    assert gaps[0] == 1.0 and min(gaps) == 0.125
    assert r[0][3] < r[-1][3]
    assert all(n[1] < 31.0 for n in r)                 # last beat left empty

# ---------------------------------------------------------------- melody


CHORDS = ["Gm7", "Gm7", "Bbmaj7", "Bbmaj7"]


@pytest.mark.parametrize("seed", range(12))
def test_call_and_response_obeys_its_rules(seed):
    out = melody.call_and_response("G", "minor_hexatonic", CHORDS, seed=seed)
    scale = theory.Scale("G", "minor_hexatonic")
    call, resp = out["call"], out["response"]
    assert not melody.audit(call, scale, CHORDS[:2]), melody.audit(call, scale, CHORDS[:2])
    assert not melody.audit(resp, scale, CHORDS[2:]), melody.audit(resp, scale, CHORDS[2:])
    assert out["call_ends_on_degree"] in melody.OPEN_DEGREES
    assert out["response_ends_on_degree"] in melody.CLOSED_DEGREES
    assert all(62 <= n[0] <= 79 for n in call) and all(55 <= n[0] <= 74 for n in resp)
    # the response echoes the call's opening rhythm
    c_on = [n[1] for n in call if n[1] < 4]
    r_on = [n[1] for n in resp if n[1] < 4]
    assert c_on == r_on
    # phrases breathe: nothing rings into the next phrase
    assert all(n[1] + n[2] <= 8.0 for n in call + resp)


def test_call_and_response_is_reproducible():
    a = melody.call_and_response(seed=3)
    b = melody.call_and_response(seed=3)
    assert a == b

# ---------------------------------------------------------------- samples

SR = 44100


def _tone(freqs_amps, secs):
    t = np.arange(int(secs * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * t) for f, a in freqs_amps)


def test_key_of_a_g_minor_texture(tmp_path):
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    x = _tone([(hz(43), 0.5), (hz(55), 0.3), (hz(58), 0.25), (hz(62), 0.25),
               (hz(65), 0.15)], 6)
    p = tmp_path / "gm.wav"
    sf.write(p, (x / np.abs(x).max() * 0.8).astype(np.float32), SR)
    k = samples.analyze_sample(str(p), tempo=120)["key"]
    assert (k["tonic"], k["mode"]) == ("G", "minor"), k


def _clicks(times, secs):
    x = np.zeros(int(secs * SR), dtype=np.float32)
    burst = (np.random.default_rng(0).normal(0, 0.6, 200) * np.hanning(200)).astype(np.float32)
    for t in times:
        i = int(t * SR)
        x[i:i + 200] += burst[: max(0, min(200, x.size - i))]
    return x


def test_tempo_of_a_click_track():
    beat = 60 / 123.0
    x = _clicks([i * beat for i in range(int(16 / beat))], 16)
    assert abs(samples.estimate_tempo(x, SR) - 123.0) <= 1.0


def test_swing_of_swung_16ths():
    bpm, sw = 123.0, 60.0
    pair = 60 / bpm / 2
    times = []
    for k in range(int(12 / pair)):
        times.append(k * pair)
        times.append(k * pair + pair * sw / 100)
    x = _clicks(times, 12.5)
    assert abs(samples.estimate_swing(x, SR, bpm) - sw) <= 3
