# SPDX-License-Identifier: 0BSD
"""Oracle tests for contacts list reliability (pagination, 503, enrichment)."""

from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.http.routes.contacts import (
    CONTACTS_MAX_LIMIT,
    enrich_contact_row,
    parse_contacts_pagination,
    register_contacts_routes,
)


class _Query(dict):
    def get(self, key, default=None):
        return dict.get(self, key, default)


def _oracle_pagination(raw_limit, raw_offset, default_limit=100):
    """Independent expected (limit, offset) or None for non-integers."""
    try:
        limit = int(raw_limit if raw_limit is not None else default_limit)
        offset = int(raw_offset if raw_offset is not None else 0)
    except (TypeError, ValueError):
        return None
    if limit < 1:
        limit = 1
    elif limit > CONTACTS_MAX_LIMIT:
        limit = CONTACTS_MAX_LIMIT
    if offset < 0:
        offset = 0
    return limit, offset


@pytest.mark.parametrize(
    ("limit", "offset"),
    [
        ("100", "0"),
        ("1", "0"),
        ("9999", "0"),
        ("0", "0"),
        ("50", "-3"),
        ("abc", "0"),
        ("10", "x"),
        (None, None),
    ],
)
def test_parse_contacts_pagination_matches_oracle(limit, offset):
    query = _Query()
    if limit is not None:
        query["limit"] = limit
    if offset is not None:
        query["offset"] = offset
    expected = _oracle_pagination(limit, offset)
    assert parse_contacts_pagination(query) == expected


def test_enrich_contact_row_survives_hash_resolution_failure():
    row = {"id": 1, "name": "A", "remote_identity_hash": "aa" * 16}
    app = SimpleNamespace(
        get_lxmf_destination_hash_for_identity_hash=MagicMock(
            side_effect=RuntimeError("rns boom"),
        ),
        get_lxst_telephony_hash_for_identity_hash=MagicMock(return_value=None),
        database=SimpleNamespace(misc=SimpleNamespace(get_user_icon=MagicMock())),
    )
    out = enrich_contact_row(app, row)
    assert out["name"] == "A"
    assert out["remote_identity_hash"] == "aa" * 16
    assert "remote_destination_hash" not in out


def test_enrich_contact_row_attaches_hashes_and_icon():
    row = {"id": 2, "name": "B", "remote_identity_hash": "bb" * 16}
    icon = {"destination_hash": "cc" * 16, "emoji": "x"}
    app = SimpleNamespace(
        get_lxmf_destination_hash_for_identity_hash=MagicMock(
            return_value="cc" * 16,
        ),
        get_lxst_telephony_hash_for_identity_hash=MagicMock(
            return_value="dd" * 16,
        ),
        database=SimpleNamespace(
            misc=SimpleNamespace(get_user_icon=MagicMock(return_value=icon)),
        ),
    )
    out = enrich_contact_row(app, row)
    assert out["remote_destination_hash"] == "cc" * 16
    assert out["remote_telephony_hash"] == "dd" * 16
    assert out["remote_icon"] == icon


def _make_handler(app):
    routes = MagicMock()
    captured = {}

    def _get(path):
        def decorator(fn):
            captured[path] = fn
            return fn

        return decorator

    routes.get = _get
    routes.post = MagicMock(side_effect=lambda path: lambda fn: fn)
    routes.patch = MagicMock(side_effect=lambda path: lambda fn: fn)
    routes.delete = MagicMock(side_effect=lambda path: lambda fn: fn)
    register_contacts_routes(routes, app)
    return captured["/api/v1/telephone/contacts"]


@pytest.mark.asyncio
async def test_contacts_get_returns_503_when_database_missing():
    app = SimpleNamespace(database=None)
    handler = _make_handler(app)
    request = MagicMock()
    request.query = _Query({"limit": "10", "offset": "0"})
    response = await handler(request)
    assert response.status == 503
    body = json.loads(response.body)
    assert "unavailable" in body["error"].lower()


@pytest.mark.asyncio
async def test_contacts_get_returns_400_for_non_integer_limit():
    app = SimpleNamespace(database=MagicMock())
    handler = _make_handler(app)
    request = MagicMock()
    request.query = _Query({"limit": "nope", "offset": "0"})
    response = await handler(request)
    assert response.status == 400
    app.database.contacts.get_contacts.assert_not_called()


@pytest.mark.asyncio
async def test_contacts_get_returns_503_on_locked_database():
    contacts_dao = MagicMock()
    contacts_dao.get_contacts.side_effect = sqlite3.OperationalError(
        "database is locked",
    )
    app = SimpleNamespace(
        database=SimpleNamespace(contacts=contacts_dao),
    )
    handler = _make_handler(app)
    request = MagicMock()
    request.query = _Query({"limit": "10", "offset": "0"})
    response = await handler(request)
    assert response.status == 503


@pytest.mark.asyncio
async def test_contacts_get_keeps_rows_when_one_enrichment_fails():
    good = {"id": 1, "name": "Good", "remote_identity_hash": "11" * 16}
    bad = {"id": 2, "name": "Bad", "remote_identity_hash": "22" * 16}
    contacts_dao = MagicMock()
    contacts_dao.get_contacts.return_value = [good, bad]
    contacts_dao.get_contacts_count.return_value = 2

    def _lxmf(identity_hash):
        if identity_hash == "22" * 16:
            raise RuntimeError("derive failed")
        return "33" * 16

    app = SimpleNamespace(
        database=SimpleNamespace(
            contacts=contacts_dao,
            misc=SimpleNamespace(get_user_icon=MagicMock(return_value=None)),
        ),
        get_lxmf_destination_hash_for_identity_hash=_lxmf,
        get_lxst_telephony_hash_for_identity_hash=MagicMock(return_value=None),
    )
    handler = _make_handler(app)
    request = MagicMock()
    request.query = _Query({"limit": "10", "offset": "0"})
    response = await handler(request)
    assert response.status == 200
    data = json.loads(response.body)
    assert data["total_count"] == 2
    assert len(data["contacts"]) == 2
    assert data["contacts"][0]["remote_destination_hash"] == "33" * 16
    assert "remote_destination_hash" not in data["contacts"][1]
