# SPDX-License-Identifier: 0BSD

"""HTTP oracles for per-bot LXMF config routes."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.bot_handler import BotHandler
from meshchatx.src.backend.http.routes.bots import register_bots_routes


@pytest.fixture
def bot_http_client(tmp_path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    handler = BotHandler(str(identity_dir))
    storage = os.path.join(handler.bots_dir, "bot1")
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [
        {
            "id": "bot1",
            "template_id": "echo",
            "name": "Oracle Bot",
            "storage_dir": storage,
            "enabled": False,
        },
    ]
    handler._save_state()

    mesh_app = MagicMock()
    mesh_app.bot_handler = handler
    mesh_app.database = None

    routes = web.RouteTableDef()
    register_bots_routes(routes, mesh_app)
    aio_app = web.Application()
    aio_app.add_routes(routes)
    return aio_app, handler


@pytest.mark.asyncio
async def test_lxmf_config_patch_persists(bot_http_client):
    aio_app, handler = bot_http_client
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.patch(
            "/api/v1/bots/lxmf-config",
            json={"bot_id": "bot1", "lxmf_config": {"propagation_mode": "autopeer"}},
        )
        assert response.status == 200
        body = await response.json()
        assert body["success"] is True
        assert body["lxmf_config"]["propagation_mode"] == "autopeer"

    status = handler.get_status()
    bot = next(b for b in status["bots"] if b["id"] == "bot1")
    assert bot["lxmf_config"]["propagation_mode"] == "autopeer"
    assert bot["effective_lxmf_config"]["autopeer_propagation"] is True


@pytest.mark.asyncio
async def test_lxmf_config_rejects_manual_without_hash(bot_http_client):
    aio_app, _handler = bot_http_client
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.patch(
            "/api/v1/bots/lxmf-config",
            json={
                "bot_id": "bot1",
                "lxmf_config": {
                    "propagation_mode": "manual",
                    "propagation_node": "bad",
                },
            },
        )
        assert response.status == 400
        body = await response.json()
        assert "propagation_node" in body["message"]


@pytest.mark.asyncio
async def test_start_accepts_initial_lxmf_config(bot_http_client):
    aio_app, handler = bot_http_client
    proc = MagicMock()
    proc.pid = 4242
    with patch("meshchatx.src.backend.bot_handler.subprocess.Popen", return_value=proc):
        async with TestClient(TestServer(aio_app)) as client:
            response = await client.post(
                "/api/v1/bots/start",
                json={
                    "template_id": "echo",
                    "name": "New",
                    "lxmf_config": {
                        "propagation_mode": "manual",
                        "propagation_node": "a" * 32,
                    },
                },
            )
            assert response.status == 200
            body = await response.json()
            bot_id = body["bot_id"]

    entry = next(e for e in handler.bots_state if e["id"] == bot_id)
    assert entry["lxmf_config"]["propagation_node"] == "a" * 32


@pytest.mark.asyncio
async def test_update_icon_patch_roundtrip(bot_http_client):
    aio_app, handler = bot_http_client
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.patch(
            "/api/v1/bots/update",
            json={
                "bot_id": "bot1",
                "icon": {"icon_name": "robot", "fg_color": "AABBCC"},
            },
        )
        assert response.status == 200
        body = await response.json()
        assert body["icon"]["icon_name"] == "robot"
        assert body["icon"]["fg_color"] == "#aabbcc"

        status = handler.get_status()
        bot = next(b for b in status["bots"] if b["id"] == "bot1")
        assert bot["icon"]["icon_name"] == "robot"

        response = await client.patch(
            "/api/v1/bots/update",
            json={"bot_id": "bot1", "icon": None},
        )
        assert response.status == 200
        body = await response.json()
        assert body["icon"] is None

        bot = next(b for b in handler.get_status()["bots"] if b["id"] == "bot1")
        assert bot["icon"] is None


@pytest.mark.asyncio
async def test_update_icon_rejects_invalid(bot_http_client):
    aio_app, _handler = bot_http_client
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.patch(
            "/api/v1/bots/update",
            json={"bot_id": "bot1", "icon": {"icon_name": "bad name"}},
        )
        assert response.status == 400


@pytest.mark.asyncio
async def test_custom_config_rejected_on_non_custom_bot(bot_http_client):
    aio_app, _handler = bot_http_client
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.patch(
            "/api/v1/bots/update",
            json={
                "bot_id": "bot1",
                "custom": {"commands": [{"name": "x", "response": "y"}]},
            },
        )
        assert response.status == 400


@pytest.mark.asyncio
async def test_start_custom_template_with_commands(bot_http_client):
    aio_app, handler = bot_http_client
    proc = MagicMock()
    proc.pid = 4343
    with patch("meshchatx.src.backend.bot_handler.subprocess.Popen", return_value=proc):
        async with TestClient(TestServer(aio_app)) as client:
            response = await client.post(
                "/api/v1/bots/start",
                json={
                    "template_id": "custom",
                    "name": "Custom",
                    "icon": {"icon_name": "robot"},
                    "custom": {
                        "commands": [{"name": "joke", "response": "ha"}],
                        "welcome": "hi",
                    },
                },
            )
            assert response.status == 200
            bot_id = (await response.json())["bot_id"]

    entry = next(e for e in handler.bots_state if e["id"] == bot_id)
    assert entry["custom"]["commands"][0]["name"] == "joke"
    assert entry["icon"]["icon_name"] == "robot"

    runtime = os.path.join(entry["storage_dir"], "meshchatx_bot_runtime.json")
    import json

    with open(runtime, encoding="utf-8") as handle:
        sidecar = json.load(handle)
    assert sidecar["icon"]["icon_name"] == "robot"
    assert sidecar["custom"]["welcome"] == "hi"


@pytest.mark.asyncio
async def test_start_custom_template_without_commands_rejected(bot_http_client):
    aio_app, _handler = bot_http_client
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.post(
            "/api/v1/bots/start",
            json={"template_id": "custom", "name": "NoCmds"},
        )
        assert response.status == 400
