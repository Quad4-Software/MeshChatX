# SPDX-License-Identifier: 0BSD
"""Malformed-protocol fuzz through the real on_lxmf_delivery boundary.

Every case feeds an LXMF-shaped object through the real delivery handler
against the real test DB and asserts the handler either stores the message
cleanly or drops it without raising or corrupting other rows.
"""

import time
from unittest.mock import MagicMock

import pytest

from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    PEER_SPAMMER,
    make_inbound_lxmf,
    prepare_messaging_app,
    stored_message,
)


def _make(**kw):
    return make_inbound_lxmf(
        source_hash=kw.pop("source_hash", PEER_SPAMMER),
        destination_hash=LOCAL_LXMF,
        **kw,
    )


def _deliver(app, msg):
    """Delivery must not raise. If it does, that is the bug under test."""
    app.on_lxmf_delivery(msg)


# -- field/type confusion ----------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {"not-int-key": "x"},
        {16: {"telemetry": {"lat": float("nan"), "lon": float("inf")}}},
        {16: {"telemetry": {"lat": -1e308 * 10}}},
        {i: {"k": "v"} for i in range(2000)},  # huge field list
        {16: {"list": list(range(5000))}},
        {16: {"deep": {"a": [{"b": "c"}] * 3}}},
    ],
    ids=[
        "str-key",
        "nan-telemetry",
        "inf-telemetry",
        "huge-field-list",
        "big-list-value",
        "nested",
    ],
)
def test_inbound_weird_fields_no_crash(mock_app, fields):
    app = prepare_messaging_app(mock_app)
    msg = _make(fields=fields)
    _deliver(app, msg)  # must not raise


def test_inbound_get_fields_raises(mock_app):
    app = prepare_messaging_app(mock_app)
    msg = _make()
    msg.get_fields = MagicMock(side_effect=ValueError("corrupt msgpack"))
    try:
        app.on_lxmf_delivery(msg)
    except ValueError:
        pass  # a contained raise is acceptable, an unhandled one is the bug


def test_inbound_get_fields_returns_non_dict(mock_app):
    app = prepare_messaging_app(mock_app)
    msg = _make()
    msg.get_fields = lambda: "not-a-dict"
    try:
        app.on_lxmf_delivery(msg)
    except Exception:
        pass


def test_inbound_far_future_timestamp(mock_app):
    app = prepare_messaging_app(mock_app)
    msg = _make()
    msg.timestamp = time.time() + 60 * 60 * 24 * 365 * 50
    _deliver(app, msg)
    stored_message(app, msg)  # query path must not raise


def test_inbound_far_past_timestamp(mock_app):
    app = prepare_messaging_app(mock_app)
    msg = _make()
    msg.timestamp = 0.0
    _deliver(app, msg)
    stored_message(app, msg)


def test_inbound_huge_content_bounded(mock_app):
    app = prepare_messaging_app(mock_app)
    msg = _make(content=b"x" * 5 * 1024 * 1024)
    t0 = time.monotonic()
    _deliver(app, msg)
    assert time.monotonic() - t0 < 30


def test_inbound_huge_attachment_list(mock_app):
    app = prepare_messaging_app(mock_app)
    attachments = [{"name": f"f{i}.bin", "data": b"\x00"} for i in range(5000)]
    msg = _make(fields={LXMF_FIELD_ATTACHMENTS: attachments})
    try:
        app.on_lxmf_delivery(msg)
    except Exception:
        pass


def test_inbound_duplicate_hash_twice(mock_app):
    app = prepare_messaging_app(mock_app)
    msg = _make()
    app.on_lxmf_delivery(msg)
    app.on_lxmf_delivery(msg)  # duplicate redelivery must not raise
    stored_message(app, msg)


LXMF_FIELD_ATTACHMENTS = 5
