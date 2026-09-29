"""Leak and resource tests for LXMFy."""

import threading
import psutil
import pytest
import gc
from lxmfy import BotConfig, LXMFBot
from unittest.mock import MagicMock


def get_open_fds():
    """Get count of open file descriptors."""
    return psutil.Process().num_fds()


def get_thread_count():
    """Get count of active threads."""
    return threading.active_count()


def get_memory_usage():
    """Get current memory usage in bytes."""
    return psutil.Process().memory_info().rss


@pytest.mark.reliability
class TestLeaks:
    """Test for resource leaks in LXMFy."""

    def test_memory_leak_intent_classifier(self):
        """Check for memory leaks in IntentClassifier training/prediction."""
        from lxmfy.nlp import IntentClassifier

        gc.collect()
        start_mem = get_memory_usage()

        # Run many iterations
        for i in range(100):
            nlp = IntentClassifier()
            nlp.add_intent(f"intent_{i}", [f"example text {j}" for j in range(10)])
            for _ in range(50):
                nlp.predict("some random text")
            del nlp
            if i % 10 == 0:
                gc.collect()

        gc.collect()
        end_mem = get_memory_usage()

        # Allow some growth for fragmentation/internal caches but not massive
        # 5MB is a very generous threshold for this test
        assert (end_mem - start_mem) < 5 * 1024 * 1024

    def test_fd_leak_bot_restarts(self, test_config_dir):
        """Check for file descriptor leaks when repeatedly creating/destroying bots."""
        gc.collect()
        start_fds = get_open_fds()

        for i in range(20):
            config = BotConfig(
                name=f"LeakBot_{i}",
                storage_path=str(test_config_dir / f"leak_storage_{i}"),
                test_mode=True,
            )
            bot = LXMFBot(**config.__dict__)
            bot.router = MagicMock()  # Avoid RNS starting real background threads
            # Do some operations
            bot.storage.set("test", "data")
            bot.storage.get("test")
            # Shutdown/Cleanup
            bot.cleanup()
            del bot
            gc.collect()

        end_fds = get_open_fds()

        # We allow a small increase if some RNS/internal things don't close immediately,
        # but it shouldn't be proportional to iterations.
        assert end_fds <= start_fds + 5

    def test_thread_leak_bot_creation(self, test_config_dir):
        """Check for thread leaks when creating bots."""
        gc.collect()
        start_threads = get_thread_count()

        for i in range(10):
            config = BotConfig(
                name=f"ThreadBot_{i}",
                storage_path=str(test_config_dir / f"thread_storage_{i}"),
                test_mode=True,
            )
            bot = LXMFBot(**config.__dict__)
            bot.router = MagicMock()
            bot.cleanup()
            del bot
            gc.collect()

        end_threads = get_thread_count()

        # Threads should return to baseline
        assert end_threads <= start_threads + 2
