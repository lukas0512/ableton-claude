import json

import pytest

from ableton_claude import producer_intelligence as intelligence
from ableton_claude.desktop_agent import ProducerAgent
from test_desktop_agent import Connection, finished, transport_responses


def tool(name):
    return {'name': name, 'description': 'tool description', 'parameters': {'type': 'object', 'properties': {}}}


def message(text='Proposta pronta', usage=None):
    return {'output': [{'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': text}]}],
            'usage': usage or {}}


def function(name, args, id='1'):
    return {'type': 'function_call', 'call_id': id, 'name': name, 'arguments': json.dumps(args)}


@pytest.mark.parametrize('text,group', [('Melhore o groove', 'groove'), ('Dê impacto à transição do drop', 'arrange'),
                                      ('Deixe minha faixa profissional', 'mix'), ('Crie uma ideia do zero', 'compose'),
                                      ('Compare o áudio', 'verify'), ('Improve the drums', 'groove')])
def test_simple_multilingual_requests_load_relevant_capabilities(text, group):
    assert group in intelligence.task_groups(text)


def test_compaction_is_valid_json_and_discloses_omitted_notes_without_fabricating_values():
    notes = [[60, i / 4, .2, 90] for i in range(400)]
    compact = json.loads(intelligence.compact({'notes': notes, 'measured_lufs': -9.37}))
    assert compact['measured_lufs'] == -9.37
    assert compact['notes']['total'] == 400 and compact['notes']['omitted'] > 0
    assert compact['notes']['items'] == notes[:len(compact['notes']['items'])]
    assert json.loads(intelligence.compact({'huge': {str(i): i for i in range(5000)}}, 1000))['incomplete']


def test_local_context_preserves_live_evidence_and_selected_genre_without_sending_full_manual():
    connection, requests = Connection(), []
    connection.tools += [tool('genre_knowledge'), tool('music_drum_pattern'), tool('analyze_timbre')]
    def call(name, args=None):
        connection.calls.append((name, args))
        if name == 'producer_brief':
            return 'Long general manual. ' * 5000
        if name == 'genre_knowledge':
            return {'genre': args['genre'], 'measured': {'bpm': {'median': 126.4}, 'n_tracks': 6}}
        return {'tempo': 127, 'signature': '4/4', 'tracks': [{'name': 'Original Hook', 'vol_db': -7.2}]}
    connection.call = call
    agent = ProducerAgent(connection, transport_responses([message(), message()], requests))
    for _ in range(2):
        agent.start('Melhore o groove sem mudar o hook', 'openai', 'model', 'token', 'My House')
        assert finished(agent)['state'] == 'idle'
    prompt = requests[0]['instructions']
    assert 'My House' in prompt and '126.4' in prompt and 'Original Hook' in prompt
    assert 'Long general manual.' not in prompt
    assert len(prompt) < 8000
    assert sum(n == 'producer_brief' for n, _ in connection.calls) == 1
    names = {t['name'] for t in requests[0]['tools']}
    assert 'music_drum_pattern' in names and 'analyze_timbre' not in names


def test_missing_tools_can_be_unlocked_locally_in_the_same_turn():
    connection, requests = Connection(), []
    connection.tools += [tool('analyze_timbre')]
    agent = ProducerAgent(connection, transport_responses([
        {'output': [function('producer_tools', {'groups': ['mix']})]}, message()], requests))
    agent.start('Analise', 'openai', 'model', 'token', 'Jazz')
    assert finished(agent)['state'] == 'idle'
    assert 'analyze_timbre' not in {t['name'] for t in requests[0]['tools']}
    assert 'analyze_timbre' in {t['name'] for t in requests[1]['tools']}
    assert not any(n == 'producer_tools' for n, _ in connection.calls)


def test_generated_notes_are_reused_exactly_only_after_review():
    connection, requests = Connection(), []
    notes = [[36 + i % 12, i / 4, .2, 90] for i in range(600)]
    connection.tools += [tool('music_drum_pattern')]
    original = connection.call
    def call(name, args=None):
        if name == 'music_drum_pattern':
            connection.calls.append((name, args))
            return notes
        return original(name, args)
    connection.call = call
    responses = [{'output': [function('music_drum_pattern', {'bars': 16})]},
                 {'output': [function('ableton_command', {'cmd': 'create_midi_clip',
                              'args': {'track': 'Drums', 'length': 64, 'notes': {'$result': 'material-1'}}}, '2')]}, message()]
    agent = ProducerAgent(connection, transport_responses(responses, requests))
    agent.start('Crie um groove', 'openai', 'model', 'token', 'Jazz')
    state = finished(agent)
    assert state['state'] == 'review' and state['pending'][0]['args']['args']['notes'] == notes
    assert not any(n == 'ableton_command' for n, _ in connection.calls)
    preview = json.loads(requests[1]['input'][-1]['output'])
    assert preview['result_ref'] == 'material-1' and preview['data']['total'] == 600
    assert len(requests[1]['input'][-1]['output']) < len(json.dumps(notes)) / 4
    agent.start('', 'openai', 'model', 'token', 'Jazz', approve=True)
    assert finished(agent)['state'] == 'idle'
    assert [a['args']['notes'] for n, a in connection.calls if n == 'ableton_command'] == [notes]


def test_expired_material_or_unknown_tool_never_becomes_executable_proposal():
    for name, args in [('ableton_command', {'cmd': 'create_midi_clip', 'args': {'notes': {'$result': 'invalid'}}}),
                       ('unknown_tool', {})]:
        connection = Connection()
        agent = ProducerAgent(connection, transport_responses([{'output': [function(name, args)]}], []))
        agent.start('Crie', 'openai', 'model', 'token', 'Jazz')
        state = finished(agent)
        assert state['state'] == 'error' and not state['pending']
        assert not any(n == 'ableton_command' for n, _ in connection.calls)


def test_club_notes_reuse_the_exact_field_and_still_wait_for_review():
    from ableton_claude.music.club import motif
    connection = Connection()
    connection.tools += [tool('music_club_motif'), tool('genre_knowledge')]
    generated = motif()
    original = connection.call
    connection.call = lambda name, args=None: generated if name == 'music_club_motif' else original(name, args)
    agent = ProducerAgent(connection, transport_responses([
        {'output': [function('music_club_motif', {'part': 'bass'})]},
        {'output': [function('ableton_command', {'cmd': 'create_midi_clip', 'args': {
            'track': 'Bass', 'length': 32, 'notes': {'$result': 'material-1', 'field': 'notes'}}}, '2')]},
    ], []))
    agent.start('faca um tech house pista', 'openai', 'model', 'token', '')
    state = finished(agent)
    assert state['state'] == 'review'
    assert state['pending'][0]['args']['args']['notes'] == generated['notes']
    assert not any(n == 'ableton_command' for n, _ in connection.calls)
    assert ('genre_knowledge', {'genre': 'tech house'}) in connection.calls
    with pytest.raises(ValueError, match='campo'):
        agent._resolve_material({'$result': 'material-1', 'field': 'missing'})


def test_history_pruning_keeps_complete_recent_call_result_pairs_and_encrypted_reasoning():
    agent = ProducerAgent(Connection())
    reasoning = {'type': 'reasoning', 'encrypted_content': 'opaque'}
    call = function('ableton_status', {}, 'recent-call')
    output = {'type': 'function_call_output', 'call_id': 'recent-call', 'output': '{}'}
    agent._history = [{'role': 'user', 'content': 'old' * 10000},
                      {'role': 'user', 'content': 'keep'}, reasoning, call, output,
                      {'role': 'user', 'content': 'latest'}]
    agent._turn_starts = [0, 1, 5]
    agent._memory = ['old', 'keep', 'latest']
    agent._prepare_turn('new')
    assert agent._history[0]['content'] == 'keep'
    assert reasoning in agent._history and call in agent._history and output in agent._history
    assert agent._turn_starts == [0, 4, 5] and agent._history_pruned


def test_actual_usage_is_summed_without_estimating_tokens_when_not_reported():
    connection, requests = Connection(), []
    responses = [{'output': [function('ableton_status', {})], 'usage': {'input_tokens': 100, 'output_tokens': 20}},
                 message(usage={'input_tokens': 130, 'output_tokens': 30, 'input_tokens_details': {'cached_tokens': 60}})]
    agent = ProducerAgent(connection, transport_responses(responses, requests))
    agent.start('Analise', 'openai', 'model', 'token', 'Jazz')
    efficiency = finished(agent)['efficiency']
    assert efficiency['requests'] == 2 and efficiency['input_tokens'] == 230 and efficiency['output_tokens'] == 50
    assert efficiency['cached_tokens'] == 60
    agent.reset()
    assert agent.status()['efficiency'] == {}


def test_large_or_partially_failed_batches_do_not_continue_later_mutations():
    connection = Connection()
    connection.call = lambda n, a: [{'ok': False, 'error': 'missing track'}]
    agent = ProducerAgent(connection)
    results = agent._tool_results([{'id': '1', 'name': 'ableton_batch', 'args': {'commands': []}},
                                   {'id': '2', 'name': 'ableton_command', 'args': {'cmd': 'set_tempo'}}], 'anthropic')
    assert all(r['is_error'] for r in results)
    assert 'anterior falhou' in results[1]['content']



def test_pocket_nested_notes_reach_review_without_live_writes():
    from ableton_claude.music.pocket import sketch
    connection = Connection()
    connection.tools += [tool('music_pocket_sketch')]
    generated = sketch()
    original = connection.call
    connection.call = lambda name, args=None: generated if name == 'music_pocket_sketch' else original(name, args)
    agent = ProducerAgent(connection, transport_responses([
        {'output': [function('music_pocket_sketch', {})]},
        {'output': [function('ableton_command', {'cmd': 'create_midi_clip', 'args': {
            'track': 'Bass', 'length': 32, 'notes': {'$result': 'material-1', 'field': 'stripped.bass'}}}, '2')]},
    ], []))
    agent.start('melhore o groove', 'openai', 'model', 'token', '')
    state = finished(agent)
    assert state['state'] == 'review'
    assert state['pending'][0]['args']['args']['notes'] == generated['stripped']['bass']
    assert not any(n == 'ableton_command' for n, _ in connection.calls)
    for field in ('main.missing', 'main.kick.0', '__class__', '', 5):
        with pytest.raises(ValueError, match='campo'):
            agent._resolve_material({'$result': 'material-1', 'field': field})
