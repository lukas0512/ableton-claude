"""Exercise review → apply → read back → revert through real desktop MCP/Live.

Uses a deterministic simulated model; no provider requests, tokens or credentials.
Requires an explicitly confirmed project copy. Example from mcp_server:
  .venv/bin/python ../scripts/qa_producer_live.py --copy-confirmed --track 'Bass'
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude.desktop_agent import ProducerAgent
from ableton_claude.desktop_mcp import LocalMCP


def wait(agent):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        state = agent.status()
        if state['state'] != 'running':
            if state['error']:
                raise RuntimeError(state['error'])
            return state
        time.sleep(.1)
    raise TimeoutError('Producer did not finish within 60 seconds.')


def check(track):
    with tempfile.TemporaryDirectory(prefix='ableton-claude-review-qa-') as data:
        connection = LocalMCP({'command': sys.executable,
                               'args': ['-m', 'ableton_claude.desktop', '--mcp']}, data)
        connection.start()
        receipt, reverted, attempted = [], False, False
        baseline = None
        try:
            before = connection.call('ableton_command', {'cmd': 'get_track', 'args': {'track': track}})
            baseline = before['vol_db']
            if not isinstance(baseline, (int, float)) or baseline < -50:
                raise ValueError('Choose an audible track with a measurable volume.')
            proposed = baseline - 2
            responses = [
                {'output': [{'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'output_text', 'text': 'Teste de integração: reduzir esta faixa em 2 dB, conferir o valor no Live e restaurar o original.'}]},
                    {'type': 'function_call', 'call_id': 'qa-edit', 'name': 'ableton_command',
                     'arguments': json.dumps({'cmd': 'set_track', 'args': {'track': track, 'volume_db': proposed}})}]},
                {'output': [{'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'output_text', 'text': 'Comando concluído. A verificação do valor será feita pelo teste local.'}]}]},
            ]
            transport = httpx.MockTransport(lambda request: httpx.Response(200, json=responses.pop(0)))
            agent = ProducerAgent(connection, transport)
            agent.start('Teste de revisão do volume', 'openai', 'qa-model', 'offline-test-token', '')
            review = wait(agent)
            assert review['state'] == 'review' and review['pending'][0]['preview']
            unchanged = connection.call('ableton_command', {'cmd': 'get_track', 'args': {'track': track}})
            assert unchanged['vol_db'] == baseline, 'Edit ran before review!'
            attempted = True
            agent.start('', 'openai', 'qa-model', 'offline-test-token', '', approve=True)
            applied = wait(agent)
            receipt = applied['execution']
            assert receipt[0]['status'] == 'applied' and receipt[0].get('change_id') is not None
            after = connection.call('ableton_command', {'cmd': 'get_track', 'args': {'track': track}})
            assert abs(after['vol_db'] - proposed) < .15, after
            revert = connection.call('revert_changes', {'ids': [receipt[0]['change_id']]})
            restored = connection.call('ableton_command', {'cmd': 'get_track', 'args': {'track': track}})
            assert abs(restored['vol_db'] - baseline) < .15, revert
            reverted = True
            print(json.dumps({'review_before_edit': 'ok', 'receipt': receipt,
                              'live_readback_db': after['vol_db'], 'restored_db': restored['vol_db'],
                              'provider': 'simulated; no external requests'}, ensure_ascii=False))
        finally:
            if attempted and not reverted and baseline is not None:
                connection.call('ableton_command', {'cmd': 'set_track', 'args': {'track': track, 'volume_db': baseline}})
            connection.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--track', required=True)
    parser.add_argument('--copy-confirmed', action='store_true')
    args = parser.parse_args()
    if not args.copy_confirmed:
        parser.error('Save/open a project copy and explicitly pass --copy-confirmed.')
    check(args.track)
