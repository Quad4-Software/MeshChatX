# SPDX-License-Identifier: 0BSD

"""Unit tests for cross-platform self-check helpers."""

from __future__ import annotations

from types import SimpleNamespace

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


def test_check_meshchatx_run_module_ok():
    result = self_check.check_meshchatx_run_module()
    assert result["status"] == "ok", result["reason"]


def test_self_check_labels_cover_schema_keys():
    from tests.backend.api_json_contract_schemas import SELF_TEST_SCHEMA

    required = set(SELF_TEST_SCHEMA["required"])
    assert set(self_check.SELF_CHECK_LABELS) == required
