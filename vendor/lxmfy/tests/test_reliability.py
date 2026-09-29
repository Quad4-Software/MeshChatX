"""Reliability and crash recovery tests for LXMFy."""

import os
import pytest
import time
from lxmfy import BotConfig, LXMFBot
from unittest.mock import MagicMock


@pytest.mark.reliability
class TestReliability:
    """Long-term reliability and crash recovery tests."""

    def test_state_persistence_after_crash(self, test_config_dir):
        """Simulate a crash and verify state recovery from storage."""
        storage_path = str(test_config_dir / "recovery_storage")

        # 1. Setup bot and save some state
        config1 = BotConfig(
            name="PersistentBot", storage_path=storage_path, test_mode=True
        )
        bot1 = LXMFBot(**config1.__dict__)
        bot1.storage.set("important_state", {"data": 123})
        bot1.storage.set("user_pref:abc", "value1")

        # 2. Simulate "crash" by deleting the bot instance without graceful shutdown
        del bot1

        # 3. Restart bot with same storage
        config2 = BotConfig(
            name="PersistentBot", storage_path=storage_path, test_mode=True
        )
        bot2 = LXMFBot(**config2.__dict__)

        # 4. Verify state is recovered
        assert bot2.storage.get("important_state") == {"data": 123}
        assert bot2.storage.get("user_pref:abc") == "value1"

    def test_corrupted_storage_recovery(self, test_config_dir):
        """Verify that the bot can handle/recover from corrupted storage files."""
        storage_path = test_config_dir / "corrupt_storage"
        storage_path.mkdir(parents=True, exist_ok=True)

        # Create a corrupted JSON file in storage
        corrupt_file = storage_path / "corrupt_data.json"
        with open(corrupt_file, "w") as f:
            f.write("{ invalid json...")

        config = BotConfig(
            name="CorruptBot", storage_path=str(storage_path), test_mode=True
        )
        # Initialization should not crash despite corrupted file
        bot = LXMFBot(**config.__dict__)
        assert bot.storage is not None

        # Attempting to read corrupted data should return None or handle gracefully
        # Depending on how Storage is implemented
        val = bot.storage.get("corrupt_data")
        assert val is None or isinstance(val, dict)  # Should not raise Exception

    def test_long_running_message_processing(self, test_config_dir):
        """Simulate a long-running bot processing messages continuously."""
        config = BotConfig(
            name="StableBot",
            storage_path=str(test_config_dir / "stable_storage"),
            test_mode=True,
        )
        bot = LXMFBot(**config.__dict__)
        bot.router = MagicMock()

        processed_count = 0

        def handler(sender, msg):
            nonlocal processed_count
            processed_count += 1
            return True

        bot.message_handlers.append(handler)

        import LXMF

        # Process messages in a loop for a short while
        # In a real reliability test this would run for hours
        start_time = time.time()
        while time.time() - start_time < 2:  # 2 seconds of intense processing
            mock_msg = MagicMock(spec=LXMF.LXMessage)
            mock_msg.content = b"test content"
            mock_msg.hash = os.urandom(16)
            mock_msg.source_hash = b"source"
            mock_msg.destination_hash = (
                bot.local.hash if hasattr(bot.local, "hash") else b"local"
            )
            mock_msg.fields = {}
            mock_msg.signature_validated = True
            bot._message_received(mock_msg)

        assert processed_count > 0
        print(f"Processed {processed_count} messages reliably.")

    def test_concurrent_storage_access(self, test_config_dir):
        """Test storage reliability under concurrent access from multiple threads."""
        from threading import Thread

        config = BotConfig(
            name="ConcurrentBot",
            storage_path=str(test_config_dir / "concurrent_storage"),
            test_mode=True,
        )
        bot = LXMFBot(**config.__dict__)

        errors = []

        def worker(worker_id):
            try:
                for i in range(100):
                    key = f"thread_{worker_id}_key_{i}"
                    bot.storage.set(key, {"val": i})
                    val = bot.storage.get(key)
                    if val["val"] != i:
                        errors.append(f"Data mismatch in worker {worker_id}")
            except Exception as e:
                errors.append(f"Exception in worker {worker_id}: {e}")

        threads = [Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent storage errors: {errors}"
