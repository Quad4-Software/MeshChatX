"""Tests for LXMF router control wrappers.

Non-test-mode bots run on the session's isolated Reticulum instance, so
router state changes are real but nothing reaches a network.
"""

import time
import uuid

import pytest
import RNS

from lxmfy import BotConfig, LXMFBot
from lxmfy.validation import destination_bytes


def _wait_for(predicate, timeout=5.0):
    """Poll until predicate() is truthy or the timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def _make_bot(test_config_dir, reticulum_instance, **overrides):
    """Create a real bot on the shared isolated Reticulum instance."""
    unique_config_path = test_config_dir / f"ctrl_{uuid.uuid4().hex[:8]}"
    unique_config_path.mkdir(exist_ok=True)
    config = BotConfig(
        name="ControlTestBot",
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


@pytest.fixture
def bot(test_config_dir, reticulum_instance):
    return _make_bot(test_config_dir, reticulum_instance)


@pytest.fixture
def test_bot():
    return LXMFBot(name="TestBot", test_mode=True)


@pytest.fixture
def some_dest():
    return RNS.hexrep(RNS.Identity().hash, delimit=False)


@pytest.fixture
def some_dest_bytes(some_dest):
    return bytes.fromhex(some_dest)


class TestDestinationBytes:
    def test_valid_hash(self, some_dest, some_dest_bytes):
        assert destination_bytes(some_dest) == some_dest_bytes

    def test_invalid_hex(self):
        assert destination_bytes("not-hex") is None

    def test_wrong_length(self):
        assert destination_bytes("abcd") is None

    def test_non_string(self):
        assert destination_bytes(None) is None
        assert destination_bytes(b"1234") is None


class TestIgnoreList:
    def test_ignore_and_unignore(self, bot, some_dest, some_dest_bytes):
        assert bot.ignore_destination(some_dest) is True
        assert some_dest_bytes in bot.router.ignored_list
        assert bot.is_ignored(some_dest) is True

        assert bot.unignore_destination(some_dest) is True
        assert bot.is_ignored(some_dest) is False

    def test_unignore_absent(self, bot, some_dest):
        assert bot.unignore_destination(some_dest) is True
        assert bot.is_ignored(some_dest) is False

    def test_invalid_hash(self, bot):
        assert bot.ignore_destination("nope") is False
        assert bot.is_ignored("nope") is False
        assert bot.unignore_destination("nope") is False

    def test_test_mode(self, test_bot, some_dest):
        assert test_bot.ignore_destination(some_dest) is False
        assert test_bot.is_ignored(some_dest) is False


class TestAllowList:
    def test_allow_and_disallow(self, bot, some_dest, some_dest_bytes):
        assert bot.allow_destination(some_dest) is True
        assert some_dest_bytes in bot.router.allowed_list

        assert bot.disallow_destination(some_dest) is True
        assert some_dest_bytes not in bot.router.allowed_list

    def test_disallow_absent_returns_false(self, bot, some_dest):
        assert bot.disallow_destination(some_dest) is False

    def test_invalid_hash(self, bot):
        assert bot.allow_destination("zz") is False
        assert bot.disallow_destination("zz") is False


class TestPrioritisedList:
    def test_prioritise_and_unprioritise(self, bot, some_dest, some_dest_bytes):
        assert bot.prioritise_destination(some_dest) is True
        assert some_dest_bytes in bot.router.prioritised_list

        assert bot.unprioritise_destination(some_dest) is True
        assert some_dest_bytes not in bot.router.prioritised_list

    def test_unprioritise_absent_returns_false(self, bot, some_dest):
        assert bot.unprioritise_destination(some_dest) is False

    def test_invalid_hash(self, bot):
        assert bot.prioritise_destination("0x") is False
        assert bot.unprioritise_destination("0x") is False


class TestStampControls:
    def test_set_inbound_stamp_cost(self, bot):
        assert bot.set_inbound_stamp_cost(8) is True
        assert bot.local.stamp_cost == 8

        assert bot.set_inbound_stamp_cost(None) is True
        assert bot.local.stamp_cost is None

    def test_stamp_cost_out_of_range(self, bot):
        assert bot.set_inbound_stamp_cost(255) is False
        assert bot.local.stamp_cost != 255

    def test_enforce_and_ignore_stamps(self, bot):
        assert bot.ignore_stamps() is True
        assert bot.router._enforce_stamps is False
        assert bot.enforce_stamps() is True
        assert bot.router._enforce_stamps is True

    def test_test_mode(self, test_bot):
        assert test_bot.set_inbound_stamp_cost(8) is False
        assert test_bot.enforce_stamps() is False


class TestTickets:
    def test_generate_ticket(self, bot, some_dest, some_dest_bytes):
        result = bot.generate_ticket(some_dest)
        assert result is not None
        assert isinstance(result["expires"], float)
        assert isinstance(result["ticket"], bytes)
        assert (
            result["ticket"] in bot.router.available_tickets["inbound"][some_dest_bytes]
        )

    def test_generate_ticket_reuses_valid(self, bot, some_dest):
        first = bot.generate_ticket(some_dest)
        second = bot.generate_ticket(some_dest)
        assert second is not None
        assert second["ticket"] == first["ticket"]

    def test_get_inbound_tickets(self, bot, some_dest):
        assert bot.get_inbound_tickets(some_dest) is None
        generated = bot.generate_ticket(some_dest)
        tickets = bot.get_inbound_tickets(some_dest)
        assert generated["ticket"] in tickets

    def test_outbound_ticket_queries(self, bot, some_dest):
        assert bot.get_outbound_ticket(some_dest) is None
        assert bot.get_outbound_ticket_expiry(some_dest) is None

    def test_invalid_hash(self, bot):
        assert bot.generate_ticket("bad") is None
        assert bot.get_inbound_tickets("bad") is None
        assert bot.get_outbound_ticket("bad") is None


class TestOutboundControls:
    def test_delivery_link_available(self, bot, some_dest):
        assert bot.delivery_link_available(some_dest) is False
        assert bot.delivery_link_available("bad") is False

    def test_outbound_queue_empty(self, bot):
        assert bot.outbound_queue() == []

    def test_outbound_queue_and_cancel(self, bot):
        identity = RNS.Identity()
        dest_hex = RNS.hexrep(
            RNS.Destination(
                identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "lxmf",
                "delivery",
            ).hash,
            delimit=False,
        )
        RNS.Identity.remember(
            packet_hash=None,
            destination_hash=bytes.fromhex(dest_hex),
            public_key=identity.get_public_key(),
        )

        assert bot.send(dest_hex, "queued message") is True
        # run() normally drains the internal queue into the router
        while not bot.queue.empty():
            bot.router.handle_outbound(bot.queue.get(block=False))
        assert _wait_for(lambda: len(bot.outbound_queue()) == 1)
        entry = bot.outbound_queue()[0]
        assert entry["destination"] == dest_hex
        assert entry["message_id"]
        assert entry["hash"]

        progress = bot.get_outbound_progress(entry["hash"])
        assert progress is not None

        assert bot.cancel_outbound(entry["message_id"]) is True
        assert _wait_for(lambda: bot.outbound_queue() == [])
        assert bot.get_outbound_progress(entry["hash"]) is None

    def test_get_outbound_progress_unknown(self, bot):
        assert bot.get_outbound_progress("ff" * 32) is None
        assert bot.get_outbound_progress("bad") is None

    def test_cancel_outbound_invalid(self, bot):
        assert bot.cancel_outbound("bad") is False
        assert bot.cancel_outbound(None) is False

    def test_get_outbound_stamp_cost(self, bot, some_dest):
        assert bot.get_outbound_stamp_cost(some_dest) is None
        assert bot.get_outbound_stamp_cost("bad") is None

    def test_test_mode(self, test_bot, some_dest):
        assert test_bot.outbound_queue() == []
        assert test_bot.delivery_link_available(some_dest) is False
        assert test_bot.get_outbound_progress("ff" * 32) is None


class TestPropagationSync:
    def test_sync_without_node(self, bot):
        assert bot.sync_propagation_node() is False

    def test_sync_with_node_no_path(self, bot, some_dest):
        bot.set_propagation_node(some_dest)
        assert bot.sync_propagation_node() is True
        assert bot.router.propagation_transfer_state is not None

    def test_cancel_sync(self, bot):
        assert bot.cancel_propagation_sync() is True

    def test_get_propagation_stats_not_a_node(self, bot):
        assert bot.get_propagation_stats() is None

    def test_get_propagation_stats_as_node(self, test_config_dir, reticulum_instance):
        node_bot = _make_bot(
            test_config_dir,
            reticulum_instance,
            enable_propagation_node=True,
        )
        stats = node_bot.get_propagation_stats()
        assert stats is not None
        assert isinstance(stats, dict)

    def test_set_retain_on_node(self, bot):
        assert bot.set_retain_on_node(True) is True
        assert bot.router.retain_synced_on_node is True
        assert bot.set_retain_on_node(False) is True
        assert bot.router.retain_synced_on_node is False

    def test_announce_propagation_node_requires_propagation(self, bot):
        assert bot.announce_propagation_node() is False

    def test_control_list(self, bot, some_dest, some_dest_bytes):
        assert bot.allow_control_identity(some_dest) is True
        assert some_dest_bytes in bot.router.control_allowed_list

        assert bot.disallow_control_identity(some_dest) is True
        assert some_dest_bytes not in bot.router.control_allowed_list
        assert bot.disallow_control_identity(some_dest) is False

    def test_control_list_invalid(self, bot):
        assert bot.allow_control_identity("xx") is False
        assert bot.disallow_control_identity("xx") is False

    def test_test_mode(self, test_bot, some_dest):
        assert test_bot.sync_propagation_node() is False
        assert test_bot.cancel_propagation_sync() is False
        assert test_bot.get_propagation_stats() is None
        assert test_bot.set_retain_on_node(True) is False
        assert test_bot.announce_propagation_node() is False
        assert test_bot.allow_control_identity(some_dest) is False


class TestIngestUri:
    def test_invalid_uri(self, bot):
        assert bot.ingest_lxm_uri("not a uri") is False
        assert bot.ingest_lxm_uri("lxm://AAA") is False
        assert bot.ingest_lxm_uri(None) is False

    def test_test_mode(self, test_bot):
        assert test_bot.ingest_lxm_uri("lxm://AAAA") is False
