# SPDX-License-Identifier: 0BSD

"""Oracle tests for meshchatx.src.json_store.

Accept/reject oracle: load_json must return exactly the stored object or
exactly the default; never a partial parse, never raise for missing or
corrupt files, and never return a wrong-typed top level.
"""

from __future__ import annotations

import os
import uuid

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.json_store import (
    load_json,
    load_json_required,
    save_json,
)


def _tmpfile(tmp_path):
    return tmp_path / str(uuid.uuid4())


class TestLoadJson:
    def test_missing_file_returns_default(self, tmp_path):
        missing = tmp_path / "nope.json"
        assert load_json(missing) is None
        assert load_json(missing, {}) == {}
        assert load_json(missing, "sentinel") == "sentinel"

    def test_valid_roundtrip(self, tmp_path):
        path = _tmpfile(tmp_path)
        path.write_text('{"a": 1, "b": [2]}', encoding="utf-8")
        assert load_json(path) == {"a": 1, "b": [2]}

    def test_corrupt_returns_default(self, tmp_path):
        path = _tmpfile(tmp_path)
        path.write_bytes(b'{"a": 1, broken')
        assert load_json(path, {"x": 0}) == {"x": 0}

    def test_non_utf8_returns_default(self, tmp_path):
        path = _tmpfile(tmp_path)
        path.write_bytes(b'{"a": "\xff\xfe"}')
        assert load_json(path, "d") == "d"

    def test_max_bytes_enforced(self, tmp_path):
        path = _tmpfile(tmp_path)
        path.write_bytes(b'{"a": "' + b"x" * 64 + b'"}')
        assert load_json(path, "d", max_bytes=10) == "d"
        assert load_json(path, "d", max_bytes=1024) == {"a": "x" * 64}

    def test_max_bytes_none_reads_all(self, tmp_path):
        path = _tmpfile(tmp_path)
        path.write_bytes(b"[" + b"1," * 500 + b"1]")
        assert len(load_json(path, max_bytes=None)) == 501

    def test_expect_filters_type(self, tmp_path):
        path = _tmpfile(tmp_path)
        path.write_text("[1, 2]", encoding="utf-8")
        assert load_json(path, "d", expect=dict) == "d"
        assert load_json(path, expect=list) == [1, 2]

    def test_scalar_top_level(self, tmp_path):
        path = _tmpfile(tmp_path)
        path.write_text("42", encoding="utf-8")
        assert load_json(path) == 42
        assert load_json(path, "d", expect=dict) == "d"

    def test_directory_returns_default(self, tmp_path):
        assert load_json(tmp_path, "d") == "d"

    def test_nul_path_returns_default(self):
        assert load_json("a\x00b", "d") == "d"

    @given(
        payload=st.recursive(
            st.none()
            | st.booleans()
            | st.integers()
            | st.floats(allow_nan=False)
            | st.text(),
            lambda children: (
                st.lists(children, max_size=5)
                | st.dictionaries(st.text(), children, max_size=5)
            ),
            max_leaves=20,
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_save_then_load_roundtrip(self, payload, tmp_path):
        path = _tmpfile(tmp_path)
        save_json(path, payload)
        assert load_json(path, max_bytes=None) == payload


class TestLoadJsonRequired:
    def test_missing_raises(self, tmp_path):
        with pytest.raises(ValueError):
            load_json_required(tmp_path / "nope.json")

    def test_corrupt_raises_generic(self, tmp_path):
        path = _tmpfile(tmp_path)
        path.write_bytes(b"{broken")
        with pytest.raises(ValueError) as excinfo:
            load_json_required(path)
        # Message names the file basename only, not parse internals.
        assert "broken" not in str(excinfo.value)
        assert "Expecting" not in str(excinfo.value)

    def test_wrong_type_raises(self, tmp_path):
        path = _tmpfile(tmp_path)
        path.write_text("[1]", encoding="utf-8")
        with pytest.raises(ValueError):
            load_json_required(path, expect=dict)


class TestSaveJson:
    def test_writes_indented_sorted(self, tmp_path):
        path = _tmpfile(tmp_path)
        save_json(path, {"b": 1, "a": 2}, sort_keys=True)
        text = path.read_text(encoding="utf-8")
        assert text == '{\n  "a": 2,\n  "b": 1\n}\n'

    def test_overwrites_atomically_no_tmp_left(self, tmp_path):
        path = _tmpfile(tmp_path)
        save_json(path, {"v": 1})
        save_json(path, {"v": 2})
        assert load_json(path) == {"v": 2}
        leftovers = [
            p
            for p in path.parent.iterdir()
            if p.name != path.name and p.name.endswith(".tmp")
        ]
        assert leftovers == []

    def test_mode_private(self, tmp_path):
        path = _tmpfile(tmp_path)
        save_json(path, {"secret": 1}, mode=0o600)
        assert (os.stat(path).st_mode & 0o777) == 0o600

    def test_non_serializable_raises(self, tmp_path):
        with pytest.raises(TypeError):
            save_json(_tmpfile(tmp_path), {"x": object()})
