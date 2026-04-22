# SPDX-License-Identifier: 0BSD

"""Tests for ReticulumMeshChat.get_package_version (About page / frozen bundles)."""

from __future__ import annotations

import importlib.metadata
import sys
from unittest.mock import patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat


def test_get_package_version_uses_metadata_when_available():
    with patch(
        "importlib.metadata.version",
        side_effect=lambda name: "9.8.7" if name == "websockets" else "0",
    ):
        assert ReticulumMeshChat.get_package_version("websockets") == "9.8.7"


def test_get_package_version_resolves_websockets_when_metadata_missing():
    def _missing(*_a, **_k):
        raise importlib.metadata.PackageNotFoundError

    real_import = __import__

    def _import_module(name, package=None):
        if name == "websockets":
            return real_import("websockets")
        return real_import(name, package=package)

    with (
        patch("importlib.metadata.version", side_effect=_missing),
        patch("importlib.metadata.distribution", side_effect=_missing),
        patch("importlib.metadata.packages_distributions", return_value={}),
        patch("importlib.import_module", side_effect=_import_module),
    ):
        v = ReticulumMeshChat.get_package_version("websockets")
    assert v != "unknown"
    assert v[0].isdigit()


def test_get_package_version_resolves_lxmfy_when_metadata_missing():
    def _missing(*_a, **_k):
        raise importlib.metadata.PackageNotFoundError

    real_import = __import__

    def _import_module(name, package=None):
        if name in ("lxmfy", "lxmfy.__version__"):
            return real_import(name)
        return real_import(name, package=package)

    with (
        patch("importlib.metadata.version", side_effect=_missing),
        patch("importlib.metadata.distribution", side_effect=_missing),
        patch("importlib.metadata.packages_distributions", return_value={}),
        patch("importlib.import_module", side_effect=_import_module),
    ):
        v = ReticulumMeshChat.get_package_version("lxmfy")
    assert v != "unknown"
    assert v[0].isdigit()


@pytest.mark.parametrize(
    "package",
    (
        "aiohttp",
        "aiohttp-session",
        "cryptography",
        "psutil",
        "websockets",
        "ply",
        "bcrypt",
        "lxmfy",
    ),
)
def test_app_info_dependency_keys_resolve_in_dev_env(package: str):
    """Regression: About backend stack must not show vunknown for bundled deps."""
    v = ReticulumMeshChat.get_package_version(package)
    assert v != "unknown", f"{package} must resolve when installed"


@pytest.mark.skipif(
    sys.version_info < (3, 13), reason="audioop-lts only on Python 3.13+"
)
def test_audioop_lts_resolves_when_applicable():
    v = ReticulumMeshChat.get_package_version("audioop-lts")
    assert v != "unknown"


def test_get_package_version_works_without_packaging_module():
    real_import = __import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("packaging"):
            raise ModuleNotFoundError("No module named 'packaging'")
        return real_import(name, globals, locals, fromlist, level)

    with (
        patch("builtins.__import__", side_effect=_import),
        patch(
            "importlib.metadata.version",
            side_effect=importlib.metadata.PackageNotFoundError,
        ),
        patch(
            "importlib.metadata.distribution",
            side_effect=importlib.metadata.PackageNotFoundError,
        ),
        patch("importlib.metadata.packages_distributions", return_value={}),
        patch("importlib.import_module", side_effect=Exception),
    ):
        assert ReticulumMeshChat.get_package_version("lxst", "fallback") == "fallback"
