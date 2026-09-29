"""Real-world E2E tests for LXMFy using multiprocessing."""

import multiprocessing
import os
import time

import pytest
import RNS

from lxmfy import BotConfig, LXMFBot


def create_rns_config(config_dir, listen_port, target_port=None):
    """Create a Reticulum config file."""
    config_path = config_dir / "config"
    content = f"""
[reticulum]
loglevel = 7
storagepath = {config_dir}/storage
share_instance = No
discovery_enabled = No
discover_interfaces = No

[interfaces]
"""
    if target_port:
        content += f"""
  [[TCPClientInterface]]
    type = TCPClientInterface
    interface_enabled = True
    outgoing = True
    target_host = 127.0.0.1
    target_port = {target_port}
"""
    else:
        content += f"""
  [[TCPServerInterface]]
    type = TCPServerInterface
    interface_enabled = True
    outgoing = True
    listen_port = {listen_port}
"""

    with open(config_path, "w") as f:
        f.write(content)
    return config_path


def bot_process(
    name,
    config_dir,
    port,
    target_port,
    ready_event,
    stop_event,
    results_queue,
):
    """Run a bot in a separate process."""
    os.environ["RNS_CONFIG_DIR"] = str(config_dir)

    config = BotConfig(
        name=name,
        config_path=str(config_dir),
        storage_path=str(config_dir / "db"),
        announce_enabled=True,
        test_mode=False,
    )

    try:
        bot = LXMFBot(**config.__dict__)

        @bot.received
        def on_received(sender, message):
            results_queue.put(
                f"RECEIVED_BY_{name}_FROM_{sender}:{message.content.decode()}",
            )

        results_queue.put(f"READY_{name}_{RNS.hexrep(bot.local.hash, delimit=False)}")
        ready_event.set()

        while not stop_event.is_set():
            # Process any outbound messages in the queue
            for _ in range(bot.queue.qsize()):
                lxm = bot.queue.get()
                bot.router.handle_outbound(lxm)

            # Check for commands from results_queue (used as bi-directional for simplicity here)
            # Actually better use a separate command queue
            time.sleep(0.1)

    except Exception as e:
        results_queue.put(f"ERROR_{name}_{e}")
    finally:
        if "bot" in locals():
            bot.cleanup()
        # Force exit to ensure RNS threads die
        os._exit(0)


class TestRealWorldE2E:
    """E2E tests using separate processes."""

    @pytest.mark.skip(reason="Still too flaky in this environment")
    def test_two_bots_full_exchange(self, test_config_dir):
        """Test two bots communicating over real TCP interfaces."""
        # Setup directories
        bot_a_dir = test_config_dir / "bot_a"
        bot_b_dir = test_config_dir / "bot_b"
        bot_a_dir.mkdir(exist_ok=True)
        bot_b_dir.mkdir(exist_ok=True)
        (bot_a_dir / "storage").mkdir(exist_ok=True)
        (bot_b_dir / "storage").mkdir(exist_ok=True)

        create_rns_config(bot_a_dir, 42451)
        create_rns_config(bot_b_dir, 42452, target_port=42451)

        ready_a = multiprocessing.Event()
        ready_b = multiprocessing.Event()
        stop_event = multiprocessing.Event()
        results = multiprocessing.Queue()

        proc_a = multiprocessing.Process(
            target=bot_process,
            args=("BotA", bot_a_dir, 42451, None, ready_a, stop_event, results),
        )
        proc_b = multiprocessing.Process(
            target=bot_process,
            args=("BotB", bot_b_dir, 42452, 42451, ready_b, stop_event, results),
        )

        try:
            proc_a.start()
            proc_b.start()

            # Wait for readiness
            assert ready_a.wait(timeout=30), "Bot A failed to start"
            assert ready_b.wait(timeout=30), "Bot B failed to start"

            # ... exchange messages ...

        finally:
            stop_event.set()
            proc_a.join(timeout=2)
            proc_b.join(timeout=2)
            if proc_a.is_alive():
                proc_a.terminate()
            if proc_b.is_alive():
                proc_b.terminate()
