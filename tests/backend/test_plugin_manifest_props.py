# SPDX-License-Identifier: 0BSD

"""Property tests for plugin manifest validation rules."""

from __future__ import annotations

import tempfile

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.plugin_manager import (
    PLUGIN_ID_RE,
    SUPPORTED_API_VERSION,
    PluginManager,
)


def _manager():
    tmp = tempfile.mkdtemp()
    return PluginManager(tmp)


def _valid_manifest(plugin_id="com.example.prop"):
    return {
        "id": plugin_id,
        "version": "1.0.0",
        "apiVersion": SUPPORTED_API_VERSION,
        "name": "Prop Test",
        "permissions": {},
    }


valid_ids = st.from_regex(PLUGIN_ID_RE, fullmatch=True).filter(
    lambda s: "\x00" not in s,
)
invalid_ids = st.text(min_size=0, max_size=40).filter(
    lambda s: not PLUGIN_ID_RE.match(s),
)


@given(
    plugin_id=valid_ids,
    name=st.text(max_size=60),
    version=st.text(alphabet="0123456789.", min_size=1, max_size=12),
)
@settings(max_examples=100, deadline=None)
def test_valid_manifests_always_pass(plugin_id, name, version):
    manifest = _valid_manifest(plugin_id)
    manifest["name"] = name
    manifest["version"] = version
    result = _manager()._validate_manifest(dict(manifest))
    assert result["id"] == plugin_id


@given(plugin_id=invalid_ids)
@settings(max_examples=100, deadline=None)
def test_invalid_ids_always_rejected(plugin_id):
    manifest = _valid_manifest()
    manifest["id"] = plugin_id
    with pytest.raises(ValueError):
        _manager()._validate_manifest(dict(manifest))


@given(
    api_version=st.one_of(
        st.integers().filter(lambda v: v != SUPPORTED_API_VERSION),
        # ASCII letters never parse as an int, so the version is always invalid.
        st.text(alphabet="abcdefxyz!", min_size=1, max_size=8),
        st.none(),
    )
)
@settings(max_examples=100, deadline=None)
def test_wrong_api_version_rejected(api_version):
    manifest = _valid_manifest()
    manifest["apiVersion"] = api_version
    with pytest.raises(ValueError):
        _manager()._validate_manifest(dict(manifest))


@given(data=st.data())
@settings(max_examples=100, deadline=None)
def test_validation_is_deterministic(data):
    manifest = _valid_manifest()
    manifest["name"] = data.draw(st.text(max_size=50))
    manifest["version"] = data.draw(
        st.text(alphabet="0123456789.", min_size=1, max_size=10)
    )
    first = None
    for _ in range(3):
        try:
            _manager()._validate_manifest(dict(manifest))
            outcome = "ok"
        except ValueError:
            outcome = "reject"
        if first is None:
            first = outcome
        assert outcome == first


@given(
    backend_type=st.text(min_size=1, max_size=20).filter(
        lambda s: s not in ("wasm", "python")
    )
)
@settings(max_examples=80, deadline=None)
def test_unknown_backend_type_rejected(backend_type):
    manifest = _valid_manifest()
    manifest["backend"] = {"entry": "plugin.wasm", "type": backend_type}
    with pytest.raises(ValueError):
        _manager()._validate_manifest(dict(manifest))
