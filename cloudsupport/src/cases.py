"""Five local support cases. Each run_<name>() returns an evidence dict with
timestamped steps. Loopback only; stdlib only (openssl CLI for case 4)."""
import hashlib
import hmac
import http.client
import http.server
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import urllib.request
from datetime import datetime, timezone

REFUSED_ERRNOS = {61, 111}  # ECONNREFUSED macOS / Linux


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class ThreadServer:
    """Run a BaseHTTPServer subclass in a daemon thread; cleanup via stop()."""

    def __init__(self, handler, use_ssl=None):
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        if use_ssl:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(use_ssl["cert"], use_ssl["key"])
            self.srv.socket = ctx.wrap_socket(self.srv.socket, server_side=True)
        self.port = self.srv.server_address[1]
        self.thread = threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.05})
        self.thread.daemon = True

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.srv.shutdown()
        self.srv.server_close()
        self.thread.join(timeout=5)


def run_dns():
    steps = []

    def step(phase, detail):
        steps.append({"t": now(), "phase": phase, "detail": detail})

    try:
        socket.getaddrinfo("no-such-host.invalid", 80)
        return {"name": "dns_unresolvable", "outcome": "fail", "steps": steps,
                "note": ".invalid unexpectedly resolved"}
    except socket.gaierror as e:
        step("symptom", f"getaddrinfo('no-such-host.invalid') -> gaierror {e}")
    step("diagnostics", ".invalid is non-resolvable by design (RFC 2606); not a resolver outage")
    step("root_cause", "wrong hostname in configuration")
    addrs = socket.getaddrinfo("localhost", 80)
    got = sorted({a[4][0] for a in addrs})
    step("fix", "use the correct hostname 'localhost'")
    step("recovery_proof", f"localhost resolves to {got}")
    step("customer_explanation", "The name ...invalid can never resolve by design; "
         "point the client at the documented hostname and retest DNS first.")
    return {"name": "dns_unresolvable", "outcome": "pass", "steps": steps}


def run_tcp_refused():
    steps = []

    def step(phase, detail):
        steps.append({"t": now(), "phase": phase, "detail": detail})

    port = closed_port()
    try:
        socket.create_connection(("127.0.0.1", port), timeout=3).close()
        return {"name": "tcp_refused", "outcome": "fail", "steps": steps,
                "note": "port unexpectedly open (race); rerun"}
    except ConnectionRefusedError as e:
        err_no = e.errno
        step("symptom", f"connect 127.0.0.1:{port} -> ConnectionRefusedError errno={err_no}")
        assert err_no in REFUSED_ERRNOS, f"unexpected errno {err_no}"
    step("diagnostics", f"errno {err_no} means nothing is listening on that port (no firewall RST seen)")
    step("root_cause", "service not running on the expected port")
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", port))
    listener.listen(1)

    def serve_once():
        conn, _ = listener.accept()
        with conn:
            conn.sendall(b"OK\n")

    t = threading.Thread(target=serve_once, daemon=True)
    t.start()
    with socket.create_connection(("127.0.0.1", port), timeout=3) as s:
        banner = s.recv(16)
    listener.close()
    t.join(timeout=5)
    step("fix", "start the service on the documented port")
    step("recovery_proof", f"reconnect banner={banner!r}")
    assert banner == b"OK\n"
    step("customer_explanation", "Connection refused = reached host, no service on port. "
         "Start/enable the service (or correct the port) rather than changing firewall rules.")
    return {"name": "tcp_refused", "outcome": "pass", "steps": steps}


class SlowHandler(http.server.BaseHTTPRequestHandler):
    SLOW_S = 2.5

    def do_GET(self):
        if self.path == "/slow":
            time.sleep(self.SLOW_S)
            body = b"slow-ok"
        else:
            body = b"fast-ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def run_http_timeout():
    steps = []

    def step(phase, detail):
        steps.append({"t": now(), "phase": phase, "detail": detail})

    with ThreadServer(SlowHandler) as srv:
        base = f"http://127.0.0.1:{srv.port}"
        with urllib.request.urlopen(base + "/fast", timeout=5) as r:
            assert r.status == 200 and r.read() == b"fast-ok"
        step("diagnostics", "control /fast answers instantly: server is healthy")
        t0 = time.monotonic()
        try:
            urllib.request.urlopen(base + "/slow", timeout=0.5)
            return {"name": "http_timeout", "outcome": "fail", "steps": steps,
                    "note": "/slow answered within 0.5s unexpectedly"}
        except Exception as e:
            el = time.monotonic() - t0
            if "timed out" not in str(e).lower() and not isinstance(e, TimeoutError):
                raise
            step("symptom", f"GET /slow timeout=0.5s -> {type(e).__name__} after {el:.2f}s")
        step("diagnostics", f"server needs {SlowHandler.SLOW_S}s; client gave up at 0.5s")
        step("root_cause", "client timeout shorter than normal handler latency")
        time.sleep(0.2)  # backoff
        with urllib.request.urlopen(base + "/slow", timeout=8) as r:
            body = r.read()
        h = hashlib.sha256(body).hexdigest()
        step("fix", "retry once after backoff with timeout 8s")
        step("recovery_proof", f"200 body sha256={h}")
        assert body == b"slow-ok"
    step("customer_explanation", "The request timed out client-side while the server was "
         "still working. Retried with a timeout above the known latency; no server change needed.")
    return {"name": "http_timeout", "outcome": "pass", "steps": steps}


def run_tls_hostname():
    steps = []

    def step(phase, detail):
        steps.append({"t": now(), "phase": phase, "detail": detail})

    if shutil.which("openssl") is None:
        return {"name": "tls_hostname", "outcome": "skip", "steps": steps,
                "note": "openssl CLI missing; cannot mint test cert"}
    tmp = tempfile.mkdtemp(prefix="cs-tls-")
    key, cert = os.path.join(tmp, "key.pem"), os.path.join(tmp, "cert.pem")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048",
                    "-keyout", key, "-out", cert, "-days", "2", "-nodes",
                    "-subj", "/CN=localhost",
                    "-addext", "subjectAltName=DNS:localhost"],
                   check=True, capture_output=True)
    ident = subprocess.run(["openssl", "x509", "-noout", "-subject", "-ext",
                            "subjectAltName", "-in", cert],
                           check=True, capture_output=True, text=True).stdout.strip()

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"tls-ok"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    try:
        with ThreadServer(H, use_ssl={"cert": cert, "key": key}) as srv:
            ctx = ssl.create_default_context(cafile=cert)
            raw = socket.create_connection(("127.0.0.1", srv.port), timeout=5)
            try:
                ctx.wrap_socket(raw, server_hostname="wrongname.example")
                raw.close()
                return {"name": "tls_hostname", "outcome": "fail", "steps": steps,
                        "note": "wrong hostname unexpectedly accepted"}
            except ssl.CertificateError as e:
                step("symptom", f"handshake server_hostname='wrongname.example' -> CertificateError: {e}")
                raw.close()
            step("diagnostics", f"server cert identity: {ident}")
            step("root_cause", "client requested a name not present in the cert SAN/CN")
            raw2 = socket.create_connection(("127.0.0.1", srv.port), timeout=5)
            tls = ctx.wrap_socket(raw2, server_hostname="localhost")
            tls.sendall(b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n")
            chunks = []
            while True:
                blk = tls.recv(4096)
                if not blk:
                    break
                chunks.append(blk)
            resp = b"".join(chunks)
            tls.close()
            step("fix", "connect with the name on the certificate ('localhost')")
            step("recovery_proof", f"verified TLS, first response line: {resp.splitlines()[0]!r}")
            assert b"200" in resp.splitlines()[0] and resp.endswith(b"tls-ok")
    finally:
        for f in (key, cert):
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
    step("customer_explanation", "TLS validates the server NAME, not just encryption. "
         "Use the hostname printed on the certificate (or reissue it for the right name).")
    return {"name": "tls_hostname", "outcome": "pass", "steps": steps}


SECRET_LEN = 16


def run_upload_expiry():
    steps = []

    def step(phase, detail):
        steps.append({"t": now(), "phase": phase, "detail": detail})

    secret = os.urandom(SECRET_LEN)  # ephemeral per run; never leaves this process
    store = {}

    def sign(path, exp):
        return hmac.new(secret, f"{path}|{exp}".encode(), hashlib.sha256).hexdigest()

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            exp = int(q.get("exp", ["0"])[0])
            sig = q.get("sig", [""])[0]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            if not hmac.compare_digest(sign("/upload", exp), sig):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"bad-signature")
                return
            if int(time.time()) > exp:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"expired")
                return
            store["obj"] = body
            self.send_response(200)
            self.end_headers()
            self.wfile.write(hashlib.sha256(body).hexdigest().encode())

        def log_message(self, *a):
            pass

    def post(exp, sig, body):
        conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
        conn.request("POST", f"/upload?exp={exp}&sig={sig}", body=body)
        r = conn.getresponse()
        out = (r.status, r.read())
        conn.close()
        return out

    payload = b'{"invoice": 42, "total": "100.00"}'
    want = hashlib.sha256(payload).hexdigest()
    with ThreadServer(H) as srv:
        old_exp = int(time.time()) - 60
        st, body = post(old_exp, sign("/upload", old_exp), payload)
        assert (st, body) == (403, b"expired"), (st, body)
        step("symptom", f"POST with exp={old_exp} (60s old) -> 403 expired")
        step("diagnostics", f"server time ok; signature valid; only exp is stale "
             f"(replay/expiry, not a signing bug)")
        step("root_cause", "upload URL used after its expiry")
        fresh_exp = int(time.time()) + 300
        st, body = post(fresh_exp, sign("/upload", fresh_exp), payload)
        assert st == 200 and body.decode() == want, (st, body)
        assert store.get("obj") == payload
        step("fix", "mint a fresh URL (exp=+300s) and re-upload")
        step("recovery_proof", f"200 stored sha256={body.decode()} matches client")
        bad_sig = sign("/upload", fresh_exp)[:-1] + ("0" if sign("/upload", fresh_exp)[-1] != "0" else "1")
        st, body = post(fresh_exp, bad_sig, payload)
        assert (st, body) == (403, b"bad-signature"), (st, body)
        step("diagnostics", "tampered signature stays 403: expiry and signature are independent checks")
    step("customer_explanation", "Signed upload links expire on purpose. Generate a new link "
         "just before uploading instead of reusing an old one.")
    return {"name": "upload_expiry", "outcome": "pass", "steps": steps}


CASES = {
    "dns_unresolvable": run_dns,
    "tcp_refused": run_tcp_refused,
    "http_timeout": run_http_timeout,
    "tls_hostname": run_tls_hostname,
    "upload_expiry": run_upload_expiry,
}
