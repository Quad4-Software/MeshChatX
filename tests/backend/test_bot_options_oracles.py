# SPDX-License-Identifier: 0BSD

"""Oracles for the non-LXMF bot options: icon appearance and custom commands."""

import json
import os

import pytest

from meshchatx.src.backend.bot_options import (
    load_bot_runtime_sidecar,
    normalize_bot_custom,
    normalize_bot_icon,
    normalize_hex_colour,
    write_bot_runtime_sidecar,
)


class TestIconNormalizer:
    def test_roundtrip_normalizes_case_and_missing_hash(self):
        out = normalize_bot_icon(
            {"icon_name": "robot", "fg_color": "AABBCC", "bg_color": "#112233"}
        )
        assert out == {
            "icon_name": "robot",
            "fg_color": "#aabbcc",
            "bg_color": "#112233",
        }

    def test_absent_values_become_none(self):
        assert normalize_bot_icon(None) is None
        assert normalize_bot_icon({}) is None
        assert normalize_bot_icon({"icon_name": ""}) is None
        assert normalize_bot_icon({"icon_name": "   "}) is None

    def test_missing_colours_get_defaults(self):
        out = normalize_bot_icon({"icon_name": "forum"})
        assert out["fg_color"] == "#6b7280"
        assert out["bg_color"] == "#e5e7eb"

    @pytest.mark.parametrize(
        "bad",
        [
            "not a dict",
            {"icon_name": "has space"},
            {"icon_name": "x" * 65},
            {"icon_name": "ok", "fg_color": "notacolour"},
            {"icon_name": "ok", "fg_color": "#12345"},
            {"icon_name": "ok", "bg_color": "gggggg"},
        ],
    )
    def test_invalid_input_raises(self, bad):
        with pytest.raises(ValueError):
            normalize_bot_icon(bad)

    def test_hex_colour_helper(self):
        assert normalize_hex_colour(None) is None
        assert normalize_hex_colour("") is None
        assert normalize_hex_colour("FF00AA") == "#ff00aa"
        with pytest.raises(ValueError):
            normalize_hex_colour("#12345")


class TestCustomNormalizer:
    def test_commands_and_welcome(self):
        out = normalize_bot_custom(
            {
                "commands": [
                    {"name": "ping", "response": "pong"},
                    {"name": "About", "response": "v1", "description": "d"},
                ],
                "welcome": "hi",
            }
        )
        assert out["welcome"] == "hi"
        assert [c["name"] for c in out["commands"]] == ["ping", "About"]
        assert out["commands"][1]["description"] == "d"

    def test_empty_input_returns_none(self):
        assert normalize_bot_custom(None) is None
        assert normalize_bot_custom({}) is None
        assert normalize_bot_custom({"commands": []}) is None
        assert normalize_bot_custom({"welcome": "   "}) is None

    @pytest.mark.parametrize(
        "bad",
        [
            "text",
            {"commands": "notalist"},
            {"commands": [{"name": "bad name", "response": "x"}]},
            {"commands": [{"name": "ok"}]},
            {"commands": [{"name": "a", "response": "1"}, {"name": "A", "response": "2"}]},
            {"welcome": 42},
        ],
    )
    def test_invalid_input_raises(self, bad):
        with pytest.raises(ValueError):
            normalize_bot_custom(bad)

    def test_command_cap(self):
        many = [{"name": f"c{i}", "response": "r"} for i in range(65)]
        with pytest.raises(ValueError):
            normalize_bot_custom({"commands": many})
        ok = [{"name": f"c{i}", "response": "r"} for i in range(64)]
        assert len(normalize_bot_custom({"commands": ok})["commands"]) == 64


class TestRuntimeSidecar:
    def test_roundtrip(self, tmp_path):
        icon = {"icon_name": "robot", "fg_color": "#aabbcc", "bg_color": "#112233"}
        custom = {"commands": [{"name": "x", "response": "y"}], "welcome": "hi"}
        path = write_bot_runtime_sidecar(
            str(tmp_path), {"icon": icon, "custom": custom}
        )
        loaded = load_bot_runtime_sidecar(path)
        assert loaded["icon"] == icon
        assert loaded["custom"] == custom

    def test_explicit_null_icon_is_preserved(self, tmp_path):
        path = write_bot_runtime_sidecar(str(tmp_path), {"icon": None})
        loaded = load_bot_runtime_sidecar(path)
        assert "icon" in loaded
        assert loaded["icon"] is None

    def test_absent_icon_key_means_default(self, tmp_path):
        path = write_bot_runtime_sidecar(str(tmp_path), {})
        loaded = load_bot_runtime_sidecar(path)
        assert "icon" not in loaded

    def test_missing_file_and_garbage(self, tmp_path):
        assert load_bot_runtime_sidecar(None) == {}
        assert load_bot_runtime_sidecar(str(tmp_path / "nope.json")) == {}
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        assert load_bot_runtime_sidecar(str(bad)) == {}
        arr = tmp_path / "arr.json"
        arr.write_text("[1,2]", encoding="utf-8")
        assert load_bot_runtime_sidecar(str(arr)) == {}

    def test_invalid_sections_are_dropped_not_fatal(self, tmp_path):
        path = tmp_path / "meshchatx_bot_runtime.json"
        path.write_text(
            json.dumps(
                {
                    "icon": {"icon_name": "bad name"},
                    "custom": {"commands": [{"name": "ok", "response": "r"}]},
                }
            ),
            encoding="utf-8",
        )
        loaded = load_bot_runtime_sidecar(str(path))
        assert loaded["icon"] is None
        assert loaded["custom"]["commands"][0]["name"] == "ok"
