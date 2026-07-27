# SPDX-License-Identifier: 0BSD

import os

from meshchatx.src.path_utils import resolve_meshchat_data_roots


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
