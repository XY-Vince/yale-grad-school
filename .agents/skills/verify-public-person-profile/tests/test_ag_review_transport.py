"""Loopback-only TLS integration checks for address-pinned retrieval."""
import http.server
import shutil
import socket
import ssl
import subprocess
import threading

import pytest
import requests
import urllib3.util.connection

from core.collectors import base


@pytest.fixture
def tls_server(tmp_path):
    if not shutil.which("openssl"):
        pytest.skip("openssl is needed to generate a temporary test certificate")
    key = tmp_path / "key.pem"
    cert = tmp_path / "cert.pem"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(cert), "-days", "1",
        "-subj", "/CN=research.test", "-addext", "subjectAltName=DNS:research.test",
    ], check=True, capture_output=True, timeout=20)
    observed = {"host": [], "sni": []}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            observed["host"].append(self.headers.get("Host"))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"local TLS response")

        def do_POST(self):
            observed["host"].append(self.headers.get("Host"))
            length = int(self.headers.get("Content-Length", "0"))
            observed["post_body"] = self.rfile.read(length)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"local TLS POST response")

        def log_message(self, *args):
            pass

    try:
        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    except PermissionError:
        pytest.skip("sandbox forbids loopback sockets")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(cert), keyfile=str(key))
    context.set_servername_callback(lambda connection, name, ctx: observed["sni"].append(name))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port, cert, observed
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def route_public_test_address_to_loopback(monkeypatch, port, cert):
    real_getaddrinfo = socket.getaddrinfo
    real_connect = urllib3.util.connection.create_connection
    session_class = requests.Session

    def resolve(host, service, *args, **kwargs):
        if host in {"research.test", "wrong.test"}:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", service))]
        return real_getaddrinfo(host, service, *args, **kwargs)

    def connect(address, *args, **kwargs):
        assert address == ("8.8.8.8", port)
        return real_connect(("127.0.0.1", port), *args, **kwargs)

    class TrustedTestSession(session_class):
        def __init__(self):
            super().__init__()
            self.verify = str(cert)

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(urllib3.util.connection, "create_connection", connect)
    monkeypatch.setattr(base.requests, "Session", TrustedTestSession)


def test_pinned_connection_verifies_tls_for_original_hostname(monkeypatch, tls_server):
    port, cert, observed = tls_server
    route_public_test_address_to_loopback(monkeypatch, port, cert)
    response = base.safe_fetch(f"https://research.test:{port}/test")
    assert response.status_code == 200
    assert response.content == b"local TLS response"
    assert observed == {"host": [f"research.test:{port}"], "sni": ["research.test"]}


def test_pinned_connection_rejects_wrong_certificate_hostname(monkeypatch, tls_server):
    port, cert, observed = tls_server
    route_public_test_address_to_loopback(monkeypatch, port, cert)
    with pytest.raises(requests.exceptions.SSLError):
        base.safe_fetch(f"https://wrong.test:{port}/test")
    assert observed["host"] == []


def test_pinned_post_preserves_body_host_sni_and_certificate(monkeypatch, tls_server):
    port, cert, observed = tls_server
    route_public_test_address_to_loopback(monkeypatch, port, cert)
    response = base.safe_fetch(
        f"https://research.test:{port}/search", method="POST", data=b"q=alice",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.content == b"local TLS POST response"
    assert observed == {
        "host": [f"research.test:{port}"], "sni": ["research.test"], "post_body": b"q=alice",
    }
