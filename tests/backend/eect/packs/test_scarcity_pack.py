# SPDX-License-Identifier: 0BSD
"""ScarcityPack: conversation list stays slim under large payloads."""

from __future__ import annotations

import secrets
import tempfile
import time

import pytest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.message_handler import MessageHandler
from tests.backend.eect.asserts import assert_preview_capped
from tests.backend.eect.harness import eect_scenario

pytestmark = pytest.mark.eect


def _message(peer_hash, i, *, fields="{}", content="hello"):
    return {
        "hash": secrets.token_hex(16),
        "source_hash": peer_hash,
        "destination_hash": "localhashlocalhashlocalhashlo12",
        "peer_hash": peer_hash,
        "state": "delivered",
        "progress": 1.0,
        "is_incoming": 1,
        "method": "direct",
        "delivery_attempts": 1,
        "next_delivery_attempt_at": None,
        "title": f"t{i}",
        "content": content,
        "fields": fields,
        "timestamp": time.time() - i,
        "rssi": -50,
        "snr": 5.0,
        "quality": 3,
        "is_spam": 0,
        "reply_to_hash": None,
    }


@pytest.fixture
def handler_db():
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
        DatabaseProvider._instance = None
    tmp = tempfile.TemporaryDirectory()
    db = Database(f"{tmp.name}/database.db")
    db.initialize()
    handler = MessageHandler(db)
    yield handler, db
    db.close()
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
        DatabaseProvider._instance = None
    tmp.cleanup()


def test_eect_conversation_preview_capped(handler_db):
    with eect_scenario("scarcity.conversation.preview_capped") as (_s, _seed, rng):
        handler, db = handler_db
        peer = secrets.token_hex(16)
        long_content = "x" * (MessageHandler._CONVERSATION_CONTENT_PREVIEW_CHARS + 500)
        # Sprinkle a few shorter messages so list still forms.
        for i in range(3):
            content = long_content if i == 0 else ("y" * (20 + rng.randint(0, 40)))
            db.messages.upsert_lxmf_message(_message(peer, i, content=content))
        rows = handler.get_conversations("local", limit=10)
        assert rows
        for row in rows:
            assert_preview_capped(
                dict(row).get("content"),
                MessageHandler._CONVERSATION_CONTENT_PREVIEW_CHARS,
            )


def test_eect_conversation_list_omits_fields(handler_db):
    with eect_scenario("scarcity.conversation.fields_slim") as (_s, _seed, _rng):
        handler, db = handler_db
        peer = secrets.token_hex(16)
        big_b64 = "C" * 90000
        db.messages.upsert_lxmf_message(
            _message(
                peer,
                0,
                fields={
                    "image": {"image_type": "png", "image_bytes": big_b64},
                },
                content="",
            ),
        )
        rows = handler.get_conversations("local", limit=10)
        assert rows
        row = dict(rows[0])
        assert "fields" not in row
        assert row.get("has_image") == 1
