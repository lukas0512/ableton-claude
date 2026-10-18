"""Perceptual invariants on known signals; these do not test subjective music quality."""
import copy
import json

import numpy as np
import pytest

from ableton_claude import intent, production_review, producer_intelligence, server, tension
from ableton_claude.desktop_agent import read_only
from ableton_claude.ear import perception
from ableton_claude.music import club

SR = 8000


def heard(bass_gain=.1, upper=.1, bars=4, anti=False, bass_notes=()):
    t = np.arange(bars * 2 * SR) / SR
    bass = np.sin(2 * np.pi * 64 * t) + upper * np.sin(2 * np.pi * 512 * t)
    bass *= bass_gain / np.sqrt(np.mean(bass ** 2))
    drums = np.sin(2 * np.pi * 1000 * t) * .1 * np.sqrt(2)
    bs = np.stack([bass, -bass if anti else bass], axis=1)
    ds = np.stack([drums, drums], axis=1)
    g = {'period': .5, 'first_downbeat': 0., 'n_bars': bars}
    arr = {'bar_lufs': [-12.] * bars,
           'sections': [{'start_bar': 1, 'end_bar': bars, 'label': 'groove', 'elements': ['kick', 'bass']}]}
    return perception.analyze(bs + ds, SR, {'bass': bs, 'drums': ds}, g, arr, bass_notes)


def test_amount_and_openness_are_independent_and_not_stereo_width():
    base = heard()['sections'][0]['metrics']
    heavier = heard(bass_gain=.2)['sections'][0]['metrics']
    brighter = heard(upper=1.)['sections'][0]['metrics']
    assert heavier['bass_vs_drums_db'] - base['bass_vs_drums_db'] == pytest.approx(6.02, abs=.02)
    assert heavier['bass_upper_to_low_db'] == pytest.approx(base['bass_upper_to_low_db'], abs=.01)
    assert brighter['bass_vs_drums_db'] == pytest.approx(base['bass_vs_drums_db'], abs=.01)
    assert brighter['bass_upper_to_low_db'] - base['bass_upper_to_low_db'] > 18
    assert brighter['bass_low_mono_loss_db'] == pytest.approx(0., abs=.01)


def test_antiphase_bass_keeps_stereo_weight_but_exposes_mono_loss():
    mono = heard()['sections'][0]['metrics']
    anti = heard(anti=True)['sections'][0]['metrics']
    assert anti['bass_vs_drums_db'] == mono['bass_vs_drums_db']
    assert anti['bass_upper_to_low_db'] == mono['bass_upper_to_low_db']
    assert anti['bass_low_mono_loss_db'] < -100
    assert anti['mix_low_share_pct'] == pytest.approx(mono['mix_low_share_pct'], abs=.01)


def test_silence_reports_unknown_ratios_without_nan_or_fake_brightness():
    silent = np.zeros((4 * SR, 2))
    g = {'period': .5, 'first_downbeat': 0., 'n_bars': 2}
    p = perception.analyze(silent, SR, {'bass': silent, 'drums': silent}, g,
                           {'sections': [{'start_bar': 1, 'end_bar': 2, 'label': 'break', 'elements': []}]})
    m = p['sections'][0]['metrics']
    assert m['bass_upper_to_low_db'] is None and m['bass_vs_drums_db'] is None
    assert m['bass_low_mono_loss_db'] is None and m['mix_low_share_pct'] is None
    json.dumps(p, allow_nan=False)


def test_occupancy_counts_overlapping_and_cross_bar_tails_once():
    notes = [{'bar': 0, 'step': 14, 'dur_steps': 6}, {'bar': 1, 'step': 0, 'dur_steps': 2}]
    p = heard(bass_notes=notes)
    assert p['bars'][0]['bass_occupancy_pct'] == 12.5
    assert p['bars'][1]['bass_occupancy_pct'] == 25
    assert p['bars'][1]['bass_notes_per_bar'] == 1


def test_all_drops_keep_independent_cues_at_equal_loudness_and_near_start():
    rows = []
    for bar in range(8):
        drop = bar in (1, 2, 6, 7)
        rows.append({'bar': bar + 1, 'lufs': -12., 'bass_level_db': -12. if drop else -30.,
                     'drums_level_db': -10., 'mix_low_share_pct': 50. if drop else 5.,
                     'bass_upper_to_low_db': -10., 'drum_attack_to_tail_db': 7.})
    sections = [{'start_bar': 1, 'end_bar': 1, 'label': 'break', 'elements': ['other']},
                {'start_bar': 2, 'end_bar': 3, 'label': 'drop', 'elements': ['kick', 'bass']},
                {'start_bar': 4, 'end_bar': 6, 'label': 'break', 'elements': ['other']},
                {'start_bar': 7, 'end_bar': 8, 'label': 'drop', 'elements': ['kick', 'bass']}]
    transitions = perception.transitions(rows, sections)
    assert [t['drop_bar'] for t in transitions] == [2, 7]
    assert all(t['loudness_jump_lu'] == 0 and t['bass_return_db'] == 18 for t in transitions)
    assert all(t['low_share_change_pct'] == 45 and 'kick' in t['entering'] for t in transitions)
    assert transitions[0]['predrop_dip_lu'] is None
    assert transitions[1]['before_bars'] == [4, 6]  # excludes previous drop


def test_reference_pool_has_one_vote_per_track_and_keeps_section_roles():
    a = heard()
    b = copy.deepcopy(a)
    b['sections'][0]['metrics']['bass_vs_drums_db'] = 12.
    b['sections'] *= 10
    targets = perception.profile([{'perception': a}, {'perception': b}, {'perception': {'version': 0}}])
    assert targets['n_tracks'] == 2
    assert targets['sections']['groove']['bass_vs_drums_db']['median'] == pytest.approx(6.)
    assert targets['sections']['groove']['bass_vs_drums_db']['n'] == 2
    assert perception.compare(a, targets)['rows']
    assert 'not a defect' in perception.compare(a, targets)['note']


def test_intent_distinguishes_closed_heavy_from_open_light_bass():
    a = intent.interpret('Quero muito bass, um bass fechado e hipnótico')
    b = intent.interpret('Quero pouco grave, bass aberto com poucas notas')
    assert {('bass_amount', 'heavy'), ('bass_openness', 'closed')} <= {(d['axis'], d['value']) for d in a['directions']}
    assert {('bass_amount', 'light'), ('bass_openness', 'open'), ('bass_density', 'sparse')} <= {(d['axis'], d['value']) for d in b['directions']}
    assert a['moods'][0]['mood'] == 'hypnotic'
    assert not a['conflicts'] and not b['conflicts']


def test_intent_keeps_section_targets_negation_and_uncertainty():
    p = intent.interpret('Bass fechado no break, bass aberto no drop; não quero bass estéreo')
    assert {(d['scope'], d['value']) for d in p['directions']} == {('break', 'closed'), ('drop', 'open')}
    assert any(d.get('value') == 'wide' for d in p['avoid'])
    assert not intent.interpret('deixe o volume mais baixo')['directions']
    assert not intent.interpret('não quero música triste')['moods']
    assert intent.interpret('bass fechado e aberto')['conflicts']
    assert not intent.interpret('Faça algo que me toque')['moods']


def test_review_without_reference_does_not_invent_emotional_or_quality_score():
    report = {'file': 'mix.wav', 'perception': heard(anti=True)}
    out = production_review.review(report, 'muito bass fechado')
    assert len(out['findings']) == 1 and out['findings'][0]['axis'] == 'low_end_mono'
    assert not out['section_comparison']['rows']
    assert 'no professional/emotional quality score' in out['assessment']
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize('density', ['sparse', 'normal', 'busy'])
@pytest.mark.parametrize('articulation', ['short', 'sustained'])
def test_motif_expression_stays_monophonic_bounded_and_clear_of_kick(density, articulation):
    out = club.motif(density=density, articulation=articulation, development='evolving')
    notes = out['notes']
    assert all(0 <= p <= 127 and 0 <= t < t + d <= 32 for p, t, d, _ in notes)
    assert all(a[1] + a[2] <= b[1] for a, b in zip(notes, notes[1:]))
    assert all(t + d < np.floor(t) + 1 for _, t, d, _ in notes)
    assert notes[0][0] == 31  # G1, not an unintended G2 mid-bass


def test_motif_changes_density_independently_of_articulation_and_keeps_identity():
    sparse = club.motif(density='sparse')['notes']
    normal = club.motif()['notes']
    busy = club.motif(density='busy')['notes']
    sustained = club.motif(articulation='sustained')['notes']
    assert len(sparse) < len(normal) < len(busy)
    assert [n[:2] for n in normal] == [n[:2] for n in sustained]
    assert sum(n[2] for n in sustained) > sum(n[2] for n in normal)
    evolving = club.motif(development='evolving')['notes']
    assert normal[:len(normal) // 4] == evolving[:len(normal) // 4]
    assert normal != evolving


def test_early_break_metrics_never_wrap_to_song_tail_or_emit_nan():
    bars = [[-12., -30., -40., -30.], [-12., -10., -10., -20.], [-8., -5., -5., -10.]]
    out = tension.metrics(bars, 0, 1, 1)
    assert out['drop_vs_pre_break_lu'] is None
    assert out['predrop_dip_lu'] is None and out['build_lu_per_bar'] is None
    json.dumps(out, allow_nan=False)


def test_expression_tools_are_discoverable_read_only_and_use_direct_reference(monkeypatch):
    report = {'file': 'mix.wav', 'perception': heard()}
    monkeypatch.setattr('ableton_claude.ear.listen.listen', lambda path, bpm_hint=None: report)
    result = server.production_review('mix.wav', prompt='bass fechado', reference_path='ref.wav')
    assert result['reference_source']['kind'] == 'direct_reference'
    assert result['section_comparison']['rows']
    assert read_only('production_review', {}) and read_only('production_intent', {})
    groups = producer_intelligence.task_groups('Quero bass fechado e hipnótico')
    assert {'compose', 'verify', 'mix'} <= groups
    system = producer_intelligence.system_prompt('tech house', {}, {}, '', groups, request='Quero bass fechado')
    assert 'bass_openness' in system and 'EXPRESSION AND DELIBERATION' in system


def test_changed_drop_cannot_reuse_reference_analysis_from_identical_intro(tmp_path):
    from ableton_claude.references import _file_id
    first, revised = tmp_path / 'first.wav', tmp_path / 'revised.wav'
    intro = b'unchanged intro' * 100000
    first.write_bytes(intro + b'original drop')
    revised.write_bytes(intro + b'changed  drop')
    assert _file_id(first) != _file_id(revised)
    revised.write_bytes(first.read_bytes())
    assert _file_id(first) == _file_id(revised)


def test_near_silent_separation_residue_is_not_interpreted_as_bass_openness():
    sr = SR
    t = np.arange(4 * sr) / sr
    bass = np.sin(2 * np.pi * 64 * t) * .1
    bass[:2 * sr] = np.sin(2 * np.pi * 512 * t[:2 * sr]) * 1e-5
    bass = np.stack([bass, bass], axis=1)
    drums = np.ones_like(bass) * .01
    g = {'period': .5, 'first_downbeat': 0., 'n_bars': 2}
    arr = {'sections': [{'start_bar': 1, 'end_bar': 1, 'label': 'break', 'elements': []},
                        {'start_bar': 2, 'end_bar': 2, 'label': 'drop', 'elements': ['bass', 'kick']}]}
    result = perception.analyze(bass + drums, sr, {'bass': bass, 'drums': drums}, g, arr)
    assert result['bars'][0]['bass_usable'] is False
    assert result['bars'][0]['bass_upper_to_low_db'] is None
    assert result['bars'][1]['bass_usable'] is True
    assert result['bars'][1]['bass_upper_to_low_db'] < -100
    assert result['transitions'][0]['bass_openness_change_db'] is None


def test_review_can_narrow_long_song_without_relabelling_partial_sections():
    p = heard()
    second = copy.deepcopy(p['sections'][0])
    second.update(start_bar=5, end_bar=8, label='drop')
    p['sections'].append(second)
    result = production_review.review({'file': 'mix.wav', 'perception': p}, start_bar=6, end_bar=7)
    assert len(result['sections']) == 1
    assert result['sections'][0]['start_bar'] == 5 and result['sections'][0]['end_bar'] == 8
    with pytest.raises(ValueError):
        production_review.review({'file': 'mix.wav', 'perception': p}, start_bar=7, end_bar=6)
