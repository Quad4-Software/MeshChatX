# SPDX-License-Identifier: 0BSD

"""Unit tests for cross-platform self-check helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from meshchatx.src.backend import self_check


def test_check_python_runtime_ok():
    assert self_check.check_python_runtime()["status"] == "ok"


def test_check_critical_imports_ok():
    assert self_check.check_critical_imports()["status"] == "ok"


def test_check_identity_ok():
    identity = SimpleNamespace(hash=b"\x11" * 16)
    assert self_check.check_identity(identity)["status"] == "ok"


def test_check_identity_missing():
    result = self_check.check_identity(None)
    assert result["status"] == "failed"
    assert "not loaded" in result["reason"].lower()


def test_check_identity_bad_hash_length():
    identity = SimpleNamespace(hash=b"\x11" * 8)
    result = self_check.check_identity(identity)
    assert result["status"] == "failed"


def test_check_lxmf_router_ok():
    router = object()
    dest = SimpleNamespace(hash=b"\xaa" * 16)
    assert self_check.check_lxmf_router(router, dest)["status"] == "ok"


def test_check_lxmf_router_missing():
    result = self_check.check_lxmf_router(None, None)
    assert result["status"] == "failed"


def test_check_storage_lock_ok(tmp_path):
    result = self_check.check_storage_lock(str(tmp_path))
    assert result["status"] == "ok", result["reason"]
    assert not (tmp_path / ".self_test_storage_lock").exists()
    assert not (tmp_path / ".self_test_storage_lock_soft").exists()


def test_check_storage_lock_soft_fallback_helper(tmp_path):
    soft_dir = tmp_path / "soft"
    soft_dir.mkdir()
    result = self_check._check_storage_lock_soft_fallback(str(soft_dir))
    assert result["status"] == "ok", result["reason"]


def test_check_temp_filesystem_ok():
    assert self_check.check_temp_filesystem()["status"] == "ok"


def test_check_public_assets_ok(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")

    def public_path(name=""):
        return str(tmp_path / name) if name else str(tmp_path)

    assert self_check.check_public_assets(public_path)["status"] == "ok"


def test_check_public_assets_allows_source_tree_without_build(tmp_path, monkeypatch):
    missing = tmp_path / "nope"

    def public_path(name=""):
        return str(missing / name) if name else str(missing)

    monkeypatch.setattr(self_check, "_is_frozen_executable", lambda: False)
    monkeypatch.setattr(self_check, "_frontend_source_available", lambda: True)
    assert self_check.check_public_assets(public_path)["status"] == "ok"


def test_check_public_assets_missing_when_frozen(tmp_path, monkeypatch):
    missing = tmp_path / "nope"

    def public_path(name=""):
        return str(missing / name) if name else str(missing)

    monkeypatch.setattr(self_check, "_is_frozen_executable", lambda: True)
    monkeypatch.setattr(self_check, "_frontend_source_available", lambda: False)
    result = self_check.check_public_assets(public_path)
    assert result["status"] == "failed"


def test_check_subprocess_spawn_ok():
    assert self_check.check_subprocess_spawn()["status"] == "ok"


def test_check_subprocess_spawn_frozen_uses_run_module(monkeypatch):
    calls: list[list[str]] = []

    class _Result:
        returncode = 0
        stdout = "meshchatx-self-check-probe spawn-ok\n"
        stderr = ""

    def _fake_run(cmd, **_kwargs):
        calls.append(list(cmd))
        return _Result()

    monkeypatch.setattr(self_check, "_is_frozen_executable", lambda: True)
    monkeypatch.setattr(self_check.subprocess, "run", _fake_run)
    result = self_check.check_subprocess_spawn()
    assert result["status"] == "ok", result["reason"]
    assert calls
    assert "-c" not in calls[0]
    assert "--meshchatx-run-module" in calls[0]
    assert "meshchatx.src.backend.self_check_probe" in calls[0]


def test_check_meshchatx_run_module_ok():
    result = self_check.check_meshchatx_run_module()
    assert result["status"] == "ok", result["reason"]


def test_check_sqlite_roundtrip_ok(tmp_path):
    assert self_check.check_sqlite_roundtrip(str(tmp_path))["status"] == "ok"


def test_check_identity_file_roundtrip_ok(tmp_path):
    result = self_check.check_identity_file_roundtrip(str(tmp_path))
    assert result["status"] == "ok", result["reason"]


def test_check_loopback_tcp_ok():
    assert self_check.check_loopback_tcp()["status"] == "ok"


def test_check_unicode_path_ok(tmp_path):
    assert self_check.check_unicode_path(str(tmp_path))["status"] == "ok"


def test_check_rnode_support_ok():
    assert self_check.check_rnode_support()["status"] == "ok"


def test_check_bot_launcher_ok():
    assert self_check.check_bot_launcher()["status"] == "ok"


def test_check_plugins_runtime_ok(mock_app):
    result = self_check.check_plugins_runtime(mock_app)
    assert result["status"] == "ok", result.get("reason")


def test_check_web_stack_ok(mock_app, require_loopback_tcp):
    from unittest.mock import AsyncMock, MagicMock

    # Avoid MagicMock telephone objects taking the "enabled" code path.
    mock_app.telephone_manager.telephone = None
    # /api/v1/config and /api/v1/app/info must JSON-serialize reticulum/identity fields.
    mock_app.current_context.identity.get_public_key = MagicMock(
        return_value=bytes(32),
    )
    mock_app.current_context.local_lxmf_destination.hexhash = "a" * 32
    mock_app.current_context.message_router.propagation_destination.hexhash = "b" * 32
    if getattr(mock_app, "reticulum", None) is not None:
        mock_app.reticulum.is_connected_to_shared_instance = False
        mock_app.reticulum.share_instance = True
        mock_app.reticulum.transport_enabled = MagicMock(return_value=False)
        mock_app.reticulum.get_path_table = MagicMock(return_value=[])

        class _Cfg(dict):
            def write(self):
                return True

        mock_app.reticulum.config = _Cfg(
            {
                "reticulum": {
                    "share_instance": "Yes",
                    "local_hops_delta": "No",
                },
                "interfaces": {},
            },
        )
    # WebSocket handler awaits these.
    mock_app.send_config_to_websocket_clients = AsyncMock(return_value=None)
    mock_app.websocket_broadcast = AsyncMock()
    results = self_check.check_web_stack(mock_app)
    expected = set(self_check._WEB_PROBE_KEYS)
    assert set(results) == expected
    for key, value in results.items():
        assert value["status"] == "ok", f"{key}: {value.get('reason')}"


def test_self_check_labels_cover_schema_keys():
    from tests.backend.api_json_contract_schemas import SELF_TEST_SCHEMA

    required = set(SELF_TEST_SCHEMA["required"])
    assert set(self_check.SELF_CHECK_LABELS) == required


@pytest.mark.asyncio
async def test_probe_rns_link_api_accepts_no_active_link():
    from unittest.mock import AsyncMock

    from aiohttp import WSMsgType

    class FakeMsg:
        def __init__(self, payload):
            self.type = WSMsgType.TEXT
            self.data = payload

    ws = AsyncMock()
    ws.send_str = AsyncMock()
    ws.receive = AsyncMock(
        return_value=FakeMsg(
            '{"type":"rns.link.close","request_id":"self-check-rns-link",'
            '"status":"failure","failure_reason":"no_active_link"}',
        ),
    )
    result = await self_check._probe_rns_link_api(ws, timeout=1)
    assert result["status"] == "ok"
    ws.send_str.assert_awaited()


@pytest.mark.asyncio
async def test_probe_rns_link_api_rejects_unexpected_failure():
    from unittest.mock import AsyncMock

    from aiohttp import WSMsgType

    class FakeMsg:
        def __init__(self, payload):
            self.type = WSMsgType.TEXT
            self.data = payload

    ws = AsyncMock()
    ws.send_str = AsyncMock()
    ws.receive = AsyncMock(
        return_value=FakeMsg(
            '{"type":"rns.link.close","request_id":"self-check-rns-link",'
            '"status":"failure","failure_reason":"boom"}',
        ),
    )
    result = await self_check._probe_rns_link_api(ws, timeout=1)
    assert result["status"] == "failed"
