# SPDX-License-Identifier: 0BSD

import asyncio
import base64
import json
from unittest.mock import AsyncMock, patch

import meshchatx.meshchat as meshchat_module
import msgpack

from meshchatx.meshchat import _truncated_hash32_hex_ok
from meshchatx.src.backend import rngit_tool


def test_truncated_hash32_hex_ok_does_not_use_rns_width():
    assert _truncated_hash32_hex_ok("cc" * 16)
    assert not _truncated_hash32_hex_ok("zz" * 16)
    assert not _truncated_hash32_hex_ok("ab")


def _run_async_sync(coro):
    if not asyncio.iscoroutine(coro):
        return
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def _rngit_row(
    *,
    dest_hash="926baefe13daf5178c174f158dae1b45",
    ident_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    app_data=None,
):
    return {
        "id": 1,
        "aspect": rngit_tool.RNGIT_ANNOUNCE_ASPECT,
        "destination_hash": dest_hash,
        "identity_hash": ident_hash,
        "identity_public_key": base64.b64encode(b"\x00" * 32).decode("ascii"),
        "app_data": app_data,
        "rssi": None,
        "snr": None,
        "quality": None,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }


def test_convert_rngit_resolves_display_from_identity(mock_app):
    row = _rngit_row()
    with (
        patch("meshchatx.meshchat.RNS.Transport.hops_to", return_value=3),
        patch.object(
            mock_app.database.announces,
            "get_filtered_announces",
            return_value=[],
        ),
        patch.object(
            mock_app,
            "get_name_for_identity_hash",
            return_value="Contact label",
        ),
    ):
        d = mock_app.convert_db_announce_to_dict(row)
    assert d["display_name"] == "Contact label"
    assert d["hops"] == 3


def test_convert_rngit_prefers_lxmf_same_identity(mock_app):
    ident = "aa" * 16
    lxmf_app = base64.b64encode(msgpack.packb(["Quad4 rngit"])).decode("ascii")
    lxmf_row = {
        "identity_hash": ident,
        "destination_hash": "bb" * 16,
        "app_data": lxmf_app,
    }
    row = _rngit_row(ident_hash=ident)
    with (
        patch("meshchatx.meshchat.RNS.Transport.hops_to", return_value=1),
        patch.object(
            mock_app.database.announces,
            "get_filtered_announces",
            return_value=[lxmf_row],
        ),
        patch.object(
            mock_app,
            "get_name_for_identity_hash",
            return_value="ignored when lxmf wins",
        ),
    ):
        d = mock_app.convert_db_announce_to_dict(row)
    assert d["display_name"] == "Quad4 rngit"


def _announce_upsert_payload(dest, ident, aspect=None):
    aspect = aspect or rngit_tool.RNGIT_ANNOUNCE_ASPECT
    return {
        "destination_hash": dest,
        "aspect": aspect,
        "identity_hash": ident,
        "identity_public_key": base64.b64encode(b"\x01" * 32).decode("ascii"),
        "app_data": None,
        "rssi": None,
        "snr": None,
        "quality": None,
    }


def test_rebroadcast_rngit_for_identity_hashes_pushes_ws(mock_app):
    ident = "ab" * 16
    d1, d2 = "cd" * 16, "ef" * 16
    mock_app.database.announces.upsert_announce(_announce_upsert_payload(d1, ident))
    mock_app.database.announces.upsert_announce(_announce_upsert_payload(d2, ident))
    q = mock_app.database.announces.get_filtered_announces(
        aspect=rngit_tool.RNGIT_ANNOUNCE_ASPECT,
        identity_hash=ident,
        limit=50,
        offset=0,
    )
    assert len(q) == 2, q
    mock_app.websocket_broadcast = AsyncMock()
    run_async_calls = []

    def _track_run_async(coro):
        run_async_calls.append(1)
        return _run_async_sync(coro)

    with (
        patch("meshchatx.meshchat.RNS.Transport.hops_to", return_value=0),
        patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_track_run_async),
    ):
        mock_app.websocket_rebroadcast_rngit_for_identity_hashes({ident})
    assert run_async_calls
    assert mock_app.websocket_broadcast.call_count == 2
    dests = set()
    for c in mock_app.websocket_broadcast.call_args_list:
        payload = json.loads(c[0][0])
        assert payload["type"] == "announce"
        dests.add(payload["announce"]["destination_hash"])
    assert dests == {d1, d2}


def test_rebroadcast_rngit_after_custom_on_lxmf_dest(mock_app):
    ident = "ff" * 16
    lxmf_dest = "11" * 16
    rngit_dest = "22" * 16
    mock_app.database.announces.upsert_announce(
        _announce_upsert_payload(lxmf_dest, ident, aspect="lxmf.delivery"),
    )
    mock_app.database.announces.upsert_announce(
        _announce_upsert_payload(rngit_dest, ident)
    )
    mock_app.websocket_broadcast = AsyncMock()
    with (
        patch("meshchatx.meshchat.RNS.Transport.hops_to", return_value=0),
        patch.object(
            meshchat_module.AsyncUtils, "run_async", side_effect=_run_async_sync
        ),
    ):
        mock_app.websocket_rebroadcast_rngit_after_custom_destination_display_name_change(
            lxmf_dest,
        )
    assert mock_app.websocket_broadcast.call_count == 1
    payload = json.loads(mock_app.websocket_broadcast.call_args[0][0])
    assert payload["announce"]["destination_hash"] == rngit_dest
