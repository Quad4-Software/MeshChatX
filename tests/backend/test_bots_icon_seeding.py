# SPDX-License-Identifier: 0BSD

"""Tests for bot icon seeding in the /bots/status route."""

from __future__ import annotations

import json
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.http.routes.bots import register_bots_routes


def _capture_get(app):
    routes = MagicMock()
    captured = {}

    def _get(path):
        def decorator(fn):
            captured[path] = fn
            return fn

        return decorator

    routes.get = _get
    routes.post = MagicMock(side_effect=lambda path: lambda fn: fn)
    routes.delete = MagicMock(side_effect=lambda path: lambda fn: fn)
    register_bots_routes(routes, app)
    return captured


def _make_app(bots):
    return SimpleNamespace(
        bot_handler=SimpleNamespace(
            get_status=MagicMock(return_value={"bots": bots}),
            get_available_templates=MagicMock(return_value=[]),
        ),
        database=SimpleNamespace(
            misc=SimpleNamespace(
                update_lxmf_user_icon=MagicMock(),
                get_user_icon=MagicMock(return_value=None),
                delete_user_icon=MagicMock(),
            ),
            announces=SimpleNamespace(
                get_announce_by_hash=MagicMock(return_value=None),
            ),
        ),
    )


ADDR = "ab" * 16


@pytest.mark.asyncio
async def test_status_seeds_configured_bot_icon():
    app = _make_app(
        [
            {
                "lxmf_address": ADDR,
                "icon": {
                    "icon_name": "robot",
                    "fg_color": "#112233",
                    "bg_color": "#445566",
                },
            }
        ],
    )
    handler = _capture_get(app)["/api/v1/bots/status"]
    response = await handler(MagicMock())
    assert response.status == 200
    app.database.misc.update_lxmf_user_icon.assert_called_once_with(
        ADDR,
        icon_name="robot",
        foreground_colour="#112233",
        background_colour="#445566",
    )


@pytest.mark.asyncio
async def test_status_falls_back_to_template_default_icon(monkeypatch):
    template_cls = SimpleNamespace(
        DEFAULT_ICON={
            "icon_name": "help",
            "fg_color": "#ffffff",
            "bg_color": "#000000",
        },
    )
    fake_module = types.ModuleType("meshchatx.src.backend.bot_process")
    fake_module.TEMPLATE_MAP = {"echo": template_cls}
    monkeypatch.setitem(sys.modules, "meshchatx.src.backend.bot_process", fake_module)

    app = _make_app([{"lxmf_address": ADDR, "template_id": "echo"}])
    handler = _capture_get(app)["/api/v1/bots/status"]
    response = await handler(MagicMock())
    assert response.status == 200
    app.database.misc.update_lxmf_user_icon.assert_called_once_with(
        ADDR,
        icon_name="help",
        foreground_colour="#ffffff",
        background_colour="#000000",
    )


@pytest.mark.asyncio
async def test_status_survives_missing_template_and_lxmfy(monkeypatch):
    monkeypatch.setitem(sys.modules, "meshchatx.src.backend.bot_process", None)
    app = _make_app([{"lxmf_address": ADDR, "template_id": "ghost"}])
    handler = _capture_get(app)["/api/v1/bots/status"]
    response = await handler(MagicMock())
    assert response.status == 200
    app.database.misc.update_lxmf_user_icon.assert_not_called()


@pytest.mark.asyncio
async def test_status_survives_icon_write_failure():
    app = _make_app(
        [
            {
                "lxmf_address": ADDR,
                "icon": {"icon_name": "robot"},
            }
        ],
    )
    app.database.misc.update_lxmf_user_icon.side_effect = RuntimeError("db boom")
    handler = _capture_get(app)["/api/v1/bots/status"]
    response = await handler(MagicMock())
    assert response.status == 200
    payload = json.loads(response.body)
    assert payload["status"]["bots"][0]["lxmf_address"] == ADDR


@pytest.mark.asyncio
async def test_status_skips_icon_seed_without_address():
    app = _make_app([{"name": "noaddr"}])
    handler = _capture_get(app)["/api/v1/bots/status"]
    response = await handler(MagicMock())
    assert response.status == 200
    app.database.misc.update_lxmf_user_icon.assert_not_called()


@pytest.mark.asyncio
async def test_status_skips_rewrite_when_seeded_row_matches():
    app = _make_app(
        [
            {
                "lxmf_address": ADDR,
                "icon": {
                    "icon_name": "robot",
                    "fg_color": "#112233",
                    "bg_color": "#445566",
                },
            }
        ],
    )
    app.database.misc.get_user_icon.return_value = {
        "destination_hash": ADDR,
        "icon_name": "robot",
        "foreground_colour": "#112233",
        "background_colour": "#445566",
    }
    handler = _capture_get(app)["/api/v1/bots/status"]
    response = await handler(MagicMock())
    assert response.status == 200
    app.database.misc.update_lxmf_user_icon.assert_not_called()


@pytest.mark.asyncio
async def test_status_deletes_seeded_row_for_cleared_icon():
    app = _make_app(
        [
            {
                "lxmf_address": ADDR,
                "template_id": "echo",
                "icon": None,
                "icon_cleared": True,
            }
        ],
    )
    handler = _capture_get(app)["/api/v1/bots/status"]
    response = await handler(MagicMock())
    assert response.status == 200
    app.database.misc.delete_user_icon.assert_called_once_with(ADDR)
    app.database.misc.update_lxmf_user_icon.assert_not_called()


def test_status_marks_cleared_icon_in_payload(tmp_path):
    # entry["icon"] explicitly None means cleared. Get_status surfaces it
    from meshchatx.src.backend.bot_handler import BotHandler

    handler = BotHandler(str(tmp_path), config_manager=MagicMock())
    storage = os.path.join(handler.bots_dir, "bot1")
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [
        {
            "id": "bot1",
            "template_id": "echo",
            "name": "Bot",
            "storage_dir": storage,
            "enabled": False,
            "icon": None,
        },
    ]
    bot = handler.get_status()["bots"][0]
    assert bot["icon_cleared"] is True
    assert bot["icon"] is None
