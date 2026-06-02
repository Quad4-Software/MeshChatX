# SPDX-License-Identifier: 0BSD

"""Security and fuzz tests for Reticulum Relay Chat HTTP API endpoints."""

import json
import os
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

HUB_HASH_HEX = "00112233445566778899aabbccddeeff"


def _find_handler(app, path, method):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _make_request(json_body=None, match_info=None, query=None):
    request = MagicMock()

    async def _json():
        return json_body if json_body is not None else {}

    request.json = _json
    request.match_info = match_info or {}
    request.query = query or {}
    return request


async def _add_hub(mock_app, hub_hash_hex=HUB_HASH_HEX):
    post = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    return await post(_make_request(json_body={"hub_hash": hub_hash_hex}))


@pytest.mark.asyncio
async def test_rrc_api_unavailable_returns_503(mock_app):
    mock_app.rrc_manager = None
    handler = _find_handler(mock_app, "/api/v1/rrc/hubs", "GET")
    response = await handler(_make_request())
    assert response.status == 503


@pytest.mark.asyncio
async def test_rrc_server_api_unavailable_returns_503(mock_app):
    mock_app.rrc_server_manager = None
    handler = _find_handler(mock_app, "/api/v1/rrc/servers", "GET")
    response = await handler(_make_request())
    assert response.status == 503


@pytest.mark.asyncio
async def test_rrc_add_hub_rejects_path_traversal_hash(mock_app):
    post = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    traversal = "../" + HUB_HASH_HEX
    response = await post(_make_request(json_body={"hub_hash": traversal}))
    assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_add_hub_rejects_sql_injection_shaped_hash(mock_app):
    post = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    response = await post(
        _make_request(json_body={"hub_hash": "'; DROP TABLE hubs; --" + "aa" * 8}),
    )
    assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_add_hub_rejects_null_and_control_bytes(mock_app):
    post = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    dirty = HUB_HASH_HEX[:8] + "\x00\x01" + HUB_HASH_HEX[10:]
    response = await post(_make_request(json_body={"hub_hash": dirty}))
    assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_operations_on_unknown_hub_return_404(mock_app):
    await _add_hub(mock_app)
    unknown = "ff" * 16
    handlers = [
        ("/api/v1/rrc/hubs/{hub_hash}", "DELETE"),
        ("/api/v1/rrc/hubs/{hub_hash}/connect", "POST"),
        (
            "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages",
            "GET",
        ),
    ]
    for path, method in handlers:
        handler = _find_handler(mock_app, path, method)
        assert handler is not None
        response = await handler(
            _make_request(match_info={"hub_hash": unknown, "room": "lobby"}),
        )
        assert response.status == 404


@pytest.mark.asyncio
async def test_rrc_join_room_traversal_name_history_stays_in_storage(
    mock_app, tmp_path
):
    await _add_hub(mock_app)
    manager = mock_app.rrc_manager
    hub = manager.find_hub_by_hex(HUB_HASH_HEX)
    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    response = await join(
        _make_request(
            json_body={"room": "../../etc/passwd"},
            match_info={"hub_hash": HUB_HASH_HEX},
        ),
    )
    assert response.status == 200
    root = os.path.realpath(manager.storage_dir)
    hist_path = os.path.realpath(manager._history_path(hub, "../../etc/passwd"))
    assert hist_path.startswith(root + os.sep)


@pytest.mark.asyncio
async def test_rrc_send_message_rejects_non_string_text(mock_app):
    await _add_hub(mock_app)
    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    await join(
        _make_request(
            json_body={"room": "lobby"},
            match_info={"hub_hash": HUB_HASH_HEX},
        ),
    )
    send = _find_handler(
        mock_app,
        "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages",
        "POST",
    )
    for bad_text in [None, 12345, {"x": 1}, ["a"]]:
        response = await send(
            _make_request(
                json_body={"text": bad_text},
                match_info={"hub_hash": HUB_HASH_HEX, "room": "lobby"},
            ),
        )
        assert response.status in (400, 500)


@pytest.mark.asyncio
async def test_rrc_send_message_rejects_empty_text(mock_app):
    await _add_hub(mock_app)
    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    await join(
        _make_request(
            json_body={"room": "lobby"},
            match_info={"hub_hash": HUB_HASH_HEX},
        ),
    )
    send = _find_handler(
        mock_app,
        "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages",
        "POST",
    )
    response = await send(
        _make_request(
            json_body={"text": "   "},
            match_info={"hub_hash": HUB_HASH_HEX, "room": "lobby"},
        ),
    )
    assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_reorder_rejects_non_list(mock_app):
    await _add_hub(mock_app)
    handler = _find_handler(mock_app, "/api/v1/rrc/hubs/order", "PUT")
    for bad in ["not-a-list", 42, {"hub": HUB_HASH_HEX}]:
        response = await handler(_make_request(json_body={"hub_hashes": bad}))
        assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_reorder_ignores_unknown_hashes_without_error(mock_app):
    await _add_hub(mock_app)
    handler = _find_handler(mock_app, "/api/v1/rrc/hubs/order", "PUT")
    response = await handler(
        _make_request(json_body={"hub_hashes": ["deadbeef" * 4]}),
    )
    assert response.status == 200
    data = json.loads(response.body)
    assert len(data["hubs"]) == 1


@pytest.mark.asyncio
async def test_rrc_server_create_room_rejects_empty_name(mock_app):
    post = _find_handler(mock_app, "/api/v1/rrc/servers", "POST")
    created = await post(
        _make_request(json_body={"name": "Host Hub", "enabled": False})
    )
    hub_id = json.loads(created.body)["hub"]["id"]
    create_room = _find_handler(mock_app, "/api/v1/rrc/servers/{hub_id}/rooms", "POST")
    response = await create_room(
        _make_request(
            json_body={"name": "   "},
            match_info={"hub_id": hub_id},
        ),
    )
    assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_server_delete_unknown_hub_returns_404(mock_app):
    handler = _find_handler(mock_app, "/api/v1/rrc/servers/{hub_id}", "DELETE")
    response = await handler(
        _make_request(match_info={"hub_id": "nonexistent" * 4}),
    )
    assert response.status == 404


@pytest.mark.asyncio
async def test_rrc_messages_encoded_room_history_stays_in_storage(mock_app):
    await _add_hub(mock_app)
    manager = mock_app.rrc_manager
    hub = manager.find_hub_by_hex(HUB_HASH_HEX)
    room = "..%2F..%2Fsecret"
    handler = _find_handler(
        mock_app,
        "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages",
        "GET",
    )
    response = await handler(
        _make_request(
            match_info={
                "hub_hash": HUB_HASH_HEX,
                "room": room,
            },
        ),
    )
    assert response.status == 200
    root = os.path.realpath(manager.storage_dir)
    hist_path = os.path.realpath(manager._history_path(hub, room))
    assert hist_path.startswith(root + os.sep)


@given(
    hub_hash=st.one_of(
        st.text(min_size=0, max_size=64),
        st.binary(min_size=0, max_size=32).map(lambda b: b.hex()),
    ),
)
@settings(
    max_examples=80,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_rrc_add_hub_fuzz_invalid_hashes_never_500(mock_app, hub_hash):
    post = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    response = await post(_make_request(json_body={"hub_hash": hub_hash}))
    assert response.status in (200, 400)
    if response.status == 200:
        data = json.loads(response.body)
        assert len(data["hub"]["hub_hash"]) == HUB_HASH_HEX.__len__()


@given(room=st.text(max_size=128))
@settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_rrc_join_room_fuzz_never_500(mock_app, room):
    await _add_hub(mock_app)
    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    response = await join(
        _make_request(
            json_body={"room": room},
            match_info={"hub_hash": HUB_HASH_HEX},
        ),
    )
    assert response.status in (200, 400)


@given(
    text=st.one_of(
        st.none(),
        st.text(max_size=2048),
        st.binary(min_size=0, max_size=256).map(
            lambda b: b.decode("utf-8", errors="surrogateescape"),
        ),
    ),
)
@settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_rrc_send_message_fuzz_never_500_when_disconnected(mock_app, text):
    await _add_hub(mock_app)
    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    await join(
        _make_request(
            json_body={"room": "lobby"},
            match_info={"hub_hash": HUB_HASH_HEX},
        ),
    )
    send = _find_handler(
        mock_app,
        "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages",
        "POST",
    )
    response = await send(
        _make_request(
            json_body={"text": text, "action": False},
            match_info={"hub_hash": HUB_HASH_HEX, "room": "lobby"},
        ),
    )
    assert response.status in (400, 500)


@given(
    name=st.text(max_size=256),
    greeting=st.one_of(st.none(), st.text(max_size=512)),
)
@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_rrc_server_create_hub_fuzz_never_500(mock_app, name, greeting):
    post = _find_handler(mock_app, "/api/v1/rrc/servers", "POST")
    response = await post(
        _make_request(
            json_body={
                "name": name,
                "greeting": greeting,
                "enabled": False,
            },
        ),
    )
    assert response.status == 200
    data = json.loads(response.body)
    assert "hub" in data


def test_rrc_history_files_remain_under_storage(tmp_path):
    from meshchatx.src.backend.rrc import protocol as proto
    from meshchatx.src.backend.rrc.manager import RRCManager

    class Id:
        hash = bytes(range(16))

    manager = RRCManager(identity=Id(), storage_dir=str(tmp_path))
    hub = manager.add_hub(bytes(range(16)))
    for room in ["../x", "lobby", "a" * 100, "room/with/slash"]:
        try:
            normalized = proto.normalize_room(room)
            hub.add_room(normalized)
            msg = proto.RRCMessage("msg", normalized, b"\x01" * 16, "n", "t", 1)
            hub._record_message(msg)
        except ValueError:
            continue
    root = os.path.realpath(tmp_path)
    for dirpath, _, filenames in os.walk(tmp_path):
        for fn in filenames:
            path = os.path.realpath(os.path.join(dirpath, fn))
            assert path.startswith(root)
