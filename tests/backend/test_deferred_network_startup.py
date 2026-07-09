# SPDX-License-Identifier: 0BSD

import json
import shutil
import tempfile
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from tests.backend.api_json_contract_schemas import (
    API_V1_STATUS_SCHEMA,
    AUTH_STATUS_SCHEMA,
    assert_matches_schema,
)


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_identity():
    identity = MagicMock(spec=RNS.Identity)
    identity.hash = b"test_hash_32_bytes_long_01234567"
    identity.hexhash = identity.hash.hex()
    return identity


def _make_deferred_app(mock_identity, temp_dir, **kwargs):
    with (
        patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
        patch.object(ReticulumMeshChat, "setup_identity"),
    ):
        return ReticulumMeshChat(
            identity=mock_identity,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            defer_network_setup=True,
            **kwargs,
        )


def test_deferred_init_skips_reticulum_until_background_setup(mock_identity, temp_dir):
    with (
        patch("RNS.Reticulum") as mock_reticulum,
        patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
        patch.object(ReticulumMeshChat, "setup_identity") as mock_setup,
    ):
        app = ReticulumMeshChat(
            identity=mock_identity,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            defer_network_setup=True,
        )
        assert app._network_ready is False
        assert app._startup_stage == "http"
        mock_reticulum.assert_not_called()
        mock_setup.assert_not_called()

        payload = app._startup_status_payload()
        assert payload["status"] == "starting"
        assert payload["network_ready"] is False
        assert payload["stage"] == "http"
        assert_matches_schema(payload, API_V1_STATUS_SCHEMA)


def test_background_network_setup_marks_ready(mock_identity, temp_dir):
    ready = threading.Event()

    def fake_setup(self, identity):
        context = MagicMock()
        context.running = True
        context.config = MagicMock()
        context.config.auth_session_secret.set = MagicMock()
        self.current_context = context
        ready.set()

    with (
        patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
        patch.object(ReticulumMeshChat, "setup_identity", fake_setup),
    ):
        app = ReticulumMeshChat(
            identity=mock_identity,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            defer_network_setup=True,
        )
        app.session_secret_key = "test-secret"
        app.start_network_setup_in_background()
        assert ready.wait(timeout=5)
        assert app.wait_until_network_ready(timeout=5)
        payload = app._startup_status_payload()
        assert payload["status"] == "ok"
        assert payload["network_ready"] is True
        assert payload["stage"] == "ready"
        assert_matches_schema(payload, API_V1_STATUS_SCHEMA)


def test_create_reticulum_instance_works_off_main_thread(temp_dir):
    from meshchatx import meshchat as meshchat_mod

    result = {"error": None, "instance": None, "signal_calls": 0}

    def worker():
        real_signal = meshchat_mod.signal.signal

        def boom(signum, handler):
            result["signal_calls"] += 1
            raise ValueError(
                "signal only works in main thread of the main interpreter",
            )

        def ctor(config_dir, **kwargs):
            meshchat_mod.signal.signal(meshchat_mod.signal.SIGINT, lambda *a: None)
            return MagicMock(name="rns")

        meshchat_mod.signal.signal = boom
        try:
            with (
                patch.object(meshchat_mod.RNS, "Reticulum", side_effect=ctor),
                patch(
                    "meshchatx.meshchat.threading.current_thread",
                    return_value=threading.Thread(name="worker"),
                ),
            ):
                result["instance"] = meshchat_mod._create_reticulum_instance(temp_dir)
        except Exception as exc:
            result["error"] = exc
        finally:
            meshchat_mod.signal.signal = real_signal

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=5)
    assert result["error"] is None, result["error"]
    assert result["instance"] is not None
    assert result["signal_calls"] >= 1


def test_create_reticulum_instance_main_thread_passes_loglevel(temp_dir):
    from meshchatx import meshchat as meshchat_mod

    with patch.object(meshchat_mod.RNS, "Reticulum") as mock_ctor:
        mock_ctor.return_value = MagicMock(name="rns")
        with patch(
            "meshchatx.meshchat.threading.current_thread",
            return_value=threading.main_thread(),
        ):
            meshchat_mod._create_reticulum_instance(temp_dir, loglevel=3)
        mock_ctor.assert_called_once_with(temp_dir, loglevel=3)


def test_immediate_init_still_sets_up_network(mock_identity, temp_dir):
    with (
        patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
        patch.object(ReticulumMeshChat, "setup_identity") as mock_setup,
    ):
        app = ReticulumMeshChat(
            identity=mock_identity,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            defer_network_setup=False,
        )
        mock_setup.assert_called_once_with(mock_identity)
        assert app._network_ready is True
        assert app._startup_stage == "ready"


def test_network_setup_failure_sets_failed_status(mock_identity, temp_dir):
    def boom(self, identity):
        raise RuntimeError("RNS init exploded")

    with (
        patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
        patch.object(ReticulumMeshChat, "setup_identity", boom),
    ):
        app = ReticulumMeshChat(
            identity=mock_identity,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            defer_network_setup=True,
        )
        app.start_network_setup_in_background()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and app._startup_stage != "failed":
            time.sleep(0.02)
        payload = app._startup_status_payload()
        assert payload["status"] == "failed"
        assert payload["network_ready"] is False
        assert payload["stage"] == "failed"
        assert "RNS init exploded" in payload.get("error", "")
        assert_matches_schema(payload, API_V1_STATUS_SCHEMA)
        assert app.wait_until_network_ready(timeout=0.05) is False


def test_double_start_network_setup_is_idempotent(mock_identity, temp_dir):
    calls = []
    gate = threading.Event()
    entered = threading.Event()

    def slow_setup(self, identity):
        calls.append(identity)
        entered.set()
        gate.wait(timeout=2)
        context = MagicMock()
        context.running = True
        context.config = MagicMock()
        context.config.auth_session_secret.set = MagicMock()
        self.current_context = context

    with (
        patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
        patch.object(ReticulumMeshChat, "setup_identity", slow_setup),
    ):
        app = ReticulumMeshChat(
            identity=mock_identity,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            defer_network_setup=True,
        )
        app.session_secret_key = "secret"
        app.start_network_setup_in_background()
        assert entered.wait(timeout=2)
        app.start_network_setup_in_background()
        app.start_network_setup_in_background()
        gate.set()
        assert app.wait_until_network_ready(timeout=5)
        assert len(calls) == 1


def test_start_without_pending_identity_raises(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    app._pending_identity = None
    with pytest.raises(RuntimeError, match="No identity"):
        app.start_network_setup_in_background()


def test_wait_until_network_ready_true_when_already_ready(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    context = MagicMock()
    context.running = True
    app.current_context = context
    app._mark_network_ready()
    assert app.wait_until_network_ready(timeout=0) is True


def test_startup_status_payload_stages(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    for stage in ("http", "starting", "rns", "identity"):
        app._set_startup_stage(stage)
        payload = app._startup_status_payload()
        assert payload["status"] == "starting"
        assert payload["stage"] == stage
        assert payload["network_ready"] is False
        assert_matches_schema(payload, API_V1_STATUS_SCHEMA)


def test_session_secret_persisted_after_background_setup(mock_identity, temp_dir):
    secret_set = MagicMock()

    def fake_setup(self, identity):
        context = MagicMock()
        context.running = True
        context.config = MagicMock()
        context.config.auth_session_secret.set = secret_set
        self.current_context = context

    with (
        patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
        patch.object(ReticulumMeshChat, "setup_identity", fake_setup),
    ):
        app = ReticulumMeshChat(
            identity=mock_identity,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            defer_network_setup=True,
        )
        app.session_secret_key = "persisted-secret"
        app.start_network_setup_in_background()
        assert app.wait_until_network_ready(timeout=5)
        secret_set.assert_called_once_with("persisted-secret")


def _route_handler(app: ReticulumMeshChat, path: str, method: str):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


@pytest.mark.asyncio
async def test_status_endpoint_while_starting(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    handler = _route_handler(app, "/api/v1/status", "GET")
    response = await handler(MagicMock())
    data = json.loads(response.body)
    assert data["status"] == "starting"
    assert data["network_ready"] is False
    assert_matches_schema(data, API_V1_STATUS_SCHEMA)


@pytest.mark.asyncio
async def test_auth_status_while_starting(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    handler = _route_handler(app, "/api/v1/auth/status", "GET")
    response = await handler(MagicMock())
    data = json.loads(response.body)
    assert data["network_ready"] is False
    assert data["status"] == "starting"
    assert data["authenticated"] is False
    assert data["password_set"] is False
    assert_matches_schema(data, AUTH_STATUS_SCHEMA)


@pytest.mark.asyncio
async def test_auth_middleware_allows_status_and_static_while_starting(
    mock_identity,
    temp_dir,
):
    app = _make_deferred_app(mock_identity, temp_dir)
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw])
    aio_app.add_routes(routes)

    async with TestClient(TestServer(aio_app)) as client:
        status = await client.get("/api/v1/status")
        assert status.status == 200
        body = await status.json()
        assert body["status"] == "starting"

        auth = await client.get("/api/v1/auth/status")
        assert auth.status == 200
        auth_body = await auth.json()
        assert auth_body["network_ready"] is False

        blocked = await client.get("/api/v1/config")
        assert blocked.status == 503
        blocked_body = await blocked.json()
        assert blocked_body["status"] == "starting"
        assert blocked_body["network_ready"] is False


@pytest.mark.asyncio
async def test_auth_middleware_allows_csrf_while_starting(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw])
    aio_app.add_routes(routes)

    with patch(
        "meshchatx.meshchat.get_session",
        new_callable=AsyncMock,
    ) as mock_session:
        mock_session.return_value = {}
        async with TestClient(TestServer(aio_app)) as client:
            csrf = await client.get("/api/v1/auth/csrf")
            assert csrf.status == 200


@given(
    status=st.sampled_from(["ok", "starting", "failed"]),
    stage=st.sampled_from(["http", "starting", "rns", "identity", "ready", "failed"]),
    network_ready=st.booleans(),
    error=st.one_of(st.none(), st.text(max_size=200)),
)
@settings(deadline=None, max_examples=80)
def test_status_schema_fuzz_valid_envelopes(status, stage, network_ready, error):
    sample = {
        "status": status,
        "stage": stage,
        "network_ready": network_ready,
        "listen_host": "127.0.0.1",
        "listen_port": 9337,
        "https_enabled": True,
        "is_loopback_bind": True,
        "plugins_enabled": True,
        "landlock_kernel_supported": False,
        "landlock_requested": False,
        "landlock_auto_enabled": False,
        "landlock_disabled_by_env": False,
        "landlock_active": False,
    }
    if error is not None:
        sample["error"] = error
    assert_matches_schema(sample, API_V1_STATUS_SCHEMA)


@given(
    stage=st.sampled_from(["http", "starting", "rns", "identity"]),
    listen_port=st.one_of(st.none(), st.integers(min_value=1, max_value=65535)),
    https_enabled=st.booleans(),
)
@settings(deadline=None, max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_startup_status_payload_fuzz_stages(stage, listen_port, https_enabled):
    identity = MagicMock(spec=RNS.Identity)
    identity.hash = b"test_hash_32_bytes_long_01234567"
    identity.hexhash = identity.hash.hex()
    dir_path = tempfile.mkdtemp()
    try:
        app = _make_deferred_app(identity, dir_path)
        app.listen_host = "127.0.0.1"
        app.listen_port = listen_port
        app.use_https = https_enabled
        app._set_startup_stage(stage)
        payload = app._startup_status_payload()
        assert payload["status"] == "starting"
        assert payload["stage"] == stage
        assert payload["network_ready"] is False
        assert_matches_schema(payload, API_V1_STATUS_SCHEMA)
    finally:
        shutil.rmtree(dir_path, ignore_errors=True)


@given(error=st.text(min_size=0, max_size=500))
@settings(deadline=None, max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_failed_status_payload_fuzz_errors(error):
    identity = MagicMock(spec=RNS.Identity)
    identity.hash = b"test_hash_32_bytes_long_01234567"
    identity.hexhash = identity.hash.hex()
    dir_path = tempfile.mkdtemp()
    try:
        app = _make_deferred_app(identity, dir_path)
        app._set_startup_stage("failed", error)
        payload = app._startup_status_payload()
        assert payload["status"] == "failed"
        assert payload["network_ready"] is False
        if error:
            assert payload["error"] == error
        assert_matches_schema(payload, API_V1_STATUS_SCHEMA)
    finally:
        shutil.rmtree(dir_path, ignore_errors=True)


def test_concurrent_status_payload_reads_during_setup(mock_identity, temp_dir):
    gate = threading.Event()
    results = []

    def fake_setup(self, identity):
        self._set_startup_stage("rns")
        gate.wait(timeout=2)
        self._set_startup_stage("identity")
        context = MagicMock()
        context.running = True
        context.config = MagicMock()
        context.config.auth_session_secret.set = MagicMock()
        self.current_context = context

    with (
        patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
        patch.object(ReticulumMeshChat, "setup_identity", fake_setup),
    ):
        app = ReticulumMeshChat(
            identity=mock_identity,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            defer_network_setup=True,
        )
        app.session_secret_key = "secret"
        app.start_network_setup_in_background()

        def reader():
            for _ in range(20):
                payload = app._startup_status_payload()
                results.append(payload)
                assert payload["status"] in ("starting", "ok", "failed")
                assert "stage" in payload
                assert "network_ready" in payload
                time.sleep(0.005)

        threads = [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        time.sleep(0.05)
        gate.set()
        for t in threads:
            t.join(timeout=5)
        assert app.wait_until_network_ready(timeout=5)
        assert results
        for payload in results:
            assert_matches_schema(payload, API_V1_STATUS_SCHEMA)
