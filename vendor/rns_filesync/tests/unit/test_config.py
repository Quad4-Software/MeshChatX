"""Unit tests for FileSync config helpers."""

import os

import pytest

from rns_filesync.config import (
    allowed_sidecar_paths,
    ensure_config,
    load_config,
    parse_csv_hashes,
)

pytestmark = pytest.mark.unit


def test_ensure_and_load_config(tmp_path):
    cfg_dir = tmp_path / "fsconf"
    path = ensure_config(str(cfg_dir))
    assert os.path.isfile(os.path.join(path, "config"))
    loaded_dir, config = load_config(str(cfg_dir))
    assert loaded_dir == path
    assert "filesync" in config


def test_allowed_sidecar_paths(tmp_path):
    sync = tmp_path / "shared"
    sync.mkdir()
    paths = allowed_sidecar_paths(str(sync))
    assert any(p.endswith(".allowed") for p in paths)
    assert any(
        p.endswith(os.path.join("shared", ".allowed")) or p.endswith("shared/.allowed")
        for p in paths
    )


def test_parse_csv_hashes():
    assert parse_csv_hashes("aa, bb") == ["aa", "bb"]
    assert parse_csv_hashes(None) == []
