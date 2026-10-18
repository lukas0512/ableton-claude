import json

from ableton_claude import proposals
from ableton_claude.desktop_agent import ProducerAgent
from test_desktop_agent import Connection, finished, transport_responses


def batch(commands):
    return {'id': 'batch-1', 'name': 'ableton_batch', 'args': {'commands': commands}}


def test_review_exposes_actual_targets_values_and_full_midi_count():
    call = batch([
        {'cmd': 'set_track', 'args': {'track': 'Bass', 'volume_db': -8, 'mute': False}},
        {'cmd': 'create_midi_clip', 'args': {'track': 'Hook', 'bar': 9, 'length': 32,
                                         'notes': [[60, 0, 1, 90]] * 600}},
    ])
    preview = proposals.preview(call)
    assert len(preview) == 2
    assert 'Bass' in preview[0]['detail'] and '-8' in preview[0]['detail']
    assert 'False' in preview[0]['detail']
    assert '600 notas MIDI' in preview[1]['detail'] and 'Compasso: 9' in preview[1]['detail']


def test_batch_stops_at_first_failure_preserving_receipts_and_change_ids():
    connection = Connection()
    def execute(name, args=None):
        connection.calls.append((name, args))
        if args['cmd'] == 'load_device':
            raise ValueError('Instrumento indisponível')
        return {'change_id': 17, 'name': 'Hook'}
    connection.call = execute
    agent = ProducerAgent(connection)
    call = batch([
        {'cmd': 'create_track', 'args': {'name': 'Hook', 'kind': 'midi'}},
        {'cmd': 'load_device', 'args': {'track': 'Hook', 'query': 'Missing'}},
        {'cmd': 'create_midi_clip', 'args': {'track': 'Hook', 'notes': [[60, 0, 1, 90]]}},
    ])
    later = {'id': 'later', 'name': 'ableton_command', 'args': {'cmd': 'set_tempo', 'args': {'bpm': 126}}}
    results = agent._tool_results([call, later], 'openai')
    assert [args['cmd'] for _, args in connection.calls] == ['create_track', 'load_device']
    assert all(name == 'ableton_command' for name, _ in connection.calls)
    assert [item['status'] for item in agent.status()['execution']] == ['applied', 'failed', 'skipped', 'skipped']
    assert agent.status()['execution'][0]['change_id'] == 17
    assert 'Instrumento indisponível' in agent.status()['execution'][1]['error']
    assert json.loads(results[0]['output'])[2]['skipped']


def test_acknowledged_failure_stops_batch_without_exception():
    connection = Connection()
    def execute(name, args=None):
        connection.calls.append((name, args))
        return {'ok': False, 'error': 'Device failed'}
    connection.call = execute
    agent = ProducerAgent(connection)
    agent._tool_results([batch([{'cmd': 'set_tempo'}, {'cmd': 'delete_track'}])], 'anthropic')
    assert len(connection.calls) == 1
    assert [r['status'] for r in agent.execution] == ['failed', 'skipped']


def test_skipped_entire_batch_marks_every_command_as_skipped():
    connection = Connection()
    connection.call = lambda *args: {'error': 'offline'}
    agent = ProducerAgent(connection)
    first = {'id': 'first', 'name': 'ableton_command', 'args': {'cmd': 'set_tempo'}}
    agent._tool_results([first, batch([{'cmd': 'create_track'}, {'cmd': 'load_device'}])], 'openai')
    assert [r['status'] for r in agent.execution] == ['failed', 'skipped', 'skipped']


def test_discard_has_no_execution_receipt_and_reset_clears_previous_receipt():
    agent = ProducerAgent(Connection())
    call = batch([{'cmd': 'set_tempo', 'args': {'bpm': 125}}])
    agent._tool_results([call], 'openai', approved=False)
    assert agent.execution == []
    agent._tool_results([call], 'openai')
    assert agent.execution[0]['status'] == 'applied'
    assert agent.reset()['execution'] == []


def test_receipt_survives_provider_failure_after_changes_were_applied():
    connection = Connection()
    agent = ProducerAgent(connection, transport_responses([{'output': []}], []))
    agent.pending = [{'id': 'edit', 'name': 'ableton_command',
                      'args': {'cmd': 'set_tempo', 'args': {'bpm': 125}}}]
    agent._provider_model = ('openai', 'model')
    agent.start('', 'openai', 'model', 'key', '', approve=True)
    state = finished(agent)
    assert state['state'] == 'error'
    assert state['pending'] == [] and state['execution'][0]['status'] == 'applied'
    assert sum(n == 'ableton_command' for n, _ in connection.calls) == 1


def test_invalid_batch_never_reaches_review_or_live():
    for commands in [[], [{'cmd': 'set_tempo', 'args': 'invalid'}], [{}]]:
        connection = Connection()
        connection.tools.append({'name': 'ableton_batch', 'description': '', 'parameters': {}})
        response = {'output': [{'type': 'function_call', 'call_id': 'b', 'name': 'ableton_batch',
                               'arguments': json.dumps({'commands': commands})}]}
        agent = ProducerAgent(connection, transport_responses([response], []))
        agent.start('Proponha', 'openai', 'model', 'key', '')
        state = finished(agent)
        assert state['state'] == 'error' and not state['pending']
        assert not any(n in {'ableton_batch', 'ableton_command'} for n, _ in connection.calls)


def test_changed_project_blocks_application_and_allows_discard():
    from test_desktop_agent import anthropic_call
    connection = Connection()
    original = connection.call
    overview = {'tempo': 120, 'tracks': [{'i': 0, 'name': 'Original'}], 'time_beats': 0}
    def execute(name, args=None):
        if name == 'ableton_status':
            return json.loads(json.dumps(overview))
        return original(name, args)
    connection.call = execute
    agent = ProducerAgent(connection, transport_responses([
        anthropic_call(), {'content': [{'type': 'text', 'text': 'Descartada.'}]}], []))
    agent.start('Ajuste o tempo', 'anthropic', 'model', 'key', '')
    assert finished(agent)['state'] == 'review'
    overview['tracks'][0]['name'] = 'Outro projeto'
    agent.start('', 'anthropic', 'model', 'key', '', approve=True)
    state = finished(agent)
    assert state['state'] == 'error' and 'projeto mudou' in state['error']
    assert state['pending'] and state['execution'] == []
    assert not any(n == 'ableton_command' for n, _ in connection.calls)
    agent.start('', 'anthropic', 'model', 'key', '', approve=False)
    assert finished(agent)['state'] == 'idle'
    assert not agent.pending


def test_project_guard_ignores_transport_but_detects_track_and_mix_changes():
    overview = {'tempo': 123, 'tracks': [{'name': 'Bass', 'vol_db': -6}],
                'time_beats': 32, 'is_playing': False, 'song_length_beats': 200}
    baseline = proposals.project_state(overview)
    assert proposals.project_state(dict(overview, time_beats=64, is_playing=True)) == baseline
    assert proposals.project_state(dict(overview, tempo=124)) != baseline
    assert proposals.project_state(dict(overview, tracks=[{'name': 'Bass', 'vol_db': -12}])) != baseline


def test_failed_review_snapshot_does_not_poison_the_next_model_request():
    from test_desktop_agent import anthropic_call
    connection, requests = Connection(), []
    original = connection.call
    reads = 0
    def execute(name, args=None):
        nonlocal reads
        if name == 'ableton_status':
            reads += 1
            if reads == 2:
                raise ValueError('Live desconectado')
        return original(name, args)
    connection.call = execute
    agent = ProducerAgent(connection, transport_responses([
        anthropic_call(), {'content': [{'type': 'text', 'text': 'Projeto reconectado.'}]}], requests))
    agent.start('Ajuste o tempo', 'anthropic', 'model', 'key', '')
    state = finished(agent)
    assert state['state'] == 'error' and not state['pending']
    agent.start('Tente novamente', 'anthropic', 'model', 'key', '')
    assert finished(agent)['state'] == 'idle'
    assert not any(part.get('type') == 'tool_use' for message in requests[-1]['messages']
                   if isinstance(message['content'], list) for part in message['content'])
