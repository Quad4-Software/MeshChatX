# SPDX-License-Identifier: 0BSD

import os

from meshchatx.src.path_utils import resolve_log_dir, resolve_meshchat_data_roots


def test_data_dir_unset_passes_through_explicit_roots():
    storage, rns = resolve_meshchat_data_roots(
        data_dir=None,
        storage_dir="/app/storage",
        reticulum_config_dir="/app/.reticulum",
    )
    assert storage == "/app/storage"
    assert rns == "/app/.reticulum"


def test_data_dir_fills_missing_roots(tmp_path, monkeypatch):
    monkeypatch.delenv("MESHCHAT_DATA_DIR", raising=False)
    root = tmp_path / "persist"
    storage, rns = resolve_meshchat_data_roots(
        data_dir=str(root),
        storage_dir=None,
        reticulum_config_dir=None,
    )
    assert storage == os.path.join(str(root.resolve()), "storage")
    assert rns == os.path.join(str(root.resolve()), ".reticulum")


def test_data_dir_does_not_override_explicit_storage(tmp_path, monkeypatch):
    monkeypatch.delenv("MESHCHAT_DATA_DIR", raising=False)
    root = tmp_path / "persist"
    storage, rns = resolve_meshchat_data_roots(
        data_dir=str(root),
        storage_dir="/custom/storage",
        reticulum_config_dir=None,
    )
    assert storage == "/custom/storage"
    assert rns == os.path.join(str(root.resolve()), ".reticulum")


def test_data_dir_from_env(monkeypatch, tmp_path):
    root = tmp_path / "tails"
    monkeypatch.setenv("MESHCHAT_DATA_DIR", str(root))
    storage, rns = resolve_meshchat_data_roots(
        data_dir=None,
        storage_dir=None,
        reticulum_config_dir=None,
    )
    assert storage == os.path.join(str(root.resolve()), "storage")
    assert rns == os.path.join(str(root.resolve()), ".reticulum")


def _clear_log_dir_env(monkeypatch):
    for var in ("MESHCHAT_LOG_DIR", "MESHCHAT_STORAGE_DIR", "MESHCHAT_DATA_DIR"):
        monkeypatch.delenv(var, raising=False)


def test_resolve_log_dir_prefers_explicit_log_dir_env(monkeypatch, tmp_path):
    _clear_log_dir_env(monkeypatch)
    log_dir = tmp_path / "custom-logs"
    monkeypatch.setenv("MESHCHAT_LOG_DIR", str(log_dir))
    monkeypatch.setenv("MESHCHAT_STORAGE_DIR", str(tmp_path / "storage"))
    assert resolve_log_dir() == str(log_dir)


def test_resolve_log_dir_uses_storage_dir_env(monkeypatch, tmp_path):
    _clear_log_dir_env(monkeypatch)
    storage_dir = tmp_path / "storage"
    monkeypatch.setenv("MESHCHAT_STORAGE_DIR", str(storage_dir))
    assert resolve_log_dir() == os.path.join(str(storage_dir), "logs")


def test_resolve_log_dir_falls_back_to_data_dir_env_for_portable_mode(
    monkeypatch,
    tmp_path,
):
    """Keep logs off the home directory when only MESHCHAT_DATA_DIR is set.

    A Tails-style persistent volume set via MESHCHAT_DATA_DIR should relocate
    logs even when MESHCHAT_STORAGE_DIR is unset.
    """
    _clear_log_dir_env(monkeypatch)
    persist_root = tmp_path / "tails"
    monkeypatch.setenv("MESHCHAT_DATA_DIR", str(persist_root))
    assert resolve_log_dir() == os.path.join(
        str(persist_root.resolve()),
        "storage",
        "logs",
    )


def test_resolve_log_dir_storage_dir_env_wins_over_data_dir_env(monkeypatch, tmp_path):
    _clear_log_dir_env(monkeypatch)
    storage_dir = tmp_path / "explicit-storage"
    data_dir = tmp_path / "persist"
    monkeypatch.setenv("MESHCHAT_STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("MESHCHAT_DATA_DIR", str(data_dir))
    assert resolve_log_dir() == os.path.join(str(storage_dir), "logs")
