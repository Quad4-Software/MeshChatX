"""Tests for LXMF reply threading fields and send/reply integration."""

from __future__ import annotations

import pytest

from lxmfy import (
    FIELD_REPLY_QUOTE,
    FIELD_REPLY_TO,
    FIELD_THREAD,
    TestBot,
    pack_reply,
    unpack_reply,
)

MSG_HASH = bytes(range(32))
MSG_HEX = MSG_HASH.hex()
THREAD_HASH = bytes(reversed(range(32)))
THREAD_HEX = THREAD_HASH.hex()


class TestPackReply:
    def test_reply_to_bytes(self):
        fields = pack_reply(MSG_HASH)
        assert fields[FIELD_REPLY_TO] == MSG_HASH
        assert fields[FIELD_THREAD] == MSG_HASH

    def test_reply_to_hex(self):
        fields = pack_reply(MSG_HEX)
        assert fields[FIELD_REPLY_TO] == MSG_HASH

    def test_explicit_thread(self):
        fields = pack_reply(MSG_HASH, thread=THREAD_HASH)
        assert fields[FIELD_THREAD] == THREAD_HASH
        assert fields[FIELD_REPLY_TO] == MSG_HASH

    def test_thread_hex(self):
        fields = pack_reply(MSG_HASH, thread=THREAD_HEX)
        assert fields[FIELD_THREAD] == THREAD_HASH

    def test_thread_only(self):
        fields = pack_reply(None, thread=THREAD_HASH)
        assert FIELD_REPLY_TO not in fields
        assert fields[FIELD_THREAD] == THREAD_HASH

    def test_quote_str(self):
        fields = pack_reply(MSG_HASH, quote="original text")
        assert fields[FIELD_REPLY_QUOTE] == b"original text"

    def test_quote_bytes(self):
        fields = pack_reply(MSG_HASH, quote=b"raw quote")
        assert fields[FIELD_REPLY_QUOTE] == b"raw quote"

    def test_quote_truncated(self):
        fields = pack_reply(MSG_HASH, quote="x" * 500)
        assert len(fields[FIELD_REPLY_QUOTE]) == 200

    def test_quote_bool_ignored(self):
        fields = pack_reply(MSG_HASH, quote=True)
        assert FIELD_REPLY_QUOTE not in fields

    def test_invalid_hash(self):
        assert pack_reply("not-hex") == {}
        assert pack_reply(None) == {}

    def test_empty(self):
        assert pack_reply(None) == {}
        assert pack_reply(None, quote=None, thread=None) == {}


class TestUnpackReply:
    def test_roundtrip(self):
        fields = pack_reply(MSG_HASH, quote="hi", thread=THREAD_HASH)
        info = unpack_reply(fields)
        assert info == {
            "reply_to": MSG_HEX,
            "quote": "hi",
            "thread": THREAD_HEX,
        }

    def test_reply_only(self):
        info = unpack_reply({FIELD_REPLY_TO: MSG_HASH})
        assert info["reply_to"] == MSG_HEX
        assert info["quote"] is None
        assert info["thread"] is None

    def test_missing(self):
        assert unpack_reply(None) is None
        assert unpack_reply({}) is None
        assert unpack_reply({1: "x"}) is None

    def test_string_keys(self):
        info = unpack_reply({"reply_to": MSG_HEX, "quote": "q", "thread": THREAD_HEX})
        assert info["reply_to"] == MSG_HEX
        assert info["quote"] == "q"
        assert info["thread"] == THREAD_HEX

    def test_str_quote(self):
        info = unpack_reply({FIELD_REPLY_QUOTE: "already text"})
        assert info["quote"] == "already text"


@pytest.fixture
def bot():
    b = TestBot()
    yield b
    b.close()


class TestSendReplyFields:
    def test_send_reply_to(self, bot):
        sent = bot.send(
            bot.sender_hex("alice"),
            "response",
            reply_to=MSG_HASH,
        )
        assert sent is True
        msg = bot.drain()[0]
        assert msg.fields[FIELD_REPLY_TO] == MSG_HASH
        assert msg.fields[FIELD_THREAD] == MSG_HASH

    def test_send_reply_to_hex(self, bot):
        bot.send(bot.sender_hex("alice"), "r", reply_to=MSG_HEX)
        assert bot.drain()[0].fields[FIELD_REPLY_TO] == MSG_HASH

    def test_send_quote_and_thread(self, bot):
        bot.send(
            bot.sender_hex("alice"),
            "r",
            reply_to=MSG_HASH,
            quote="quoted",
            thread=THREAD_HASH,
        )
        fields = bot.drain()[0].fields
        assert fields[FIELD_REPLY_QUOTE] == b"quoted"
        assert fields[FIELD_THREAD] == THREAD_HASH

    def test_send_no_reply_fields(self, bot):
        bot.send(bot.sender_hex("alice"), "r")
        fields = bot.drain()[0].fields
        assert fields is None or FIELD_REPLY_TO not in fields

    def test_explicit_kwarg_wins_over_fields(self, bot):
        bot.send(
            bot.sender_hex("alice"),
            "r",
            reply_to=MSG_HASH,
            lxmf_fields={FIELD_REPLY_TO: THREAD_HASH},
        )
        assert bot.drain()[0].fields[FIELD_REPLY_TO] == MSG_HASH

    def test_other_fields_preserved(self, bot):
        bot.send(
            bot.sender_hex("alice"),
            "r",
            reply_to=MSG_HASH,
            lxmf_fields={0xFB: "custom"},
        )
        fields = bot.drain()[0].fields
        assert fields[0xFB] == "custom"
        assert fields[FIELD_REPLY_TO] == MSG_HASH


class TestReplyHelper:
    def test_reply_auto_threads(self, bot):
        captured = {}

        @bot.command("echo")
        def echo(msg):
            captured["hash"] = msg.hash
            msg.reply("echoed")

        inbound_hash = bytes(range(32))
        sent = bot.receive("/echo", sender="alice", message_hash=inbound_hash)
        fields = sent[0].fields
        assert fields[FIELD_REPLY_TO] == inbound_hash
        assert fields[FIELD_THREAD] == inbound_hash
        assert captured["hash"] == inbound_hash.hex()

    def test_reply_disabled(self, bot):
        @bot.command("plain")
        def plain(msg):
            msg.reply("flat", reply_to=None)

        sent = bot.receive("/plain", sender="alice")
        assert FIELD_REPLY_TO not in (sent[0].fields or {})

    def test_reply_inherits_thread(self, bot):
        @bot.command("next")
        def nxt(msg):
            msg.reply("continued")

        sent = bot.receive(
            "/next",
            sender="alice",
            fields={FIELD_THREAD: THREAD_HASH},
        )
        fields = sent[0].fields
        assert fields[FIELD_THREAD] == THREAD_HASH

    def test_reply_quote_true(self, bot):
        @bot.command("quoted")
        def quoted(msg):
            msg.reply("answer", quote=True)

        sent = bot.receive("/quoted extra words", sender="alice")
        assert sent[0].fields[FIELD_REPLY_QUOTE] == b"/quoted extra words"

    def test_inbound_reply_fields_on_ctx(self, bot):
        captured = {}

        @bot.command("inspect")
        def inspect(msg):
            captured["reply_to"] = msg.reply_to
            captured["quote"] = msg.reply_quote
            captured["thread"] = msg.thread

        bot.receive(
            "/inspect",
            sender="alice",
            fields=pack_reply(MSG_HASH, quote="earlier", thread=THREAD_HASH),
        )
        assert captured["reply_to"] == MSG_HEX
        assert captured["quote"] == "earlier"
        assert captured["thread"] == THREAD_HEX

    def test_inbound_no_reply_fields(self, bot):
        captured = {}

        @bot.command("bare")
        def bare(msg):
            captured["reply_to"] = msg.reply_to
            captured["thread"] = msg.thread

        bot.receive("/bare", sender="alice")
        assert captured["reply_to"] is None
        assert captured["thread"] is None
