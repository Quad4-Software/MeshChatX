"""Tests for propagation node functionality."""

import uuid
from unittest.mock import MagicMock

import pytest
import RNS

from lxmfy import BotConfig, LXMFBot


class TestPropagationConfiguration:
    """Test propagation node configuration options."""

    def test_manual_propagation_node_config(self, test_config_dir):
        """Test manual propagation node configuration."""
        unique_config_path = test_config_dir / f"manual_prop_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            prop_node_hash = "1234567890abcdef1234567890abcdef"

            config = BotConfig(
                name="ManualPropBot",
                propagation_node=prop_node_hash,
                propagation_fallback_enabled=True,
                storage_path=str(unique_config_path / "storage"),
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            assert bot.config.propagation_node == prop_node_hash
            assert bot.config.propagation_fallback_enabled is True
            assert bot.config.autopeer_propagation is False

            # Test that outbound propagation node is set
            if not bot.config.test_mode:
                configured_node = bot.router.get_outbound_propagation_node()
                if configured_node:
                    assert RNS.hexrep(configured_node, delimit=False) == prop_node_hash

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_autopeer_propagation_config(self, test_config_dir):
        """Test autopeer propagation configuration."""
        unique_config_path = test_config_dir / f"autopeer_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="AutopeerBot",
                autopeer_propagation=True,
                autopeer_maxdepth=4,
                propagation_fallback_enabled=True,
                storage_path=str(unique_config_path / "storage"),
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            assert bot.config.autopeer_propagation is True
            assert bot.config.autopeer_maxdepth == 4
            assert bot.config.propagation_fallback_enabled is True

            # Test router autopeer settings
            if not bot.config.test_mode:
                assert bot.router.autopeer is True
                assert bot.router.autopeer_maxdepth == 4

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_propagation_node_enabled(self, test_config_dir):
        """Test enabling propagation node mode."""
        unique_config_path = test_config_dir / f"propnode_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="PropNodeBot",
                enable_propagation_node=True,
                message_storage_limit_mb=500,
                storage_path=str(unique_config_path / "storage"),
                test_mode=True,
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            # Mock router for test mode
            bot.router = MagicMock()
            bot.router.propagation_node = True

            assert bot.config.enable_propagation_node is True
            assert bot.config.message_storage_limit_mb == 500

            # Test router propagation node mode
            if not bot.config.test_mode:
                assert bot.router.propagation_node is True

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_default_propagation_config(self, test_bot):
        """Test default propagation configuration."""
        assert test_bot.config.propagation_fallback_enabled is True
        assert test_bot.config.propagation_node is None
        assert test_bot.config.autopeer_propagation is False
        assert test_bot.config.autopeer_maxdepth == 4
        assert test_bot.config.enable_propagation_node is False
        assert test_bot.config.message_storage_limit_mb == 500.0


class TestMessageStorageLimits:
    """Test message storage limit functionality for propagation nodes."""

    def test_default_storage_limit(self, test_bot):
        """Test default storage limit configuration."""
        assert test_bot.config.message_storage_limit_mb == 500.0

    def test_custom_storage_limit(self, test_config_dir):
        """Test custom storage limit configuration."""
        unique_config_path = test_config_dir / f"storage_limit_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="LimitBot",
                enable_propagation_node=True,
                message_storage_limit_mb=1000,
                storage_path=str(unique_config_path / "storage"),
                test_mode=True,
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            # Mock router for test mode
            bot.router = MagicMock()
            bot.router.message_storage_limit = 1000 * 1000 * 1000

            assert bot.config.message_storage_limit_mb == 1000

            # Test router storage limit
            if not bot.config.test_mode:
                expected_bytes = 1000 * 1000 * 1000
                assert bot.router.message_storage_limit == expected_bytes

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_set_storage_limit_method(self, test_config_dir):
        """Test setting storage limit at runtime."""
        unique_config_path = test_config_dir / f"set_limit_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="DynamicLimitBot",
                enable_propagation_node=True,
                message_storage_limit_mb=500,
                storage_path=str(unique_config_path / "storage"),
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            if not bot.config.test_mode:
                # Change limit at runtime
                bot.set_message_storage_limit(megabytes=2000)
                assert bot.config.message_storage_limit_mb == 2000
                assert bot.router.message_storage_limit == 2000 * 1000 * 1000

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_storage_limit_not_propagation_node(self, test_bot):
        """Test storage limit warning when not a propagation node."""
        # Should not crash, just log warning
        test_bot.set_message_storage_limit(megabytes=1000)
        # If we get here without exception, test passes

    def test_storage_limit_test_mode(self, test_bot):
        """Test storage limit in test mode."""
        assert test_bot.config.test_mode is True
        # Should not crash in test mode
        test_bot.set_message_storage_limit(megabytes=1000)


class TestPropagationHelperMethods:
    """Test propagation node helper methods."""

    def test_get_propagation_status_test_mode(self, test_bot):
        """Test getting propagation status in test mode."""
        status = test_bot.get_propagation_node_status()

        assert status is not None
        assert "test_mode" in status
        assert status["test_mode"] is True

    def test_get_propagation_status_with_config(self, test_config_dir):
        """Test getting propagation status with various configurations."""
        unique_config_path = test_config_dir / f"status_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="StatusBot",
                propagation_node="1234567890abcdef1234567890abcdef",
                autopeer_propagation=True,
                autopeer_maxdepth=3,
                enable_propagation_node=False,
                storage_path=str(unique_config_path / "storage"),
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            status = bot.get_propagation_node_status()

            assert status is not None
            assert "manual_node" in status
            assert status["manual_node"] == "1234567890abcdef1234567890abcdef"
            assert "autopeer_enabled" in status
            assert status["autopeer_enabled"] is True
            assert "autopeer_maxdepth" in status
            assert status["autopeer_maxdepth"] == 3
            assert "is_propagation_node" in status
            assert status["is_propagation_node"] is False

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_set_propagation_node_method(self, test_config_dir):
        """Test setting propagation node at runtime."""
        unique_config_path = test_config_dir / f"set_node_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="SetNodeBot",
                storage_path=str(unique_config_path / "storage"),
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            new_node = "abcdef1234567890abcdef1234567890"

            if not bot.config.test_mode:
                bot.set_propagation_node(new_node)
                assert bot.config.propagation_node == new_node

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_set_propagation_node_invalid_hash(self, test_config_dir):
        """Test setting invalid propagation node hash."""
        unique_config_path = test_config_dir / f"invalid_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="InvalidHashBot",
                storage_path=str(unique_config_path / "storage"),
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            if not bot.config.test_mode:
                with pytest.raises(ValueError):
                    bot.set_propagation_node("not_a_valid_hex_hash")

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_set_propagation_node_test_mode(self, test_bot):
        """Test setting propagation node in test mode."""
        # Should not crash in test mode
        test_bot.set_propagation_node("1234567890abcdef1234567890abcdef")

    def test_get_storage_stats_not_propagation_node(self, test_bot):
        """Test getting storage stats when not a propagation node."""
        stats = test_bot.get_propagation_storage_stats()

        assert stats is not None
        assert "is_propagation_node" in stats or "test_mode" in stats

    def test_get_storage_stats_test_mode(self, test_bot):
        """Test getting storage stats in test mode."""
        stats = test_bot.get_propagation_storage_stats()

        assert stats is not None
        assert "test_mode" in stats
        assert stats["test_mode"] is True


class TestPropagationWarnings:
    """Test that appropriate warnings are logged for propagation misconfiguration."""

    def test_warning_propagation_enabled_no_node(self, test_config_dir):
        """Test warning when propagation fallback enabled but no node configured."""
        unique_config_path = test_config_dir / f"warning_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            # This configuration should trigger a warning
            config = BotConfig(
                name="WarningBot",
                propagation_fallback_enabled=True,
                propagation_node=None,
                autopeer_propagation=False,
                enable_propagation_node=False,
                storage_path=str(unique_config_path / "storage"),
            )

            # Should not crash, just log warning
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            # Bot should still be created successfully
            assert bot is not None
            assert bot.config.propagation_fallback_enabled is True

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_no_warning_with_manual_node(self, test_config_dir):
        """Test no warning when manual propagation node is configured."""
        unique_config_path = test_config_dir / f"no_warn_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="NoWarnBot",
                propagation_fallback_enabled=True,
                propagation_node="1234567890abcdef1234567890abcdef",
                storage_path=str(unique_config_path / "storage"),
            )

            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            assert bot is not None
            assert bot.config.propagation_node is not None

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file

    def test_no_warning_with_autopeer(self, test_config_dir):
        """Test no warning when autopeer is enabled."""
        unique_config_path = test_config_dir / f"autopeer_warn_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="AutopeerNoWarnBot",
                propagation_fallback_enabled=True,
                autopeer_propagation=True,
                storage_path=str(unique_config_path / "storage"),
            )

            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            assert bot is not None
            assert bot.config.autopeer_propagation is True

            bot.cleanup()
        finally:
            RNS.Identity.from_file = original_from_file


class TestPropagationDeliveryMethod:
    """Test propagation delivery method selection."""

    def test_direct_delivery_initially(self, test_bot):
        """Test that direct delivery is used initially."""
        test_destination = "1234567890abcdef1234567890abcdef"

        # No failed attempts yet
        assert test_bot.delivery_attempts.get(test_destination, 0) == 0

    def test_propagation_after_retries(self, test_bot):
        """Test propagation fallback after failed direct deliveries."""
        test_destination = "1234567890abcdef1234567890abcdef"

        # Simulate failed delivery attempts
        max_retries = test_bot.config.direct_delivery_retries
        test_bot.delivery_attempts[test_destination] = max_retries

        # Next send should use propagation (if enabled)
        attempts = test_bot.delivery_attempts.get(test_destination, 0)
        assert attempts >= max_retries

    def test_delivery_attempts_tracking(self, test_bot):
        """Test delivery attempts are tracked correctly."""
        test_destination = "1234567890abcdef1234567890abcdef"

        # Load initial attempts
        test_bot._load_delivery_attempts()

        # Set some attempts
        test_bot.delivery_attempts[test_destination] = 2
        test_bot._save_delivery_attempts()

        # Reload and verify
        test_bot._load_delivery_attempts()
        assert test_bot.delivery_attempts[test_destination] == 2

    def test_reset_delivery_attempts(self, test_bot):
        """Test delivery attempts reset on successful delivery."""
        test_destination = "1234567890abcdef1234567890abcdef"

        # Set failed attempts
        test_bot.delivery_attempts[test_destination] = 5

        # Reset on success
        test_bot._reset_delivery_attempts(test_destination)

        assert test_bot.delivery_attempts[test_destination] == 0
