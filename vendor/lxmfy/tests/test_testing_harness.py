"""Tests for the lxmfy.testing harness itself."""

from __future__ import annotations

import time

from lxmfy import TestBot, fake_message
from lxmfy.testing import SentMessage


class TestHarness:
    def test_defaults(self):
        with TestBot() as bot:
            assert bot.config.test_mode is True
            assert bot.config.storage_type == "memory"

    def test_overrides(self):
        with TestBot(name="Custom", command_prefix="!") as bot:
            assert bot.config.name == "Custom"
            assert bot.command_prefix == "!"

    def test_receive_captures_reply(self):
        with TestBot() as bot:

            @bot.command("hi")
            def hi(msg):
                msg.reply("hello")

            sent = bot.receive("/hi", sender="alice")
            assert len(sent) == 1
            assert sent[0].content == "hello"
            assert sent[0].destination == bot.sender_hex("alice")

    def test_sender_hash_stable(self):
        with TestBot() as bot:
            assert bot.sender_hash("alice") == bot.sender_hash("alice")
            assert bot.sender_hash("alice") != bot.sender_hash("bob")
            raw = bytes.fromhex("ab" * 16)
            assert bot.sender_hash("ab" * 16) == raw

    def test_sender_hex(self):
        with TestBot() as bot:
            assert bot.sender_hex("alice") == bot.sender_hash("alice").hex()

    def test_outbox_accumulates(self):
        with TestBot() as bot:

            @bot.command("x")
            def x(msg):
                msg.reply("one")

            bot.receive("/x")
            bot.receive("/x")
            assert len(bot.outbox) == 2

    def test_last_sent(self):
        with TestBot() as bot:

            @bot.command("y")
            def y(msg):
                msg.reply("two")

            bot.receive("/y", sender="alice")
            bot.receive("/y", sender="bob")
            assert bot.last_sent().content == "two"
            assert bot.last_sent(sender="alice").destination == bot.sender_hex("alice")
            assert bot.last_sent(sender="nobody") is None

    def test_wait_sent_threaded(self):
        with TestBot() as bot:

            @bot.command("slow", threaded=True)
            def slow(msg):
                time.sleep(0.1)
                msg.reply("done")

            bot.receive("/slow")
            sent = bot.wait_sent(1, timeout=3)
            assert sent[0].content == "done"

    def test_receive_fields_passthrough(self):
        with TestBot() as bot:
            captured = {}

            @bot.command("f")
            def f(msg):
                captured.update(msg.fields)

            bot.receive("/f", fields={0xFB: "custom"})
            assert captured[0xFB] == "custom"

    def test_duplicate_hash_deduped(self):
        with TestBot() as bot:
            seen = []

            @bot.on_message()
            def spy(sender, message):
                seen.append(message.content)
                return True

            fixed = b"\x11" * 32
            bot.receive("first", message_hash=fixed)
            bot.receive("dup", message_hash=fixed)
            assert seen == [b"first"]

    def test_fake_message(self):
        m = fake_message("hi", source_hash=b"\x01" * 16, title="T", fields={1: 2})
        assert m.content == b"hi"
        assert m.title == b"T"
        assert m.fields == {1: 2}
        assert len(m.hash) == 32

    def test_sent_message_normalization(self):
        with TestBot() as bot:
            bot.send(bot.sender_hex("alice"), "body", title="T")
            msg = bot.drain()[0]
            assert isinstance(msg, SentMessage)
            assert msg.content == "body"
            assert msg.title == "T"
            assert msg.destination == bot.sender_hex("alice")
            assert repr(msg).startswith("SentMessage(")

    def test_receive_later_answers_ask(self):
        with TestBot() as bot:

            @bot.command("q")
            def q(msg):
                ans = msg.ask("ping?", timeout=5)
                msg.reply("pong" if ans else "none")

            bot.receive_later("yes", delay=0.1)
            bot.receive("/q")
            time.sleep(0.3)
            assert bot.last_sent().content == "pong"

    def test_close_is_idempotent(self):
        bot = TestBot()
        bot.close()
