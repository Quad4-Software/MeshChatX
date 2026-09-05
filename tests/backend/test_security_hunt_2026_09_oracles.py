# SPDX-License-Identifier: 0BSD

"""Oracle tests from the 2026-09 exploratory security hunt.

Each test states an invariant, predicts accept or reject from the input, then
checks the implementation. Failures are confirmed bugs.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
import RNS
from aiohttp import web

from meshchatx.src.backend.management_identities import (
    create_management_identity,
    resolve_identity_path,
)


def test_oracle_h1_management_identity_path_jailed_to_identities_dir(tmp_path):
    """H1: identity_path must stay under reticulum storage/identities.

    Absolute paths outside that directory (including MeshChatX identity keys)
    must raise PermissionError or FileNotFoundError, never load.
    """
    created = create_management_identity(str(tmp_path), "mgmt")
    outside = tmp_path / "outside_identity"
    RNS.Identity().to_file(str(outside))

    assert resolve_identity_path(str(tmp_path), identity_path=created["path"]) == os.path.realpath(
        created["path"],
    )
    assert resolve_identity_path(str(tmp_path), identity_name="mgmt") == os.path.realpath(
        created["path"],
    )

    with pytest.raises((PermissionError, FileNotFoundError, ValueError)):
        resolve_identity_path(str(tmp_path), identity_path=str(outside))

    with pytest.raises((PermissionError, FileNotFoundError, ValueError)):
        resolve_identity_path(
            str(tmp_path),
            identity_path=os.path.join(str(tmp_path), "..", "outside_identity"),
        )


def test_oracle_h1_management_identity_path_rejects_symlink_escape(tmp_path):
    """H1: symlink under identities dir that points outside must fail closed."""
    create_management_identity(str(tmp_path), "mgmt")
    identities = tmp_path / "storage" / "identities"
    bait = tmp_path / "bait_key"
    bait.write_bytes(b"not-a-real-key-but-a-file")
    link = identities / "linked"
    try:
        link.symlink_to(bait)
    except OSError:
        pytest.skip("symlink not supported on this filesystem")

    with pytest.raises((PermissionError, FileNotFoundError, ValueError, OSError)):
        resolve_identity_path(str(tmp_path), identity_path=str(link))


def _handler(app, method: str, path: str):
    for route in app.get_routes():
        if route.method == method and route.path == path:
            return route.handler
    return None


def test_oracle_h4_database_backup_download_is_post_not_get(mock_app):
    """H4: creating a backup zip is state-changing and must use POST for CSRF."""
    path = "/api/v1/database/backup/download"
    assert _handler(mock_app, "POST", path) is not None, path
    assert _handler(mock_app, "GET", path) is None, path


@pytest.mark.asyncio
async def test_oracle_h4_database_backup_download_post_streams_file(tmp_path):
    """H4: POST handler still creates and streams the backup zip."""
    zip_path = tmp_path / "backup-stream.zip"
    zip_path.write_bytes(b"PK\x03\x04not-a-real-zip-but-enough")
    app = MagicMock()
    app.storage_path = str(tmp_path)
    app.database.backup_database.return_value = {"path": str(zip_path)}

    from meshchatx.src.backend.http.routes.database import register_database_routes

    routes = web.RouteTableDef()
    register_database_routes(routes, app)
    handler = None
    for route in routes:
        if (
            getattr(route, "path", None) == "/api/v1/database/backup/download"
            and getattr(route, "method", None) == "POST"
        ):
            handler = route.handler
            break
    assert handler is not None
    response = await handler(MagicMock())
    assert isinstance(response, web.FileResponse)
    assert os.path.realpath(response._path) == os.path.realpath(zip_path)
    app.database.backup_database.assert_called_once_with(str(tmp_path))


def test_oracle_h5_libretranslate_dns_link_local_rejected(monkeypatch):
    """H5: normalize must reject hostnames that resolve to link-local IPs."""
    import socket

    from meshchatx.src.backend.http_url_guard import (
        UnsafeOutboundUrlError,
        normalize_libretranslate_http_service_base,
    )

    def fake_getaddrinfo(host, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(UnsafeOutboundUrlError, match="link-local"):
        normalize_libretranslate_http_service_base("https://ssrf-bait.example/")
