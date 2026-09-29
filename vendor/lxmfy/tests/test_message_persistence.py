"""Tests for LXMF outgoing queue crash recovery."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from lxmfy import BotConfig, LXMFBot


def _bot(tmp_path, name: str) -> LXMFBot:
    config = BotConfig(
        test_mode=True,
        config_path=str(tmp_path / f"cfg_{name}"),
        storage_path=str(tmp_path / f"data_{name}"),
        announce_enabled=False,
        cogs_enabled=False,
        landlock_enabled=False,
        message_persistence_enabled=True,
    )
    return LXMFBot(**config.__dict__)


def test_persisted_queue_survives_and_restores(tmp_path):
    bot = _bot(tmp_path, "survive")
    assert bot.send("aabbccddeeff00112233445566778899", "hello crash", title="t")
    assert bot.storage.get("persisted_queue")
    assert len(bot.storage.get("persisted_queue")) == 1
    assert bot.storage.get("persisted_queue")[0]["content"] == "hello crash"

    bot.queue.get(block=False)
    bot._persist_queue()
    assert bot.storage.get("persisted_queue") == []


def test_persisted_queue_restore_keeps_success_and_failures(tmp_path):
    bot = _bot(tmp_path, "restore")
    good = "aabbccddeeff00112233445566778899"
    fail = "11223344556677889900aabbccddeeff"
    bot.storage.set(
        "persisted_queue",
        [
            {
                "destination": good,
                "content": "one",
                "title": "t",
                "fields": None,
                "method": None,
            },
            {
                "destination": fail,
                "content": "two",
                "title": "t",
                "fields": None,
                "method": None,
            },
        ],
    )

    original_send = bot.send

    def flaky_send(destination, message, **kwargs):
        if destination == fail:
            raise ValueError("boom")
        return original_send(destination, message, **kwargs)

    bot.send = flaky_send  # type: ignore[method-assign]
    bot._load_persisted_queue()
    remaining = bot.storage.get("persisted_queue")
    contents = [item["content"] for item in remaining]
    assert "one" in contents
    assert "two" in contents
    assert not bot.queue.empty()


def test_persisted_queue_restore_keeps_unqueued(tmp_path):
    bot = _bot(tmp_path, "unqueued")
    bot.storage.set(
        "persisted_queue",
        [
            {
                "destination": "aabbccddeeff00112233445566778899",
                "content": "pending",
                "title": "t",
                "fields": None,
                "method": None,
            },
        ],
    )

    bot.send = MagicMock(return_value=False)  # type: ignore[method-assign]
    bot._load_persisted_queue()
    remaining = bot.storage.get("persisted_queue")
    assert remaining == [
        {
            "destination": "aabbccddeeff00112233445566778899",
            "content": "pending",
            "title": "t",
            "fields": None,
            "method": None,
        },
    ]


def test_cleanup_persists_remaining_queue(tmp_path):
    bot = _bot(tmp_path, "cleanup")
    bot.send("aabbccddeeff00112233445566778899", "still queued")
    bot.cleanup()
    assert bot.storage.get("persisted_queue")
    assert bot.storage.get("persisted_queue")[0]["content"] == "still queued"


def test_persist_serializes_queue_items(tmp_path):
    bot = _bot(tmp_path, "serialize")
    msg = SimpleNamespace(
        destination_hash=bytes.fromhex("aabbccddeeff00112233445566778899"),
        content=b"bytes content",
        title=b"title",
        fields={"a": 1},
        desired_method="direct",
    )
    bot.queue.put(msg)
    bot._persist_queue()
    persisted = bot.storage.get("persisted_queue")
    assert persisted[0]["content"] == "bytes content"
    assert persisted[0]["title"] == "title"
    assert persisted[0]["fields"] == {"a": 1}


def test_run_requeues_on_outbound_failure(tmp_path):
    bot = _bot(tmp_path, "requeue")
    bot.send("aabbccddeeff00112233445566778899", "retry me")
    bot.router = MagicMock()
    bot.router.handle_outbound.side_effect = RuntimeError("link down")

    with (
        patch.object(bot.scheduler, "start"),
        patch("lxmfy.core.time.sleep", side_effect=KeyboardInterrupt),
    ):
        bot.run(delay=0)

    assert not bot.queue.empty()
    assert bot.storage.get("persisted_queue")[0]["content"] == "retry me"
