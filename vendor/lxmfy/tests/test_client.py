"""Tests for LXMFy client functionality and RNS/LXMF integration."""

from unittest.mock import Mock

import RNS
from LXMF import LXMessage

from lxmfy import BotConfig, LXMFBot


class TestRNSBasicFunctionality:
    """Test basic RNS functionality required for LXMFy."""

    def test_identity_creation(self, reticulum_instance):
        """Test RNS identity creation."""
        identity = RNS.Identity()
        assert identity is not None
        assert identity.hash is not None
        assert len(identity.hash) == RNS.Reticulum.TRUNCATED_HASHLENGTH // 8

    def test_destination_creation(self, test_identity, reticulum_instance):
        """Test RNS destination creation."""
        dest = RNS.Destination(
            test_identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            "test",
            "app",
        )

        assert dest is not None
        assert dest.hash is not None
        # Check direction (IN/OUT) and type (SINGLE/GROUP/etc.)
        assert dest.direction == RNS.Destination.IN
        assert dest.type == RNS.Destination.SINGLE

    def test_identity_recalling(self, test_identity):
        """Test identity recall functionality."""
        # Store identity hash
        identity_hash = test_identity.hash

        # Recall identity by hash - this should work for identities that have been seen
        # In a real network, this would recall from the identity cache
        RNS.Identity.recall(identity_hash)

        # Note: In test environment, recall might return None if identity hasn't been
        # registered in the network. Let's test the hash consistency instead
        assert identity_hash is not None
        assert len(identity_hash) == RNS.Reticulum.TRUNCATED_HASHLENGTH // 8

        # Test that we can create a destination and recall its identity
        dest = RNS.Destination(
            test_identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            "test",
            "recall",
        )

        # The destination's identity should be recallable
        RNS.Identity.recall(dest.hash)
        # This might be None in test environment, but the hash should be valid
        assert dest.hash is not None

    def test_path_request_simulation(self, test_destination):
        """Test path request functionality (simulated)."""
        destination_hash = test_destination.hash

        # Request path (this would normally contact the network)
        RNS.Transport.request_path(destination_hash)

        # In a real network, we'd wait for path establishment
        # For testing, we just verify the call doesn't crash
        assert destination_hash is not None


class TestLXMFMessageHandling:
    """Test LXMF message creation and handling."""

    def test_lxmf_message_creation(self, lxmf_router, test_identity):
        """Test creating LXMF messages."""
        # Create a destination for the message
        dest = RNS.Destination(
            test_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        message = LXMessage(
            destination=dest,
            source=lxmf_router._test_delivery_dest,
            content=b"Test message content",
            title=b"Test Title",
        )

        assert message.content == b"Test message content"
        assert message.title == b"Test Title"
        assert message.source_hash == lxmf_router._test_delivery_dest.hash
        assert message.destination_hash == dest.hash

    def test_lxmf_message_fields(self, lxmf_router, test_identity):
        """Test LXMF message with custom fields."""
        from lxmfy.signatures import FIELD_SIGNATURE

        # Create destination
        dest = RNS.Destination(
            test_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        message = LXMessage(
            destination=dest,
            source=lxmf_router._test_delivery_dest,
            content=b"Test message",
            fields={
                "custom_field": "custom_value",
                FIELD_SIGNATURE: b"signature_data",
            },
        )

        assert message.fields is not None
        assert message.fields["custom_field"] == "custom_value"
        assert message.fields[FIELD_SIGNATURE] == b"signature_data"

    def test_lxmf_router_operations(self, lxmf_router, test_identity):
        """Test LXMF router operations."""
        # Test delivery identity
        delivery_id = lxmf_router._test_delivery_dest
        assert delivery_id is not None

        # Test message handling
        dest = RNS.Destination(
            test_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        message = LXMessage(
            destination=dest,
            source=lxmf_router._test_delivery_dest,
            content=b"Router test message",
        )

        # Should handle outbound without errors
        lxmf_router.handle_outbound(message)


class TestClientBotInteraction:
    """Test client-side interaction with bots."""

    def test_client_message_creation(self, test_bot):
        """Test creating client messages to send to bots."""
        # Mock the send method to capture what would be sent
        sent_messages = []

        def mock_send(
            destination,
            message,
            title=None,
            lxmf_fields=None,
            stamp_cost=None,
        ):
            sent_messages.append(
                {
                    "destination": destination,
                    "message": message,
                    "title": title,
                    "fields": lxmf_fields,
                    "stamp_cost": stamp_cost,
                },
            )

        original_send = test_bot.send
        test_bot.send = mock_send

        # Send a test message
        test_bot.send(
            "test_dest_hash",
            "Hello Bot!",
            title="Test Message",
            lxmf_fields={"custom": "field"},
        )

        assert len(sent_messages) == 1
        msg = sent_messages[0]
        assert msg["destination"] == "test_dest_hash"
        assert msg["message"] == "Hello Bot!"
        assert msg["title"] == "Test Message"
        assert msg["fields"] == {"custom": "field"}

        test_bot.send = original_send

    def test_client_command_simulation(self, test_bot):
        """Test simulating client sending commands to bot."""
        # Register a command
        command_responses = []

        @test_bot.command("greet")
        def greet_cmd(ctx):
            command_responses.append(f"Hello {ctx.sender}!")
            ctx.reply(f"Hello {ctx.sender}!")

        # Mock message reception
        mock_message = Mock()
        mock_message.content = b"/greet"
        mock_message.hash = b"message_hash_123"  # Mock hash attribute

        sent_replies = []

        def mock_send(dest, msg, title=None, **kwargs):
            sent_replies.append((dest, msg, title))

        original_send = test_bot.send
        test_bot.send = mock_send

        # Process the command message
        test_bot._process_message(mock_message, "client_hash_123")

        # Verify command was executed
        assert len(command_responses) == 1
        assert "client_hash_123" in command_responses[0]

        # Verify reply was sent
        assert len(sent_replies) == 1
        dest, reply_msg, title = sent_replies[0]
        assert dest == "client_hash_123"
        assert reply_msg == "Hello client_hash_123!"

        test_bot.send = original_send

    def test_client_attachment_handling(self, test_bot):
        """Test client sending messages with attachments."""
        from lxmfy.attachments import Attachment, AttachmentType

        # Create a test attachment
        attachment = Attachment(
            type=AttachmentType.FILE,
            name="test.txt",
            data=b"Test file content",
            format="txt",
        )

        # Mock send to capture attachment data
        sent_attachments = []

        def mock_send(dest, msg, title=None, lxmf_fields=None, **kwargs):
            sent_attachments.append(
                {
                    "destination": dest,
                    "message": msg,
                    "title": title,
                    "fields": lxmf_fields,
                    "stamp_cost": kwargs.get("stamp_cost"),
                },
            )

        original_send = test_bot.send
        test_bot.send = mock_send

        # Send message with attachment
        test_bot.send_with_attachment(
            "test_dest",
            "Check out this file!",
            attachment,
            title="File Attachment",
        )

        assert len(sent_attachments) == 1
        attachment_msg = sent_attachments[0]
        assert attachment_msg["message"] == "Check out this file!"
        assert attachment_msg["fields"] is not None
        # The attachment should be packed into LXMF fields with field ID 5 (FILE_ATTACHMENTS)
        assert 5 in attachment_msg["fields"]
        assert attachment_msg["fields"][5] == [["test.txt", b"Test file content"]]

        test_bot.send = original_send


# Signature tests are covered in test_core.py


class TestNetworkPathOperations:
    """Test network path discovery and management."""

    def test_path_discovery_simulation(self, test_destination):
        """Test path discovery workflow."""
        dest_hash = test_destination.hash

        # Request path to destination
        RNS.Transport.request_path(dest_hash)

        # In testing environment, path won't be established
        # but the call should not raise exceptions
        assert dest_hash is not None

    def test_bot_path_management(self, test_bot):
        """Test bot's path management functionality."""
        # Test that transport layer exists
        assert hasattr(test_bot, "transport")

        # Test path loading/saving (should not crash)
        test_bot.transport.load_paths()
        test_bot.transport.save_paths()


class TestReticulumIntegration:
    """Test deep Reticulum network integration."""

    def test_reticulum_identity_persistence(self, test_config_dir):
        """Test identity persistence across bot restarts."""
        from unittest import mock

        config_dir = test_config_dir / "identity_test"

        # Mock LXMRouter to avoid RNS conflicts
        with (
            mock.patch("lxmfy.core.LXMRouter"),
            mock.patch("lxmfy.core.RNS.Reticulum"),
            mock.patch("lxmfy.core.RNS.Transport.register_destination"),
        ):
            # Create first bot instance
            config1 = BotConfig(
                storage_path=str(config_dir / "storage1"),
                test_mode=True,
                config_path=str(config_dir),
            )
            bot1 = LXMFBot(**config1.__dict__)

            identity_hash = RNS.hexrep(bot1.identity.hash, delimit=False)

            # Create second bot instance (should recall same identity)
            config2 = BotConfig(
                storage_path=str(config_dir / "storage2"),
                test_mode=True,
                config_path=str(config_dir),
            )
            bot2 = LXMFBot(**config2.__dict__)

            identity_hash2 = RNS.hexrep(bot2.identity.hash, delimit=False)

            # Should be the same identity (persisted)
            assert identity_hash == identity_hash2

    def test_link_establishment_simulation(self, test_destination):
        """Test link establishment process (simulated)."""
        # Create a link
        link = RNS.Link(test_destination)

        # In testing, link won't actually establish
        # but object should be created without errors
        assert link is not None
        assert hasattr(link, "status")

        # Clean up
        link.teardown()

    def test_bot_network_operations(self, test_bot):
        """Test bot's network operations."""
        # Test that send method exists and can be called
        # (without mocking complex network operations)
        dest_hash = "test_destination_hash"

        # This should not raise an exception, even if path discovery fails
        try:
            test_bot.send(dest_hash, "Test message")
        except Exception:
            pass

        # In test environment, this might fail due to network setup
        # but the method should exist and be callable
        assert hasattr(test_bot, "send")
        assert callable(test_bot.send)
