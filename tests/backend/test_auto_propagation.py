from unittest.mock import MagicMock, patch
import pytest
import RNS
from meshchatx.src.backend.auto_propagation_manager import AutoPropagationManager


@pytest.mark.asyncio
async def test_auto_propagation_logic():
    # Mock dependencies
    app = MagicMock()
    context = MagicMock()
    config = MagicMock()
    database = MagicMock()

    context.config = config
    context.database = database
    context.identity_hash = "test_identity"
    context.running = True

    manager = AutoPropagationManager(app, context)

    # 1. Test disabled state
    config.lxmf_preferred_propagation_node_auto_select.get.return_value = False
    with patch.object(manager, "check_and_update_propagation_node") as mock_check:
        # Run one iteration manually
        if config.lxmf_preferred_propagation_node_auto_select.get():
            await manager.check_and_update_propagation_node()
        mock_check.assert_not_called()

    # 2. Test selection logic
    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = None

    # Mock announces
    announce1 = {
        "destination_hash": "aaaa1111",
        "app_data": b"\x94\x00\x00\x01\x00",  # msgpack for [0, 0, 1, 0] -> enabled=True
    }
    announce2 = {"destination_hash": "bbbb2222", "app_data": b"\x94\x00\x00\x01\x00"}
    database.announces.get_announces.return_value = [announce1, announce2]

    # Mock RNS Transport
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "hops_to") as mock_hops,
        patch.object(manager, "probe_node", return_value=True),
    ):
        # announce1 is closer (1 hop)
        # announce2 is further (3 hops)
        mock_hops.side_effect = lambda dh: 1 if dh == bytes.fromhex("aaaa1111") else 3

        await manager.check_and_update_propagation_node()

        # Should have selected aaaa1111
        app.set_active_propagation_node.assert_called_with("aaaa1111", context=context)
        config.lxmf_preferred_propagation_node_destination_hash.set.assert_called_with(
            "aaaa1111"
        )

    # 3. Test switching to better node
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        "bbbb2222"
    )
    app.set_active_propagation_node.reset_mock()

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "hops_to") as mock_hops,
        patch.object(manager, "probe_node", return_value=True),
    ):
        mock_hops.side_effect = lambda dh: 1 if dh == bytes.fromhex("aaaa1111") else 3

        await manager.check_and_update_propagation_node()

        # Should have switched to aaaa1111 because it's closer
        app.set_active_propagation_node.assert_called_with("aaaa1111", context=context)

    # 4. Test failover when probe fails
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        "cccc3333"
    )
    announce3 = {"destination_hash": "cccc3333", "app_data": b"\x94\x00\x00\x01\x00"}
    database.announces.get_announces.return_value = [announce1, announce3]
    app.set_active_propagation_node.reset_mock()

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "hops_to") as mock_hops,
        patch.object(manager, "probe_node") as mock_probe,
    ):
        # announce1 is 1 hop, but probe fails
        # announce3 is 2 hops, probe succeeds
        mock_hops.side_effect = lambda dh: 1 if dh == bytes.fromhex("aaaa1111") else 2
        mock_probe.side_effect = (
            lambda dh: False if dh == bytes.fromhex("aaaa1111") else True
        )

        await manager.check_and_update_propagation_node()

        # Should NOT switch to aaaa1111 because probe failed
        # Should STAY on cccc3333 or switch to it if it was different
        # Since it's already on cccc3333 and it's the best reachable, no switch
        app.set_active_propagation_node.assert_not_called()
