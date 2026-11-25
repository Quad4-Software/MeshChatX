# SPDX-License-Identifier: 0BSD
"""Write-reduction guarantee for telemetry stream ingestion.

A trusted telemetry stream of N entries used to cost up to 3N autocommit
transactions (upsert + trim + tracking reset per entry). The stream loop
now runs inside one explicit transaction. These tests prove the batching
against a real SQLite database while checking every entry still lands.
"""

from __future__ import annotations

import os
import threading
import time
from unittest.mock import MagicMock

import LXMF
import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema
from meshchatx.src.backend.telemetry_utils import Telemeter


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "telemetry_stream_batch.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    database = Database(path)
    yield database
    database.close_all()
    provider.close_all()


def _build_app(db):
    app = MagicMock(spec=ReticulumMeshChat)
    app._lxmf_flood_lock = threading.RLock()
    app.database = db
    app.current_context = MagicMock()
    app.current_context.database = db
    app.current_context.running = True
    app.current_context.local_lxmf_destination = MagicMock()
    app.current_context.local_lxmf_destination.hexhash = "aa" * 16
    app.current_context.config.block_all_from_strangers.get.return_value = False
    app.current_context.config.block_attachments_from_strangers.get.return_value = False
    app.current_context.config.message_blocklist_enabled.get.return_value = False

    app.on_lxmf_delivery = ReticulumMeshChat.on_lxmf_delivery.__get__(
        app,
        ReticulumMeshChat,
    )
    app.process_incoming_telemetry = (
        ReticulumMeshChat.process_incoming_telemetry.__get__(app, ReticulumMeshChat)
    )
    app.handle_forwarding = ReticulumMeshChat.handle_forwarding.__get__(
        app,
        ReticulumMeshChat,
    )
    app.is_destination_blocked = MagicMock(return_value=False)
    app.db_upsert_lxmf_message = MagicMock()
    app.update_lxmf_user_icon = MagicMock()
    app._apply_lxmf_sieve_folder_rule = MagicMock()
    app._apply_lxmf_sieve_banish_rule = MagicMock()
    app._apply_message_blocklist_banish_rule = MagicMock()
    app._maybe_store_path_at_send_for_lxmf = MagicMock()
    app._merge_stored_path_fields_from_db = MagicMock()
    app._lxmf_sieve_suppresses_notifications = MagicMock(return_value=False)
    app.check_spam_keywords = MagicMock(return_value=False)
    app._is_contact = MagicMock(return_value=True)
    app._lxmf_incoming_timestamps = []
    app.websocket_broadcast = MagicMock()
    app.send_message = MagicMock()
    app.reticulum = MagicMock()
    app.reticulum.get_packet_rssi.return_value = None
    app.reticulum.get_packet_snr.return_value = None
    app.reticulum.get_packet_q.return_value = None
    return app


def _stream_msg(sender, entries):
    msg = MagicMock()
    msg.source_hash = sender
    msg.hash = os.urandom(32)
    msg.destination_hash = os.urandom(16)
    msg.signature_validated = True
    msg.unverified_reason = None
    msg.title = ""
    msg.content = ""
    msg.get_fields.return_value = {LXMF.FIELD_TELEMETRY_STREAM: entries}
    return msg


def test_stream_batch_uses_single_transaction(db):
    sender = os.urandom(16)
    now = int(time.time())
    entries = [
        (
            sender,
            now - 20 + i,
            Telemeter.pack(location={"latitude": float(i), "longitude": 2.0}),
        )
        for i in range(4)
    ]

    real_begin = db.provider.begin
    real_commit = db.provider.commit
    begins = []
    commits = []

    def counting_begin():
        begins.append(1)
        return real_begin()

    def counting_commit():
        commits.append(1)
        return real_commit()

    db.provider.begin = counting_begin
    db.provider.commit = counting_commit

    app = _build_app(db)
    app.on_lxmf_delivery(_stream_msg(sender, entries))

    # One explicit transaction covers the whole stream instead of one
    # autocommit transaction per insert/trim/reset statement.
    assert len(begins) == 1
    assert len(commits) == 1
    # The transaction is finished when the handler returns.
    assert not db.provider.connection.in_transaction

    rows = db.telemetry.get_telemetry_history(sender.hex(), limit=10)
    assert len(rows) == 4


def test_stream_entries_still_written_and_broadcast(db):
    sender = os.urandom(16)
    now = int(time.time())
    entries = [
        (
            sender,
            now - 5,
            Telemeter.pack(location={"latitude": 10.0, "longitude": 20.0}),
        ),
        (
            sender,
            now,
            Telemeter.pack(location={"latitude": 11.0, "longitude": 21.0}),
        ),
    ]

    app = _build_app(db)
    app.on_lxmf_delivery(_stream_msg(sender, entries))

    rows = db.telemetry.get_telemetry_history(sender.hex(), limit=10)
    assert len(rows) == 2
    timestamps = sorted(row["timestamp"] for row in rows)
    assert timestamps == [now - 5, now]
    # Per-entry websocket fanout is unchanged by the batching.
    assert app.websocket_broadcast.call_count == 2


def test_single_telemetry_field_not_batched(db):
    """The single-entry FIELD_TELEMETRY path keeps its plain autocommit write."""
    sender = os.urandom(16)
    packed = Telemeter.pack(location={"latitude": 1.0, "longitude": 2.0})

    real_begin = db.provider.begin
    begins = []

    def counting_begin():
        begins.append(1)
        return real_begin()

    db.provider.begin = counting_begin

    app = _build_app(db)
    msg = _stream_msg(sender, [])
    msg.get_fields.return_value = {LXMF.FIELD_TELEMETRY: packed}
    app.on_lxmf_delivery(msg)

    assert begins == []
    rows = db.telemetry.get_telemetry_history(sender.hex(), limit=10)
    assert len(rows) == 1
