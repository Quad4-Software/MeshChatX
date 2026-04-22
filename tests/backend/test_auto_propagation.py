# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock, patch

import pytest
import RNS
from LXMF.LXMRouter import LXMRouter

from meshchatx.src.backend.auto_propagation_manager import AutoPropagationManager

_VALID_HASH_A = "01" * 16
_VALID_HASH_B = "02" * 16
_VALID_HASH_C = "03" * 16

_APP_DATA_ENABLED = b"\x94\x00\x00\x01\x00"


@pytest.mark.asyncio
async def test_auto_propagation_logic():
    app = MagicMock()
    context = MagicMock()
    config = MagicMock()
    database = MagicMock()

    context.config = config
    context.database = database
    context.identity_hash = "test_identity"
    context.running = True
    context.message_router = MagicMock()
    context.message_router.propagation_transfer_state = LXMRouter.PR_IDLE

    manager = AutoPropagationManager(app, context)

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = False
    with patch.object(manager, "check_and_update_propagation_node") as mock_check:
        if config.lxmf_preferred_propagation_node_auto_select.get():
            await manager.check_and_update_propagation_node()
        mock_check.assert_not_called()

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = None

    announce1 = {
        "destination_hash": _VALID_HASH_A,
        "app_data": _APP_DATA_ENABLED,
    }
    announce2 = {
        "destination_hash": _VALID_HASH_B,
        "app_data": _APP_DATA_ENABLED,
    }
    database.announces.get_announces.return_value = [announce1, announce2]

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "hops_to") as mock_hops,
        patch.object(manager, "_wait_for_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", return_value=True),
    ):
        mock_hops.side_effect = lambda dh: (
            1 if dh == bytes.fromhex(_VALID_HASH_A) else 3
        )

        await manager.check_and_update_propagation_node()

        app.set_active_propagation_node.assert_called_with(
            _VALID_HASH_A,
            context=context,
        )
        config.lxmf_preferred_propagation_node_destination_hash.set.assert_called_with(
            _VALID_HASH_A,
        )

    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_B
    )
    app.set_active_propagation_node.reset_mock()

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "hops_to") as mock_hops,
        patch.object(manager, "_wait_for_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", side_effect=[False, True]),
    ):
        mock_hops.side_effect = lambda dh: (
            1 if dh == bytes.fromhex(_VALID_HASH_A) else 3
        )

        await manager.check_and_update_propagation_node()

        app.set_active_propagation_node.assert_called_with(
            _VALID_HASH_A,
            context=context,
        )

    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_C
    )
    announce3 = {
        "destination_hash": _VALID_HASH_C,
        "app_data": _APP_DATA_ENABLED,
    }
    database.announces.get_announces.return_value = [announce1, announce3]
    app.set_active_propagation_node.reset_mock()

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "hops_to") as mock_hops,
        patch.object(manager, "_wait_for_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", return_value=True),
    ):
        mock_hops.side_effect = lambda dh: (
            1 if dh == bytes.fromhex(_VALID_HASH_A) else 2
        )

        await manager.check_and_update_propagation_node()

        app.set_active_propagation_node.assert_not_called()
