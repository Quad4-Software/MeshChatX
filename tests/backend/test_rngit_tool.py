# SPDX-License-Identifier: 0BSD

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.src.backend import rngit_tool


def test_normalize_destination_hash_hex():
    h = "a" * 32
    assert rngit_tool.normalize_destination_hash_hex(h) == h
    assert rngit_tool.normalize_destination_hash_hex("A" * 32) == h
    assert rngit_tool.normalize_destination_hash_hex("x" * 32) is None


def test_parse_repository_name_lines():
    text = "  one  \n#skip\ntwo\n\nthree"
    assert rngit_tool.parse_repository_name_lines(text) == ["one", "two", "three"]


def test_clone_command():
    assert (
        rngit_tool.clone_command("ab" * 16, "g", "r")
        == f"git clone rns://{'ab' * 16}/g/r"
    )


def test_display_name_from_rngit_app_data():
    import base64

    enc = base64.b64encode(b"My mirror\nextra").decode("ascii")
    assert rngit_tool.display_name_from_rngit_app_data(enc) == "My mirror"
    assert rngit_tool.display_name_from_rngit_app_data(None) is None


@pytest.mark.asyncio
async def test_probe_rejects_invalid_destination():
    ident = MagicMock()
    out = await rngit_tool.probe_repositories(ident, "not-hex", "g", ["a"])
    assert out["ok"] is False
    assert out["error"] == "invalid_destination_hash"


@pytest.mark.asyncio
async def test_probe_rejects_empty_names():
    ident = MagicMock()
    out = await rngit_tool.probe_repositories(ident, "a" * 32, "group", [])
    assert out["ok"] is False
    assert out["error"] == "no_repository_names"


@pytest.mark.asyncio
async def test_probe_calls_list_per_repo():
    ident = MagicMock()
    with patch.object(
        rngit_tool, "list_remote_git_refs", new_callable=AsyncMock
    ) as mock_list:
        mock_list.side_effect = [
            {"ok": True, "refs": "ref1\n"},
            {"ok": False, "error": "Not found"},
        ]
        out = await rngit_tool.probe_repositories(
            ident, "a" * 32, "quad4", ["R1", "R2"]
        )
    assert out["ok"] is True
    assert len(out["results"]) == 2
    assert out["results"][0]["reachable"] is True
    assert out["results"][0]["clone_command"] == f"git clone rns://{'a' * 32}/quad4/R1"
    assert mock_list.await_count == 2
