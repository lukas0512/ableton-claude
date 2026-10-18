"""Official Sign in with ChatGPT for a locally hosted client.

PKCE + OIDC, app-owned registrations, and protected rotating credentials.
Never reads credentials belonging to Codex, Claude, or browser sessions.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
import uuid

import httpx
import jwt

ISSUER = 'https://auth.openai.com'
AUTHORIZE = ISSUER + '/api/accounts/authorize'
TOKEN = ISSUER + '/api/accounts/oauth/token'
RESOURCE = 'https://api.openai.com/v1'
SCOPE = 'openid profile email offline_access resource.invoke chatgpt.tokens.use.direct'
USAGE_URL = 'https://chatgpt.com/#settings/Usage'


class ChatGPTAuth:
    def __init__(self, data_dir, transport=None):
        self.directory = Path(data_dir) / 'Authentication'
        self.transport = transport
        self._lock = threading.RLock()
        self._pending = None
        self._server = None
        self._error = None
        self._jwks = None
        self._jwks_at = 0

    def _load(self):
        path = self.directory / 'accounts.json'
        if not path.exists():
            return {'host_id': 'urn:uuid:' + str(uuid.uuid4()), 'active': None, 'accounts': []}
        return json.loads(path.read_text())

    def _save(self, value):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        fd, name = tempfile.mkstemp(dir=self.directory, prefix='accounts.', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as file:
                json.dump(value, file)
            os.replace(name, self.directory / 'accounts.json')
        finally:
            if os.path.exists(name):
                os.unlink(name)

    @staticmethod
    def _active(data):
        return next((a for a in data['accounts'] if a['id'] == data.get('active')), None)

    def status(self):
        with self._lock:
            data = self._load()
            account = self._active(data)
            def public(a):
                return {'id': a['id'], 'email': a.get('email', ''), 'label': a.get('email') or 'Conta ChatGPT',
                        'connected': bool(a.get('access_token') and 'chatgpt.tokens.use.direct' in a.get('scopes', []))}
            return {'connected': bool(account and public(account)['connected']),
                    'account': public(account) if account else None,
                    'accounts': [public(a) for a in data['accounts']],
                    'models': account.get('models', []) if account else [],
                    'awaiting_login': self._pending is not None, 'error': self._error,
                    'welcome_seen': account.get('welcome_seen', False) if account else False,
                    'usage_url': USAGE_URL}

    def _request(self, method, url, **kwargs):
        try:
            with httpx.Client(timeout=20, transport=self.transport, follow_redirects=False) as client:
                response = client.request(method, url, **kwargs)
            if response.is_error:
                code = response.json().get('error', '') if 'json' in response.headers.get('content-type', '') else ''
                if code in ('invalid_grant', 'invalid_token'):
                    raise ValueError('Sua sessão expirou ou foi revogada. Continue com ChatGPT novamente.')
                raise ValueError('A OpenAI não concluiu a conexão (HTTP %s). Confira a elegibilidade do plano e tente novamente.' % response.status_code)
            return response.json() if response.content else {}
        except httpx.HTTPError:
            raise ValueError('Não foi possível alcançar a OpenAI. Confira a internet e tente novamente.') from None

    def begin(self, new_account=False):
        self.cancel()
        with self._lock:
            data = self._load()
            self._save(data)  # Persist the host ID before first registration.
            account = None if new_account else self._active(data)
            verifier = secrets.token_urlsafe(48)
            pending = {'state': secrets.token_urlsafe(32), 'nonce': secrets.token_urlsafe(32),
                       'verifier': verifier, 'client_id': account['client_id'] if account else None,
                       'subject': account['subject'] if account else None, 'expires': time.time() + 600}
            owner = self
            class Callback(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass  # Authorization codes and login hints must never appear in logs.
                def do_GET(self):
                    parsed = urlparse(self.path)
                    if parsed.path != '/auth/callback':
                        self.send_error(404); return
                    query = parse_qs(parsed.query)
                    flat = {k: values[0] for k, values in query.items() if len(values) == 1}
                    try:
                        owner.finish(flat)
                        self.send_response(200)
                        message = 'Conta conectada. Pode voltar ao Ableton Claude.'
                    except ValueError:
                        self.send_response(400)
                        message = 'Não foi possível conectar. Volte ao app para ver o próximo passo.'
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.end_headers()
                    self.wfile.write(('<!doctype html><html lang="pt"><title>Ableton Claude</title><body><h1>' + message + '</h1></body></html>').encode())
            server = HTTPServer(('127.0.0.1', 0), Callback)
            server.timeout = 0.5
            pending['redirect_uri'] = 'http://127.0.0.1:%s/auth/callback' % server.server_port
            self._pending, self._server, self._error = pending, server, None
            params = {'client_id': pending['client_id'] or 'dynamic_agent_client',
                      'ext_agent_host_id': data['host_id'], 'response_type': 'code',
                      'redirect_uri': pending['redirect_uri'], 'scope': SCOPE, 'resource': RESOURCE,
                      'state': pending['state'], 'nonce': pending['nonce'], 'code_challenge_method': 'S256',
                      'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()}
            if not account:
                params['agent_name_hint'] = 'Ableton Claude'
            else:
                if account.get('id_token'):
                    params['id_token_hint'] = account['id_token']
                if account.get('email'):
                    params['login_hint'] = account['email']
            def listen():
                try:
                    while self._pending is pending and time.time() < pending['expires']:
                        server.handle_request()
                    with self._lock:
                        if self._pending is pending:
                            self._pending = None
                            self._error = 'O login expirou. Clique em Continuar com ChatGPT para tentar novamente.'
                finally:
                    server.server_close()
            threading.Thread(target=listen, daemon=True, name='chatgpt-login').start()
            return {'auth_url': AUTHORIZE + '?' + urlencode(params)}

    def cancel(self):
        with self._lock:
            self._pending = None

    def _identity(self, token, client_id, nonce=None, subject=None):
        try:
            header = jwt.get_unverified_header(token)
            if header.get('alg') != 'RS256':
                raise ValueError('unexpected algorithm')
            if not self._jwks or time.time() - self._jwks_at > 300 or not any(k.get('kid') == header.get('kid') for k in self._jwks['keys']):
                self._jwks = self._request('GET', ISSUER + '/.well-known/jwks.json')
                self._jwks_at = time.time()
            key = next(k for k in self._jwks['keys'] if k.get('kid') == header.get('kid'))
            claims = jwt.decode(token, jwt.PyJWK.from_dict(key).key, algorithms=['RS256'],
                                audience=client_id, issuer=ISSUER, leeway=5,
                                options={'require': ['sub', 'exp', 'iat']})
            if not isinstance(claims['sub'], str) or not claims['sub']:
                raise ValueError('missing identity')
            if nonce is not None and not secrets.compare_digest(str(claims.get('nonce', '')), nonce):
                raise ValueError('nonce mismatch')
            if subject is not None and claims['sub'] != subject:
                raise ValueError('account mismatch')
            return claims
        except (jwt.PyJWTError, ValueError, KeyError, StopIteration):
            raise ValueError('Não foi possível validar a identidade da conta. Inicie o login novamente.') from None

    @staticmethod
    def _credentials(tokens, previous=None):
        scopes = tokens.get('scope', ' '.join((previous or {}).get('scopes', []))).split()
        if 'chatgpt.tokens.use.direct' not in scopes:
            raise ValueError('A conta não autorizou usar o plano ChatGPT neste app. Habilite esse acesso no login.')
        if not tokens.get('access_token') or tokens.get('token_type', 'Bearer').lower() != 'bearer':
            raise ValueError('A OpenAI não retornou uma sessão válida.')
        return {'access_token': tokens['access_token'], 'refresh_token': tokens.get('refresh_token') or (previous or {}).get('refresh_token'),
                'id_token': tokens.get('id_token') or (previous or {}).get('id_token'), 'scopes': scopes,
                'expires_at': time.time() + int(tokens.get('expires_in', 3600))}

    def finish(self, query):
        with self._lock:
            pending = self._pending
            if not pending or not secrets.compare_digest(query.get('state', ''), pending['state']):
                raise ValueError('Login não corresponde à solicitação do app.')
            self._pending = None  # One-time consumption, including denial/error.
            try:
                if time.time() > pending['expires']:
                    raise ValueError('O login expirou. Tente novamente.')
                if query.get('error'):
                    raise ValueError('A conexão foi cancelada ou o plano não autorizou este app.')
                client_id = query.get('client_id') or pending['client_id']
                if not client_id or client_id == 'dynamic_agent_client' or (pending['client_id'] and client_id != pending['client_id']):
                    raise ValueError('O registro do app não foi confirmado. Inicie o login novamente.')
                if not query.get('code'):
                    raise ValueError('A OpenAI não retornou o código de autorização.')
                tokens = self._request('POST', TOKEN, data={'grant_type': 'authorization_code', 'client_id': client_id,
                      'code': query['code'], 'code_verifier': pending['verifier'], 'redirect_uri': pending['redirect_uri'], 'resource': RESOURCE})
                identity = self._identity(tokens.get('id_token', ''), client_id, pending['nonce'], pending['subject'])
                credentials = self._credentials(tokens)
                data = self._load()
                account = next((a for a in data['accounts'] if a['client_id'] == client_id and a['subject'] == identity['sub']), None)
                if not account:
                    account = {'id': str(uuid.uuid4()), 'client_id': client_id, 'subject': identity['sub']}
                    data['accounts'].append(account)
                account.update(credentials, email=identity.get('email', ''), models=[])
                data['active'] = account['id']
                self._save(data)
                self._error = None
            except (ValueError, TypeError) as error:
                self._error = str(error)
                raise ValueError(self._error) from None
        try:
            self.models()
        except ValueError as error:
            self._error = str(error)

    def access_token(self):
        # Interprocess lock prevents concurrent rotating refreshes from losing a token.
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            import fcntl
            with open(self.directory / 'refresh.lock', 'a') as lock:
                os.chmod(lock.name, 0o600)
                fcntl.flock(lock, fcntl.LOCK_EX)
                data = self._load()
                account = self._active(data)
                if not account or not account.get('access_token'):
                    raise ValueError('Continue com ChatGPT nas configurações para conectar sua conta.')
                if account.get('expires_at', 0) <= time.time() + 60:
                    if not account.get('refresh_token'):
                        raise ValueError('Sua sessão expirou. Continue com ChatGPT novamente.')
                    tokens = self._request('POST', TOKEN, data={'grant_type': 'refresh_token', 'client_id': account['client_id'],
                              'refresh_token': account['refresh_token'], 'resource': RESOURCE})
                    if tokens.get('id_token'):
                        self._identity(tokens['id_token'], account['client_id'], subject=account['subject'])
                    account.update(self._credentials(tokens, account))
                    self._save(data)
                return account['access_token']

    def models(self):
        token = self.access_token()
        response = self._request('GET', RESOURCE + '/models', headers={'Authorization': 'Bearer ' + token})
        models = [{'id': m['slug'], 'name': m.get('display_name') or m['slug']}
                  for m in response.get('models', []) if m.get('visibility') == 'list']
        if not models:
            raise ValueError('Esta conta não disponibilizou modelos para o app. Confira o acesso ao plano no ChatGPT.')
        with self._lock:
            data = self._load()
            account = self._active(data)
            if account and account.get('access_token') == token:
                account['models'] = models
                self._save(data)
                self._error = None
        return {'models': models}

    def select(self, account_id):
        with self._lock:
            data = self._load()
            if not any(a['id'] == account_id for a in data['accounts']):
                raise ValueError('Conta desconhecida.')
            data['active'] = account_id
            self._save(data)
            self._error = None
        return self.status()

    def acknowledge(self):
        with self._lock:
            data = self._load()
            account = self._active(data)
            if account:
                account['welcome_seen'] = True
                self._save(data)
        return self.status()

    def logout(self):
        self.cancel()
        with self._lock:
            data = self._load()
            account = self._active(data)
            confirmed = True
            if account and account.get('refresh_token'):
                try:
                    discovery = self._request('GET', ISSUER + '/.well-known/openid-configuration')
                    endpoint = discovery['revocation_endpoint']
                    if urlparse(endpoint).scheme != 'https' or urlparse(endpoint).netloc != 'auth.openai.com':
                        raise ValueError('Invalid revocation endpoint')
                    self._request('POST', endpoint, data={'token': account['refresh_token'], 'token_type_hint': 'refresh_token', 'client_id': account['client_id']})
                except (ValueError, KeyError):
                    confirmed = False
            if account:
                for key in ('access_token', 'refresh_token', 'id_token', 'expires_at', 'scopes', 'models'):
                    account.pop(key, None)
                self._save(data)
            self._error = None
        return {'message': 'Conta desconectada.' if confirmed else 'Conta desconectada neste Mac. A revogação remota não foi confirmada; gerencie o acesso nas configurações do ChatGPT.'}
