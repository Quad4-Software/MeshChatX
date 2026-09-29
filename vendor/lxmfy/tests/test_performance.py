"""Performance and stress tests for LXMFy."""

import os
import time
from unittest.mock import MagicMock, patch

import LXMF
import psutil
import pytest
import RNS

from lxmfy import BotConfig, LXMFBot
from lxmfy.middleware import MiddlewareType


def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


class TestPerformance:
    """Stress tests for LXMFy."""

    @pytest.fixture
    def stress_bot(self, test_config_dir):
        """Create a bot configured for stress testing."""
        config = BotConfig(
            name="StressBot",
            test_mode=True,
            storage_path=str(test_config_dir / "stress_storage"),
            signature_verification_enabled=True,
            require_message_signatures=False,
            rate_limit=10000,  # High limit for testing
            cooldown=1,
            cogs_enabled=False,
            first_message_enabled=False,  # Disable first message handling for performance tests
        )
        bot = LXMFBot(**config.__dict__)
        # Mock some components to avoid RNS overhead in performance tests
        bot.router = MagicMock()
        bot.local = MagicMock()
        bot.local.hash = b"local_identity_hash"
        return bot

    def test_message_processing_flood(self, stress_bot):
        """Flood the bot with messages to test processing throughput."""
        message_count = 10000  # Increased to 10k
        messages = []

        processed_count = 0

        def count_handler(sender, msg):
            nonlocal processed_count
            processed_count += 1
            return True

        stress_bot.message_handlers.append(count_handler)

        # Pre-generate messages
        for i in range(message_count):
            mock_msg = MagicMock(spec=LXMF.LXMessage)
            mock_msg.content = f"Stress test message {i}".encode()
            mock_msg.title = f"Title {i}".encode()
            mock_msg.source_hash = b"source_" + str(i % 10).encode().rjust(10, b"0")
            mock_msg.destination_hash = b"local_identity_hash"
            mock_msg.hash = b"hash_" + os.urandom(16)
            mock_msg.fields = {}
            mock_msg.signature_validated = True
            messages.append(mock_msg)

        start_mem = get_memory_usage()
        start_time = time.time()

        # Simulate receiving messages
        for msg in messages:
            stress_bot._message_received(msg)

        duration = time.time() - start_time
        end_mem = get_memory_usage()

        print(f"\n[Performance] Processed {message_count} messages in {duration:.4f}s")
        print(f"[Performance] Throughput: {message_count / duration:.2f} msg/s")
        print(f"[Performance] Memory delta: {end_mem - start_mem:.2f} MB")

        # Verify all messages were processed
        assert processed_count == message_count
        assert duration < 2.0  # Should be very fast in test mode

    def test_signature_verification_stress(self, stress_bot):
        """Test performance of signature verification logic."""
        sig_manager = stress_bot.signature_manager
        identity = RNS.Identity()
        sender_hash = RNS.hexrep(identity.hash, delimit=False)

        # Pre-generate a signed message
        mock_msg = MagicMock(spec=LXMF.LXMessage)
        mock_msg.content = b"Performance test content"
        mock_msg.title = b"Performance test title"
        mock_msg.source_hash = identity.hash
        mock_msg.destination_hash = b"dest"
        mock_msg.fields = {}
        mock_msg.timestamp = int(time.time())

        # Our signature logic uses _canonicalize_message
        signature = sig_manager.sign_message(mock_msg, identity)

        iteration_count = 5000  # Increased to 5k
        start_time = time.time()

        # Patch where it is USED, which is lxmfy.signatures
        with patch("lxmfy.signatures.RNS.Identity.recall", return_value=identity):
            for _ in range(iteration_count):
                sig_manager.verify_message_signature(mock_msg, signature, sender_hash)

        duration = time.time() - start_time
        print(
            f"\n[Performance] Verified {iteration_count} signatures in {duration:.4f}s",
        )
        print(
            f"[Performance] Avg verification time: {(duration / iteration_count) * 1000:.4f}ms",
        )

        assert duration < 5.0

    def test_storage_extreme_load(self, stress_bot):
        """Test storage performance under heavy load."""
        storage = stress_bot.storage
        record_count = 10000  # Increased to 10k

        start_mem = get_memory_usage()
        start_time = time.time()

        # Write load
        for i in range(record_count):
            storage.set(f"key_{i}", {"data": "value" * 10, "index": i})

        write_duration = time.time() - start_time

        # Read load
        read_start = time.time()
        for i in range(record_count):
            storage.get(f"key_{i}")
        read_duration = time.time() - read_start

        end_mem = get_memory_usage()

        print(f"\n[Performance] Storage {record_count} records:")
        print(
            f"[Performance] Write time: {write_duration:.4f}s ({record_count / write_duration:.2f} ops/s)",
        )
        print(
            f"[Performance] Read time: {read_duration:.4f}s ({record_count / read_duration:.2f} ops/s)",
        )
        print(f"[Performance] Memory delta: {end_mem - start_mem:.2f} MB")

        assert write_duration < 10.0
        assert read_duration < 5.0

    def test_heavy_middleware_load(self, stress_bot):
        """Test impact of multiple middlewares on message processing."""
        # Add multiple dummy middlewares
        for i in range(10):

            def make_middleware(idx):
                def mw(ctx):
                    ctx.data[f"mw_{idx}"] = True
                    return ctx

                return mw

            stress_bot.middleware.register(MiddlewareType.PRE_EVENT, make_middleware(i))

        message_count = 500

        processed_count = 0

        def count_handler(sender, msg):
            nonlocal processed_count
            processed_count += 1
            return True

        stress_bot.message_handlers.append(count_handler)

        start_time = time.time()
        for i in range(message_count):
            mock_msg = MagicMock(spec=LXMF.LXMessage)
            mock_msg.content = b"middleware test"
            mock_msg.source_hash = b"source"
            mock_msg.destination_hash = b"local"
            mock_msg.hash = b"hash_" + str(i).encode()
            mock_msg.fields = {}
            mock_msg.signature_validated = True
            stress_bot._message_received(mock_msg)

        duration = time.time() - start_time
        print(
            f"\n[Performance] Middleware (10 layers) x {message_count} msgs: {duration:.4f}s",
        )

        assert processed_count == message_count
        assert duration < 2.0

    def test_memory_stability_long_run(self, stress_bot):
        """Run bot for a period to check for memory leaks."""
        duration_seconds = 5
        start_time = time.time()
        start_mem = get_memory_usage()

        message_count = 0
        mock_msg = MagicMock(spec=LXMF.LXMessage)
        mock_msg.content = b"stability test"
        mock_msg.source_hash = b"source"
        mock_msg.destination_hash = b"local"
        mock_msg.fields = {}
        mock_msg.signature_validated = True

        while time.time() - start_time < duration_seconds:
            mock_msg.hash = os.urandom(16)
            stress_bot._message_received(mock_msg)
            message_count += 1

        end_mem = get_memory_usage()
        print("\n[Performance] Stability run (5s):")
        print(f"[Performance] Total messages: {message_count}")
        print(f"[Performance] Start memory: {start_mem:.2f} MB")
        print(f"[Performance] End memory: {end_mem:.2f} MB")
        print(f"[Performance] Memory delta: {end_mem - start_mem:.2f} MB")

        # Stability check: Memory shouldn't grow boundlessly
        # We allow some growth for caches but not massive
        assert (end_mem - start_mem) < 10.0
