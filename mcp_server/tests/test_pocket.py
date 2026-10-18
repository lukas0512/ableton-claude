import math

import pytest

from ableton_claude.music import pocket
from ableton_claude import producer_intelligence as pi
from ableton_claude.desktop_agent import read_only


@pytest.mark.parametrize("style", ["tech_house", "deep_house"])
@pytest.mark.parametrize("swing", [50, 56, 66])
@pytest.mark.parametrize("seed", [0, 7, 42])
def test_pocket_anchors_space_and_valid_notes(style, swing, seed):
    result = pocket.sketch(style=style, swing=swing, seed=seed, drum_layers=5)
    main, stripped = result['main'], result['stripped']
    assert [n[1] for n in main['kick']] == list(range(32))
    assert main['kick'] == stripped['kick']
    assert main['clap'] == stripped['clap']
    assert main['bass'] == stripped['bass']
    assert result['midi_diagnostics']['stripped_notes'] < result['midi_diagnostics']['main_notes']
    bass_slots = {round(n[1] * 4) for n in main['bass']}
    rim_slots = {round(n[1] * 4) for n in main['rim']}
    for part in ('rim', 'shaker'):
        assert not bass_slots & {round(n[1] * 4) for n in main[part]}
    assert not rim_slots & {round(n[1] * 4) for n in main['shaker']}
    for notes in main.values():
        assert notes == sorted(notes, key=lambda n: n[1])
        for pitch, start, duration, velocity in notes:
            assert 0 <= pitch <= 127 and 1 <= velocity <= 127
            assert 0 <= start < 32 and 0 < duration <= 32 - start + 1e-8
    for _, start, duration, _ in main['bass']:
        assert start + duration <= math.floor(start) + 1 - .0399


def test_repeatable_identity_and_delays_follow_tempo():
    a = pocket.sketch(bpm=120, clap_delay_ms=10)
    assert a == pocket.sketch(bpm=120, clap_delay_ms=10)
    b = pocket.sketch(bpm=60, clap_delay_ms=10)
    assert a['main']['clap'][0][1] == 1.02
    assert b['main']['clap'][0][1] == 1.01
    for part in ('closed_hat', 'rim', 'shaker', 'bass'):
        notes = a['main'].get(part, [])
        cell = [n for n in notes if n[1] < 8]
        repeat = [[p, round(t - 8, 4), d, v] for p, t, d, v in notes if 8 <= t < 16]
        assert cell == repeat


@pytest.mark.parametrize('kwargs', [dict(bars=3), dict(bars=True), dict(bars=66),
    dict(drum_layers=6), dict(drum_layers=True), dict(bpm=float('nan')),
    dict(swing=float('inf')), dict(swing=67), dict(clap_delay_ms=26),
    dict(percussion_delay_ms=-16), dict(style='invented')])
def test_rejects_invalid_sketch(kwargs):
    with pytest.raises(ValueError):
        pocket.sketch(**kwargs)


def test_extreme_offsets_and_minimal_layer_budget():
    result = pocket.sketch(bars=2, bpm=200, percussion_delay_ms=-15, drum_layers=3)
    assert set(result['main']) == {'kick', 'clap', 'closed_hat', 'bass'}
    assert all(n[1] >= 0 for notes in result['main'].values() for n in notes)


def test_available_to_desktop_for_composition_and_groove():
    for group in ('compose', 'groove'):
        assert 'music_pocket_sketch' in pi.GROUPS[group]
    assert read_only('music_pocket_sketch', {})
    prompt = pi.system_prompt(None, {}, {}, '', {'groove'}, 'melhore o swing')
    assert 'music_pocket_sketch' in prompt and 'double swing' in prompt


def test_mcp_tool_matches_generator():
    from ableton_claude.server import music_pocket_sketch
    assert music_pocket_sketch() == pocket.sketch()
