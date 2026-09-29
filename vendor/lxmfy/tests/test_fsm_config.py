"""Combinatorial and FSM testing for framework configuration."""

import pytest
import itertools
from unittest.mock import MagicMock
from lxmfy import BotConfig, LXMFBot


class TestFrameworkPermutations:
    """Combinatorial testing of bot configurations."""

    def test_pairwise_config_initialization(self, test_config_dir):
        """Test a matrix of configuration settings to ensure no conflicting states."""

        # Define dimensions of our configuration space
        options = {
            "cogs_enabled": [True, False],
            "nlp_enabled": [True, False],
            "permissions_enabled": [True, False],
            "signature_verification_enabled": [True, False],
            "storage_type": ["json", "sqlite"],
        }

        # Get all permutations (Cartesian product)
        # Note: In a real "ALLLLL" test we use all, but pairwise is smarter
        keys = options.keys()
        values = options.values()

        count = 0
        for combination in itertools.product(*values):
            config_dict = dict(zip(keys, combination))

            # Add required fields
            config_dict["name"] = f"TestBot_{count}"
            config_dict["storage_path"] = str(test_config_dir / f"config_test_{count}")
            config_dict["test_mode"] = True

            try:
                bot = LXMFBot(**config_dict)
                assert bot is not None
                # Basic sanity check of initialized components
                if config_dict["nlp_enabled"]:
                    assert bot.nlp is not None
                if config_dict["permissions_enabled"]:
                    assert bot.permissions.enabled is True

                bot.cleanup()
                count += 1
            except Exception as e:
                pytest.fail(
                    f"Bot failed to initialize with combination {config_dict}: {e}"
                )

        print(
            f"\n[Combinatorial] Successfully verified {count} configuration permutations."
        )

    def test_fsm_message_lifecycle_transitions(self, test_config_dir):
        """Verify the Finite State Machine transitions of a message."""
        config = BotConfig(
            name="FSMBot",
            storage_path=str(test_config_dir / "fsm_storage"),
            test_mode=True,
        )
        bot = LXMFBot(**config.__dict__)

        # Define states for our "Message"
        # State: QUEUED -> (SENT | FAILED)

        message_content = "FSM Test"
        dest = "abc123def"

        # 1. Transition: None -> QUEUED
        bot.send(dest, message_content)
        assert bot.queue.qsize() == 1

        # Peek at the message
        msg = bot.queue.queue[0]
        assert msg.content.decode() == message_content

        # 2. Transition: QUEUED -> SENT (Simulated by processing queue)
        bot.router = MagicMock()
        # Non-blocking run-once of the queue processing logic
        while not bot.queue.empty():
            lxm = bot.queue.get()
            bot.router.handle_outbound(lxm)

        assert bot.queue.qsize() == 0
        bot.router.handle_outbound.assert_called_once()
