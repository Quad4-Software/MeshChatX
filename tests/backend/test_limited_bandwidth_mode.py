# SPDX-License-Identifier: 0BSD

import os
import sqlite3
import time
from unittest.mock import AsyncMock, MagicMock, patch

import LXMF
import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend import rns_discovery_live
from meshchatx.src.backend.limited_bandwidth import (
    LIMITED_BANDWIDTH_ANNOUNCE_MIN_INTERVAL_SECONDS,
    LIMITED_BANDWIDTH_TELEMETRY_MIN_INTERVAL_SECONDS,
    clamp_periodic_mesh_interval,
    crawler_runtime_enabled,
    read_stored_limited_bandwidth_enabled,
    telemetry_request_minimum_interval,
)
from meshchatx.src.backend.reticulum_pathfinding import OutboundPathOutcome
from meshchatx.src.backend.telemetry_request_policy import effective_request_interval


class Field:
    def __init__(self, value):
        self.value = value
        self.set = MagicMock(side_effect=self._set)

    def _set(self, value):
        self.value = value

    def get(self):
        return self.value


def config(**values):
    cfg = MagicMock()
    cfg.limited_bandwidth_enabled = Field(
        bool(values.pop("limited_bandwidth_enabled", False)),
    )
    for key, value in values.items():
        setattr(cfg, key, Field(value))
    return cfg


def running_context(cfg):
    ctx = MagicMock()
    ctx.running = True
    ctx.session_id = 1
    ctx.config = cfg
    return ctx


def loop_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.running = True
    return app


def one_iteration_sleep(app):
    async def sleep(_seconds):
        app.running = False

    return sleep


@pytest.mark.asyncio
async def test_announce_loop_uses_stored_interval_when_mode_is_off():
    cfg = config(
        limited_bandwidth_enabled=False,
        auto_announce_enabled=True,
        auto_announce_interval_seconds=900,
        last_announced_at=int(time.time() - 901),
    )
    ctx = running_context(cfg)
    app = loop_app()
    app.announce = AsyncMock(return_value=True)
    app._aget_interface_stats_payload = AsyncMock(return_value={"interfaces": []})
    app.memory_pressure = MagicMock()

    with patch("meshchatx.meshchat.asyncio.sleep", new=one_iteration_sleep(app)):
        await app.announce_loop(1, context=ctx)

    app.announce.assert_awaited_once()
    cfg.auto_announce_interval_seconds.set.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("elapsed,expected_calls", [(901, 0), (21601, 1)])
async def test_announce_loop_applies_six_hour_runtime_floor_when_mode_is_on(
    elapsed,
    expected_calls,
):
    cfg = config(
        limited_bandwidth_enabled=True,
        auto_announce_enabled=True,
        auto_announce_interval_seconds=900,
        last_announced_at=int(time.time() - elapsed),
    )
    ctx = running_context(cfg)
    app = loop_app()
    app.announce = AsyncMock(return_value=True)
    app._aget_interface_stats_payload = AsyncMock(return_value={"interfaces": []})
    app.memory_pressure = MagicMock()

    with patch("meshchatx.meshchat.asyncio.sleep", new=one_iteration_sleep(app)):
        await app.announce_loop(1, context=ctx)

    assert app.announce.await_count == expected_calls
    assert cfg.auto_announce_interval_seconds.get() == 900
    cfg.auto_announce_interval_seconds.set.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enabled,elapsed,expected_calls",
    [(False, 901, 1), (True, 901, 0), (True, 21601, 1)],
)
async def test_propagation_autosync_runtime_floor(enabled, elapsed, expected_calls):
    cfg = config(
        limited_bandwidth_enabled=enabled,
        lxmf_preferred_propagation_node_auto_sync_interval_seconds=900,
        lxmf_preferred_propagation_node_last_synced_at=int(time.time() - elapsed),
    )
    ctx = running_context(cfg)
    ctx.message_router.get_outbound_propagation_node.return_value = b"x" * 16
    app = loop_app()
    app.sync_propagation_nodes = AsyncMock(return_value=False)
    app.send_config_to_websocket_clients = AsyncMock()

    with patch("meshchatx.meshchat.asyncio.sleep", new=one_iteration_sleep(app)):
        await app.announce_sync_propagation_nodes(1, context=ctx)

    assert app.sync_propagation_nodes.await_count == expected_calls
    assert cfg.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get() == 900
    cfg.lxmf_preferred_propagation_node_auto_sync_interval_seconds.set.assert_not_called()


def test_periodic_mesh_interval_helper_is_runtime_only():
    cfg = config(limited_bandwidth_enabled=True)
    assert (
        clamp_periodic_mesh_interval(cfg, 900)
        == LIMITED_BANDWIDTH_ANNOUNCE_MIN_INTERVAL_SECONDS
    )
    cfg.limited_bandwidth_enabled.value = False
    assert clamp_periodic_mesh_interval(cfg, 900) == 900


def test_telemetry_effective_interval_minimum():
    cfg = config(limited_bandwidth_enabled=True)
    assert (
        telemetry_request_minimum_interval(cfg)
        == LIMITED_BANDWIDTH_TELEMETRY_MIN_INTERVAL_SECONDS
    )
    assert (
        effective_request_interval(
            60,
            0,
            minimum_interval_seconds=telemetry_request_minimum_interval(cfg),
        )
        == LIMITED_BANDWIDTH_TELEMETRY_MIN_INTERVAL_SECONDS
    )
    assert (
        effective_request_interval(
            60,
            5,
            minimum_interval_seconds=telemetry_request_minimum_interval(cfg),
        )
        == 1920
    )
    cfg.limited_bandwidth_enabled.value = False
    assert telemetry_request_minimum_interval(cfg) == 1
    assert (
        effective_request_interval(
            60,
            0,
            minimum_interval_seconds=telemetry_request_minimum_interval(cfg),
        )
        == 60
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enabled,last_age,expected_marks",
    [(False, 61, 1), (True, 61, 0), (True, 901, 1)],
)
async def test_telemetry_loop_applies_fifteen_minute_runtime_minimum(
    enabled,
    last_age,
    expected_marks,
):
    now = time.time()
    peer = {
        "destination_hash": "aa" * 16,
        "interval_seconds": 60,
        "unanswered_count": 0,
        "last_request_at": now - last_age,
    }
    cfg = config(limited_bandwidth_enabled=enabled, telemetry_enabled=True)
    ctx = running_context(cfg)
    ctx.database.telemetry.get_tracked_peers.return_value = [peer]
    app = loop_app()
    app._send_telemetry_tracking_request = AsyncMock()

    async def stop_after_sleep(_seconds):
        app.running = False

    async def immediate_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    with (
        patch("meshchatx.meshchat.asyncio.sleep", new=stop_after_sleep),
        patch("meshchatx.meshchat.asyncio.to_thread", side_effect=immediate_to_thread),
    ):
        await app.telemetry_tracking_loop(1, context=ctx)

    assert ctx.database.telemetry.mark_request_sent.call_count == expected_marks
    for task in getattr(app, "_telemetry_request_tasks", set()):
        task.cancel()


@pytest.mark.parametrize("enabled", [False, True])
def test_crawler_runtime_enabled_gate(enabled):
    cfg = config(limited_bandwidth_enabled=enabled, crawler_enabled=True)
    assert crawler_runtime_enabled(cfg) is not enabled


@pytest.mark.parametrize("enabled", [False, True])
def test_queue_crawler_task_blocks_manual_and_automatic_work_when_enabled(enabled):
    cfg = config(limited_bandwidth_enabled=enabled, crawler_enabled=True)
    ctx = running_context(cfg)
    ctx.crawler_manager = MagicMock()
    app = loop_app()
    app.current_context = ctx

    app.queue_crawler_task("aa" * 16, "/page/index.mu", force=True)

    assert bool(ctx.crawler_manager.queue_if_allowed.called) is not enabled


@pytest.mark.parametrize("enabled", [False, True])
def test_queue_crawler_task_without_manager_never_writes_task_when_enabled(enabled):
    cfg = config(limited_bandwidth_enabled=enabled, crawler_enabled=True)
    ctx = running_context(cfg)
    ctx.crawler_manager = None
    app = loop_app()
    app.current_context = ctx

    app.queue_crawler_task("aa" * 16, "/page/index.mu", force=True)

    assert bool(ctx.database.misc.upsert_crawl_task.called) is not enabled


@pytest.mark.asyncio
async def test_crawler_loop_does_not_scan_or_crawl_when_mode_is_on():
    cfg = config(
        limited_bandwidth_enabled=True,
        crawler_enabled=True,
        nomad_default_page_path="/page/index.mu",
    )
    ctx = running_context(cfg)
    app = loop_app()

    with patch("meshchatx.meshchat.asyncio.sleep", new=one_iteration_sleep(app)):
        await app.crawler_loop(1, context=ctx)

    ctx.database.announces.get_announces.assert_not_called()
    ctx.crawler_manager.queue_if_allowed.assert_not_called()


@pytest.mark.parametrize("paused", [False, True])
def test_discovery_autoconnect_gate_blocks_only_while_paused(monkeypatch, paused):
    assert rns_discovery_live.install_discovery_autoconnect_gate()
    original = MagicMock(return_value="connected")
    monkeypatch.setattr(
        rns_discovery_live,
        "_ORIGINAL_INTERFACE_AUTOCONNECT",
        original,
    )
    monkeypatch.setattr(rns_discovery_live, "_AUTOCONNECT_GATE_PAUSED", paused)

    from RNS.Discovery import InterfaceDiscovery

    result = InterfaceDiscovery.autoconnect(object(), {"type": "BackboneInterface"})
    if paused:
        assert result is None
        original.assert_not_called()
    else:
        assert result == "connected"
        original.assert_called_once()


def test_stored_mode_read_for_startup(tmp_path):
    database_path = tmp_path / "database.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT)")
    connection.execute(
        "INSERT INTO config (key, value) VALUES (?, ?)",
        ("limited_bandwidth_enabled", "true"),
    )
    connection.commit()
    connection.close()

    assert read_stored_limited_bandwidth_enabled(str(database_path)) is True

    connection = sqlite3.connect(database_path)
    connection.execute(
        "UPDATE config SET value = ? WHERE key = ?",
        ("false", "limited_bandwidth_enabled"),
    )
    connection.commit()
    connection.close()
    assert read_stored_limited_bandwidth_enabled(str(database_path)) is False
    assert read_stored_limited_bandwidth_enabled(str(tmp_path / "missing.db")) is False


@pytest.mark.asyncio
async def test_update_config_does_not_rewrite_stored_intervals(mock_app):
    mock_app.config.auto_announce_interval_seconds.set(900)
    mock_app.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.set(900)

    await mock_app.update_config({"limited_bandwidth_enabled": True})

    assert mock_app.config.limited_bandwidth_enabled.get() is True
    assert mock_app.config.auto_announce_interval_seconds.get() == 900
    assert (
        mock_app.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
        == 900
    )
    mock_app.current_context.identity.get_public_key = MagicMock(return_value=b"")
    config_dict = mock_app.get_config_dict()
    assert config_dict["limited_bandwidth_enabled"] is True
    assert config_dict["auto_announce_interval_seconds"] == 900

    await mock_app.update_config({"limited_bandwidth_enabled": False})
    assert mock_app.config.auto_announce_interval_seconds.get() == 900


@pytest.fixture
def sendable_limited_app(tmp_path):
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = MagicMock()
    app.config = MagicMock()
    app.database = MagicMock()
    app.reticulum = MagicMock()
    app.storage_dir = str(tmp_path / "meshchat_test")
    os.makedirs(app.storage_dir, exist_ok=True)
    ctx = app.current_context
    ctx.config = MagicMock()
    ctx.config.limited_bandwidth_enabled = Field(False)
    ctx.config.auto_send_failed_messages_to_propagation_node.get.return_value = False
    ctx.message_router.delivery_link_available.return_value = True
    ctx.local_lxmf_destination = MagicMock()
    ctx.forwarding_manager = None
    app._await_transport_path = AsyncMock(
        return_value=OutboundPathOutcome(True, "reused_valid_path", False),
    )
    app.get_current_icon_hash = MagicMock(return_value=None)
    app.db_upsert_lxmf_message = MagicMock()
    app.websocket_broadcast = AsyncMock()
    app.handle_lxmf_message_progress = AsyncMock()
    return app


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_direct_message_sending_is_not_clamped(sendable_limited_app, enabled):
    app = sendable_limited_app
    app.current_context.config.limited_bandwidth_enabled.value = enabled
    fake_identity = MagicMock()
    fake_destination = MagicMock()
    fake_lxm = MagicMock(spec=LXMF.LXMessage)
    fake_lxm.fields = {}
    fake_lxm.include_ticket = False
    app.recall_identity = MagicMock(return_value=fake_identity)
    app._is_self_lxmf_destination = MagicMock(return_value=False)
    real_lxm_class = LXMF.LXMessage
    fake_lxm_class = MagicMock(return_value=fake_lxm)
    for constant in (
        "DIRECT",
        "OPPORTUNISTIC",
        "PROPAGATED",
        "DELIVERED",
        "SENT",
        "FAILED",
    ):
        setattr(fake_lxm_class, constant, getattr(real_lxm_class, constant, None))

    with (
        patch("meshchatx.meshchat.RNS.Destination", return_value=fake_destination),
        patch("meshchatx.meshchat.LXMF.LXMessage", fake_lxm_class) as lxm_cls,
        patch(
            "meshchatx.meshchat.convert_lxmf_message_to_dict",
            return_value={"hash": "x"},
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        await app.send_message(
            destination_hash="aa" * 16,
            content="hi",
            delivery_method="direct",
        )

    assert lxm_cls.call_args.kwargs["desired_method"] == real_lxm_class.DIRECT
    app._await_transport_path.assert_awaited_once()
