# SPDX-License-Identifier: 0BSD

"""Tests for the Reticulum Relay Chat HTTP API endpoints."""

import json

import pytest


def _find_handler(app, path, method):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _make_request(json_body=None, match_info=None):
    from unittest.mock import MagicMock

    request = MagicMock()

    async def _json():
        return json_body if json_body is not None else {}

    request.json = _json
    request.match_info = match_info or {}
    request.query = {}
    return request


HUB_HASH_HEX = "00112233445566778899aabbccddeeff"


@pytest.mark.asyncio
async def test_rrc_hubs_empty(mock_app):
    handler = _find_handler(mock_app, "/api/v1/rrc/hubs", "GET")
    assert handler is not None
    response = await handler(_make_request())
    data = json.loads(response.body)
    assert data == {"hubs": []}


@pytest.mark.asyncio
async def test_rrc_add_hub_and_list(mock_app):
    post = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    response = await post(
        _make_request(json_body={"hub_hash": HUB_HASH_HEX, "name": "My Hub"}),
    )
    assert response.status == 200
    data = json.loads(response.body)
    assert data["hub"]["hub_hash"] == HUB_HASH_HEX
    assert data["hub"]["name"] == "My Hub"

    get = _find_handler(mock_app, "/api/v1/rrc/hubs", "GET")
    listing = json.loads((await get(_make_request())).body)
    assert len(listing["hubs"]) == 1


@pytest.mark.asyncio
async def test_rrc_add_hub_invalid_hash(mock_app):
    post = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    response = await post(_make_request(json_body={"hub_hash": "zzzz"}))
    assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_add_hub_wrong_length(mock_app):
    post = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    response = await post(_make_request(json_body={"hub_hash": "aabb"}))
    assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_join_room_offline_adds_room(mock_app):
    post_hub = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    await post_hub(_make_request(json_body={"hub_hash": HUB_HASH_HEX}))

    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    response = await join(
        _make_request(
            json_body={"room": "lobby"},
            match_info={"hub_hash": HUB_HASH_HEX},
        ),
    )
    assert response.status == 200
    data = json.loads(response.body)
    assert "lobby" in data["hub"]["known_rooms"]


@pytest.mark.asyncio
async def test_rrc_join_room_requires_name(mock_app):
    post_hub = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    await post_hub(_make_request(json_body={"hub_hash": HUB_HASH_HEX}))

    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    response = await join(
        _make_request(json_body={"room": ""}, match_info={"hub_hash": HUB_HASH_HEX}),
    )
    assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_messages_for_unknown_hub(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages",
        "GET",
    )
    response = await handler(
        _make_request(match_info={"hub_hash": HUB_HASH_HEX, "room": "lobby"}),
    )
    assert response.status == 404


@pytest.mark.asyncio
async def test_rrc_send_message_when_disconnected_fails(mock_app):
    post_hub = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    await post_hub(_make_request(json_body={"hub_hash": HUB_HASH_HEX}))
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
            json_body={"text": "hello"},
            match_info={"hub_hash": HUB_HASH_HEX, "room": "lobby"},
        ),
    )
    # not connected to the hub link, so sending should fail gracefully
    assert response.status == 400


@pytest.mark.asyncio
async def test_rrc_remove_hub(mock_app):
    post_hub = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    await post_hub(_make_request(json_body={"hub_hash": HUB_HASH_HEX}))

    delete = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}", "DELETE")
    response = await delete(_make_request(match_info={"hub_hash": HUB_HASH_HEX}))
    assert response.status == 200

    get = _find_handler(mock_app, "/api/v1/rrc/hubs", "GET")
    listing = json.loads((await get(_make_request())).body)
    assert listing["hubs"] == []
