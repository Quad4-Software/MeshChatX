# SPDX-License-Identifier: 0BSD

"""Verify aiohttp FileResponse over TLS (regression guard for static file serving)."""

import os
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

from meshchatx.src.backend.http.safe_file_response import file_response

pytestmark = pytest.mark.usefixtures("require_loopback_tcp")


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
    with open(cert_path, "wb") as f:  # nosec: PTC-W6004
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
def ssl_context_server(temp_storage):
    cert_dir = temp_storage
    cert_path = os.path.join(cert_dir, "cert.pem")
    key_path = os.path.join(cert_dir, "key.pem")
    _make_self_signed_cert_and_key(cert_path, key_path)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    return ctx


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.mark.asyncio
async def test_https_file_response_body_matches(ssl_context_server, temp_storage):
    """Large file over HTTPS: exercises loop.sendfile / fallback paths."""
    payload = b"x" * (256 * 1024 + 17)
    path = os.path.join(temp_storage, "blob.bin")
    with open(path, "wb") as f:
        f.write(payload)

    app = web.Application()

    async def file_handler(_request):
        return web.FileResponse(path)

    app.router.add_get("/f", file_handler)
    runner = web.AppRunner(app, keepalive_timeout=0)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0, ssl_context=ssl_context_server)
    await site.start()
    try:
        port = site._server.sockets[0].getsockname()[1]
        client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_ctx.check_hostname = False
        client_ctx.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"https://127.0.0.1:{port}/f",
                ssl=client_ctx,
            )
            assert resp.status == 200
            body = await resp.read()
            assert body == payload
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_safe_file_response_ignores_sendfile_crashes(
    ssl_context_server,
    temp_storage,
    monkeypatch,
):
    """CPython's SSL sendfile fallback can die mid-write (GH issue 118).

    SafeFileResponse never calls loop.sendfile, so a transport-level
    crash there cannot 500 the response or poison frame asset loads.
    """
    payload = b"y" * (256 * 1024 + 31)
    path = os.path.join(temp_storage, "blob.bin")
    with open(path, "wb") as f:
        f.write(payload)

    async def exploding_sendfile(*_args, **_kwargs):
        raise AttributeError("'NoneType' object has no attribute '_write_appdata'")

    monkeypatch.setattr(
        "asyncio.base_events.BaseEventLoop.sendfile",
        exploding_sendfile,
    )

    app = web.Application()

    async def file_handler(_request):
        return file_response(path)

    app.router.add_get("/f", file_handler)
    runner = web.AppRunner(app, keepalive_timeout=0)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0, ssl_context=ssl_context_server)
    await site.start()
    try:
        port = site._server.sockets[0].getsockname()[1]
        client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_ctx.check_hostname = False
        client_ctx.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"https://127.0.0.1:{port}/f",
                ssl=client_ctx,
            )
            assert resp.status == 200
            body = await resp.read()
            assert body == payload
    finally:
        await runner.cleanup()
