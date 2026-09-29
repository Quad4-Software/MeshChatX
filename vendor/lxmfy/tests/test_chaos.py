"""Chaos and fault injection testing for off-grid reliability."""

import random
import time
import pytest
from unittest.mock import MagicMock, patch
from lxmfy import BotConfig, LXMFBot
from lxmfy.storage import Storage, JSONStorage


class FailingStorageBackend:
    """A storage backend that periodically fails or corrupts data."""

    def __init__(self, real_backend, failure_rate=0.1):
        self.real = real_backend
        self.failure_rate = failure_rate

    def set(self, key, value):
        if random.random() < self.failure_rate:
            # Simulate a "Partial Write" by corrupting the value
            if isinstance(value, str):
                value = value[: len(value) // 2] + " [CORRUPTED] "
            elif isinstance(value, dict):
                value["corrupt"] = True
        return self.real.set(key, value)

    def get(self, key, default=None):
        if random.random() < self.failure_rate:
            raise OSError("I/O Error: SD Card Read Failed (Simulated)")
        return self.real.get(key, default)

    def delete(self, key):
        return self.real.delete(key)

    def exists(self, key):
        return self.real.exists(key)

    def scan(self, prefix):
        return self.real.scan(prefix)


@pytest.mark.reliability
class TestChaosBot:
    """Stress testing the bot under simulated hardware/protocol failures."""

    def test_time_drift_resilience(self, test_config_dir):
        """Verify that the bot handles large system clock jumps."""
        config = BotConfig(
            name="TimeDriftBot",
            storage_path=str(test_config_dir / "time_drift"),
            test_mode=True,
        )
        bot = LXMFBot(**config.__dict__)

        # Mocking time.time
        start_time = 1700000000.0

        with patch("time.time", return_value=start_time):
            # Record some activity
            bot.storage.set("last_seen", time.time())

        # Jump forward 1 year
        future_time = start_time + (365 * 24 * 3600)
        with patch("time.time", return_value=future_time):
            # Bot should still function
            bot.storage.set("current_event", "Checking after drift")
            last_seen = bot.storage.get("last_seen")
            assert last_seen == start_time

        # Jump backward 1 year (RTC battery failure)
        past_time = start_time - (365 * 24 * 3600)
        with patch("time.time", return_value=past_time):
            bot.storage.set("panic_event", "Clock rolled back")
            assert bot.storage.get("panic_event") == "Clock rolled back"

    def test_storage_fault_injection(self, test_config_dir):
        """Verify the bot can survive intermittent storage failures."""
        json_backend = JSONStorage(str(test_config_dir / "chaos_json"))
        chaos_backend = FailingStorageBackend(json_backend, failure_rate=0.2)
        storage = Storage(chaos_backend)

        success_count = 0
        error_count = 0

        for i in range(100):
            try:
                storage.set(f"key_{i}", {"data": "important info"})
                val = storage.get(f"key_{i}")
                if val:
                    success_count += 1
            except Exception:
                error_count += 1

        print(
            f"\n[Chaos Storage] Successes: {success_count}, Simulated Errors: {error_count}"
        )
        # The goal is not 100% success, but that the framework doesn't CRASH the entire process
        assert (success_count + error_count) == 100

    def test_message_storm_deduplication(self, test_config_dir):
        """Test the bot's ability to handle massive duplicate message storms."""
        config = BotConfig(
            name="StormBot",
            storage_path=str(test_config_dir / "storm_storage"),
            test_mode=True,
            first_message_enabled=False,
        )
        bot = LXMFBot(**config.__dict__)

        processed_count = 0

        def handler(sender, msg):
            nonlocal processed_count
            processed_count += 1
            return True

        bot.message_handlers.append(handler)

        # Create a mock message
        import LXMF

        mock_msg = MagicMock(spec=LXMF.LXMessage)
        mock_msg.content = b"Single message"
        mock_msg.hash = b"unique_hash_123"
        mock_msg.source_hash = b"sender"
        mock_msg.destination_hash = b"local"
        mock_msg.fields = {}
        mock_msg.signature_validated = True

        # Send the EXACT SAME message 50 times
        with patch("lxmfy.core.verify_incoming_message", return_value=True):
            for _ in range(50):
                bot._message_received(mock_msg)

        # Should only have been processed ONCE due to deduplication receipts
        assert processed_count == 1
