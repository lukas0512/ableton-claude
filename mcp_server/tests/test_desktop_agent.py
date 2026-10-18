import json
import time

import httpx
import pytest

from ableton_claude.desktop_agent import ProducerAgent, available_models


class Connection:
    def __init__(self):
        self.calls = []
        self.tools = [{"name": name, "description": "test tool", "parameters": {"type": "object", "properties": {}}}
                      for name in ("producer_brief", "ableton_status", "ableton_command")]

    def call(self, name, args=None):
        self.calls.append((name, args or {}))
        return "GENRE CONTEXT: Jazz" if name == "producer_brief" else {"tempo": 120}


def finished(agent):
    end = time.monotonic() + 3
    while time.monotonic() < end:
        state = agent.status()
        if state["state"] != "running":
            return state
        time.sleep(0.01)
    pytest.fail("agent did not finish")


def transport_responses(responses, requests):
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=responses.pop(0))
    return httpx.MockTransport(respond)


def anthropic_call(cmd="set_tempo"):
    return {"content": [{"type": "text", "text": "Proponho ajustar o tempo."},
                        {"type": "tool_use", "id": "edit-1", "name": "ableton_command",
                         "input": {"cmd": cmd, "args": {"bpm": 125}}}]}


def test_mutations_wait_for_review_and_approved_call_resumes_conversation():
    connection, requests = Connection(), []
    responses = [anthropic_call(), {"content": [{"type": "text", "text": "Tempo ajustado."}]}]
    agent = ProducerAgent(connection, transport_responses(responses, requests))
    agent.start("Ajuste o tempo", "anthropic", "test-model", "test-key", "Jazz")
    assert finished(agent)["state"] == "review"
    assert not any(name == "ableton_command" for name, _ in connection.calls)
    agent.start("", "anthropic", "test-model", "test-key", "Jazz", approve=True)
    state = finished(agent)
    assert state["state"] == "idle"
    assert ("ableton_command", {"cmd": "set_tempo", "args": {"bpm": 125}}) in connection.calls
    assert requests[1]["messages"][-1]["content"][0]["tool_use_id"] == "edit-1"
    assert "test-key" not in json.dumps(state)


def test_discarded_proposal_never_executes_mutating_tools():
    connection, requests = Connection(), []
    responses = [anthropic_call(), {"content": [{"type": "text", "text": "Proposta descartada."}]}]
    agent = ProducerAgent(connection, transport_responses(responses, requests))
    agent.start("Proponha", "anthropic", "model", "key", "Jazz")
    finished(agent)
    agent.start("", "anthropic", "model", "key", "Jazz", approve=False)
    assert finished(agent)["state"] == "idle"
    assert not any(name == "ableton_command" for name, _ in connection.calls)
    assert requests[-1]["messages"][-1]["content"][0]["is_error"]


def test_openai_preserves_reasoning_and_matches_function_call_outputs():
    connection, requests = Connection(), []
    reasoning = {"type": "reasoning", "id": "reason-1", "summary": [], "encrypted_content": "opaque"}
    responses = [{"output": [reasoning, {"type": "function_call", "call_id": "read-1",
                                         "name": "ableton_status", "arguments": "{}"}]},
                 {"output": [{"type": "message", "role": "assistant", "content": [
                     {"type": "output_text", "text": "Seu projeto tem 120 BPM."}]}]}]
    agent = ProducerAgent(connection, transport_responses(responses, requests))
    agent.start("Analise", "openai", "model", "key", "Jazz")
    assert finished(agent)["state"] == "idle"
    assert reasoning in requests[1]["input"]
    assert requests[1]["input"][-1]["call_id"] == "read-1"
    assert requests[1]["store"] is False
    assert connection.calls[-1][0] == "ableton_status"


def test_wrong_provider_cannot_apply_an_existing_proposal():
    agent = ProducerAgent(Connection(), transport_responses([anthropic_call()], []))
    agent.start("Proponha", "anthropic", "model", "key", "Jazz")
    finished(agent)
    with pytest.raises(ValueError, match="mesmo assistente"):
        agent.start("", "openai", "other", "key", "Jazz", approve=True)


def test_api_probe_is_never_executed_even_after_review():
    connection = Connection()
    agent = ProducerAgent(connection, transport_responses([anthropic_call("api_probe"), {"content": []}], []))
    agent.start("Proponha", "anthropic", "model", "key", "Jazz")
    finished(agent)
    agent.start("", "anthropic", "model", "key", "Jazz", approve=True)
    finished(agent)
    assert not any(name == "ableton_command" for name, _ in connection.calls)


def test_authentication_error_is_actionable_and_does_not_expose_key():
    transport = httpx.MockTransport(lambda req: httpx.Response(401, json={"error": "private"}))
    agent = ProducerAgent(Connection(), transport)
    agent.start("Analise", "openai", "model", "secret-test-key", "Jazz")
    state = finished(agent)
    assert state["state"] == "error" and "chave" in state["error"]
    assert "secret-test-key" not in json.dumps(state)


def test_model_access_uses_official_provider_and_filters_non_chat_models():
    requests = []
    def respond(req):
        requests.append(str(req.url))
        return httpx.Response(200, json={"data": [{"id": "gpt-test"}, {"id": "gpt-image-test"}, {"id": "other"}]})
    assert available_models("openai", "key", httpx.MockTransport(respond)) == [{"id": "gpt-test", "name": "gpt-test"}]
    assert requests == ["https://api.openai.com/v1/models"]


def test_failed_mutation_stops_later_changes_in_the_group():
    connection = Connection()
    def fail(name, args=None):
        connection.calls.append((name, args))
        raise ValueError("track not found")
    connection.call = fail
    agent = ProducerAgent(connection)
    calls = [{"id": "1", "name": "ableton_command", "args": {"cmd": "set_track"}},
             {"id": "2", "name": "ableton_command", "args": {"cmd": "delete_track"}}]
    results = agent._tool_results(calls, "anthropic")
    assert len(connection.calls) == 1
    assert all(result["is_error"] for result in results)


def test_chatgpt_plan_streams_namespaced_tools_and_requires_completion():
    connection, requests = Connection(), []
    response = {'status': 'completed', 'output': [{'type': 'message', 'role': 'assistant',
               'content': [{'type': 'output_text', 'text': 'Vamos produzir.'}]}]}
    def respond(request):
        requests.append(json.loads(request.content))
        events = [{'type': 'response.output_text.delta', 'delta': 'Vamos produzir.'},
                  {'type': 'response.completed', 'response': response}]
        return httpx.Response(200, text=''.join('data: ' + json.dumps(e) + '\n\n' for e in events),
                              headers={'content-type': 'text/event-stream'})
    agent = ProducerAgent(connection, httpx.MockTransport(respond))
    agent.start('Olá', 'chatgpt', 'test-model', 'oauth-token', 'Jazz')
    state = finished(agent)
    assert state['state'] == 'idle' and state['messages'][-1]['text'] == 'Vamos produzir.'
    assert requests[0]['stream'] is True and requests[0]['store'] is False
    assert 'max_output_tokens' not in requests[0]
    assert requests[0]['tools'][0]['type'] == 'namespace'
    assert 'oauth-token' not in json.dumps(state)


@pytest.mark.parametrize('ending', ['disconnect', 'failure', 'incomplete', 'limit'])
def test_chatgpt_partial_stream_and_usage_errors_never_execute_tools(ending):
    response = {'output': [{'type': 'function_call', 'call_id': 'edit-1', 'name': 'ableton_command',
                            'arguments': '{"cmd":"set_tempo"}'}]}
    events = [{'type': 'response.output_text.delta', 'delta': 'Analisando…'},
              {'type': 'response.output_item.done', 'output_index': 0, 'item': response['output'][0]}]
    if ending != 'disconnect':
        events.append({'type': 'response.incomplete' if ending == 'incomplete' else 'response.failed',
                       'response': response | {'error': {'code': 'subscription_sharing_usage_limit_exceeded' if ending == 'limit' else 'error'}}})
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text=''.join('data: ' + json.dumps(e) + '\n\n' for e in events)))
    connection = Connection()
    agent = ProducerAgent(connection, transport)
    agent.start('Analise', 'chatgpt', 'model', 'token', 'Jazz')
    state = finished(agent)
    assert state['state'] == 'error' and state['pending'] == []
    assert not any(name == 'ableton_command' for name, _ in connection.calls)
    if ending == 'limit':
        assert 'limite' in state['error']


def test_incomplete_response_without_error_details_has_recovery_message():
    event = {'type': 'response.incomplete', 'response': {'error': None}}
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text='data: ' + json.dumps(event) + '\n\n'))
    agent = ProducerAgent(Connection(), transport)
    agent.start('Analise', 'chatgpt', 'model', 'token', 'Jazz')
    state = finished(agent)
    assert state['state'] == 'error' and 'interrompida' in state['error']


def test_plan_stream_preserves_final_items_when_terminal_output_is_empty():
    from ableton_claude.desktop_agent import stream_chatgpt
    reasoning = {'id': 'r1', 'type': 'reasoning', 'encrypted_content': 'final-opaque', 'summary': []}
    call = {'type': 'function_call', 'call_id': 'c1', 'name': 'ableton_status', 'arguments': '{}'}
    events = [{'type': 'response.output_item.done', 'output_index': 0, 'item': reasoning},
              {'type': 'response.output_item.done', 'output_index': 1, 'item': call},
              {'type': 'response.completed', 'response': {'status': 'completed', 'output': [], 'usage': {'input_tokens': 100}}}]
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text=''.join('data: ' + json.dumps(e) + '\n\n' for e in events)))
    result = stream_chatgpt('token', {}, transport)
    assert result['output'] == [reasoning, call] and result['usage']['input_tokens'] == 100


def test_plan_stream_deduplicates_items_and_prefers_final_encrypted_reasoning():
    from ableton_claude.desktop_agent import stream_chatgpt
    old = {'type': 'reasoning', 'encrypted_content': None}
    final = {'type': 'reasoning', 'encrypted_content': 'complete'}
    events = [{'type': 'response.output_item.done', 'output_index': 0, 'item': final},
              {'type': 'response.completed', 'response': {'status': 'completed', 'output': [old]}}]
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text=''.join('data: ' + json.dumps(e) + '\n\n' for e in events)))
    assert stream_chatgpt('token', {}, transport)['output'] == [final]


def test_completed_but_empty_response_is_an_actionable_error():
    agent = ProducerAgent(Connection(), transport_responses([{'output': []}], []))
    agent.start('Analise', 'openai', 'model', 'token', 'Jazz')
    state = finished(agent)
    assert state['state'] == 'error' and 'resposta utilizável' in state['error']


def test_guided_workflow_rejects_premature_arrangement_without_poisoning_next_request(tmp_path):
    from ableton_claude.production_session import ProductionSession
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    flow = ProductionSession(tmp_path, write)
    flow.begin({'tracks': []}, copy_confirmed=True)
    responses = [anthropic_call('set_tempo'), {'content': [{'type': 'text', 'text': 'Vamos construir o loop curto.'}]}]
    connection, requests = Connection(), []
    agent = ProducerAgent(connection, transport_responses(responses, requests), production=flow)
    agent.start('Abra logo o arranjo', 'anthropic', 'model', 'key', 'Jazz')
    state = finished(agent)
    assert state['state'] == 'error' and not state['pending']
    assert not any(n == 'ableton_command' for n, _ in connection.calls)
    agent.start('Vamos fazer o loop primeiro', 'anthropic', 'model', 'key', 'Jazz')
    assert finished(agent)['state'] == 'idle'
    assert 'MUSICAL WORKFLOW' in requests[-1]['system']
    assert not any(part.get('type') == 'tool_use' for msg in requests[-1]['messages']
                   if isinstance(msg['content'], list) for part in msg['content'])
    assert flow.status()['stage'] == 'loop'


def test_existing_project_changes_still_require_review_without_loop_approval(tmp_path):
    from ableton_claude.production_session import ProductionSession
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    flow = ProductionSession(tmp_path, write)
    flow.begin_existing({'tracks': [{'name': 'Hook'}]}, True, 'Minha track', 'mix')
    response = {'content': [{'type': 'tool_use', 'id': 'edit-hook', 'name': 'ableton_command',
                            'input': {'cmd': 'set_track', 'args': {'track': 'Hook', 'volume_db': -5}}}]}
    connection, requests = Connection(), []
    agent = ProducerAgent(connection, transport_responses([response, {'content': [{'type': 'text', 'text': 'Ouça a melhoria.'}]}], requests), production=flow)
    agent.start('Melhore o equilíbrio da minha track', 'anthropic', 'model', 'key', 'Jazz')
    assert finished(agent)['state'] == 'review'
    assert 'EXISTING PROJECT WORKFLOW' in requests[0]['system']
    assert not any(n == 'ableton_command' for n, _ in connection.calls)
    agent.start('', 'anthropic', 'model', 'key', 'Jazz', approve=True)
    assert finished(agent)['state'] == 'idle'
    assert ('ableton_command', {'cmd': 'set_track', 'args': {'track': 'Hook', 'volume_db': -5}}) in connection.calls
    assert flow.status()['stage'] == 'existing' and flow.status()['approvals'] == []
