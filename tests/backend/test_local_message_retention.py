# SPDX-License-Identifier: 0BSD

import time
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend import local_message_retention as lmr
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


def test_normalize_unit():
    assert lmr.normalize_unit("DAYS") == lmr.UNIT_DAYS
    assert lmr.normalize_unit("Month") == lmr.UNIT_MONTHS
    assert lmr.normalize_unit("m") == lmr.UNIT_MONTHS
    assert lmr.normalize_unit(None) == lmr.UNIT_DAYS


def test_retention_window_seconds():
    assert lmr.retention_window_seconds(1, "days") == 86400
    assert lmr.retention_window_seconds(2, "months") == 2 * 30 * 86400
    assert lmr.retention_window_seconds(20000, "days") == lmr.MAX_VALUE_DAYS * 86400
    assert (
        lmr.retention_window_seconds(200, "months") == lmr.MAX_VALUE_MONTHS * 30 * 86400
    )


def test_local_message_retention_cutoff_ts():
    now = 1_000_000.0
    c = lmr.local_message_retention_cutoff_ts(now, 1, "days")
    assert c == now - 86400.0


@pytest.fixture
def _db_path(tmp_path):
    return str(tmp_path / "t.db")


def test_apply_deletes_and_prunes(_db_path):
    provider = DatabaseProvider(_db_path)
    DatabaseSchema(provider).initialize()
    db = Database(_db_path)
    now = time.time()
    old_ts = now - 10 * 86400
    new_ts = now - 86400
    peer = "a" * 32
    base = {
        "source_hash": peer,
        "destination_hash": peer,
        "peer_hash": peer,
        "state": "delivered",
        "progress": 1.0,
        "is_incoming": 1,
        "method": "ephemeral",
        "delivery_attempts": 0,
        "next_delivery_attempt_at": None,
        "title": "t",
        "content": "c",
        "fields": None,
        "rssi": None,
        "snr": None,
        "quality": None,
        "is_spam": 0,
        "reply_to_hash": None,
        "attachments_stripped": 0,
    }
    db.messages.upsert_lxmf_message(
        {**base, "hash": "a" * 32, "timestamp": old_ts},
    )
    db.messages.upsert_lxmf_message(
        {**base, "hash": "b" * 32, "timestamp": new_ts},
    )
    db.provider.execute(
        "INSERT INTO lxmf_conversation_read_state (destination_hash) VALUES (?)",
        (peer,),
    )
    n = lmr.apply_local_message_retention(
        db.messages,
        None,
        value=2,
        unit=lmr.UNIT_DAYS,
        now=now,
    )
    assert n == 1
    assert db.messages.count_lxmf_messages() == 1
    left = db.provider.fetchone(
        "SELECT 1 AS ok FROM lxmf_messages WHERE hash = ?", ("b" * 32,)
    )
    assert left is not None
    rs = db.provider.fetchall(
        "SELECT 1 AS ok FROM lxmf_conversation_read_state WHERE destination_hash = ?",
        (peer,),
    )
    assert len(rs) == 1
    db.close_all()
    provider.close_all()


def test_prune_clears_read_state_when_conversation_empty(_db_path):
    provider = DatabaseProvider(_db_path)
    DatabaseSchema(provider).initialize()
    db = Database(_db_path)
    now = time.time()
    peer = "c" * 32
    h = "d" * 32
    old_ts = now - 3 * 86400
    db.messages.upsert_lxmf_message(
        {
            "hash": h,
            "source_hash": peer,
            "destination_hash": peer,
            "peer_hash": peer,
            "state": "delivered",
            "progress": 1.0,
            "is_incoming": 1,
            "method": "ephemeral",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "t",
            "content": "c",
            "fields": None,
            "timestamp": old_ts,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
        },
    )
    db.provider.execute(
        "INSERT INTO lxmf_conversation_read_state (destination_hash) VALUES (?)",
        (peer,),
    )
    lmr.apply_local_message_retention(
        db.messages,
        None,
        value=1,
        unit=lmr.UNIT_DAYS,
        now=now,
    )
    assert db.messages.count_lxmf_messages() == 0
    assert (
        len(
            db.provider.fetchall(
                "SELECT 1 AS x FROM lxmf_conversation_read_state WHERE destination_hash = ?",
                (peer,),
            )
        )
        == 0
    )
    db.close_all()
    provider.close_all()


async def test_config_patch_local_message_retention_keys(mock_app):
    await mock_app.update_config(
        {
            "local_message_auto_delete_enabled": True,
            "local_message_auto_delete_value": 3,
            "local_message_auto_delete_unit": "months",
        },
    )
    assert mock_app.config.local_message_auto_delete_enabled.get() is True
    assert mock_app.config.local_message_auto_delete_value.get() == 3
    assert mock_app.config.local_message_auto_delete_unit.get() == "months"
    await mock_app.update_config(
        {
            "local_message_auto_delete_value": 9999,
            "local_message_auto_delete_unit": "months",
        },
    )
    assert mock_app.config.local_message_auto_delete_value.get() == lmr.MAX_VALUE_MONTHS


def test_apply_calls_cancel_for_hex_hashes(_db_path):
    provider = DatabaseProvider(_db_path)
    DatabaseSchema(provider).initialize()
    db = Database(_db_path)
    now = time.time()
    h = "aa" * 16
    db.messages.upsert_lxmf_message(
        {
            "hash": h,
            "source_hash": h,
            "destination_hash": h,
            "peer_hash": h,
            "state": "sending",
            "progress": 0.0,
            "is_incoming": 0,
            "method": "opportunistic",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "",
            "content": "x",
            "fields": None,
            "timestamp": now - 5 * 86400,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
        },
    )
    cancel = MagicMock()
    lmr.apply_local_message_retention(
        db.messages,
        cancel,
        value=1,
        unit="days",
        now=now,
    )
    cancel.assert_called()
    assert db.messages.count_lxmf_messages() == 0
    db.close_all()
    provider.close_all()
