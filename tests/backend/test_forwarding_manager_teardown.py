# SPDX-License-Identifier: 0BSD

"""Tests for ForwardingManager lifecycle."""

from unittest.mock import MagicMock, patch

import RNS

from meshchatx.src.backend.forwarding_manager import ForwardingManager


def test_forwarding_manager_teardown_deregisters_and_stops_routers():
    db = MagicMock()
    db.messages.get_all_forwarding_mappings.return_value = []

    mgr = ForwardingManager(
        db,
        storage_path="/tmp/fwd_test",
        delivery_callback=lambda m: None,
        config=None,
    )

    mock_dest = MagicMock()
    mock_router = MagicMock()
    mock_router.delivery_destinations = {"a": mock_dest}
    mock_router.propagation_destination = MagicMock()

    alias_hash = "deadbeef"
    mgr.forwarding_destinations[alias_hash] = mock_dest
    mgr.forwarding_routers[alias_hash] = mock_router

    with patch.object(RNS.Transport, "deregister_destination") as dd:
        mgr.teardown()
        assert dd.call_count >= 2
    mock_router.exit_handler.assert_called_once()
    assert mgr.forwarding_destinations == {}
    assert mgr.forwarding_routers == {}
