import json

import pytest

from ableton_claude import client


class Socket:
    def __init__(self, reply):
        self.reply = reply
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def settimeout(self, timeout):
        pass

    def sendall(self, data):
        self.sent.append(json.loads(data))

    def recv(self, size):
        reply, self.reply = self.reply, b''
        return reply


@pytest.mark.parametrize('reply', [b'', b'{"ok":true}', b'garbage\n', b'[]\n',
                                 b'{"id":-1,"ok":true}\n', b'\xff\n'])
def test_disconnection_and_invalid_protocol_are_actionable_without_replaying(monkeypatch, reply):
    sock = Socket(reply)
    monkeypatch.setattr(client.socket, 'create_connection', lambda *args, **kwargs: sock)
    with pytest.raises(client.BridgeError, match='Check Live before retrying'):
        client.call('create_track', {'kind': 'midi'})
    assert len(sock.sent) == 1


def test_matching_complete_response_returns_result(monkeypatch):
    sock = Socket(b'')
    def recv(size):
        return json.dumps({'id': sock.sent[-1]['id'], 'ok': True, 'result': {'tempo': 123}}).encode() + b'\n'
    sock.recv = recv
    monkeypatch.setattr(client.socket, 'create_connection', lambda *args, **kwargs: sock)
    assert client.call('get_song') == {'tempo': 123}
