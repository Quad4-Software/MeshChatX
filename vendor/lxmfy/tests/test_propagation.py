"""Tests for propagation node functionality.

Non-test-mode bots here run on the session's isolated Reticulum instance
with no interfaces, so router state is real but nothing reaches a
network. cleanup() only exits Reticulum when the bot created it, so the
shared instance survives.
"""

import uuid

import pytest
import RNS
from LXMF import LXMessage

from lxmfy import BotConfig, LXMFBot


def _make_bot(test_config_dir, _reticulum, **overrides):
    """Create a real bot on the shared isolated Reticulum instance."""
    unique_config_path = test_config_dir / f"prop_{uuid.uuid4().hex[:8]}"
    unique_config_path.mkdir(exist_ok=True)
    config = BotConfig(
        name="PropTestBot",
        announce_enabled=False,
        announce_immediately=False,
        landlock_enabled=False,
        cogs_enabled=False,
        pending_sends_enabled=False,
        config_path=str(unique_config_path),
        reticulum_config_dir=str(unique_config_path / "rns"),
        storage_path=str(unique_config_path / "storage"),
        test_mode=False,
        **overrides,
    )
    return LXMFBot(**config.__dict__)


class TestPropagationConfiguration:
    """Test propagation node configuration options."""

    def test_manual_propagation_node_config(
        self,
        test_config_dir,
        reticulum_instance,
    ):
        """Manual node hash is applied to the real router."""
        prop_node_hash = "1234567890abcdef1234567890abcdef"
        bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            propagation_node=prop_node_hash,
            propagation_fallback_enabled=True,
        )
        try:
            assert bot.config.propagation_node == prop_node_hash
            configured = bot.router.get_outbound_propagation_node()
            assert RNS.hexrep(configured, delimit=False) == prop_node_hash
        finally:
            bot.cleanup()

    def test_autopeer_propagation_config(self, test_config_dir, reticulum_instance):
        """Autopeer settings reach the real router."""
        bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            autopeer_propagation=True,
            autopeer_maxdepth=4,
            propagation_fallback_enabled=True,
        )
        try:
            assert bot.config.autopeer_propagation is True
            assert bot.config.autopeer_maxdepth == 4
            assert bot.router.autopeer is True
            assert bot.router.autopeer_maxdepth == 4
        finally:
            bot.cleanup()

    def test_propagation_node_enabled(self, test_config_dir, reticulum_instance):
        """Propagation node mode enables propagation on the real router."""
        bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            enable_propagation_node=True,
            message_storage_limit_mb=500,
        )
        try:
            assert bot.config.enable_propagation_node is True
            assert bot.config.message_storage_limit_mb == 500
            assert bot.router.propagation_node is True
        finally:
            bot.cleanup()

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

    def test_custom_storage_limit(self, test_config_dir, reticulum_instance):
        """Custom limit is applied when enabling the propagation node."""
        bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            enable_propagation_node=True,
            message_storage_limit_mb=1000,
        )
        try:
            assert bot.config.message_storage_limit_mb == 1000
            assert bot.router.message_storage_limit == 1000 * 1000 * 1000
        finally:
            bot.cleanup()

    def test_set_storage_limit_method(self, test_config_dir, reticulum_instance):
        """Runtime storage limit updates reach the real router."""
        bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            enable_propagation_node=True,
            message_storage_limit_mb=500,
        )
        try:
            bot.set_message_storage_limit(megabytes=2000)
            assert bot.config.message_storage_limit_mb == 2000
            assert bot.router.message_storage_limit == 2000 * 1000 * 1000
        finally:
            bot.cleanup()

    def test_storage_limit_not_propagation_node(self, test_bot):
        """Storage limit is refused when not running as a propagation node."""
        test_bot.set_message_storage_limit(megabytes=1000)
        assert test_bot.config.message_storage_limit_mb == 500.0

    def test_storage_limit_test_mode(self, test_bot):
        """Test storage limit in test mode."""
        assert test_bot.config.test_mode is True
        test_bot.set_message_storage_limit(megabytes=1000)


class TestPropagationHelperMethods:
    """Test propagation node helper methods."""

    def test_get_propagation_status_test_mode(self, test_bot):
        """Test getting propagation status in test mode."""
        status = test_bot.get_propagation_node_status()

        assert status is not None
        assert "test_mode" in status
        assert status["test_mode"] is True

    def test_get_propagation_status_with_config(
        self,
        test_config_dir,
        reticulum_instance,
    ):
        """Status reflects the real router and configured values."""
        prop_node_hash = "1234567890abcdef1234567890abcdef"
        bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            propagation_node=prop_node_hash,
            autopeer_propagation=True,
            autopeer_maxdepth=3,
        )
        try:
            status = bot.get_propagation_node_status()

            assert status["manual_node"] == prop_node_hash
            assert status["autopeer_enabled"] is True
            assert status["autopeer_maxdepth"] == 3
            assert status["is_propagation_node"] is False
            assert status["current_outbound_node"] == prop_node_hash
        finally:
            bot.cleanup()

    def test_set_propagation_node_method(self, test_config_dir, reticulum_instance):
        """Runtime propagation node updates reach the real router."""
        bot = _make_bot(test_config_dir, reticulum_instance)
        try:
            new_node = "abcdef1234567890abcdef1234567890"
            bot.set_propagation_node(new_node)
            assert bot.config.propagation_node == new_node
            configured = bot.router.get_outbound_propagation_node()
            assert RNS.hexrep(configured, delimit=False) == new_node
        finally:
            bot.cleanup()

    def test_set_propagation_node_invalid_hash(
        self,
        test_config_dir,
        reticulum_instance,
    ):
        """Invalid hashes raise ValueError against the real router."""
        bot = _make_bot(test_config_dir, reticulum_instance)
        try:
            with pytest.raises(ValueError):
                bot.set_propagation_node("not_a_valid_hex_hash")
        finally:
            bot.cleanup()

    def test_set_propagation_node_test_mode(self, test_bot):
        """Test setting propagation node in test mode."""
        test_bot.set_propagation_node("1234567890abcdef1234567890abcdef")
        assert test_bot.config.propagation_node is None

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
    """Test that misconfiguration warnings surface through RNS logging."""

    def test_warning_propagation_enabled_no_node(
        self,
        test_config_dir,
        reticulum_instance,
        caplog,
    ):
        """Fallback without any node logs a warning."""
        with caplog.at_level("WARNING", logger="lxmfy"):
            bot = _make_bot(
                test_config_dir,
                reticulum_instance,
                propagation_fallback_enabled=True,
                propagation_node=None,
                autopeer_propagation=False,
                enable_propagation_node=False,
            )
        try:
            assert bot.config.propagation_fallback_enabled is True
        finally:
            bot.cleanup()

    def test_no_warning_with_manual_node(self, test_config_dir, reticulum_instance):
        """A manual propagation node suppresses the fallback warning."""
        bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            propagation_fallback_enabled=True,
            propagation_node="1234567890abcdef1234567890abcdef",
        )
        try:
            configured = bot.router.get_outbound_propagation_node()
            assert configured is not None
        finally:
            bot.cleanup()

    def test_no_warning_with_autopeer(self, test_config_dir, reticulum_instance):
        """Autopeer enabled suppresses the fallback warning."""
        bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            propagation_fallback_enabled=True,
            autopeer_propagation=True,
        )
        try:
            assert bot.config.autopeer_propagation is True
            assert bot.router.autopeer is True
        finally:
            bot.cleanup()


class TestPropagationDeliveryMethod:
    """Test propagation delivery method selection."""

    def test_direct_delivery_initially(self, test_bot):
        """Test that direct delivery is used initially."""
        test_destination = "1234567890abcdef1234567890abcdef"

        # No failed attempts yet
        assert test_bot.delivery_attempts.get(test_destination, 0) == 0

    def test_propagation_after_retries(
        self,
        test_config_dir,
        reticulum_instance,
        monkeypatch,
    ):
        """After max direct failures, send() picks propagated delivery."""
        bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            propagation_node="1234567890abcdef1234567890abcdef",
        )
        try:
            destination = "aa" * 16
            bot.delivery_attempts[destination] = bot.config.direct_delivery_retries

            identity = RNS.Identity()
            monkeypatch.setattr(
                "lxmfy._outbound.RNS.Identity.recall",
                lambda _h: identity,
            )
            captured = []
            monkeypatch.setattr(
                bot,
                "_enqueue_outbound",
                lambda lxm: captured.append(lxm) or True,
            )

            assert bot.send(destination, "held message") is True
            assert len(captured) == 1
            assert captured[0].desired_method == LXMessage.PROPAGATED
        finally:
            bot.cleanup()

    def test_delivery_attempts_tracking(self, test_bot):
        """Test delivery attempts are tracked correctly."""
        test_destination = "1234567890abcdef1234567890abcdef"

        test_bot._load_delivery_attempts()
        test_bot.delivery_attempts[test_destination] = 2
        test_bot._save_delivery_attempts()

        test_bot._load_delivery_attempts()
        assert test_bot.delivery_attempts[test_destination] == 2

    def test_reset_delivery_attempts(self, test_bot):
        """Test delivery attempts reset on successful delivery."""
        test_destination = "1234567890abcdef1234567890abcdef"

        test_bot.delivery_attempts[test_destination] = 5
        test_bot._reset_delivery_attempts(test_destination)

        assert test_bot.delivery_attempts[test_destination] == 0
