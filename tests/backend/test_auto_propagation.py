# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock, patch

import pytest
import RNS
from LXMF.LXMRouter import LXMRouter

from meshchatx.src.backend.auto_propagation_manager import (
    FAILURE_COOLDOWN_SECONDS,
    MAX_CONSECUTIVE_FAILURES_BEFORE_CLEAR,
    MEMORY_CONFIG_KEY,
    AutoPropagationManager,
)

_VALID_HASH_A = "01" * 16
_VALID_HASH_B = "02" * 16
_VALID_HASH_C = "03" * 16

_APP_DATA_ENABLED = b"\x94\x00\x00\x01\x00"


def _make_manager(memory_raw=None):
    app = MagicMock()
    context = MagicMock()
    config = MagicMock()
    database = MagicMock()
    manager_store = {}

    if memory_raw is not None:
        manager_store[MEMORY_CONFIG_KEY] = memory_raw

    config_manager = MagicMock()
    config_manager.get.side_effect = lambda key, default_value=None: manager_store.get(
        key,
        default_value,
    )

    def _set(key, value):
        manager_store[key] = value

    config_manager.set.side_effect = _set
    # Real ConfigManager exposes get/set on itself (not .manager).
    config.get = config_manager.get
    config.set = config_manager.set
    config.manager = config_manager

    context.config = config
    context.database = database
    context.identity_hash = "test_identity"
    context.running = True
    context.message_router = MagicMock()
    context.message_router.propagation_transfer_state = LXMRouter.PR_IDLE
    context.message_router.get_outbound_propagation_node.return_value = None

    manager = AutoPropagationManager(app, context)
    return manager, app, context, config, database, manager_store


@pytest.mark.asyncio
async def test_auto_propagation_logic():
    manager, app, context, config, database, _store = _make_manager()

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
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch.object(manager, "_wait_for_usable_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", return_value=True),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
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
        assert _VALID_HASH_A in manager._memory
        assert manager._memory[_VALID_HASH_A]["successes"] >= 1

    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_B
    )
    app.set_active_propagation_node.reset_mock()

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "hops_to") as mock_hops,
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch.object(manager, "_wait_for_usable_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", side_effect=[False, True]),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
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
    config.lxmf_preferred_propagation_node_destination_hash.set.reset_mock()

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "hops_to") as mock_hops,
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch.object(manager, "_wait_for_usable_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", return_value=True),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
    ):
        mock_hops.side_effect = lambda dh: (
            1 if dh == bytes.fromhex(_VALID_HASH_A) else 2
        )

        await manager.check_and_update_propagation_node()

        # Preferred C still works. Refresh binding but keep the same hash.
        app.set_active_propagation_node.assert_called_with(
            _VALID_HASH_C,
            context=context,
        )
        config.lxmf_preferred_propagation_node_destination_hash.set.assert_called_with(
            _VALID_HASH_C,
        )


@pytest.mark.asyncio
async def test_auto_propagation_skips_when_sync_active_and_path_exists():
    """Skip auto-propagation changes while sync is active and the path exists.

    When a sync is active and the current node still has a path, the manager
    should leave it alone so the transfer can finish.
    """
    manager, app, context, config, database, _store = _make_manager()

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_A
    )
    context.message_router.propagation_transfer_state = LXMRouter.PR_RECEIVING

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch.object(
            manager,
            "_wait_for_usable_path",
            return_value=True,
        ),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
    ):
        await manager.check_and_update_propagation_node()

    app.stop_propagation_node_sync.assert_not_called()
    app.set_active_propagation_node.assert_not_called()
    app.remove_active_propagation_node.assert_not_called()


@pytest.mark.asyncio
async def test_auto_propagation_finds_new_node_when_sync_stuck_no_path():
    """Recover when sync is stuck and the current node has no path.

    The manager should stop the stuck sync and look for a working node.
    """
    manager, app, context, config, database, _store = _make_manager()

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
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch.object(manager, "_wait_for_usable_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", return_value=True),
        patch("meshchatx.src.backend.auto_propagation_manager.asyncio.sleep"),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
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
async def test_auto_propagation_keeps_preferred_until_repeated_failures():
    """Transient probe failures should not wipe a preferred node immediately."""
    manager, app, context, config, database, _store = _make_manager()

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
        patch.object(manager, "_wait_for_usable_path", return_value=False),
        patch.object(RNS.Transport, "request_path") as mock_request_path,
    ):
        await manager.check_and_update_propagation_node()

    app.remove_active_propagation_node.assert_not_called()
    app.set_active_propagation_node.assert_called_with(_VALID_HASH_A, context=context)
    mock_request_path.assert_called()
    assert manager._memory.get(_VALID_HASH_B, {}).get("consecutive_failures", 0) >= 1


@pytest.mark.asyncio
async def test_auto_propagation_clears_after_repeated_failures():
    """Clear the preferred node after repeated verify failures."""
    import json
    import time

    memory = {
        _VALID_HASH_A: {
            "successes": 2,
            "failures": MAX_CONSECUTIVE_FAILURES_BEFORE_CLEAR - 1,
            "consecutive_failures": MAX_CONSECUTIVE_FAILURES_BEFORE_CLEAR - 1,
            "last_success_at": int(time.time()) - 60,
            "last_failure_at": int(time.time()) - 30,
            "last_hops": 2,
        },
    }
    manager, app, context, config, database, _store = _make_manager(
        memory_raw=json.dumps(memory),
    )

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_A
    )

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
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch.object(RNS.Transport, "hops_to", return_value=1),
        patch.object(manager, "_wait_for_usable_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", return_value=False),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
        # Avoid cooldown short-circuit for A so both nodes are probed.
        patch.object(manager, "_in_failure_cooldown", return_value=False),
    ):
        await manager.check_and_update_propagation_node()

    app.set_active_propagation_node.assert_not_called()
    app.remove_active_propagation_node.assert_called_once_with(context=context)
    config.lxmf_preferred_propagation_node_destination_hash.set.assert_called_with(None)


@pytest.mark.asyncio
async def test_check_and_update_propagation_node_noops_without_message_router():
    manager, app, context, config, _database, _store = _make_manager()
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


@pytest.mark.asyncio
async def test_auto_propagation_interrupts_sync_when_path_unresponsive():
    """Stop a stuck sync when the current path is unresponsive.

    Even if RNS reports has_path=True, a stale or unresponsive path should be
    treated as broken so the manager can look for a working alternative.
    """
    manager, app, context, config, database, _store = _make_manager()

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_A
    )
    context.message_router.propagation_transfer_state = LXMRouter.PR_RECEIVING

    announce1 = {
        "destination_hash": _VALID_HASH_B,
        "app_data": _APP_DATA_ENABLED,
    }
    database.announces.get_announces.return_value = [announce1]

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive") as mock_unresponsive,
        patch.object(RNS.Transport, "hops_to", return_value=1),
        patch.object(manager, "_wait_for_usable_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", return_value=True),
        patch("meshchatx.src.backend.auto_propagation_manager.asyncio.sleep"),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
    ):
        mock_unresponsive.side_effect = lambda dh: dh == bytes.fromhex(_VALID_HASH_A)

        await manager.check_and_update_propagation_node()

    app.stop_propagation_node_sync.assert_called_once_with(context=context)
    app.set_active_propagation_node.assert_called_once_with(
        _VALID_HASH_B,
        context=context,
    )


@pytest.mark.asyncio
async def test_probe_propagation_sync_treats_complete_as_success():
    """LXMF finishes successful sync at PR_COMPLETE, not only PR_IDLE."""
    manager, app, context, config, database, _store = _make_manager()
    router = context.message_router
    router.propagation_transfer_state = LXMRouter.PR_IDLE

    call_count = [0]

    async def fake_sleep(_):
        call_count[0] += 1
        if call_count[0] == 1:
            router.propagation_transfer_state = LXMRouter.PR_LINK_ESTABLISHING
        elif call_count[0] == 2:
            router.propagation_transfer_state = LXMRouter.PR_COMPLETE

    with (
        patch(
            "meshchatx.src.backend.auto_propagation_manager.asyncio.sleep",
            fake_sleep,
        ),
        patch.object(RNS.Identity, "recall", return_value=object()),
    ):
        result = await manager._probe_propagation_sync(_VALID_HASH_A)

    assert result is True


@pytest.mark.asyncio
async def test_probe_propagation_sync_uses_scarce_message_budget():
    """Auto-select probes must not pull a full mailbox (Zen scarcity)."""
    manager, app, context, config, database, _store = _make_manager()
    router = context.message_router
    router.propagation_transfer_state = LXMRouter.PR_IDLE

    call_count = [0]

    async def fake_sleep(_):
        call_count[0] += 1
        if call_count[0] == 1:
            router.propagation_transfer_state = LXMRouter.PR_REQUEST_SENT
        elif call_count[0] == 2:
            router.propagation_transfer_state = LXMRouter.PR_COMPLETE

    with (
        patch(
            "meshchatx.src.backend.auto_propagation_manager.asyncio.sleep",
            fake_sleep,
        ),
        patch.object(RNS.Identity, "recall", return_value=object()),
    ):
        result = await manager._probe_propagation_sync(_VALID_HASH_A)

    assert result is True
    router.request_messages_from_propagation_node.assert_called_once()
    _args, kwargs = router.request_messages_from_propagation_node.call_args
    # Prefer kwargs if present, else positional max_messages.
    if "max_messages" in kwargs:
        assert kwargs["max_messages"] == 1
    else:
        assert _args[1] == 1


@pytest.mark.asyncio
async def test_auto_propagation_caps_probes_per_cycle():
    """Do not sync-probe every announced peer in one cycle."""
    from meshchatx.src.backend.auto_propagation_manager import MAX_PROBES_PER_CYCLE

    manager, app, context, config, database, _store = _make_manager()
    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = None

    announces = []
    for i in range(MAX_PROBES_PER_CYCLE + 3):
        announces.append(
            {
                "destination_hash": f"{i:02x}" * 16,
                "app_data": _APP_DATA_ENABLED,
            },
        )
    database.announces.get_announces.return_value = announces

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch.object(RNS.Transport, "hops_to", return_value=1),
        patch.object(manager, "_wait_for_usable_path", return_value=True),
        patch.object(
            manager, "_probe_propagation_sync", return_value=False
        ) as mock_probe,
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
    ):
        await manager.check_and_update_propagation_node()

    assert mock_probe.call_count == MAX_PROBES_PER_CYCLE


@pytest.mark.asyncio
async def test_probe_propagation_sync_ignores_stale_state():
    """A stale non-idle state from a previous sync must not cause a false success.

    The probe should wait for PR_IDLE before starting, then only count state
    changes that happen after the new request is issued.
    """
    import time

    manager, app, context, config, database, _store = _make_manager()
    router = context.message_router

    router.propagation_transfer_state = LXMRouter.PR_RECEIVING
    call_count = [0]

    async def fake_sleep(_):
        call_count[0] += 1
        if call_count[0] == 3:
            router.propagation_transfer_state = LXMRouter.PR_IDLE

    fake_time = [0.0]

    def fake_monotonic():
        fake_time[0] += 0.5
        return fake_time[0]

    with (
        patch(
            "meshchatx.src.backend.auto_propagation_manager.asyncio.sleep",
            fake_sleep,
        ),
        patch.object(time, "monotonic", fake_monotonic),
        patch.object(RNS.Identity, "recall", return_value=None),
        patch.object(RNS.Transport, "request_path"),
    ):
        result = await manager._probe_propagation_sync(_VALID_HASH_A)

    # The stale state goes idle after a few sleeps, but the new request never
    # leaves idle, so the probe must return False rather than True.
    assert result is False
    app.stop_propagation_node_sync.assert_called()


@pytest.mark.asyncio
async def test_sync_propagation_nodes_skips_when_active_and_not_forced():
    """Auto-sync must not overlap an already-active propagation transfer."""
    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    router = MagicMock()
    router.propagation_transfer_state = LXMRouter.PR_RECEIVING
    router.PR_IDLE = LXMRouter.PR_IDLE
    ctx.message_router = router
    ctx.config = MagicMock()

    with patch.object(app, "stop_propagation_node_sync") as mock_stop:
        await app.sync_propagation_nodes(context=ctx, force=False)

    router.request_messages_from_propagation_node.assert_not_called()
    mock_stop.assert_not_called()


@pytest.mark.asyncio
async def test_auto_propagation_keeps_recently_verified_without_probe():
    """A recently verified preferred node with a good path should not be re-probed."""
    import json
    import time

    memory = {
        _VALID_HASH_A: {
            "successes": 3,
            "failures": 0,
            "consecutive_failures": 0,
            "last_success_at": int(time.time()),
            "last_failure_at": 0,
            "last_hops": 2,
        },
    }
    manager, app, context, config, database, store = _make_manager(
        memory_raw=json.dumps(memory),
    )

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
        _VALID_HASH_A
    )
    context.message_router.get_outbound_propagation_node.return_value = bytes.fromhex(
        _VALID_HASH_A,
    )

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
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch.object(RNS.Transport, "hops_to") as mock_hops,
        patch.object(manager, "_wait_for_usable_path") as mock_wait,
        patch.object(manager, "_probe_propagation_sync") as mock_probe,
        patch.object(RNS.Transport, "request_path") as mock_request_path,
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
    ):
        # B is only one hop better, inside hysteresis, so keep A.
        mock_hops.side_effect = lambda dh: (
            2 if dh == bytes.fromhex(_VALID_HASH_A) else 1
        )
        await manager.check_and_update_propagation_node()

    mock_wait.assert_not_called()
    mock_probe.assert_not_called()
    app.set_active_propagation_node.assert_not_called()
    mock_request_path.assert_called()
    assert MEMORY_CONFIG_KEY in store or _VALID_HASH_A in manager._memory


@pytest.mark.asyncio
async def test_auto_propagation_remembers_good_node_without_announce():
    """Remembered successful nodes remain candidates when announces age out."""
    import json
    import time

    memory = {
        _VALID_HASH_A: {
            "successes": 4,
            "failures": 0,
            "consecutive_failures": 0,
            "last_success_at": int(time.time()),
            "last_failure_at": 0,
            "last_hops": 1,
        },
    }
    manager, app, context, config, database, _store = _make_manager(
        memory_raw=json.dumps(memory),
    )
    # Force re-verify so the sticky short-circuit does not skip the probe.
    manager._memory[_VALID_HASH_A]["last_success_at"] = int(time.time()) - (
        FAILURE_COOLDOWN_SECONDS * 10
    )

    config.lxmf_preferred_propagation_node_auto_select.get.return_value = True
    config.lxmf_preferred_propagation_node_destination_hash.get.return_value = None
    database.announces.get_announces.return_value = []

    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch.object(RNS.Transport, "hops_to", return_value=1),
        patch.object(manager, "_wait_for_usable_path", return_value=True),
        patch.object(manager, "_probe_propagation_sync", return_value=True),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
    ):
        await manager.check_and_update_propagation_node()

    app.set_active_propagation_node.assert_called_with(
        _VALID_HASH_A,
        context=context,
    )
    config.lxmf_preferred_propagation_node_destination_hash.set.assert_called_with(
        _VALID_HASH_A,
    )


@pytest.mark.asyncio
async def test_wait_for_usable_path_rejects_unresponsive_paths():
    manager, _app, _context, _config, _database, _store = _make_manager()
    dest = bytes.fromhex(_VALID_HASH_A)

    with (
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.prepare_fresh_path_request",
            return_value="new_path_requested",
        ),
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=True),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.reticulum_pathfinding.nudge_path_request",
        ) as mock_nudge,
        patch("meshchatx.src.backend.auto_propagation_manager.asyncio.sleep"),
        patch(
            "meshchatx.src.backend.auto_propagation_manager.time.monotonic",
        ) as mock_mono,
    ):
        mock_mono.side_effect = [0.0, 0.1, 50.0, 50.0]
        ok = await manager._wait_for_usable_path(dest, timeout=1.0)

    assert ok is False
    mock_nudge.assert_called()
