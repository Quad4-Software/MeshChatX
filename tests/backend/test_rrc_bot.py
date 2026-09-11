# SPDX-License-Identifier: 0BSD

"""Tests for the RRC bot template and its handler/CLI plumbing."""

import os
from unittest.mock import MagicMock, patch

import pytest
from lxmfy.rrc import RRCMessage

from meshchatx.src.backend.bot_handler import (
    BotHandler,
    normalize_rrc_bot_config,
)
from meshchatx.src.backend.bot_process import TEMPLATE_MAP
from meshchatx.src.backend.bot_templates import RRCBotTemplate

HUB = "ab" * 16


@pytest.fixture
def temp_identity_dir(tmp_path):
    dir_path = tmp_path / "identity"
    dir_path.mkdir()
    return str(dir_path)


def test_normalize_rrc_config_requires_32hex_hub():
    with pytest.raises(ValueError, match="32-char hex"):
        normalize_rrc_bot_config({})
    with pytest.raises(ValueError, match="32-char hex"):
        normalize_rrc_bot_config({"hub": "nothex"})
    with pytest.raises(ValueError, match="32-char hex"):
        normalize_rrc_bot_config({"hub": "ab" * 15})
    with pytest.raises(ValueError, match="object"):
        normalize_rrc_bot_config("lobby")

    cfg = normalize_rrc_bot_config({"hub": HUB.upper()})
    assert cfg["hub"] == HUB
    assert cfg["rooms"] == []
    assert cfg["nick"] is None
    assert cfg["mention_only"] is True
    assert cfg["prefix"] == "!"
    assert cfg["rate_seconds"] == 8


def test_normalize_rrc_config_sanitizes_rooms():
    cfg = normalize_rrc_bot_config(
        {"hub": HUB, "rooms": ["#Lobby", "  general ", "#lobby", "Ops"]},
    )
    assert cfg["rooms"] == ["lobby", "general", "ops"]

    with pytest.raises(ValueError, match="list"):
        normalize_rrc_bot_config({"hub": HUB, "rooms": "lobby"})
    with pytest.raises(ValueError, match="strings"):
        normalize_rrc_bot_config({"hub": HUB, "rooms": [42]})
    with pytest.raises(ValueError, match="1 to 64"):
        normalize_rrc_bot_config({"hub": HUB, "rooms": ["###"]})
    with pytest.raises(ValueError, match="1 to 64"):
        normalize_rrc_bot_config({"hub": HUB, "rooms": ["x" * 65]})


def test_normalize_rrc_config_nick_prefix_rate():
    cfg = normalize_rrc_bot_config(
        {
            "hub": HUB,
            "nick": "  Relay  Bot ",
            "prefix": "?",
            "rate_seconds": 99999,
            "mention_only": False,
        },
    )
    assert cfg["nick"] == "Relay Bot"
    assert cfg["prefix"] == "?"
    assert cfg["rate_seconds"] == 3600
    assert cfg["mention_only"] is False

    with pytest.raises(ValueError, match="nick"):
        normalize_rrc_bot_config({"hub": HUB, "nick": "x" * 33})
    with pytest.raises(ValueError, match="nick"):
        normalize_rrc_bot_config({"hub": HUB, "nick": "   "})
    with pytest.raises(ValueError, match="prefix"):
        normalize_rrc_bot_config({"hub": HUB, "prefix": "!!!!!"})
    with pytest.raises(ValueError, match="prefix"):
        normalize_rrc_bot_config({"hub": HUB, "prefix": "  "})

    cfg = normalize_rrc_bot_config({"hub": HUB, "rate_seconds": -5})
    assert cfg["rate_seconds"] == 0
    cfg = normalize_rrc_bot_config({"hub": HUB, "rate_seconds": "abc"})
    assert cfg["rate_seconds"] == 8


def test_start_bot_rejects_rrc_config_on_other_templates(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    with pytest.raises(ValueError, match="only valid for the rrc template"):
        handler.start_bot("echo", "Echo", rrc_config={"hub": HUB})
    assert handler.bots_state == []


def test_start_bot_rrc_requires_hub(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    with pytest.raises(ValueError, match="requires rrc config"):
        handler.start_bot("rrc", "Relay")
    with pytest.raises(ValueError, match="32-char hex"):
        handler.start_bot("rrc", "Relay", rrc_config={"rooms": ["lobby"]})
    assert handler.bots_state == []


@patch("subprocess.Popen")
def test_start_bot_rrc_assembles_cli_args(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 4321
    mock_popen.return_value = mock_process

    handler = BotHandler(temp_identity_dir)
    bot_id = handler.start_bot(
        "rrc",
        "Relay Bot",
        rrc_config={
            "hub": HUB,
            "rooms": ["#Lobby", "ops"],
            "nick": "RelayNick",
            "mention_only": False,
            "prefix": "?",
            "rate_seconds": 30,
        },
    )

    entry = next(e for e in handler.bots_state if e["id"] == bot_id)
    assert entry["rrc"] == {
        "hub": HUB,
        "rooms": ["lobby", "ops"],
        "nick": "RelayNick",
        "mention_only": False,
        "prefix": "?",
        "rate_seconds": 30,
    }

    cmd = mock_popen.call_args.args[0]
    assert cmd[cmd.index("--template") + 1] == "rrc"
    assert cmd[cmd.index("--rrc-hub") + 1] == HUB
    assert cmd[cmd.index("--rrc-rooms") + 1] == "lobby,ops"
    assert cmd[cmd.index("--rrc-nick") + 1] == "RelayNick"
    assert cmd[cmd.index("--rrc-mention-only") + 1] == "0"
    assert cmd[cmd.index("--rrc-prefix") + 1] == "?"
    assert cmd[cmd.index("--rrc-rate") + 1] == "30"

    status = handler.get_status()
    bot = next(b for b in status["bots"] if b["id"] == bot_id)
    assert bot["rrc"]["hub"] == HUB
    assert bot["rrc"]["rooms"] == ["lobby", "ops"]

    templates = handler.get_available_templates()
    assert any(t["id"] == "rrc" for t in templates)


@patch("subprocess.Popen")
def test_start_bot_rrc_restart_reuses_stored_config(mock_popen, temp_identity_dir):
    mock_process = MagicMock()
    mock_process.pid = 4322
    mock_popen.return_value = mock_process

    handler = BotHandler(temp_identity_dir)
    bot_id = handler.start_bot(
        "rrc",
        "Relay Bot",
        rrc_config={"hub": HUB, "rooms": ["lobby"], "nick": "RelayNick"},
    )

    # A restart without rrc_config reuses the stored block.
    handler.start_bot("rrc", "Relay Bot", bot_id=bot_id)
    cmd = mock_popen.call_args.args[0]
    assert cmd[cmd.index("--rrc-hub") + 1] == HUB
    assert cmd[cmd.index("--rrc-nick") + 1] == "RelayNick"


def test_update_bot_rrc_config(temp_identity_dir):
    handler = BotHandler(temp_identity_dir)
    storage = os.path.join(handler.bots_dir, "b1")
    os.makedirs(storage, exist_ok=True)
    handler.bots_state = [
        {
            "id": "b1",
            "template_id": "rrc",
            "name": "Relay",
            "storage_dir": storage,
            "rrc": {"hub": HUB, "rooms": ["lobby"], "nick": None},
        },
        {
            "id": "b2",
            "template_id": "echo",
            "name": "Echo",
            "storage_dir": storage,
        },
    ]

    saved = handler.update_bot_rrc_config(
        "b1",
        {"hub": "cd" * 16, "rooms": ["#new"], "mention_only": False},
    )
    assert saved["hub"] == "cd" * 16
    assert saved["rooms"] == ["new"]
    assert handler.bots_state[0]["rrc"]["mention_only"] is False

    with pytest.raises(ValueError, match="only applies to rrc bots"):
        handler.update_bot_rrc_config("b2", {"hub": HUB})
    with pytest.raises(ValueError, match="Unknown bot"):
        handler.update_bot_rrc_config("nope", {"hub": HUB})


def test_rrc_template_in_map():
    assert TEMPLATE_MAP["rrc"] is RRCBotTemplate


def _payload(text, src=b"\x01" * 16, nick="alice", room="lobby", mention=False):
    return RRCMessage(
        kind="msg",
        room=room,
        src=src,
        nick=nick,
        text=text,
        ts=0,
        mention=mention,
    )


class FakeRRCClient:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send_message(self, room, text):
        if self.fail:
            raise RuntimeError("link down")
        self.sent.append((room, text))
        return b"\x01" * 8


@pytest.fixture
def rrc_bot(tmp_path):
    bots = []

    def factory(**overrides):
        kwargs = {
            "name": "RelayBot",
            "storage_path": str(tmp_path / "storage"),
            "test_mode": True,
            "config_path": str(tmp_path / "config"),
            "reticulum_config_dir": str(tmp_path / "rns"),
            "rrc_hub": HUB,
            "rrc_rooms": ["lobby", "ops"],
            "rrc_nick": "RelayBot",
            "rrc_mention_only": False,
            "rrc_rate_seconds": 0,
        }
        kwargs.update(overrides)
        bot = RRCBotTemplate(**kwargs)
        bots.append(bot)
        return bot

    yield factory
    for bot in bots:
        try:
            bot.bot.cleanup()
        except Exception:
            pass


def test_rrc_template_requires_hub(tmp_path):
    with pytest.raises(ValueError, match="rrc_hub"):
        RRCBotTemplate(
            name="x",
            storage_path=str(tmp_path / "s"),
            test_mode=True,
            config_path=str(tmp_path / "c"),
            reticulum_config_dir=str(tmp_path / "r"),
        )


def test_rrc_template_passes_kwargs_to_lxmfy(rrc_bot):
    bot = rrc_bot()
    assert bot.bot.config.rrc_enabled is True
    assert bot.bot.config.rrc_hubs == [HUB]
    assert bot.bot.config.rrc_rooms == ["lobby", "ops"]
    assert bot.bot.config.rrc_nick == "RelayBot"


def test_rrc_ping_and_uptime_replies(rrc_bot):
    bot = rrc_bot()
    client = FakeRRCClient()

    bot._handle_rrc_event("msg", client, _payload("!ping"))
    assert client.sent == [("lobby", "@alice pong")]

    bot._handle_rrc_event("msg", client, _payload("!uptime"))
    room, text = client.sent[-1]
    assert room == "lobby"
    assert text.startswith("@alice up ")

    bot._handle_rrc_event("msg", client, _payload("!help"))
    assert "commands: !uptime" in client.sent[-1][1]

    bot._handle_rrc_event("msg", client, _payload("!status"))
    status = client.sent[-1][1]
    assert "RelayBot" in status
    assert HUB in status
    assert "lobby" in status


def test_rrc_unknown_command_sends_hint(rrc_bot):
    bot = rrc_bot()
    client = FakeRRCClient()
    bot._handle_rrc_event("msg", client, _payload("!bogus"))
    assert client.sent[-1][1] == "@alice unknown command 'bogus' - try !help"


def test_rrc_mention_only_gating(rrc_bot):
    bot = rrc_bot(rrc_mention_only=True)
    client = FakeRRCClient()

    # Plain chatter and bare commands without a mention are ignored.
    bot._handle_rrc_event("msg", client, _payload("!ping"))
    bot._handle_rrc_event("msg", client, _payload("hello there"))
    assert client.sent == []

    # Mention flag set by the client, or a literal @nick in text, both count.
    bot._handle_rrc_event("msg", client, _payload("!ping", mention=True))
    bot._handle_rrc_event("msg", client, _payload("hey @relaybot !ping"))
    assert len(client.sent) == 2
    assert all(text == "@alice pong" for _, text in client.sent)


def test_rrc_ignores_own_messages_and_non_msg_events(rrc_bot):
    bot = rrc_bot()
    client = FakeRRCClient()
    own = bot.bot.identity.hash

    bot._handle_rrc_event("msg", client, _payload("!ping", src=own))
    bot._handle_rrc_event("notice", client, _payload("!ping"))
    bot._handle_rrc_event("msg", client, None)
    assert client.sent == []


def test_rrc_per_requester_cooldown(rrc_bot):
    bot = rrc_bot(rrc_rate_seconds=8)
    client = FakeRRCClient()
    alice = b"\x01" * 16
    bob = b"\x02" * 16

    bot._handle_rrc_event("msg", client, _payload("!ping", src=alice))
    bot._handle_rrc_event("msg", client, _payload("!ping", src=alice))
    assert len(client.sent) == 1

    # A different requester is not throttled by alice's cooldown.
    bot._handle_rrc_event("msg", client, _payload("!ping", src=bob, nick="bob"))
    assert len(client.sent) == 2
    assert client.sent[-1] == ("lobby", "@bob pong")


def test_rrc_reply_failure_is_logged_not_raised(rrc_bot):
    bot = rrc_bot()
    client = FakeRRCClient(fail=True)
    bot._handle_rrc_event("msg", client, _payload("!ping"))
    assert client.sent == []
