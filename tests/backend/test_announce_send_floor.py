# SPDX-License-Identifier: 0BSD

"""Send-edge announce throttles for manual and service-triggered announces."""

import os
import time
import types
from unittest.mock import AsyncMock, MagicMock

import pytest
from lxmfy._announcing import FORCED_ANNOUNCE_MIN_INTERVAL_SECONDS, AnnounceMixin

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.constants import (
    ANNOUNCE_SEND_MIN_INTERVAL_SECONDS,
    MANUAL_ANNOUNCE_MIN_INTERVAL_SECONDS,
)
from meshchatx.src.backend.rrc.server import (
    FORCED_ANNOUNCE_MIN_INTERVAL_S,
    RRCHubServer,
)


class ConfigField:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _announce_test_app():
    app = types.SimpleNamespace(demo_mode=False)
    ctx = types.SimpleNamespace(
        identity_hash="identity-1",
        running=True,
        local_lxmf_destination=types.SimpleNamespace(
            hash=b"\x11" * 16,
            display_name=None,
        ),
        message_router=MagicMock(),
    )
    ctx.config = types.SimpleNamespace(
        last_announced_at=ConfigField(None),
        display_name=ConfigField("peer"),
        lxmf_local_propagation_node_enabled=ConfigField(False),
        telephone_announce_enabled=ConfigField(False),
    )
    app.current_context = ctx
    app.send_announced_to_websocket_clients = AsyncMock()
    app.announce = types.MethodType(ReticulumMeshChat.announce, app)
    return app, ctx


@pytest.mark.asyncio
async def test_primary_announce_has_send_edge_floor():
    app, ctx = _announce_test_app()

    assert await app.announce() is True
    assert await app.announce() is False
    assert ctx.message_router.announce.call_count == 1

    ctx.config.last_announced_at.set(
        int(time.time() - ANNOUNCE_SEND_MIN_INTERVAL_SECONDS - 1),
    )
    assert await app.announce() is True
    assert ctx.message_router.announce.call_count == 2


@pytest.mark.asyncio
async def test_forced_manual_announce_has_shorter_nonzero_floor():
    app, ctx = _announce_test_app()

    ctx.config.last_announced_at.set(
        int(time.time() - MANUAL_ANNOUNCE_MIN_INTERVAL_SECONDS - 1),
    )
    assert await app.announce(force=True) is True
    assert await app.announce(force=True) is False
    assert ctx.message_router.announce.call_count == 1


def test_config_change_announces_coalesce_trailing_repeats(monkeypatch):
    monkeypatch.setattr(
        "meshchatx.meshchat.ANNOUNCE_SEND_MIN_INTERVAL_SECONDS",
        30.0,
    )
    app = object.__new__(ReticulumMeshChat)
    ctx = types.SimpleNamespace(
        identity_hash="identity-1",
        running=True,
        local_lxmf_destination=types.SimpleNamespace(
            hash=b"\x22" * 16,
            display_name=None,
        ),
        message_router=MagicMock(),
    )
    ctx.config = types.SimpleNamespace(
        last_announced_at=ConfigField(None),
        display_name=ConfigField("peer"),
    )
    app.current_context = ctx

    app._queue_config_change_announce(ctx, "lxmf_delivery")
    app._queue_config_change_announce(ctx, "lxmf_delivery")
    app._queue_config_change_announce(ctx, "lxmf_delivery")

    assert ctx.message_router.announce.call_count == 1
    pending = app._config_change_announce_pending
    assert len(pending) == 1

    key = next(iter(pending))
    app._flush_config_change_announce(key)
    assert ctx.message_router.announce.call_count == 2

    for timer in list(app._config_change_announce_timers.values()):
        timer.cancel()


def test_rrc_forced_announce_floor_allows_first_then_throttles():
    server = RRCHubServer(
        MagicMock(),
        types.SimpleNamespace(hash=b"\x33" * 16),
        name="Hub",
    )
    server.destination = MagicMock()

    assert server.announce_now() is True
    assert server.announce_now() is False
    assert server.destination.announce.call_count == 1

    server._last_announce_sent_at -= FORCED_ANNOUNCE_MIN_INTERVAL_S + 1
    assert server.announce_now() is True
    assert server.destination.announce.call_count == 2


def _bot_for_announce_test(config_path):
    bot = object.__new__(AnnounceMixin)
    bot.config = types.SimpleNamespace(
        test_mode=False,
        name="bot",
        announce_display_name_file=None,
    )
    bot.config_path = str(config_path)
    bot.local = MagicMock()
    bot.local.hash = b"\x44" * 16
    bot.logger = MagicMock()
    bot.announce_enabled = True
    bot.announce_time = 3600
    return bot


def test_bot_forced_announce_floor_allows_first_then_throttles(tmp_path):
    bot = _bot_for_announce_test(tmp_path)
    bot.announce_now(force=True)
    bot.announce_now(force=True)
    assert bot.local.announce.call_count == 1

    # A restarted bot has no in-memory timestamp, but the throttle-file mtime
    # still prevents an immediate forced repeat.
    restarted = _bot_for_announce_test(tmp_path)
    restarted.announce_now(force=True)
    assert restarted.local.announce.call_count == 0

    announce_path = tmp_path / "announce"
    old = time.time() - FORCED_ANNOUNCE_MIN_INTERVAL_SECONDS - 2
    os.utime(announce_path, (old, old))
    restarted.announce_now(force=True)
    assert restarted.local.announce.call_count == 1
