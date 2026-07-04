# SPDX-License-Identifier: 0BSD

"""WebSocket JSON message contract tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from tests.backend.ws_contract_helpers import (
    extract_client_direct_response_types,
    extract_client_inbound_types,
    extract_server_broadcast_types,
    load_ws_manifest,
    write_ws_manifest,
)
from tests.backend.ws_json_contract_schemas import (
    WS_MESSAGE_SAMPLES,
    WS_MESSAGE_SCHEMAS,
    all_ws_message_types,
    assert_ws_message_matches_schema,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MESHCHAT_PY = _REPO_ROOT / "meshchatx" / "meshchat.py"
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ws_message_manifest.json"


def _all_manifest_types(manifest: dict[str, list[str]]) -> set[str]:
    out: set[str] = set()
    for key in ("client_inbound", "client_direct_responses", "server_broadcast"):
        out.update(manifest.get(key, []))
    return out


def test_ws_message_manifest_matches_meshchat():
    live = {
        "client_inbound": extract_client_inbound_types(_MESHCHAT_PY),
        "client_direct_responses": extract_client_direct_response_types(_MESHCHAT_PY),
        "server_broadcast": extract_server_broadcast_types(_MESHCHAT_PY),
    }
    if __import__("os").environ.get("UPDATE_WS_MESSAGE_MANIFEST") == "1":
        write_ws_manifest(_FIXTURE, live)
        pytest.skip(
            "UPDATE_WS_MESSAGE_MANIFEST=1: fixture updated; re-run without the env var",
        )
    expected = load_ws_manifest(_FIXTURE)
    assert live == expected, (
        "WebSocket message manifest drifted. Run: "
        "UPDATE_WS_MESSAGE_MANIFEST=1 uv run pytest "
        "tests/backend/test_ws_json_contracts.py -k manifest_matches_meshchat"
    )


def test_every_manifest_type_has_schema():
    manifest = load_ws_manifest(_FIXTURE)
    missing = sorted(_all_manifest_types(manifest) - all_ws_message_types())
    assert not missing, f"Missing WebSocket schemas for: {missing}"


def test_every_schema_has_sample_payload():
    missing = sorted(all_ws_message_types() - set(WS_MESSAGE_SAMPLES))
    assert not missing, f"Missing WebSocket sample payloads for: {missing}"


@pytest.mark.parametrize("msg_type", sorted(WS_MESSAGE_SCHEMAS))
def test_ws_schema_accepts_documented_sample(msg_type: str):
    sample = WS_MESSAGE_SAMPLES[msg_type]
    assert sample["type"] == msg_type
    assert_ws_message_matches_schema(sample)


@pytest.mark.asyncio
async def test_ws_ping_emits_pong_contract():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    client = MagicMock()
    sent: list[str] = []

    async def capture_send(payload: str):
        sent.append(payload)

    client.send_str = AsyncMock(side_effect=capture_send)

    with patch("meshchatx.meshchat.AsyncUtils") as mock_async_utils:
        def run_async(coro):
            import asyncio

            if asyncio.iscoroutine(coro):
                asyncio.get_event_loop().create_task(coro)

        mock_async_utils.run_async.side_effect = run_async
        await app.on_websocket_data_received(client, {"type": "ping"})
        for payload in sent:
            assert_ws_message_matches_schema(json.loads(payload))
            assert json.loads(payload)["type"] == "pong"
