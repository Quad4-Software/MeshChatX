"""Tests for LXMF FIELD_COMMANDS and FIELD_RESULTS support."""

from unittest.mock import Mock

import pytest

from lxmfy import BotConfig, LXMFBot
from lxmfy.lxmf_fields import (
    FIELD_COMMANDS,
    FIELD_RESULTS,
    pack_result,
    unpack_commands,
)


class TestUnpackCommands:
    """Test unpack_commands helper."""

    def test_empty_fields(self):
        assert unpack_commands(None) == []
        assert unpack_commands({}) == []

    def test_single_dict(self):
        fields = {FIELD_COMMANDS: {"command": "ping", "args": []}}
        assert unpack_commands(fields) == [{"command": "ping", "args": []}]

    def test_list_of_dicts(self):
        fields = {FIELD_COMMANDS: [{"command": "ping"}, {"command": "pong"}]}
        result = unpack_commands(fields)
        assert len(result) == 2
        assert result[0]["command"] == "ping"
        assert result[1]["command"] == "pong"

    def test_ignores_non_dict_entries(self):
        fields = {FIELD_COMMANDS: [{"command": "ping"}, "bad_entry", 123]}
        result = unpack_commands(fields)
        assert len(result) == 1

    def test_no_command_key(self):
        fields = {FIELD_COMMANDS: {"cmd": "ping", "args": []}}
        assert unpack_commands(fields) == [{"cmd": "ping", "args": []}]


class TestPackResult:
    """Test pack_result helper."""

    def test_basic_result(self):
        result = pack_result("pong")
        assert result["result"] == "pong"
        assert result["status"] == "ok"
        assert "request_id" not in result

    def test_result_with_request_id(self):
        result = pack_result("pong", request_id="abc123")
        assert result["result"] == "pong"
        assert result["request_id"] == "abc123"

    def test_error_status(self):
        result = pack_result("bad", status="error")
        assert result["status"] == "error"


class TestLXMFBotFieldCommands:
    """Test LXMFBot handling of FIELD_COMMANDS."""

    @pytest.fixture(scope="function")
    def bot(self, tmp_path):
        config = BotConfig(
            name="TestBot",
            test_mode=True,
            first_message_enabled=False,
            lxmf_commands_enabled=True,
            command_prefix="/",
        )
        bot = LXMFBot(**config.__dict__)
        bot.config_path = str(tmp_path)
        yield bot
        try:
            bot.cleanup()
        except Exception:
            pass

    def test_field_command_executes_registered_command(self, bot):
        """A message with FIELD_COMMANDS should trigger the matching command."""
        responses = []

        @bot.command(name="ping")
        def ping_cmd(ctx):
            responses.append(ctx.content)
            ctx.reply("pong")

        mock_message = Mock()
        mock_message.content = b""
        mock_message.hash = b"msg_hash_1"
        mock_message.fields = {FIELD_COMMANDS: {"command": "ping", "args": []}}

        sent = []

        def mock_send(dest, msg, title=None, **kwargs):
            sent.append((dest, msg, kwargs.get("lxmf_fields")))

        original_send = bot.send
        bot.send = mock_send

        bot._process_message(mock_message, "sender_hash")

        bot.send = original_send

        assert len(responses) == 1
        assert len(sent) == 1
        dest, msg, lxmf_fields = sent[0]
        assert msg == "pong"
        assert lxmf_fields is not None
        assert FIELD_RESULTS in lxmf_fields

    def test_field_command_with_request_id(self, bot):
        """Replies to field commands should include FIELD_RESULTS with request_id."""

        @bot.command(name="echo")
        def echo_cmd(ctx):
            ctx.reply(" ".join(ctx.args))

        mock_message = Mock()
        mock_message.content = b""
        mock_message.hash = b"msg_hash_2"
        mock_message.fields = {
            FIELD_COMMANDS: {
                "command": "echo",
                "args": ["hello", "world"],
                "request_id": "req-42",
            }
        }

        sent = []

        def mock_send(dest, msg, title=None, **kwargs):
            sent.append((dest, msg, kwargs.get("lxmf_fields")))

        original_send = bot.send
        bot.send = mock_send

        bot._process_message(mock_message, "sender_hash")

        bot.send = original_send

        assert len(sent) == 1
        _dest, msg, lxmf_fields = sent[0]
        assert msg == "hello world"
        assert FIELD_RESULTS in lxmf_fields
        assert lxmf_fields[FIELD_RESULTS]["request_id"] == "req-42"
        assert lxmf_fields[FIELD_RESULTS]["status"] == "ok"

    def test_field_command_unknown_command(self, bot):
        """Unknown field commands should get an error reply with FIELD_RESULTS."""
        mock_message = Mock()
        mock_message.content = b""
        mock_message.hash = b"msg_hash_3"
        mock_message.fields = {FIELD_COMMANDS: {"command": "nope", "args": []}}

        sent = []

        def mock_send(dest, msg, title=None, **kwargs):
            sent.append((dest, msg, kwargs.get("lxmf_fields")))

        original_send = bot.send
        bot.send = mock_send

        bot._process_message(mock_message, "sender_hash")

        bot.send = original_send

        assert len(sent) == 1
        _dest, msg, lxmf_fields = sent[0]
        assert "Unknown command" in msg
        assert FIELD_RESULTS in lxmf_fields
        assert lxmf_fields[FIELD_RESULTS]["status"] == "error"

    def test_field_command_disabled(self, bot):
        """When lxmf_commands_enabled is False, field commands should be ignored."""
        bot.config.lxmf_commands_enabled = False

        text_responses = []

        @bot.command(name="textonly")
        def text_cmd(ctx):
            text_responses.append(ctx.content)

        # Also set up a normal text message handler path
        mock_message = Mock()
        mock_message.content = b"/textonly hello"
        mock_message.hash = b"msg_hash_4"
        mock_message.fields = {FIELD_COMMANDS: {"command": "textonly", "args": []}}

        sent = []

        def mock_send(dest, msg, title=None, **kwargs):
            sent.append((dest, msg, kwargs.get("lxmf_fields")))

        original_send = bot.send
        bot.send = mock_send

        bot._process_message(mock_message, "sender_hash")

        bot.send = original_send

        # Should have processed the text command, not the field command
        assert len(text_responses) == 1
        assert text_responses[0] == "/textonly hello"

    def test_field_command_with_string_args(self, bot):
        """FIELD_COMMANDS args sent as a single string should be wrapped in a list."""

        @bot.command(name="greet")
        def greet_cmd(ctx):
            ctx.reply(f"Hi {ctx.args[0]}")

        mock_message = Mock()
        mock_message.content = b""
        mock_message.hash = b"msg_hash_5"
        mock_message.fields = {FIELD_COMMANDS: {"command": "greet", "args": "Alice"}}

        sent = []

        def mock_send(dest, msg, title=None, **kwargs):
            sent.append((dest, msg, kwargs.get("lxmf_fields")))

        original_send = bot.send
        bot.send = mock_send

        bot._process_message(mock_message, "sender_hash")

        bot.send = original_send

        assert len(sent) == 1
        _dest, msg, _fields = sent[0]
        assert msg == "Hi Alice"

    def test_msg_context_has_fields_and_request_id(self, bot):
        """The msg object passed to commands should expose fields and request_id."""
        captured = {}

        @bot.command(name="capture")
        def capture_cmd(ctx):
            captured["fields"] = ctx.fields
            captured["request_id"] = ctx.request_id
            ctx.reply("ok")

        mock_message = Mock()
        mock_message.content = b""
        mock_message.hash = b"msg_hash_6"
        mock_message.fields = {
            FIELD_COMMANDS: {
                "command": "capture",
                "args": [],
                "request_id": "req-99",
            }
        }

        original_send = bot.send
        bot.send = lambda *a, **k: None

        bot._process_message(mock_message, "sender_hash")

        bot.send = original_send

        assert captured["fields"] == mock_message.fields
        assert captured["request_id"] == "req-99"

    def test_text_command_does_not_add_field_results(self, bot):
        """Normal text commands without FIELD_COMMANDS should not inject FIELD_RESULTS."""

        @bot.command(name="plain")
        def plain_cmd(ctx):
            ctx.reply("plain reply")

        mock_message = Mock()
        mock_message.content = b"/plain"
        mock_message.hash = b"msg_hash_7"
        mock_message.fields = {}

        sent = []

        def mock_send(dest, msg, title=None, **kwargs):
            sent.append((dest, msg, kwargs.get("lxmf_fields")))

        original_send = bot.send
        bot.send = mock_send

        bot._process_message(mock_message, "sender_hash")

        bot.send = original_send

        assert len(sent) == 1
        _dest, _msg, lxmf_fields = sent[0]
        # lxmf_fields should be None because there's no request_id
        assert lxmf_fields is None
