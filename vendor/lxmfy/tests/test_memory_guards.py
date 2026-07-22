"""Tests for outbound queue and RRC memory guards."""

from __future__ import annotations

from unittest.mock import MagicMock

from lxmfy import BotConfig, LXMFBot
from lxmfy.rrc import RRCClient
from lxmfy.rrc.constants import (
    MAX_MEMBERS_PER_ROOM,
    MAX_RESOURCE_EXPECTATIONS,
    MAX_TRACKED_NICKS,
)
from lxmfy.templates.rrc_bot import DEFAULT_RRC_HUB, DEFAULT_RRC_ROOMS, RRCBot


def _bot(tmp_path, name: str, **kwargs) -> LXMFBot:
    config = BotConfig(
        test_mode=True,
        config_path=str(tmp_path / f"cfg_{name}"),
        storage_path=str(tmp_path / f"data_{name}"),
        announce_enabled=False,
        cogs_enabled=False,
        landlock_enabled=False,
        message_persistence_enabled=True,
        **kwargs,
    )
    return LXMFBot(**config.__dict__)


def test_invalid_persisted_destination_is_dropped(tmp_path):
    bot = _bot(tmp_path, "invalid_dest")
    bot.storage.set(
        "persisted_queue",
        [
            {
                "destination": "746573745f73656e646572",
                "content": "poison",
                "title": "t",
                "fields": None,
                "method": None,
            },
        ],
    )
    bot._load_persisted_queue()
    assert bot.storage.get("persisted_queue") == []
    assert bot.queue.empty()


def test_queue_full_drops_oldest(tmp_path):
    bot = _bot(tmp_path, "full_queue", message_queue_size=2)
    assert bot.queue.maxsize == 2
    assert bot.send("aabbccddeeff00112233445566778899", "one")
    assert bot.send("aabbccddeeff00112233445566778899", "two")
    assert bot.send("aabbccddeeff00112233445566778899", "three")
    assert bot.queue.qsize() == 2
    contents = [
        item.content.decode("utf-8")
        if isinstance(item.content, bytes)
        else item.content
        for item in list(bot.queue.queue)
    ]
    assert contents == ["two", "three"]
    persisted = bot.storage.get("persisted_queue")
    assert [item["content"] for item in persisted] == ["two", "three"]


def test_persisted_queue_truncated_to_queue_size(tmp_path):
    bot = _bot(tmp_path, "truncate", message_queue_size=2)
    dest = "aabbccddeeff00112233445566778899"
    bot.storage.set(
        "persisted_queue",
        [
            {
                "destination": dest,
                "content": f"m{i}",
                "title": "t",
                "fields": None,
                "method": None,
            }
            for i in range(5)
        ],
    )
    bot._load_persisted_queue()
    assert bot.queue.qsize() <= 2
    assert len(bot.storage.get("persisted_queue")) <= 2


def test_rrc_member_and_nick_caps():
    identity = MagicMock()
    identity.hash = bytes(range(16))
    client = RRCClient(hub_hash=bytes(range(16, 32)), identity=identity)
    room = "general"
    for i in range(MAX_MEMBERS_PER_ROOM + 50):
        client._track_member(room, i.to_bytes(16, "big"))
    assert len(client.members[room]) == MAX_MEMBERS_PER_ROOM

    for i in range(MAX_TRACKED_NICKS + 50):
        client._track_nick(i.to_bytes(16, "big"), f"n{i}")
    assert len(client.nicks) == MAX_TRACKED_NICKS


def test_rrc_resource_expectation_cap():
    identity = MagicMock()
    identity.hash = bytes(range(16))
    client = RRCClient(hub_hash=bytes(range(16, 32)), identity=identity)
    for i in range(MAX_RESOURCE_EXPECTATIONS + 10):
        client._remember_resource_expectation(
            i.to_bytes(8, "big"),
            {"kind": "motd", "size": 1, "expires": 0},
        )
    assert len(client._resource_expectations) == MAX_RESOURCE_EXPECTATIONS


def test_rrc_template_defaults():
    bot = RRCBot(test_mode=True)
    assert bot.bot.config.rrc_hubs == [DEFAULT_RRC_HUB]
    assert bot.bot.config.rrc_rooms == DEFAULT_RRC_ROOMS
    assert DEFAULT_RRC_HUB == "664fc0e8d2e448658e37bb3f34e6c88f"
    assert "general" in DEFAULT_RRC_ROOMS


def test_rrc_template_uses_home_reticulum(tmp_path, monkeypatch):
    home_rns = tmp_path / "fake_home_reticulum"
    home_rns.mkdir()
    (home_rns / "config").write_text("[reticulum]\nshare_instance = Yes\n")
    monkeypatch.setenv("LXMFY_RETICULUM_CONFIG_DIR", str(home_rns))
    bot = RRCBot(test_mode=True)
    assert bot.bot.reticulum_config_dir == str(home_rns)
