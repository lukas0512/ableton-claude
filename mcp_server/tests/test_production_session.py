import json
from copy import deepcopy

import pytest

from ableton_claude.production_session import ProductionSession


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class Live:
    def __init__(self, name):
        self.calls = []
        self.track = {'name': name, 'vol_db': -8, 'mute': False, 'devices': [{'name': 'Instrument'}],
                      'n_clips': 1, 'clips': [{'i': 0, 'type': 'midi', 'start': 0, 'end': 32, 'muted': False}]}
        self.notes = [[60, 0, 1, 100]]

    def call(self, name, args):
        self.calls.append((name, args))
        cmd = args['cmd']
        if cmd == 'get_track':
            return deepcopy(self.track)
        if cmd == 'get_notes':
            return deepcopy(self.notes)
        if cmd == 'transport':
            return {'playing': True}
        return {}


@pytest.fixture
def idea(tmp_path):
    flow = ProductionSession(tmp_path, write)
    flow.begin({'signature': '4/4', 'tracks': []}, copy_confirmed=True)
    name = flow.status()['track_prefix'] + 'Motivo'
    flow.observe('ableton_command', {'cmd': 'create_track'}, {'name': name})
    flow.observe('ableton_command', {'cmd': 'create_midi_clip'}, {})
    return flow, Live(name)


@pytest.mark.parametrize('bars', [4, 8, 16])
def test_short_loop_choice_and_explicit_copy_confirmation(tmp_path, bars):
    flow = ProductionSession(tmp_path, write)
    with pytest.raises(ValueError, match='cópia'):
        flow.begin({}, bars)
    status = flow.begin({'signature': '6/8', 'song_length_beats': 33,
                         'tracks': [{'clips_active': 3}]}, bars, True)
    assert status['beats_per_bar'] == 3
    assert status['start_bar'] == 20
    assert status['end_bar'] == 20 + bars
    assert status['approvals'] == []


def test_apply_does_not_approve_and_arrangement_requires_two_listening_approvals(idea):
    flow, live = idea
    assert flow.status()['stage'] == 'loop'
    with pytest.raises(ValueError, match='Ouça'):
        flow.approve(live)
    flow.audition(live)
    assert live.calls[-1][1] == {'cmd': 'transport', 'args': {'action': 'play', 'bar': 1}}
    assert flow.approve(live)['stage'] == 'groove'
    with pytest.raises(ValueError, match='Ouça'):
        flow.approve(live)
    flow.audition(live)
    assert flow.approve(live)['stage'] == 'arrangement'
    assert flow.status()['approvals'] == ['loop', 'groove']
    with pytest.raises(ValueError, match='seções'):
        flow.audition(live)
    live.track['clips'][0]['end'] = 128
    flow.audition(live)
    assert live.calls[-2][1]['args']['end_bar'] == 33
    assert flow.approve(live)['completed']
    assert flow.back()['stage'] == 'groove'
    assert flow.status()['approvals'] == ['loop']
    assert not flow.status()['completed']


def test_material_changed_after_listening_requires_listening_again(idea):
    flow, live = idea
    flow.audition(live)
    live.notes[0][0] = 62
    with pytest.raises(ValueError, match='mudou'):
        flow.approve(live)
    assert not flow.status()['auditioned']
    assert flow.status()['stage'] == 'loop'


def test_all_midi_clips_checked_not_only_first_four(idea):
    flow, live = idea
    live.track['clips'] = [dict(live.track['clips'][0], i=i) for i in range(5)]
    live.notes = []
    with pytest.raises(ValueError, match='material musical'):
        flow.audition(live)
    assert sum(args['cmd'] == 'get_notes' for _, args in live.calls) == 5


def test_mutating_tools_invalidate_listening_but_never_advance(idea):
    flow, live = idea
    flow.audition(live)
    flow.observe('ableton_command', {'cmd': 'set_param'}, {})
    assert not flow.status()['auditioned']
    assert flow.status()['stage'] == 'loop'
    flow.observe('ableton_command', {'cmd': 'get_notes'}, live.notes)
    assert flow.status()['revision'] == 3


def test_reopen_requires_project_confirmation_without_losing_approvals(idea):
    flow, live = idea
    flow.audition(live)
    flow.approve(live)
    loaded = ProductionSession(flow.path.parent.parent, write)
    assert loaded.status()['needs_resume']
    assert loaded.status()['approvals'] == ['loop']
    with pytest.raises(ValueError, match='Retome'):
        loaded.check('ableton_status', {})
    loaded.resume()
    assert not loaded.status()['auditioned']
    assert not loaded.status()['needs_resume']
    assert loaded.end() == {'active': False}
    with pytest.raises(ValueError, match='salva'):
        loaded.resume()


@pytest.mark.parametrize('cmd,args', [
    ('set_tempo', {'bpm': 128}),
    ('set_track', {'track': 'Original', 'volume_db': -3}),
    ('create_track', {'name': 'Original'}),
    ('delete_clips_in_range', {'track': 'Original', 'start_bar': 1, 'end_bar': 9}),
])
def test_originals_cannot_be_modified(idea, cmd, args):
    flow, _ = idea
    with pytest.raises(ValueError):
        flow.check('ableton_command', {'cmd': cmd, 'args': args})
    flow.check('ableton_command', {'cmd': 'get_track', 'args': {'track': 'Original'}})


@pytest.mark.parametrize('cmd,args', [
    ('create_midi_clip', {'bar': 1, 'length': 64}),
    ('create_audio_clip', {'bar': 8, 'length': 8}),
    ('create_midi_clip', {'bar': None, 'length': 4}),
    ('create_midi_clip', {'beat': None, 'length': 4}),
    ('create_midi_clip', {'bar': 1, 'length': float('inf')}),
    ('duplicate_clip', {'clip': 0, 'bar': 9}),
    ('trim_clip', {'clip': 0, 'end_bar': 17}),
    ('fill_range', {'src_start_bar': 1, 'src_end_bar': 9, 'start_bar': 1, 'end_bar': 33}),
])
def test_loop_cannot_expand_via_individual_or_batched_commands(idea, cmd, args):
    flow, live = idea
    args['track'] = live.track['name']
    command = {'cmd': cmd, 'args': args}
    with pytest.raises(ValueError):
        flow.check('ableton_command', command)
    with pytest.raises(ValueError):
        flow.check('ableton_batch', {'commands': [command]})


def test_sequential_new_track_proposal_allowed_but_execution_needs_created_track(idea):
    flow, _ = idea
    name = flow.status()['track_prefix'] + 'Baixo'
    flow.check('ableton_command', {'cmd': 'create_track', 'args': {'name': name}})
    call = {'cmd': 'create_midi_clip', 'args': {'track': name, 'beat': 0, 'length': 32}}
    flow.check('ableton_command', call, [name])
    with pytest.raises(ValueError):
        flow.check('ableton_command', call)
    flow.observe('ableton_command', {'cmd': 'create_track'}, {'name': name})
    flow.check('ableton_command', call)


def test_stage_tool_catalog_and_backtracking(idea):
    flow, live = idea
    catalog = [{'name': n} for n in ['music_build_roll', 'genre_plan_structure', 'music_build_notes']]
    assert flow.filter_tools(catalog) == [{'name': 'music_build_notes'}]
    for _ in range(2):
        flow.audition(live)
        flow.approve(live)
    assert flow.filter_tools(catalog) == catalog
    flow.check('ableton_command', {'cmd': 'fill_range', 'args': {'track': live.track['name'],
               'src_start_bar': 1, 'src_end_bar': 9, 'start_bar': 1, 'end_bar': 65}})
    flow.back()
    assert flow.filter_tools(catalog) == [{'name': 'music_build_notes'}]


def test_batch_track_creation_cannot_bypass_twelve_track_limit(idea):
    flow, _ = idea
    commands = [{'cmd': 'create_track', 'args': {'name': flow.status()['track_prefix'] + str(i)}} for i in range(12)]
    with pytest.raises(ValueError, match='12 faixas'):
        flow.check('ableton_batch', {'commands': commands})


def test_existing_project_has_no_loop_milestones_and_preserves_its_context(tmp_path):
    flow = ProductionSession(tmp_path, write)
    song = {'signature': '4/4', 'song_length_beats': 256, 'tracks': [{'name': 'Kick'}, {'name': 'Hook'}]}
    with pytest.raises(ValueError, match='cópia'):
        flow.begin_existing(song)
    status = flow.begin_existing(song, True, 'Minha track', 'mix')
    assert status['mode'] == 'existing' and status['stage'] == 'existing'
    assert status['end_bar'] == 65 and status['tracks'] == ['Kick', 'Hook']
    assert status['approvals'] == []
    assert 'Do not rebuild it from scratch' in flow.prompt()
    assert 'MUSICAL WORKFLOW' not in flow.prompt()
    tools = [{'name': 'mix_toward_genre'}, {'name': 'genre_plan_structure'}]
    assert flow.filter_tools(tools) == tools
    flow.check('ableton_command', {'cmd': 'set_track', 'args': {'track': 'Hook', 'volume_db': -3}})
    flow.observe('ableton_command', {'cmd': 'set_track', 'args': {'track': 'Hook', 'name': 'Melodia'}}, {})
    assert flow.status()['tracks'] == ['Kick', 'Melodia']
    assert flow.status()['stage'] == 'existing'
    with pytest.raises(ValueError, match='existentes'):
        flow.back()
    reopened = ProductionSession(tmp_path, write)
    assert reopened.status()['mode'] == 'existing' and reopened.status()['needs_resume']
    with pytest.raises(ValueError, match='Retome'):
        reopened.check('ableton_command', {'cmd': 'set_track'})


def test_multiple_projects_are_retained_and_restore_exact_approved_stage(idea):
    flow, live = idea
    flow.audition(live)
    approved = flow.approve(live)
    first_id = approved['id']
    assert flow.end() == {'active': False}
    second = flow.begin({'tracks': []}, copy_confirmed=True, label='Segunda ideia')
    second_id = second['id']
    flow.end()
    projects = flow.projects()
    assert [p['id'] for p in projects] == [second_id, first_id]
    assert projects[0]['label'] == 'Segunda ideia'
    candidate = flow.candidate(first_id)
    result = flow.restore(candidate)
    assert result['stage'] == 'groove' and result['approvals'] == ['loop']
    assert result['tracks'] == [live.track['name']]
    assert not result['auditioned']
    with pytest.raises(ValueError, match='Guarde'):
        flow.candidate(second_id)


def test_projects_do_not_copy_audio_and_invalid_selection_cannot_replace_session(idea):
    flow, _ = idea
    flow.end()
    assert len(list(flow.path.parent.rglob('*.json'))) == 2
    assert not list(flow.path.parent.rglob('*.wav'))
    for invalid in ['../session', None, 'unknown']:
        with pytest.raises(ValueError, match='válido'):
            flow.candidate(invalid)
    assert flow.status() == {'active': False}


def test_existing_goal_is_validated_before_saving(tmp_path):
    flow = ProductionSession(tmp_path, write)
    with pytest.raises(ValueError, match='diagnóstico'):
        flow.begin_existing({'tracks': [{'name': 'Kick'}]}, True, goal='invalid')
    assert not flow.path.exists()
