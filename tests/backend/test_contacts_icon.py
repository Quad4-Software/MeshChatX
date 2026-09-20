# SPDX-License-Identifier: 0BSD

"""Tests for lxmf_user_icon persistence through the contacts POST route."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.http.routes.contacts import register_contacts_routes
from tests.backend.http_request_stubs import json_request


def _capture_handlers(app):
    routes = MagicMock()
    captured = {}

    def _make(method):
        def registrar(path):
            def decorator(fn):
                captured[(method, path)] = fn
                return fn

            return decorator

        return registrar

    routes.get = _make("GET")
    routes.post = _make("POST")
    routes.patch = _make("PATCH")
    routes.delete = _make("DELETE")
    register_contacts_routes(routes, app)
    return captured


def _make_app():
    return SimpleNamespace(
        database=SimpleNamespace(
            announces=SimpleNamespace(
                get_announce_by_hash=MagicMock(return_value=None),
            ),
            contacts=SimpleNamespace(add_contact=MagicMock()),
            misc=SimpleNamespace(update_lxmf_user_icon=MagicMock()),
        ),
        recall_identity=MagicMock(return_value=None),
        get_lxmf_destination_hash_for_identity_hash=MagicMock(
            side_effect=RuntimeError("no rns"),
        ),
        get_lxst_telephony_hash_for_identity_hash=MagicMock(return_value=None),
        sync_telephone_call_policy=MagicMock(),
    )


LXMF_ADDR = "ab" * 16
ICON = {
    "icon_name": "robot",
    "foreground_colour": "#112233",
    "background_colour": "#aabbcc",
}


def _post(app, payload):
    handler = _capture_handlers(app)[("POST", "/api/v1/telephone/contacts")]
    return handler(json_request(payload))


@pytest.mark.asyncio
async def test_post_contact_persists_icon_metadata():
    app = _make_app()
    response = await _post(
        app,
        {"name": "Bot", "lxmf_address": LXMF_ADDR, "icon": ICON},
    )
    assert response.status == 200
    app.database.misc.update_lxmf_user_icon.assert_called_once_with(
        LXMF_ADDR,
        icon_name="robot",
        foreground_colour="#112233",
        background_colour="#aabbcc",
    )


@pytest.mark.asyncio
async def test_post_contact_rejects_bad_icon_fields_silently():
    app = _make_app()
    bad_icons = [
        {"icon_name": "bad name!", "foreground_colour": "#112233"},
        {"icon_name": "ok", "foreground_colour": "notacolour"},
        {"icon_name": "ok", "background_colour": "#12345"},
        {"icon_name": "ok", "foreground_colour": "#123456789"},
        {"icon_name": "x" * 65},
    ]
    for icon in bad_icons:
        app.database.misc.update_lxmf_user_icon.reset_mock()
        response = await _post(
            app,
            {"name": "Bot", "lxmf_address": LXMF_ADDR, "icon": icon},
        )
        assert response.status == 200
        app.database.misc.update_lxmf_user_icon.assert_not_called()


@pytest.mark.asyncio
async def test_post_contact_without_icon_or_address_skips_write():
    app = _make_app()
    response = await _post(
        app,
        {"name": "NoAddr", "remote_identity_hash": "cd" * 16, "icon": ICON},
    )
    assert response.status == 200
    app.database.misc.update_lxmf_user_icon.assert_not_called()

    response = await _post(
        app,
        {"name": "NoIcon", "lxmf_address": LXMF_ADDR},
    )
    assert response.status == 200
    app.database.misc.update_lxmf_user_icon.assert_not_called()


@pytest.mark.asyncio
async def test_post_contact_icon_write_failure_does_not_fail_request():
    app = _make_app()
    app.database.misc.update_lxmf_user_icon.side_effect = RuntimeError("db boom")
    response = await _post(
        app,
        {"name": "Bot", "lxmf_address": LXMF_ADDR, "icon": ICON},
    )
    assert response.status == 200
    assert json.loads(response.body)["message"] == "Contact added"
