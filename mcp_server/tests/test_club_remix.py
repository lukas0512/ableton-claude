import json

import numpy as np
import pytest

from ableton_claude import producer_intelligence as intelligence, remix, server
from ableton_claude.ear import listen as ear
from ableton_claude.music import club, groove, theory


def report(margin=.15):
    return {"file": "original.wav", "id": "test", "duration_s": 32., "key": "G minor",
            "grid": {"bpm": 120., "period": .5, "first_downbeat": 0., "n_bars": 16, "fit_ms": 4},
            "harmony": {"tonic_pc": 7, "key_confidence": margin},
            "arrangement": {"sections": [{"start_bar": 5, "end_bar": 12,
                                            "label": "groove", "elements": ["vocals", "bass"]}]}}


@pytest.mark.parametrize('text', ['faça um tech house pista', 'faca um tech-house pista',
                                 'make a tech house track', 'quero remixar essa música'])
def test_short_prompts_unlock_complete_production(text):
    groups = intelligence.task_groups(text)
    assert {'compose', 'groove', 'arrange', 'mix', 'verify'} <= groups
    names = {t['name'] for t in intelligence.select_tools(
        [{'name': n, 'description': n} for n in ('music_club_motif', 'music_drum_pattern', 'remix_plan')], groups)}
    assert 'music_club_motif' in names
    if 'remix' in groups:
        assert 'remix_plan' in names


def test_drum_style_is_distinct_and_legacy_default_preserved():
    assert server.music_drum_pattern() == groove.pattern('deep_house', 1, 56.)
    deep = server.music_drum_pattern(style='deep_house', seed=8)
    tech = server.music_drum_pattern(style='tech_house', seed=8)
    assert tech['kick'] == deep['kick'] and tech['closed_hat'] != deep['closed_hat']
    with pytest.raises(ValueError):
        server.music_drum_pattern(style='unknown')


@pytest.mark.parametrize('tonic,mode', [('G', 'minor'), ('C#', 'dorian'), ('Bb', 'minor_pentatonic')])
@pytest.mark.parametrize('part', ['bass', 'hook'])
def test_club_motifs_are_repeatable_in_key_bounded_and_leave_space(part, tonic, mode):
    out = club.motif(part, tonic, mode, bars=8, swing=66, seed=8)
    assert out == club.motif(part, tonic, mode, bars=8, swing=66, seed=8)
    scale = theory.Scale(tonic, mode)
    notes = out['notes']
    assert len(notes) < 8 * 8
    assert all(scale.contains(p) and 0 <= p <= 127 and 0 <= t < t + d <= 32 and 1 <= v <= 127
               for p, t, d, v in notes)
    assert all(a[1] + a[2] <= b[1] for a, b in zip(notes, notes[1:]))
    first = [n for n in notes if n[1] < 8]
    repeated = [[p, round(t - 8, 4), d, v] for p, t, d, v in notes if 8 <= t < 16]
    assert first == repeated
    if part == 'bass':
        assert all(t % 1 > 0 for _, t, _, _ in notes)


@pytest.mark.parametrize('kwargs', [{'bars': 3}, {'bars': 1000}, {'swing': float('nan')}, {'part': 'pad'}])
def test_invalid_motif_requests_fail(kwargs):
    with pytest.raises(ValueError):
        club.motif(**kwargs)


def test_remix_plan_preserves_source_offsets_and_withholds_uncertain_transpose():
    out = remix.plan(report(), 'tech house', 126., 'A')
    assert out['tempo_ratio'] == 1.05 and out['transpose_semitones'] == 2
    assert out['hook_candidates'][0]['source_seconds'] == [8., 24.]
    assert 'no importable stems' in out['stem_status']
    uncertain = report(.01)
    uncertain['grid']['fit_ms'] = 40
    out = remix.plan(uncertain, 'tech house', 145., 'A')
    assert out['transpose_semitones'] is None
    assert any('Beat-grid' in w for w in out['warnings'])
    assert any('Large tempo' in w for w in out['warnings'])
    json.dumps(out, allow_nan=False)


def test_remix_tool_uses_measured_tempo_before_conventions(monkeypatch):
    monkeypatch.setattr(server.knowledge, 'get', lambda g: {'measured': {'bpm': {'median': 129.5}},
                                                          'conventions': {'bpm': [124, 128]}})
    monkeypatch.setattr(ear, 'listen', lambda path, bpm_hint=None: report())
    result = server.remix_plan('original.wav')
    assert result['target']['bpm'] == 129.5
    assert result['target']['tempo_basis'] == 'measured reference median'


def test_stem_balance_excludes_intervening_break_and_handles_empty_sections():
    sr = 1000
    g = {'first_downbeat': 0., 'period': .5}
    # Two equally loud drops separated by a deliberately loud break.
    x = np.ones((6000, 2)) * .1
    x[2000:4000] = 10
    arr = {'sections': [{'start_bar': b, 'end_bar': b, 'label': label, 'elements': ['bass', 'drums']}
                        for b, label in [(1, 'drop'), (2, 'break'), (3, 'drop')]]}
    out = ear.stem_mix({'drums': x, 'bass': x / 2}, sr, g, arr)
    assert out['drums']['level_db'] == pytest.approx(-20., abs=.1)
    assert out['bass']['vs_drums_db'] == pytest.approx(-6., abs=.1)
    assert ear.stem_mix({'drums': x}, sr, g, {'sections': []}) == {}
    json.dumps(out, allow_nan=False)


def test_ear_cache_respects_tempo_hint_and_version(tmp_path, monkeypatch):
    from ableton_claude.ear import EAR_VERSION
    monkeypatch.setattr(ear, 'CACHE_DIR', str(tmp_path))
    monkeypatch.setattr(ear.R, '_file_id', lambda path: 'track')
    (tmp_path / 'track').mkdir()
    cached = {'ear_version': EAR_VERSION, 'bpm_hint': 120., 'sentinel': True}
    (tmp_path / 'track' / 'report.json').write_text(json.dumps(cached))
    assert ear.listen('unused.wav', bpm_hint=120.) == cached
    def load(path):
        raise RuntimeError('cache correctly invalidated')
    monkeypatch.setattr(ear.R, 'load_audio', load)
    with pytest.raises(RuntimeError, match='invalidated'):
        ear.listen('unused.wav', bpm_hint=128.)
    with pytest.raises(ValueError, match='bpm_hint'):
        ear.listen('unused.wav', bpm_hint=float('nan'))
