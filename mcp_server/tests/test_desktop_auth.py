import json
import time
from urllib.parse import parse_qs, urlparse
from concurrent.futures import ThreadPoolExecutor

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from ableton_claude.desktop_auth import ChatGPTAuth, ISSUER, TOKEN, SCOPE


@pytest.fixture
def login(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())) | {'kid': 'test'}
    calls, tokens = [], {}
    def respond(request):
        calls.append(request)
        if request.url.path == '/.well-known/jwks.json':
            return httpx.Response(200, json={'keys': [jwk]})
        if request.url.path == '/api/accounts/oauth/token':
            return httpx.Response(200, json=dict(tokens))
        if request.url.path == '/v1/models':
            return httpx.Response(200, json={'models': [
                {'slug': 'test-model', 'display_name': 'Test Model', 'visibility': 'list'},
                {'slug': 'hidden-model', 'visibility': 'hidden'}]})
        if request.url.path == '/.well-known/openid-configuration':
            return httpx.Response(200, json={'revocation_endpoint': ISSUER + '/revoke'})
        if request.url.path == '/revoke':
            return httpx.Response(200)
        raise AssertionError(str(request.url))
    auth = ChatGPTAuth(tmp_path, httpx.MockTransport(respond))
    def prepare(**claims_overrides):
        query = parse_qs(urlparse(auth.begin()['auth_url']).query)
        claims = {'iss': ISSUER, 'aud': 'oaiapp_test', 'sub': 'user-1', 'email': 'test@example.invalid',
                  'exp': time.time() + 300, 'iat': time.time(), 'nonce': query['nonce'][0]} | claims_overrides
        tokens.update(access_token='access-secret', refresh_token='refresh-secret',
                      id_token=jwt.encode(claims, key, algorithm='RS256', headers={'kid': 'test'}),
                      scope=SCOPE, expires_in=3600, token_type='Bearer')
        return {'state': query['state'][0], 'code': 'authorization-code', 'client_id': 'oaiapp_test'}
    yield auth, prepare, calls, tokens
    auth.cancel()


def test_pkce_loopback_host_identity_and_issued_client_exchange(login):
    auth, prepare, calls, tokens = login
    callback = prepare()
    pending = dict(auth._pending)
    assert pending['redirect_uri'].startswith('http://127.0.0.1:')
    assert pending['redirect_uri'].endswith('/auth/callback')
    auth.finish(callback)
    request = next(r for r in calls if str(r.url) == TOKEN)
    form = parse_qs(request.content.decode())
    assert form['client_id'] == ['oaiapp_test']
    assert form['code_verifier'] == [pending['verifier']]
    assert form['redirect_uri'] == [pending['redirect_uri']]
    status = auth.status()
    assert status['connected'] and status['models'] == [{'id': 'test-model', 'name': 'Test Model'}]
    assert 'secret' not in json.dumps(status) and 'id_token' not in json.dumps(status)
    assert (auth.directory / 'accounts.json').stat().st_mode & 0o777 == 0o600
    assert auth.directory.stat().st_mode & 0o777 == 0o700
    host = auth._load()['host_id']
    query = parse_qs(urlparse(auth.begin()['auth_url']).query)
    assert query['ext_agent_host_id'] == [host]
    assert query['client_id'] == ['oaiapp_test']
    assert 'agent_name_hint' not in query
    with pytest.raises(ValueError):
        auth.finish(callback)  # old callback cannot consume a new transaction


@pytest.mark.parametrize('bad', [{'nonce': 'wrong'}, {'aud': 'different'}, {'iss': 'https://attacker.invalid'},
                                  {'exp': time.time() - 60}, {'sub': ''}])
def test_signed_identity_requires_nonce_audience_issuer_expiry_and_subject(login, bad):
    auth, prepare, calls, tokens = login
    callback = prepare(**bad)
    with pytest.raises(ValueError, match='validar'):
        auth.finish(callback)
    assert not auth.status()['connected']
    assert not auth._load()['accounts']


def test_csrf_mismatch_does_not_exchange_or_consume_legitimate_attempt(login):
    auth, prepare, calls, tokens = login
    callback = prepare()
    with pytest.raises(ValueError):
        auth.finish(callback | {'state': 'attacker'})
    assert not calls and auth.status()['awaiting_login']
    auth.finish(callback)
    with pytest.raises(ValueError):
        auth.finish(callback)


def test_identity_only_permission_never_grants_inference(login):
    auth, prepare, calls, tokens = login
    callback = prepare()
    tokens['scope'] = 'openid email profile'
    with pytest.raises(ValueError, match='não autorizou'):
        auth.finish(callback)
    assert not auth.status()['connected']
    assert 'access-secret' not in (auth.directory / 'accounts.json').read_text()


def test_refresh_rotates_once_and_retains_registration(login):
    auth, prepare, calls, tokens = login
    auth.finish(prepare())
    data = auth._load()
    data['accounts'][0]['expires_at'] = 0
    auth._save(data)
    calls.clear()
    tokens.clear()
    tokens.update(access_token='new-access', refresh_token='new-refresh', expires_in=3600)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: auth.access_token(), range(2))) == ['new-access', 'new-access']
    assert len(calls) == 1
    form = parse_qs(calls[0].content.decode())
    assert form['grant_type'] == ['refresh_token'] and form['client_id'] == ['oaiapp_test']
    assert 'scope' not in form
    assert auth._load()['accounts'][0]['refresh_token'] == 'new-refresh'


def test_logout_revokes_and_clears_credentials_but_retains_registration(login):
    auth, prepare, calls, tokens = login
    auth.finish(prepare())
    assert auth.logout()['message'] == 'Conta desconectada.'
    assert not auth.status()['connected']
    data = auth._load()['accounts'][0]
    assert data['client_id'] == 'oaiapp_test' and data['subject'] == 'user-1'
    assert not any(name in data for name in ('access_token', 'refresh_token', 'id_token'))
    query = parse_qs(urlparse(auth.begin()['auth_url']).query)
    assert 'id_token_hint' not in query and query['client_id'] == ['oaiapp_test']


def test_new_registration_cannot_replace_returning_account_identity(login):
    auth, prepare, calls, tokens = login
    auth.finish(prepare())
    callback = prepare(sub='other-user')
    with pytest.raises(ValueError, match='validar'):
        auth.finish(callback)
    assert auth._load()['accounts'][0]['subject'] == 'user-1'
    assert auth.status()['connected']
