"""HTTPS/WSS: local API traffic must be TLS-only (no plain HTTP on the same port)."""

import os
import socket
import ssl
import tempfile
from datetime import UTC, datetime, timedelta

import aiohttp
import pytest
from aiohttp import web
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def _make_self_signed_cert_and_key(cert_path: str, key_path: str) -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ],
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    os.makedirs(os.path.dirname(cert_path) or ".", exist_ok=True)
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ),
        )


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def ssl_context_and_cert(temp_storage):
    cert_dir = temp_storage
    cert_path = os.path.join(cert_dir, "cert.pem")
    key_path = os.path.join(cert_dir, "key.pem")
    _make_self_signed_cert_and_key(cert_path, key_path)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    return ctx, cert_path, key_path


@pytest.mark.asyncio
async def test_https_serves_over_tls_only_plain_http_gets_no_http_response(
    ssl_context_and_cert,
):
    """TLS-only server must not emit a plaintext HTTP response to raw HTTP bytes.

    Raw TCP clients should see handshake noise or close, not ``HTTP/`` headers.
    """
    ssl_context, _, _ = ssl_context_and_cert
    app = web.Application()

    async def root_handler(_request):
        return web.Response(text="ok")

    app.router.add_get("/", root_handler)
    runner = web.AppRunner(app, keepalive_timeout=0)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0, ssl_context=ssl_context)
    await site.start()
    try:
        port = site._server.sockets[0].getsockname()[1]
        client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_ctx.check_hostname = False
        client_ctx.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"https://127.0.0.1:{port}/",
                ssl=client_ctx,
            )
            assert resp.status == 200
            assert (await resp.text()) == "ok"

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        try:
            sock.connect(("127.0.0.1", port))
            sock.sendall(b"GET / HTTP/1.0\r\n\r\n")
            try:
                raw = sock.recv(1024)
            except TimeoutError:
                raw = b""
        finally:
            sock.close()
        assert not raw.startswith(b"HTTP/"), (
            "Server must not respond with plain HTTP when TLS is enabled; "
            "plaintext would allow local side-sniffing"
        )
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_wss_over_same_tls_port(ssl_context_and_cert):
    """WebSocket on the TLS port must use WSS (encrypted transport)."""
    ssl_context, _, _ = ssl_context_and_cert
    app = web.Application()

    async def ws_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.close()
        return ws

    app.router.add_get("/ws", ws_handler)
    runner = web.AppRunner(app, keepalive_timeout=0)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0, ssl_context=ssl_context)
    await site.start()
    try:
        port = site._server.sockets[0].getsockname()[1]
        client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_ctx.check_hostname = False
        client_ctx.verify_mode = ssl.CERT_NONE

        async with (
            aiohttp.ClientSession() as session,
            session.ws_connect(
                f"wss://127.0.0.1:{port}/ws",
                ssl=client_ctx,
            ) as ws,
        ):
            msg = await ws.receive()
        assert msg.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSING,
            aiohttp.WSMsgType.CLOSED,
        )
    finally:
        await runner.cleanup()
