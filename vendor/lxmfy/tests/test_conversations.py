"""Tests for the multi-step conversation API."""

from __future__ import annotations

import threading
import time

import pytest

from lxmfy import TestBot
from lxmfy.conversations import MAX_PENDING
from lxmfy.lxmf_fields import FIELD_COMMANDS, pack_reaction


@pytest.fixture
def bot():
    b = TestBot()
    yield b
    b.close()


def _answer_later(bot, content, sender="alice", delay=0.1):
    bot.receive_later(content, sender=sender, delay=delay)


class TestBlockingAsk:
    def test_ask_returns_answer(self, bot):
        @bot.command("name")
        def name(msg):
            ans = msg.ask("Your name?", timeout=5)
            msg.reply(f"hi {ans.content}" if ans else "no answer")

        _answer_later(bot, "Ada")
        bot.receive("/name", sender="alice")
        time.sleep(0.4)
        contents = [m.content for m in bot.outbox]
        assert "Your name?" in contents
        assert "hi Ada" in contents

    def test_answer_exposes_fields_and_hash(self, bot):
        captured = {}

        @bot.command("meta")
        def meta(msg):
            ans = msg.ask("go", timeout=5)
            captured["hash"] = ans.hash
            captured["fields"] = ans.fields
            captured["sender"] = ans.sender

        def driver():
            time.sleep(0.1)
            bot.receive(
                "answer",
                sender="alice",
                fields={0xFB: "tag"},
                message_hash=b"\xab" * 32,
            )

        threading.Thread(target=driver, daemon=True).start()
        bot.receive("/meta", sender="alice")
        time.sleep(0.3)
        assert captured["hash"] == (b"\xab" * 32).hex()
        assert captured["fields"][0xFB] == "tag"
        assert captured["sender"] == bot.sender_hex("alice")

    def test_timeout_returns_none(self, bot):
        @bot.command("wait")
        def wait(msg):
            ans = msg.ask("quick?", timeout=0.2)
            msg.reply("got-none" if ans is None else "unexpected")

        bot.receive("/wait", sender="alice")
        assert bot.last_sent().content == "got-none"
        assert not bot.conversations.has_pending(bot.sender_hex("alice"))

    def test_cancel_returns_none(self, bot):
        @bot.command("long")
        def long_(msg):
            ans = msg.ask("waiting", timeout=10)
            msg.reply("cancelled" if ans is None else "answered")

        def driver():
            time.sleep(0.15)
            bot.conversations.cancel(bot.sender_hex("alice"))

        threading.Thread(target=driver, daemon=True).start()
        bot.receive("/long", sender="alice")
        time.sleep(0.4)
        assert bot.last_sent().content == "cancelled"

    def test_other_sender_does_not_resolve(self, bot):
        done = threading.Event()

        @bot.command("solo")
        def solo(msg):
            ans = msg.ask("alice only", timeout=0.5)
            done.set()
            msg.reply(f"ans={ans.content if ans else 'none'}")

        def driver():
            time.sleep(0.1)
            bot.receive("intruder reply", sender="mallory")

        threading.Thread(target=driver, daemon=True).start()
        bot.receive("/solo", sender="alice")
        done.wait(2)
        assert bot.last_sent().content == "ans=none"

    def test_prompt_sends_before_wait(self, bot):
        @bot.command("order")
        def order(msg):
            msg.ask("the prompt", timeout=0.2)

        bot.receive("/order", sender="alice")
        sent = [m.content for m in bot.outbox]
        assert sent == ["the prompt"]


class TestCommandEscape:
    def test_command_cancels_pending(self, bot):
        @bot.command("status")
        def status(msg):
            msg.reply("status-ok")

        @bot.command("flow")
        def flow(msg):
            ans = msg.ask("answer me", timeout=10)
            msg.reply("flow-done" if ans is None else "flow-answered")

        _answer_later(bot, "/status", delay=0.15)
        bot.receive("/flow", sender="alice")
        time.sleep(0.4)
        contents = [m.content for m in bot.outbox]
        assert "status-ok" in contents
        assert "flow-done" in contents
        assert not bot.conversations.has_pending(bot.sender_hex("alice"))

    def test_field_command_cancels_pending(self, bot):
        @bot.command("flow")
        def flow(msg):
            ans = msg.ask("answer me", timeout=10)
            msg.reply("done" if ans is None else "answered")

        def driver():
            time.sleep(0.15)
            bot.receive(
                "",
                sender="alice",
                fields={FIELD_COMMANDS: {"command": "status"}},
            )

        @bot.command("status")
        def status(msg):
            msg.reply("status-ran")

        threading.Thread(target=driver, daemon=True).start()
        bot.receive("/flow", sender="alice")
        time.sleep(0.4)
        contents = [m.content for m in bot.outbox]
        assert "status-ran" in contents


class TestValidator:
    def test_invalid_answer_reprompts(self, bot):
        @bot.command("num")
        def num(msg):
            ans = msg.ask(
                "pick a number",
                timeout=5,
                validator=lambda a: None if a.content.isdigit() else "digits only",
            )
            msg.reply(f"n={ans.content}")

        def driver():
            time.sleep(0.1)
            bot.receive("abc", sender="alice")
            time.sleep(0.1)
            bot.receive("42", sender="alice")

        threading.Thread(target=driver, daemon=True).start()
        bot.receive("/num", sender="alice")
        time.sleep(0.4)
        contents = [m.content for m in bot.outbox]
        assert "pick a number" in contents
        assert "digits only" in contents
        assert "n=42" in contents

    def test_validator_exception_reprompts(self, bot):
        @bot.command("v")
        def v(msg):
            def bad(a):
                raise ValueError("boom")

            ans = msg.ask("go", timeout=5, validator=bad)
            msg.reply("done" if ans is None else "answered")

        _answer_later(bot, "x", delay=0.1)
        _answer_later(bot, "y", delay=0.25)
        bot.receive("/v", sender="alice")
        time.sleep(0.5)
        assert "Invalid answer." in [m.content for m in bot.outbox]


class TestCallbackStyle:
    def test_on_answer_called(self, bot):
        got = []

        @bot.command("cb")
        def cb(msg):
            msg.ask(
                "say it",
                on_answer=lambda a: got.append(a.content),
                timeout=5,
            )

        bot.receive("/cb", sender="alice")
        assert bot.last_sent().content == "say it"
        bot.receive("the answer", sender="alice")
        time.sleep(0.1)
        assert got == ["the answer"]
        assert not bot.conversations.has_pending(bot.sender_hex("alice"))

    def test_on_timeout_called(self, bot):
        expired = []
        bot.conversations.ask_callback(
            bot.sender_hex("alice"),
            "q",
            lambda a: None,
            timeout=0.2,
            on_timeout=expired.append,
        )
        time.sleep(0.4)
        assert expired == [bot.sender_hex("alice")]
        assert bot.conversations.pending_count() == 0

    def test_callback_answer_reply(self, bot):
        @bot.command("cb2")
        def cb2(msg):
            msg.ask(
                "name?",
                on_answer=lambda a: a.reply(f"ok {a.content}"),
                timeout=5,
            )

        bot.receive("/cb2", sender="alice")
        bot.receive("bob", sender="alice")
        time.sleep(0.1)
        assert bot.last_sent().content == "ok bob"


class TestAsyncAsk:
    def test_ask_async_resolves(self, bot):
        @bot.command("aflow")
        async def aflow(msg):
            ans = await msg.ask_async("async q", timeout=5)
            msg.reply(f"a={ans.content}" if ans else "a=none")

        _answer_later(bot, "green", delay=0.15)
        bot.receive("/aflow", sender="alice")
        time.sleep(0.4)
        assert bot.last_sent().content == "a=green"

    def test_ask_async_timeout(self, bot):
        @bot.command("aslow")
        async def aslow(msg):
            ans = await msg.ask_async("async q", timeout=0.2)
            msg.reply("a=none" if ans is None else "a=bad")

        bot.receive("/aslow", sender="alice")
        assert bot.last_sent().content == "a=none"


class TestRegistry:
    def test_pending_cap(self, bot):
        for i in range(MAX_PENDING):
            sender = f"{i:032x}"
            assert bot.conversations.ask_callback(
                sender,
                None,
                lambda a: None,
                timeout=60,
            )
        assert bot.conversations.pending_count() == MAX_PENDING
        assert (
            bot.conversations.ask_callback("f" * 32, None, lambda a: None, timeout=60)
            is False
        )
        bot.conversations.cancel_all()

    def test_reask_replaces_pending(self, bot):
        sender = bot.sender_hex("alice")
        first_done = threading.Event()
        second_got = []

        def first():
            assert bot.conversations.ask(sender, "one", timeout=5) is None
            first_done.set()

        t = threading.Thread(target=first, daemon=True)
        t.start()
        time.sleep(0.1)
        assert bot.conversations.ask_callback(
            sender,
            "two",
            lambda a: second_got.append(a.content),
            timeout=5,
        )
        assert first_done.wait(2)
        bot.receive("answer", sender="alice")
        time.sleep(0.1)
        assert second_got == ["answer"]

    def test_answers_skip_message_handlers(self, bot):
        seen = []

        @bot.on_message()
        def spy(sender, message):
            seen.append(message.content)
            return False

        bot.conversations.ask_callback(
            bot.sender_hex("alice"),
            "q",
            lambda a: None,
            timeout=5,
        )
        bot.receive("the answer", sender="alice")
        time.sleep(0.1)
        assert seen == []

    def test_bare_reaction_does_not_resolve(self, bot):
        reactions = []
        answers = []

        @bot.on_reaction()
        def on_reaction(sender, reaction):
            reactions.append(reaction)
            return True

        bot.conversations.ask_callback(
            bot.sender_hex("alice"),
            "q",
            answers.append,
            timeout=5,
        )
        bot.receive(
            "",
            sender="alice",
            fields=pack_reaction(b"\x11" * 32, "yes"),
        )
        time.sleep(0.1)
        assert len(reactions) == 1
        assert answers == []
        assert bot.conversations.has_pending(bot.sender_hex("alice"))

        bot.receive("real answer", sender="alice")
        time.sleep(0.1)
        assert answers[0].content == "real answer"

    def test_cancel_all(self, bot):
        bot.conversations.ask_callback("aa" * 16, "q", lambda a: None, timeout=60)
        bot.conversations.ask_callback("bb" * 16, "q", lambda a: None, timeout=60)
        assert bot.conversations.pending_count() == 2
        bot.conversations.cancel_all()
        assert bot.conversations.pending_count() == 0
