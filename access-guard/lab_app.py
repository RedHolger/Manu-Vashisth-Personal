"""Local demo HTTP API for AccessGuard (P11): vulnerable and fixed variants.

Stdlib `http.server` on 127.0.0.1. Self-contained enforcement; this module
never imports `policy_oracle` — it is the *target* under test, and the oracle
judges it independently.

`serve(bugs=frozenset(), registry=None)` starts the fixed app; the vulnerable
lab variant passes `bugs={'cross_tenant', 'ownership', 'expiry',
'revocation'}`. The `cross_tenant` bug omits the tenant check, `ownership`
omits the owner check on write, `expiry` honors expired sessions and
`revocation` honors revoked users. Role always comes from the server-side
registry (never the token claim), even in the vulnerable variant.

Endpoints (token via `Authorization: Bearer` or `?token=`):
- GET  /docs/<tenant>/<doc>  -> read
- POST /docs/<tenant>/<doc>  -> write (?body= optional)
- DELETE /docs/<tenant>/<doc>  -> delete (admin only)
Denials: 401 malformed/unknown token, 403 revoked/expired/forbidden,
404 unknown document, 405 unknown method. All fail closed.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

REGISTRY = {'alice': 'admin', 'bob': 'member', 'carol': 'member',
            'dave': 'member', 'erin': 'member'}
USER_TENANT = {'alice': 'A', 'bob': 'A', 'carol': 'B', 'dave': 'A',
               'erin': 'A'}
REVOKED = frozenset({'erin'})
SEED_DOCS = {('A', 'doc1'): {'owner': 'alice', 'body': 'alpha'},
             ('A', 'doc2'): {'owner': 'bob', 'body': 'beta'},
             ('B', 'doc1'): {'owner': 'carol', 'body': 'gamma'},
             ('B', 'doc2'): {'owner': 'bob', 'body': 'delta'}}

VULNERABLE_BUGS = frozenset(
    {'cross_tenant', 'ownership', 'expiry', 'revocation'})


def _parse_token(token):
    if not isinstance(token, str):
        return None
    parts = token.split('-')
    if len(parts) != 5 or parts[0] != 'tok':
        return None
    _, user, tenant, claimed_role, exp = parts
    if user not in REGISTRY or tenant not in ('A', 'B') \
            or claimed_role not in ('admin', 'member'):
        return None
    try:
        exp = int(exp)
    except ValueError:
        return None
    return {'user': user, 'tenant': tenant, 'claimed_role': claimed_role,
            'exp': exp}


def make_handler(bugs, registry, docs, revoked):
    import time

    class Handler(BaseHTTPRequestHandler):
        server_version = 'AccessGuardLab/1'

        def log_message(self, *args):
            pass

        def _send(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _bearer(self):
            auth = self.headers.get('Authorization', '')
            if auth.startswith('Bearer '):
                return auth[7:].strip()
            query = parse_qs(urlparse(self.path).query)
            return (query.get('token', [None]))[0]

        def _route(self):
            parts = urlparse(self.path).path.strip('/').split('/')
            if len(parts) != 3 or parts[0] != 'docs':
                return None
            _, tenant, doc = parts
            return tenant, doc

        def _handle(self, method):
            route = self._route()
            if route is None:
                self._send(404, {'error': 'unknown-path'})
                return
            tenant, doc = route
            if method not in ('GET', 'POST', 'DELETE'):
                self._send(405, {'error': 'unknown-action'})
                return
            creds = _parse_token(self._bearer())
            if creds is None:
                self._send(401, {'error': 'malformed-or-unknown-token'})
                return
            user = creds['user']
            if user in revoked and 'revocation' not in bugs:
                self._send(403, {'error': 'revoked'})
                return
            if creds['exp'] < time.time() and 'expiry' not in bugs:
                self._send(403, {'error': 'expired'})
                return
            entry = docs.get((tenant, doc))
            if entry is None:
                self._send(404, {'error': 'unknown-resource'})
                return
            if USER_TENANT[user] != tenant and 'cross_tenant' not in bugs:
                self._send(403, {'error': 'cross-tenant'})
                return
            role = registry.get(user, 'member')
            owner = entry['owner']
            if method == 'GET':
                if role == 'admin' or user == owner:
                    self._send(200, {'ok': True, 'owner': owner,
                                     'body': entry['body']})
                else:
                    self._send(403, {'error': 'not-owner-or-admin'})
            elif method == 'POST':
                if role == 'admin' or 'ownership' in bugs or user == owner:
                    query = parse_qs(urlparse(self.path).query)
                    entry['body'] = (query.get('body', ['written']))[0]
                    self._send(200, {'ok': True, 'owner': owner})
                else:
                    self._send(403, {'error': 'not-owner-or-admin'})
            else:  # DELETE: admin only, both variants
                if role == 'admin':
                    del docs[(tenant, doc)]
                    self._send(200, {'ok': True})
                else:
                    self._send(403, {'error': 'delete-requires-admin'})

        def do_GET(self):
            self._handle('GET')

        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0) or 0)
            if length:
                self.rfile.read(length)
            self._handle('POST')

        def do_DELETE(self):
            self._handle('DELETE')

        def do_PUT(self):
            self._handle('PUT')

    return Handler


def serve(bugs=frozenset(), registry=None, revoked=None):
    """Start the app on 127.0.0.1:0. Returns (server, thread, base_url)."""
    registry = dict(REGISTRY) if registry is None else dict(registry)
    revoked = set(REVOKED) if revoked is None else set(revoked)
    docs = {k: dict(v) for k, v in SEED_DOCS.items()}
    server = HTTPServer(('127.0.0.1', 0),
                        make_handler(frozenset(bugs), registry, docs,
                                     revoked))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:%d' % server.server_address[1]
    return server, thread, base


def stop(server):
    server.shutdown()
    server.server_close()
