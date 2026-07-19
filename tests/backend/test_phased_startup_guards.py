# SPDX-License-Identifier: 0BSD

"""Guards, races, and adversarial cases for phased / early-UI startup."""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import RNS
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.identity_context import IdentityContext
from meshchatx.src.backend.integrity_manager import (
    IntegrityManager,
    select_critical_integrity_issues,
)
from tests.backend.api_json_contract_schemas import (
    API_V1_STATUS_SCHEMA,
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


def _status_oracle(payload: dict) -> None:
    """Invariant oracle for /api/v1/status style payloads."""
    assert_matches_schema(payload, API_V1_STATUS_SCHEMA)
    assert payload["network_ready"] is False or payload["status"] == "ok"
    if payload["status"] == "ok":
        assert payload["network_ready"] is True
        assert payload["ui_ready"] is True
        assert payload["network_degraded"] is False
    if payload["status"] == "failed":
        assert payload["network_ready"] is False
        assert payload["ui_ready"] is True
        assert payload["network_degraded"] is True
    if payload["status"] == "starting":
        assert payload["network_ready"] is False
        assert payload["ui_ready"] is True


def test_deferred_init_ui_ready_before_network(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    payload = app._startup_status_payload()
    _status_oracle(payload)
    assert payload["ui_ready"] is True
    assert payload["network_ready"] is False


def test_status_oracle_across_stage_transitions(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    for stage in ("http", "starting", "rns", "identity"):
        app._set_startup_stage(stage)
        _status_oracle(app._startup_status_payload())
    app._mark_network_degraded("boom")
    _status_oracle(app._startup_status_payload())
    context = MagicMock()
    context.running = True
    app.current_context = context
    app._mark_network_ready()
    _status_oracle(app._startup_status_payload())


def test_finish_deferred_calls_context_and_reticulum_secondary(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    ctx = MagicMock()
    ctx.running = True
    app.current_context = ctx
    app._reticulum_secondary_started = False
    with patch.object(app, "_start_deferred_reticulum_services") as start_rns:
        app._finish_deferred_startup_services()
        ctx.setup_deferred_services.assert_called_once_with()
        start_rns.assert_called_once_with()


def test_require_rns_tool_handler_503_while_deferred_pending(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    ctx = MagicMock()
    ctx.running = True
    app.current_context = ctx
    app._mark_network_ready()
    response = app._require_rns_tool_handler(None, "RNCP")
    assert response is not None
    assert response.status == 503
    body = json.loads(response.body)
    assert "RNCP" in body["message"]
    assert body["network_ready"] is True


def test_deferred_setup_idempotent_under_concurrent_calls(temp_dir):
    app = MagicMock()
    app.emergency = False
    app.storage_dir = temp_dir
    app.reticulum_config_dir = temp_dir
    app.get_public_path = MagicMock(return_value=temp_dir)
    app.integrity_issues = []
    app.database_health_issues = []

    identity = MagicMock()
    identity.hash = b"abcdef0123456789abcdef0123456789"

    ctx = IdentityContext.__new__(IdentityContext)
    ctx.app = app
    ctx.identity = identity
    ctx.identity_hash = identity.hash.hex()
    ctx.storage_path = temp_dir
    ctx.database_path = str(Path(temp_dir) / "database.db")
    ctx.running = True
    ctx._deferred_setup_done = False
    ctx._deferred_setup_lock = threading.Lock()
    ctx._deferred_setup_in_progress = False
    ctx._deferred_setup_finished = threading.Event()
    ctx._deferred_setup_finished.set()
    ctx.config = MagicMock()
    ctx.config.rrc_enabled.get.return_value = False
    ctx.config.libretranslate_url.get.return_value = ""
    ctx.config.libretranslate_api_key.get.return_value = ""
    ctx.config.translator_argos_enabled.get.return_value = False
    ctx.config.translator_libretranslate_enabled.get.return_value = False
    ctx.database = MagicMock()
    ctx.docs_manager = MagicMock()
    ctx.integrity_manager = MagicMock()
    ctx.integrity_manager.check_integrity.return_value = (True, [])

    calls = []
    gate = threading.Event()
    entered = threading.Event()

    def slow_body():
        calls.append("body")
        entered.set()
        gate.wait(timeout=2)

    ctx._run_deferred_services_body = slow_body

    threads = [threading.Thread(target=ctx.setup_deferred_services) for _ in range(8)]
    for thread in threads:
        thread.start()
    assert entered.wait(timeout=2)
    gate.set()
    for thread in threads:
        thread.join(timeout=2)
    assert len(calls) == 1
    assert ctx._deferred_setup_done is True
    assert ctx._deferred_setup_in_progress is False


def test_deferred_setup_aborts_when_torn_down_mid_flight(temp_dir):
    app = MagicMock()
    app.emergency = True
    app.storage_dir = temp_dir
    app.get_public_path = MagicMock(return_value=temp_dir)

    identity = MagicMock()
    identity.hash = b"abcdef0123456789abcdef0123456789"

    ctx = IdentityContext.__new__(IdentityContext)
    ctx.app = app
    ctx.identity = identity
    ctx.identity_hash = identity.hash.hex()
    ctx.storage_path = temp_dir
    ctx.running = True
    ctx._deferred_setup_done = False
    ctx._deferred_setup_lock = threading.Lock()
    ctx._deferred_setup_in_progress = False
    ctx._deferred_setup_finished = threading.Event()
    ctx._deferred_setup_finished.set()
    ctx.rncp_handler = None

    started = threading.Event()
    release = threading.Event()

    def body():
        started.set()
        release.wait(timeout=2)
        if not ctx.running:
            return
        ctx.rncp_handler = MagicMock(name="zombie-handler")

    ctx._run_deferred_services_body = body

    worker = threading.Thread(target=ctx.setup_deferred_services)
    worker.start()
    assert started.wait(timeout=2)
    ctx.running = False
    release.set()
    worker.join(timeout=2)
    assert ctx._deferred_setup_done is False
    assert ctx.rncp_handler is None


def test_teardown_waits_for_in_flight_deferred_setup(temp_dir):
    ctx = IdentityContext.__new__(IdentityContext)
    ctx.identity_hash = "abc"
    ctx.running = True
    ctx._deferred_setup_done = False
    ctx._deferred_setup_lock = threading.Lock()
    ctx._deferred_setup_in_progress = False
    ctx._deferred_setup_finished = threading.Event()
    ctx._deferred_setup_finished.set()

    started = threading.Event()
    release = threading.Event()

    def body():
        started.set()
        release.wait(timeout=2)

    ctx._run_deferred_services_body = body

    worker = threading.Thread(target=ctx.setup_deferred_services)
    worker.start()
    assert started.wait(timeout=2)
    assert ctx._deferred_setup_finished.is_set() is False

    waiter_done = threading.Event()

    def wait_like_teardown():
        ctx.running = False
        assert ctx._deferred_setup_finished.wait(timeout=2)
        waiter_done.set()

    waiter = threading.Thread(target=wait_like_teardown)
    waiter.start()
    time.sleep(0.05)
    assert waiter_done.is_set() is False
    release.set()
    waiter.join(timeout=2)
    worker.join(timeout=2)
    assert waiter_done.is_set()
    assert ctx._deferred_setup_in_progress is False
    assert ctx._deferred_setup_done is False


def test_critical_integrity_blocks_on_identity_file_tamper(temp_dir):
    storage = Path(temp_dir)
    db_path = storage / "database.db"
    db_path.write_bytes(b"ok-db")
    identity_path = storage / "identity"
    identity_path.write_bytes(b"secret-key-material")

    manager = IntegrityManager(str(storage), str(db_path), identity_hash="abc123")
    manager.save_manifest()

    identity_path.write_bytes(b"TAMPERED")
    is_ok, issues = manager.check_integrity(critical_only=True)
    assert is_ok is False
    critical = select_critical_integrity_issues(issues)
    assert critical
    assert any("identity" in issue.lower() for issue in critical)


def test_critical_integrity_ignores_non_critical_new_files(temp_dir):
    storage = Path(temp_dir)
    db_path = storage / "database.db"
    db_path.write_bytes(b"ok-db")
    (storage / "identity").write_bytes(b"secret")

    manager = IntegrityManager(str(storage), str(db_path), identity_hash="abc123")
    manager.save_manifest()

    (storage / "notes.txt").write_text("benign", encoding="utf-8")
    is_ok_critical, issues_critical = manager.check_integrity(critical_only=True)
    assert is_ok_critical is True or not select_critical_integrity_issues(
        issues_critical
    )

    is_ok_full, issues_full = manager.check_integrity(critical_only=False)
    assert is_ok_full is False
    assert any("New file detected" in issue for issue in issues_full)


def test_critical_integrity_identity_mismatch_still_raises_marker(temp_dir):
    storage = Path(temp_dir)
    db_path = storage / "database.db"
    db_path.write_bytes(b"ok-db")
    (storage / "identity").write_bytes(b"secret")

    manager = IntegrityManager(str(storage), str(db_path), identity_hash="original")
    manager.save_manifest()

    other = IntegrityManager(str(storage), str(db_path), identity_hash="other-hash")
    is_ok, issues = other.check_integrity(critical_only=True)
    assert is_ok is False
    assert select_critical_integrity_issues(issues)


@given(
    stage=st.sampled_from(["http", "starting", "rns", "identity", "ready"]),
    ui_ready=st.booleans(),
    network_ready=st.booleans(),
    degraded=st.booleans(),
)
@settings(max_examples=40, deadline=None)
def test_status_payload_never_claims_ready_without_context(
    stage,
    ui_ready,
    network_ready,
    degraded,
):
    dir_path = tempfile.mkdtemp()
    try:
        identity = MagicMock(spec=RNS.Identity)
        identity.hash = b"test_hash_32_bytes_long_01234567"
        identity.hexhash = identity.hash.hex()
        app = _make_deferred_app(identity, dir_path)
        app._startup_stage = stage
        app._ui_ready = ui_ready
        app._network_ready = network_ready
        app._network_degraded = degraded
        if degraded:
            app._startup_error = "x"
            app._startup_stage = "failed"
        payload = app._startup_status_payload()
        if payload["status"] == "ok":
            assert app.current_context is not None and app.current_context.running
            assert payload["network_ready"] is True
        if payload["network_ready"] is True:
            assert payload["status"] == "ok"
        assert_matches_schema(payload, API_V1_STATUS_SCHEMA)
    finally:
        shutil.rmtree(dir_path)


def test_background_setup_marks_ready_before_deferred_finishes(mock_identity, temp_dir):
    ready_seen = threading.Event()
    deferred_started = threading.Event()
    release_deferred = threading.Event()

    def fake_setup(self, identity):
        context = MagicMock()
        context.running = True
        context.config = MagicMock()
        context.config.auth_session_secret.set = MagicMock()

        def deferred():
            deferred_started.set()
            release_deferred.wait(timeout=2)

        context.setup_deferred_services = deferred
        self.current_context = context
        ready_seen.set()

    with (
        patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
        patch.object(ReticulumMeshChat, "setup_identity", fake_setup),
        patch.object(ReticulumMeshChat, "_start_deferred_reticulum_services"),
    ):
        app = ReticulumMeshChat(
            identity=mock_identity,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            defer_network_setup=True,
        )
        app.session_secret_key = "secret"
        app.start_network_setup_in_background()
        assert ready_seen.wait(timeout=5)
        assert app.wait_until_network_ready(timeout=5)
        payload = app._startup_status_payload()
        assert payload["network_ready"] is True
        assert deferred_started.wait(timeout=2)
        # Mesh is already advertised ready while deferred is still blocked.
        assert release_deferred.is_set() is False
        release_deferred.set()


def test_reticulum_secondary_idempotent(mock_identity, temp_dir):
    app = _make_deferred_app(mock_identity, temp_dir)
    app.reticulum = MagicMock()
    app.plugins_enabled = False
    app.page_node_manager = MagicMock()
    app.page_node_manager.nodes = {}
    app.sideband_plugin_loader = MagicMock()
    app._start_deferred_reticulum_services()
    app._start_deferred_reticulum_services()
    app.page_node_manager.start_all.assert_called_once()
