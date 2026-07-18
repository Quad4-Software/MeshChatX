# SPDX-License-Identifier: 0BSD
"""Live Validation ladder L0-L3 (acceptance for this install)."""

from __future__ import annotations

import os
import secrets
import subprocess
import sys

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session

from meshchatx.src.backend import self_check
from tests.backend.conftest import extend_meshchat_middlewares, fetch_api_csrf_headers
from tests.backend.eect.harness import eect_scenario
from tests.backend.support.test_temp_dir import subprocess_test_env

pytestmark = pytest.mark.live_validation

_LIVE = (
    os.environ.get("MESHCHAT_LIVE_VALIDATION") == "1"
    or os.environ.get(
        "MESHCHAT_LIVE_RETICULUM",
    )
    == "1"
)


def test_lv_l0_imports_sqlite_unicode(tmp_path):
    with eect_scenario("lv.l0.imports_sqlite_unicode") as (_s, _seed, _rng):
        assert self_check.check_critical_imports()["status"] == "ok"
        assert self_check.check_python_runtime()["status"] == "ok"
        assert self_check.check_sqlite_roundtrip(str(tmp_path))["status"] == "ok"
        assert self_check.check_unicode_path(str(tmp_path))["status"] == "ok"
        assert self_check.check_temp_filesystem()["status"] == "ok"


def _make_aio_app(mock_app, use_https: bool = False):
    mock_app.session_secret_key = secrets.token_urlsafe(32)
    mock_app.listen_host = "127.0.0.1"
    mock_app.listen_port = 8000
    mock_app.use_https = use_https
    mock_app.landlock_active = False
    routes = web.RouteTableDef()
    middlewares = mock_app._define_routes(routes)
    aio_app = web.Application()
    setup_session(aio_app, mock_app._encrypted_cookie_storage(use_https))
    extend_meshchat_middlewares(aio_app, middlewares)
    aio_app.add_routes(routes)
    return aio_app


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_lv_l1_status_and_csrf_reject(mock_app, monkeypatch):
    with eect_scenario("lv.l1.status_and_csrf_reject") as (_s, _seed, _rng):
        monkeypatch.delenv("MESHCHAT_DISABLE_CSRF", raising=False)
        aio_app = _make_aio_app(mock_app)
        async with TestClient(TestServer(aio_app)) as client:
            status = await client.get("/api/v1/status")
            assert status.status == 200
            body = await status.json()
            assert body.get("status") in ("ok", "starting", "failed")

            blocked = await client.patch(
                "/api/v1/server/security",
                json={"web_ui_ip_allowlist": ""},
            )
            assert blocked.status == 403

            headers = await fetch_api_csrf_headers(client)
            ok = await client.patch(
                "/api/v1/server/security",
                json={"web_ui_ip_allowlist": ""},
                headers=headers,
            )
            assert ok.status == 200


@pytest.mark.skipif(not _LIVE, reason="Set MESHCHAT_LIVE_VALIDATION=1 for LV L2+")
@pytest.mark.integration
def test_lv_l2_rns_subprocess():
    with eect_scenario("lv.l2.rns_subprocess") as (_s, _seed, _rng):
        script = r"""
import tempfile
import RNS

tmpdir = tempfile.mkdtemp(prefix="meshchat_lv_l2_")
try:
    RNS.Reticulum(configdir=tmpdir, loglevel=RNS.LOG_ERROR)
finally:
    RNS.exit(0)
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=subprocess_test_env(),
        )
        assert result.returncode == 0, result.stderr + result.stdout


@pytest.mark.skipif(not _LIVE, reason="Set MESHCHAT_LIVE_VALIDATION=1 for LV L2+")
@pytest.mark.integration
@pytest.mark.usefixtures("require_loopback_tcp")
def test_lv_l3_loopback_tcp():
    with eect_scenario("lv.l3.loopback_tcp") as (_s, _seed, _rng):
        result = self_check.check_loopback_tcp()
        assert result["status"] == "ok", result.get("reason")
