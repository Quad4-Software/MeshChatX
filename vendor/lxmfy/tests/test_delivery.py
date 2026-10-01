"""Tests for delivery event tracking, the /delivery admin command, and per-command rate limits."""

import ast
import time
from unittest.mock import Mock

from lxmfy import DeliveryTracker
from lxmfy._admin import format_delivery_timeline
from lxmfy.cli import run_init
from lxmfy.moderation import SpamProtection
from lxmfy.storage import JSONStorage, Storage


def _make_tracker(tmp_path, maxlen=100):
    storage = Storage(JSONStorage(str(tmp_path / "st")))
    return DeliveryTracker(storage, maxlen=maxlen), storage


class TestDeliveryTracker:
    def test_record_notifies_subscribers(self, tmp_path):
        tracker, _ = _make_tracker(tmp_path)
        seen = []
        tracker.subscribe(seen.append)

        tracker.record(
            "queued",
            destination="aa" * 16,
            message_id="01" * 16,
            reason="test",
        )

        assert len(seen) == 1
        event = seen[0]
        assert event["stage"] == "queued"
        assert event["destination"] == "aa" * 16
        assert event["message_id"] == "01" * 16
        assert event["reason"] == "test"
        assert isinstance(event["ts"], float)

    def test_recent_orders_and_limits(self, tmp_path):
        tracker, _ = _make_tracker(tmp_path)
        for i in range(5):
            tracker.record("queued", destination=f"dest{i}")

        recent = tracker.recent(3)
        assert len(recent) == 3
        assert recent[-1]["destination"] == "dest4"

    def test_filter_by_stage_and_destination(self, tmp_path):
        tracker, _ = _make_tracker(tmp_path)
        tracker.record("queued", destination="d1")
        tracker.record("delivered", destination="d1")
        tracker.record("failed", destination="d2")

        assert [e["stage"] for e in tracker.recent(stage="delivered")] == ["delivered"]
        assert [e["stage"] for e in tracker.recent(destination="d2")] == ["failed"]

    def test_max_events_trims_oldest(self, tmp_path):
        tracker, _ = _make_tracker(tmp_path, maxlen=5)
        for i in range(10):
            tracker.record("queued", destination=f"d{i}")

        events = tracker.recent(100)
        assert len(events) == 5
        assert events[0]["destination"] == "d5"

    def test_persistence_round_trip(self, tmp_path):
        tracker, _ = _make_tracker(tmp_path)
        tracker.record("queued", destination="d1")
        tracker.record("failed", destination="d2", reason="boom")

        storage2 = Storage(JSONStorage(str(tmp_path / "st")))
        tracker2 = DeliveryTracker(storage2)
        tracker2.load_persisted()

        events = tracker2.recent()
        assert [e["stage"] for e in events] == ["queued", "failed"]
        assert events[1]["reason"] == "boom"

    def test_subscriber_exception_does_not_break_record(self, tmp_path):
        tracker, _ = _make_tracker(tmp_path)

        def bad(event):
            raise RuntimeError("subscriber bug")

        tracker.subscribe(bad)
        tracker.subscribe(lambda e: None)
        tracker.record("queued", destination="d1")
        assert len(tracker.recent()) == 1

    def test_unsubscribe_stops_events(self, tmp_path):
        tracker, _ = _make_tracker(tmp_path)
        seen = []
        tracker.subscribe(seen.append)
        tracker.record("queued")
        assert tracker.unsubscribe(seen.append) is True
        assert tracker.unsubscribe(seen.append) is False
        tracker.record("queued")
        assert len(seen) == 1


class TestDeliveryIntegration:
    def test_bot_has_tracker(self, test_bot):
        assert isinstance(test_bot.delivery, DeliveryTracker)

    def test_send_emits_queued_event(self, test_bot):
        seen = []
        test_bot.delivery.subscribe(seen.append)
        test_bot.send("aa" * 16, "hello")

        queued = [e for e in seen if e["stage"] == "queued"]
        assert len(queued) == 1
        assert queued[0]["destination"] == "aa" * 16

    def test_on_delivery_event_decorator(self, test_bot):
        seen = []

        @test_bot.on_delivery_event()
        def listener(event):
            seen.append(event)

        test_bot.delivery.record("queued", destination="d1")
        assert len(seen) == 1

    def test_on_delivery_event_direct_call(self, test_bot):
        seen = []
        test_bot.on_delivery_event(seen.append)
        test_bot.delivery.record("queued")
        assert len(seen) == 1

    def test_persisted_events_load_into_new_tracker(self, test_bot):
        test_bot.delivery.record("queued", destination="d1")
        tracker2 = DeliveryTracker(test_bot.storage)
        tracker2.load_persisted()
        assert len(tracker2.recent()) >= 1


class TestDeliveryCommand:
    def _send_command(self, bot, text):
        sent = []
        original_send = bot.send
        bot.send = lambda dest, msg, **kw: sent.append(msg)

        msg = Mock()
        msg.content = text.encode()
        msg.hash = b"cmd_hash"
        msg.fields = {}
        msg.title = b""
        bot._process_message(msg, "admin_sender")

        bot.send = original_send
        return sent

    def test_delivery_empty(self, test_bot):
        sent = self._send_command(test_bot, "/delivery")
        assert sent
        assert "No delivery events" in sent[0]

    def test_delivery_renders_events(self, test_bot):
        test_bot.delivery.record(
            "failed",
            destination="ab" * 16,
            reason="no_route",
        )
        sent = self._send_command(test_bot, "/delivery")
        assert sent
        assert "failed" in sent[0]
        assert "no_route" in sent[0]

    def test_delivery_limit_arg(self, test_bot):
        for i in range(20):
            test_bot.delivery.record("queued", destination=f"d{i}")
        sent = self._send_command(test_bot, "/delivery 3")
        lines = sent[0].strip().split("\n")
        assert len(lines) == 3

    def test_delivery_limit_capped_at_50(self, test_bot):
        for i in range(60):
            test_bot.delivery.record("queued", destination=f"d{i}")
        sent = self._send_command(test_bot, "/delivery 500")
        assert len(sent[0].strip().split("\n")) == 50

    def test_format_timeline_empty(self):
        assert format_delivery_timeline([]) == "No delivery events recorded."

    def test_format_timeline_reason_suffix(self):
        out = format_delivery_timeline(
            [{"stage": "dropped", "destination": "x" * 32, "reason": "queue_full"}],
        )
        assert "dropped" in out
        assert "queue_full" in out


def _perms_bot(test_config_dir, name="PermBot", admins=None):
    """Create a test-mode bot with the permission system enabled."""
    import uuid

    from lxmfy import BotConfig, LXMFBot

    path = test_config_dir / f"{name}_{uuid.uuid4().hex[:8]}"
    path.mkdir(exist_ok=True)
    config = BotConfig(
        name=name,
        test_mode=True,
        cogs_enabled=False,
        permissions_enabled=True,
        admins=admins or set(),
        config_path=str(path),
        storage_path=str(path / "storage"),
        storage_type="json",
    )
    return LXMFBot(**config.__dict__)


class TestCommandRateLimit:
    def _spam(self, bot, cooldown=60):
        return SpamProtection(
            bot.storage,
            bot,
            rate_limit=100,
            cooldown=cooldown,
            max_warnings=10,
            warning_timeout=60,
        )

    def test_allows_up_to_limit(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "RL1")
        try:
            spam = self._spam(bot)
            for _ in range(3):
                allowed, _ = spam.check_command_limit("user1", "cmd", 3)
                assert allowed
            allowed, notice = spam.check_command_limit("user1", "cmd", 3)
            assert not allowed
            assert "rate limited" in notice.lower()
        finally:
            bot.cleanup()

    def test_independent_per_command(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "RL2")
        try:
            spam = self._spam(bot)
            for _ in range(2):
                spam.check_command_limit("user1", "cmdA", 2)
            allowed, _ = spam.check_command_limit("user1", "cmdB", 2)
            assert allowed
        finally:
            bot.cleanup()

    def test_independent_per_sender(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "RL3")
        try:
            spam = self._spam(bot)
            for _ in range(2):
                spam.check_command_limit("user1", "cmd", 2)
            allowed, _ = spam.check_command_limit("user2", "cmd", 2)
            assert allowed
        finally:
            bot.cleanup()

    def test_window_expiry(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "RL4")
        try:
            spam = self._spam(bot, cooldown=0.05)
            allowed, _ = spam.check_command_limit("user1", "cmd", 1)
            assert allowed
            allowed, _ = spam.check_command_limit("user1", "cmd", 1)
            assert not allowed
            time.sleep(0.06)
            allowed, _ = spam.check_command_limit("user1", "cmd", 1)
            assert allowed
        finally:
            bot.cleanup()

    def test_admin_bypass_with_permissions(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "RL5", admins={"boss"})
        try:
            spam = self._spam(bot)
            for _ in range(5):
                allowed, _ = spam.check_command_limit("boss", "cmd", 1)
                assert allowed
            allowed, _ = spam.check_command_limit("peon", "cmd", 1)
            assert allowed
            allowed, _ = spam.check_command_limit("peon", "cmd", 1)
            assert not allowed
        finally:
            bot.cleanup()

    def test_counts_persist(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "RL6")
        try:
            spam = self._spam(bot)
            spam.check_command_limit("user1", "cmd", 2)
            spam.check_command_limit("user1", "cmd", 2)
            allowed, _ = spam.check_command_limit("user1", "cmd", 2)
            assert not allowed

            spam2 = self._spam(bot)
            allowed, _ = spam2.check_command_limit("user1", "cmd", 2)
            assert not allowed
        finally:
            bot.cleanup()

    def test_dispatch_enforces_limit(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "RL7")
        try:
            calls = []
            sent = []
            bot.send = lambda dest, msg, **kw: sent.append(msg)

            @bot.command(name="limited", rate_limit=2)
            def limited(ctx):
                calls.append(1)

            msg = Mock()
            msg.content = b"/limited"
            msg.hash = b"h"
            msg.fields = {}
            msg.title = b""

            bot._process_message(msg, "user1")
            bot._process_message(msg, "user1")
            bot._process_message(msg, "user1")

            assert len(calls) == 2
            assert any("rate limited" in m.lower() for m in sent)
        finally:
            bot.cleanup()


class TestInitScaffold:
    def test_basic_scaffold(self, tmp_path):
        rc = run_init(["mybot", "--dir", str(tmp_path), "--yes"])
        assert rc == 0
        root = tmp_path / "mybot"
        src = (root / "bot.py").read_text()
        ast.parse(src)
        assert 'command_prefix="/"' in src
        assert 'storage_type="json"' in src
        assert (root / "cogs" / "__init__.py").exists()
        assert (root / "cogs" / "basic.py").exists()
        assert (root / "README.md").exists()
        assert (root / ".gitignore").exists()

    def test_scaffold_options(self, tmp_path):
        rc = run_init(
            [
                "nb",
                "--dir",
                str(tmp_path),
                "--yes",
                "--storage",
                "sqlite",
                "--prefix",
                "!",
                "--admins",
                "aabbcc, 1122",
                "--no-cogs",
                "--bot-name",
                "Nice Bot",
            ],
        )
        assert rc == 0
        root = tmp_path / "nb"
        src = (root / "bot.py").read_text()
        ast.parse(src)
        assert 'storage_type="sqlite"' in src
        assert 'command_prefix="!"' in src
        assert '"aabbcc"' in src
        assert '"1122"' in src
        assert '"Nice Bot"' in src
        assert "cogs_enabled=False" in src
        assert not (root / "cogs").exists()

    def test_template_scaffold(self, tmp_path):
        rc = run_init(
            ["eb", "--dir", str(tmp_path), "--yes", "--template", "echo"],
        )
        assert rc == 0
        src = (tmp_path / "eb" / "bot.py").read_text()
        ast.parse(src)
        assert "EchoBot" in src

    def test_refuses_nonempty_dir(self, tmp_path):
        root = tmp_path / "taken"
        root.mkdir()
        (root / "keep.txt").write_text("x")
        rc = run_init(["taken", "--dir", str(tmp_path), "--yes"])
        assert rc == 1
        assert (root / "keep.txt").read_text() == "x"
        assert not (root / "bot.py").exists()

    def test_force_overwrites(self, tmp_path):
        root = tmp_path / "taken"
        root.mkdir()
        (root / "bot.py").write_text("old")
        rc = run_init(["taken", "--dir", str(tmp_path), "--yes", "--force"])
        assert rc == 0
        assert "LXMFBot" in (root / "bot.py").read_text()

    def test_invalid_admin_hash_rejected(self, tmp_path):
        rc = run_init(
            ["b", "--dir", str(tmp_path), "--yes", "--admins", "zz"],
        )
        assert rc == 1
        assert not (tmp_path / "b").exists()

    def test_bot_name_sanitized(self, tmp_path):
        rc = run_init(
            ["x", "--dir", str(tmp_path), "--yes", "--bot-name", "bad name!!"],
        )
        assert rc == 0
        assert '"bad name"' in (tmp_path / "x" / "bot.py").read_text()

    def test_here_scaffolds_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = run_init(["--here", "--yes", "--bot-name", "HereBot"])
        assert rc == 0
        src = (tmp_path / "bot.py").read_text()
        ast.parse(src)
        assert '"HereBot"' in src

    def test_nontty_no_name_uses_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        rc = run_init(["--dir", str(tmp_path)])
        assert rc == 0
        assert (tmp_path / "mybot" / "bot.py").exists()


class TestAdminPermissionsFix:
    """Configured admins must get admin role perms when permissions are on."""

    def test_admin_gets_admin_perms(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "P1", admins={"boss"})
        try:
            from lxmfy import DefaultPerms

            assert bot.permissions.has_permission("boss", DefaultPerms.ALL)
            assert not bot.permissions.has_permission("peon", DefaultPerms.ALL)
        finally:
            bot.cleanup()

    def test_admin_only_command_runs_for_admin(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "P2", admins={"boss"})
        try:
            sent = []
            bot.send = lambda dest, msg, **kw: sent.append((dest, msg))

            msg = Mock()
            msg.content = b"/queue"
            msg.hash = b"h"
            msg.fields = {}
            msg.title = b""
            bot._process_message(msg, "boss")
            assert any("outbound" in m for _, m in sent)

            sent.clear()
            bot._process_message(msg, "peon")
            assert any("permission" in m.lower() for _, m in sent)
        finally:
            bot.cleanup()

    def test_admin_set_mutations_propagate(self, test_config_dir):
        bot = _perms_bot(test_config_dir, "P3")
        try:
            from lxmfy import DefaultPerms

            assert not bot.permissions.has_permission("late", DefaultPerms.ALL)
            bot.admins.add("late")
            assert bot.permissions.has_permission("late", DefaultPerms.ALL)
        finally:
            bot.cleanup()
