"""Integration tests for LXMFy client-bot communication."""

from unittest.mock import Mock

import RNS
from LXMF import LXMessage


class TestClientBotCommunication:
    """Test client-bot message exchange."""

    def test_message_sending(self, test_bot, test_destination):
        """Test basic message sending functionality."""
        # Mock the queue.put to capture queued messages
        original_queue_put = test_bot.queue.put
        queued_messages = []

        def capture_queue_put(message):
            queued_messages.append(message)
            return original_queue_put(message)

        test_bot.queue.put = capture_queue_put

        # Mock Identity.recall to return the test identity so send() works
        original_recall = RNS.Identity.recall
        RNS.Identity.recall = lambda hash_bytes: (
            test_destination.identity
            if hash_bytes == test_destination.hash
            else original_recall(hash_bytes)
        )

        try:
            # Send a message using the test destination's hash
            dest_hash = RNS.hexrep(test_destination.hash, delimit=False)
            test_bot.send(dest_hash, "Hello World", "Test Title")

            # Verify message was queued
            assert len(queued_messages) == 1
            message = queued_messages[0]

            # In test mode, message is a SimpleNamespace, not LXMessage
            if test_bot.config.test_mode:
                assert message.content.decode() == "Hello World"
                assert message.title.decode() == "Test Title"
            else:
                assert isinstance(message, LXMessage)
                assert message.content.decode() == "Hello World"
                assert message.title.decode() == "Test Title"
        finally:
            # Restore original methods
            test_bot.queue.put = original_queue_put
            RNS.Identity.recall = original_recall

    def test_command_processing(self, test_bot):
        """Test command processing pipeline."""
        # Register a test command
        responses = []

        @test_bot.command("test")
        def test_cmd(ctx):
            responses.append(f"Processed: {ctx.content}")
            ctx.reply("Command executed")

        # Mock the send method to capture responses
        original_send = test_bot.send
        sent_messages = []

        def mock_send(destination, message, title=None, **kwargs):
            sent_messages.append((destination, message, title))

        test_bot.send = mock_send

        # Simulate receiving a command message
        mock_message = Mock()
        mock_message.content = b"/test argument"
        mock_message.hash = b"message_hash_123"

        # Process the message
        test_bot._process_message(mock_message, "test_sender_hash")

        # Verify command was processed
        assert len(responses) == 1
        assert "Processed: /test argument" in responses[0]

        assert len(sent_messages) == 1
        dest, msg, title = sent_messages[0]
        assert dest == "test_sender_hash"
        assert msg == "Command executed"

        # Restore original send method
        test_bot.send = original_send

    def test_spam_protection(self, test_bot):
        """Test spam protection functionality."""
        sender = "spam_sender_hash"

        # Initially should allow messages
        allowed, message = test_bot.spam_protection.check_spam(sender)
        assert allowed
        assert message is None

        # Test that spam protection exists and has expected attributes
        assert hasattr(test_bot, "spam_protection")
        assert hasattr(test_bot.spam_protection, "check_spam")
        assert callable(test_bot.spam_protection.check_spam)

        # Test multiple messages - should eventually trigger protection
        # (exact behavior depends on timing, but method should exist)
        for i in range(5):  # Just test a few messages
            result_allowed, result_message = test_bot.spam_protection.check_spam(sender)
            # Should either allow or deny, but not crash
            assert isinstance(result_allowed, bool)
            if result_message:
                assert isinstance(result_message, str)

    def test_message_validation(self, test_bot):
        """Test message validation and processing."""
        # Test with various message formats
        test_cases = [
            (b"/help", True, "help command"),
            (b"regular message", True, "regular message"),
            (b"", True, "empty message"),
            (b"/nonexistent", True, "nonexistent command"),
        ]

        for content, should_process, description in test_cases:
            mock_message = Mock()
            mock_message.content = content
            mock_message.source_hash = b"test_hash"

            # Should not raise exceptions
            try:
                test_bot._process_message(mock_message, "test_hash")
                success = True
            except Exception as e:
                success = False
                print(f"Failed processing {description}: {e}")

            assert success, f"Failed to process {description}"


class TestLXMFIntegration:
    """Test LXMF-specific integration."""

    def test_lxmf_message_creation(self, lxmf_router):
        """Test LXMF message creation and basic properties."""
        # Create a test message
        message = LXMessage(
            destination=lxmf_router._test_delivery_dest,
            source=lxmf_router._test_delivery_dest,
            content=b"Test content",
            title=b"Test Title",
        )

        assert message.content == b"Test content"
        assert message.title == b"Test Title"
        assert message.source_hash is not None
        assert message.destination_hash is not None

    def test_router_functionality(self, lxmf_router):
        """Test LXMF router basic functionality."""
        assert lxmf_router._test_delivery_dest is not None
        assert lxmf_router.storagepath is not None

        # Test router can handle outbound messages
        message = LXMessage(
            destination=lxmf_router._test_delivery_dest,
            source=lxmf_router._test_delivery_dest,
            content=b"Test message",
        )

        # Should not raise exceptions
        lxmf_router.handle_outbound(message)


class TestTemplateBots:
    """Test the built-in template bots."""

    def test_echo_bot_creation(self, test_config_dir):
        """Test creating an echo bot template."""
        from lxmfy.templates import EchoBot

        # Create echo bot instance
        echo_bot = EchoBot(test_mode=True)

        assert echo_bot.bot is not None
        assert echo_bot.bot.config.name == "Echo Bot"
        assert "echo" in echo_bot.bot.commands

        # Test echo command exists
        echo_cmd = echo_bot.bot.commands["echo"]
        assert echo_cmd.name == "echo"
        assert "Echo back your message" in echo_cmd.description

        echo_bot.bot.cleanup()

    def test_note_bot_creation(self, test_config_dir):
        """Test creating a note bot template."""
        from lxmfy.templates import NoteBot

        note_bot = NoteBot(test_mode=True)

        assert note_bot.bot is not None
        assert note_bot.bot.config.name == "Note Bot"
        assert "note" in note_bot.bot.commands
        assert "notes" in note_bot.bot.commands

        note_bot.bot.cleanup()

    def test_reminder_bot_creation(self, test_config_dir):
        """Test creating a reminder bot template."""
        from lxmfy.templates import ReminderBot

        reminder_bot = ReminderBot(test_mode=True)

        assert reminder_bot.bot is not None
        assert reminder_bot.bot.config.name == "Reminder Bot"
        assert "remind" in reminder_bot.bot.commands
        assert "list" in reminder_bot.bot.commands

        reminder_bot.bot.cleanup()

    def test_cog_test_bot_creation(self, test_config_dir):
        """Test creating a cog test bot template."""
        from lxmfy.templates import CogTestBot

        cog_bot = CogTestBot(test_mode=True)

        assert cog_bot.bot is not None
        assert cog_bot.bot.config.name == "CogTestBot"
        assert "cogtest" in cog_bot.bot.commands
        assert "status" in cog_bot.bot.commands

        cog_bot.bot.cleanup()


class TestMiddlewareSystem:
    """Test middleware system integration."""

    def test_middleware_registration(self, test_bot):
        """Test middleware can be registered and executed."""
        from lxmfy.middleware import MiddlewareContext, MiddlewareType

        middleware_calls = []

        @test_bot.middleware.register(MiddlewareType.PRE_COMMAND)
        def test_middleware(ctx):
            middleware_calls.append(ctx)
            return ctx.data

        # Execute middleware
        ctx = MiddlewareContext(MiddlewareType.PRE_COMMAND, {"test": "data"})
        result = test_bot.middleware.execute(MiddlewareType.PRE_COMMAND, ctx)

        assert len(middleware_calls) == 1
        assert middleware_calls[0].data["test"] == "data"
        assert result == {"test": "data"}

    def test_middleware_cancellation(self, test_bot):
        """Test middleware can cancel processing."""
        from lxmfy.middleware import MiddlewareContext, MiddlewareType

        @test_bot.middleware.register(MiddlewareType.PRE_COMMAND)
        def cancelling_middleware(ctx):
            ctx.cancel()

        ctx = MiddlewareContext(MiddlewareType.PRE_COMMAND, {"test": "data"})
        result = test_bot.middleware.execute(MiddlewareType.PRE_COMMAND, ctx)

        assert ctx.cancelled
        assert result is None


class TestSchedulerSystem:
    """Test task scheduler integration."""

    def test_scheduler_creation(self, test_bot):
        """Test scheduler is created and functional."""
        assert test_bot.scheduler is not None
        assert hasattr(test_bot.scheduler, "tasks")
        assert hasattr(test_bot.scheduler, "add_task")

    def test_task_scheduling(self, test_bot):
        """Test task scheduling functionality."""
        task_calls = []

        def test_task():
            task_calls.append("executed")

        # Schedule a task
        test_bot.scheduler.add_task("test_task", test_task, "*/1 * * * *")

        assert "test_task" in test_bot.scheduler.tasks
        task = test_bot.scheduler.tasks["test_task"]
        assert task.name == "test_task"
        assert task.callback == test_task

        # Manually execute task
        task.callback()
        assert len(task_calls) == 1
        assert task_calls[0] == "executed"
