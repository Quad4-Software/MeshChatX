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


def _make_manager():
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
    return manager, app, context, config, database


@pytest.mark.asyncio
async def test_auto_propagation_logic():
    manager, app, context, config, database = _make_manager()

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


@pytest.mark.asyncio
async def test_auto_propagation_skips_when_sync_active_and_path_exists():
    """Skip auto-propagation changes while sync is active and the path exists.

    When a sync is active and the current node still has a path, the manager
    should leave it alone so the transfer can finish.
    """
    manager, app, context, config, database = _make_manager()

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_A
    )
    context.message_router.propagation_transfer_state = LXMRouter.PR_RECEIVING

    with patch.object(RNS.Transport, "has_path", return_value=True):
        await manager.check_and_update_propagation_node()

    app.stop_propagation_node_sync.assert_not_called()
    app.set_active_propagation_node.assert_not_called()
    app.remove_active_propagation_node.assert_not_called()


@pytest.mark.asyncio
async def test_auto_propagation_finds_new_node_when_sync_stuck_no_path():
    """Recover when sync is stuck and the current node has no path.

    The manager should stop the stuck sync and look for a working node.
    """
    manager, app, context, config, database = _make_manager()

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_A
    )
    context.message_router.propagation_transfer_state = LXMRouter.PR_PATH_REQUESTED

    announce1 = {
        "destination_hash": _VALID_HASH_B,
        "app_data": _APP_DATA_ENABLED,
    }
    database.announces.get_announces.return_value = [announce1]

    with (
        patch.object(RNS.Transport, "has_path") as mock_has_path,
        patch.object(RNS.Transport, "hops_to", return_value=1),
        patch.object(manager, "_wait_for_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", return_value=True),
    ):
        # Current node A has no path, candidate B has a path.
        mock_has_path.side_effect = lambda dh: dh == bytes.fromhex(_VALID_HASH_B)

        await manager.check_and_update_propagation_node()

    app.stop_propagation_node_sync.assert_called_once_with(context=context)
    app.set_active_propagation_node.assert_called_once_with(
        _VALID_HASH_B,
        context=context,
    )
    config.lxmf_preferred_propagation_node_destination_hash.set.assert_called_with(
        _VALID_HASH_B,
    )


@pytest.mark.asyncio
async def test_auto_propagation_removes_broken_node_when_all_candidates_fail():
    """Remove the active propagation node when no candidate works.

    When no candidate works and the previous node is unreachable, the active
    propagation node should be removed instead of restoring a broken one.
    """
    manager, app, context, config, database = _make_manager()

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_A
    )

    announce1 = {
        "destination_hash": _VALID_HASH_B,
        "app_data": _APP_DATA_ENABLED,
    }
    database.announces.get_announces.return_value = [announce1]

    with (
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch.object(manager, "_wait_for_path", return_value=False),
    ):
        await manager.check_and_update_propagation_node()

    app.set_active_propagation_node.assert_not_called()
    app.remove_active_propagation_node.assert_called_once_with(context=context)


@pytest.mark.asyncio
async def test_check_and_update_propagation_node_noops_without_message_router():
    manager, app, context, config, _database = _make_manager()
    context.message_router = None
    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True

    await manager.check_and_update_propagation_node()

    app.set_active_propagation_node.assert_not_called()
    app.remove_active_propagation_node.assert_not_called()


def test_stop_propagation_node_sync_noops_when_message_router_none():
    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    ctx.message_router = None
    ReticulumMeshChat.stop_propagation_node_sync(app, context=ctx)
