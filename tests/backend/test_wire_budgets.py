# SPDX-License-Identifier: 0BSD

"""Wire budget tests: outbound traffic stays bounded under storms.

Each suite simulates the hostile input (announce storms, connect
flapping, repeated downloads, announce-triggered resends) and asserts
the protocol's own guards keep packets on the wire under a cap.
"""

from __future__ import annotations

import json
import threading
import time
import types
from itertools import pairwise
from unittest.mock import AsyncMock, MagicMock

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend import auto_resend_guard as guard
from meshchatx.src.backend import nomadnet_downloader as nomad_dl
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema
from meshchatx.src.backend.nomadnet_downloader import (
    MAX_CACHED_LINKS,
    NomadnetDownloader,
    _cache_link_if_active,
    _nomadnet_link_last_used,
    _nomadnet_links_lock,
    nomadnet_cached_links,
)
from meshchatx.src.backend.rrc import manager as rrc_manager
from meshchatx.src.backend.rrc.manager import RRCHub
from tests.backend.test_rrc_server import FakeManager


class _Mgr(FakeManager):
    def get_nickname(self):
        return "me"


# -- RRC ---------------------------------------------------------------


def test_rrc_reconnect_attempts_bounded_per_hour(monkeypatch):
    """A connect-flapping hub cannot retry more than a handful of times an hour."""
    hub = RRCHub(_Mgr(), b"\x33" * 16, name="hub")
    monkeypatch.setattr(rrc_manager.random, "uniform", lambda _a, _b: 0.0)
    delays = []
    try:
        for _ in range(40):
            hub._schedule_reconnect()
            delays.append(hub._reconnect_timer.interval)
    finally:
        if hub._reconnect_timer is not None:
            hub._reconnect_timer.cancel()
            hub._reconnect_timer = None

    elapsed = 0.0
    attempts_in_hour = 0
    for delay in delays:
        elapsed += delay
        if elapsed > 3600.0:
            break
        attempts_in_hour += 1

    assert attempts_in_hour <= 14
    assert delays[-1] == rrc_manager.RECONNECT_BACKOFF_MAX_S
    assert all(a <= b for a, b in pairwise(delays))


def test_rrc_hello_loop_bounded(monkeypatch):
    """The HELLO handshake stops after five sends instead of retrying forever."""
    hub = RRCHub(_Mgr(), b"\x33" * 16, name="hub")
    link = MagicMock()
    link.status = RNS.Link.ACTIVE
    hub.link = link
    hub._fail_welcome_timeout = MagicMock()
    hub._stop_hello.wait = lambda *a, **k: False
    sends = 0

    def _counting_hello(_link):
        nonlocal sends
        sends += 1

    hub._send_hello = _counting_hello
    hub._hello_loop()
    assert sends == 5
    hub._fail_welcome_timeout.assert_called_once()


def test_rrc_announce_storm_resets_suppressed(monkeypatch):
    """Only one announce-driven backoff reset is allowed per window."""
    hub = RRCHub(_Mgr(), b"\x33" * 16, name="hub")
    hub.auto_reconnect = True
    hub._reconnect_attempts = 9
    hub._reconnect_timer = threading.Timer(600, lambda: None)
    reschedules = 0
    original = hub._schedule_reconnect

    def _counting():
        nonlocal reschedules
        reschedules += 1
        original()

    hub._schedule_reconnect = _counting
    try:
        for _ in range(50):
            hub.note_hub_announce()
    finally:
        if hub._reconnect_timer is not None:
            hub._reconnect_timer.cancel()
            hub._reconnect_timer = None
    assert reschedules == 1


# -- LXMF --------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "wire_budget.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    database = Database(path)
    yield database
    database.close_all()
    provider.close_all()


def _insert_failed(db, *, msg_hash, peer, content, fields="{}", ts=None):
    db.messages.upsert_lxmf_message(
        {
            "hash": msg_hash,
            "source_hash": peer,
            "destination_hash": peer,
            "peer_hash": peer,
            "state": "failed",
            "progress": 0,
            "is_incoming": 0,
            "method": "opportunistic",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "",
            "content": content,
            "fields": fields,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
            "timestamp": ts if ts is not None else time.time(),
        },
    )


def _bind_resend_app(db):
    app = MagicMock()
    app._auto_resend_coordinator = guard.AutoResendCoordinator()
    app.websocket_broadcast = AsyncMock()
    app.send_message = AsyncMock()
    app.resend_failed_messages_for_destination = types.MethodType(
        ReticulumMeshChat.resend_failed_messages_for_destination,
        app,
    )
    ctx = MagicMock()
    ctx.identity.hash.hex.return_value = "aa" * 16
    ctx.database = db
    ctx.config.allow_auto_resending_failed_messages_with_attachments.get.return_value = True
    return app, ctx


@pytest.mark.asyncio
async def test_lxmf_resend_announce_storm_bounded(db):
    """Twenty announce-triggered resend passes send each failed row at most once."""
    peer = "9" * 32
    for i in range(20):
        # Every fourth row is feature-only so the capability gate engages
        # alongside the normal-content path in the same storm.
        feature_only = i % 4 == 0
        _insert_failed(
            db,
            msg_hash=f"{i + 1:02x}" + "ab" * 15,
            peer=peer,
            content="" if feature_only else f"retry body {i}",
            fields=json.dumps({"commands": [{"0x01": 0}], "_seen": i})
            if feature_only
            else "{}",
        )
    # Feature-only rows are capability-gated; give the peer evidence so all
    # rows are resend-eligible and only the cooldown limits the traffic.
    _insert_incoming_feature(db, peer=peer, msg_hash="fe" * 16)

    app, ctx = _bind_resend_app(db)
    for _ in range(15):
        await app.resend_failed_messages_for_destination(peer, context=ctx)

    assert app.send_message.await_count <= 20


def _insert_incoming_feature(db, *, peer, msg_hash):
    db.messages.upsert_lxmf_message(
        {
            "hash": msg_hash,
            "source_hash": peer,
            "destination_hash": "0" * 32,
            "peer_hash": peer,
            "state": "delivered",
            "progress": 1,
            "is_incoming": 1,
            "method": "direct",
            "delivery_attempts": 1,
            "next_delivery_attempt_at": None,
            "title": "",
            "content": "",
            "fields": json.dumps({"reaction": {"smile": True}}),
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
            "timestamp": time.time(),
        },
    )


# -- NomadNet ----------------------------------------------------------


@pytest.fixture
def clean_link_cache():
    with _nomadnet_links_lock:
        nomadnet_cached_links.clear()
        _nomadnet_link_last_used.clear()
    yield
    with _nomadnet_links_lock:
        nomadnet_cached_links.clear()
        _nomadnet_link_last_used.clear()


def _fake_link(status=None):
    link = MagicMock()
    link.status = status if status is not None else RNS.Link.ACTIVE
    return link


def test_nomad_link_cache_bounded(clean_link_cache):
    """The sweep caps the shared link cache and tears down evictees."""
    teardowns = []

    for i in range(MAX_CACHED_LINKS + 10):
        link = _fake_link()
        link.teardown.side_effect = lambda lnk=link: teardowns.append(lnk)
        _cache_link_if_active(bytes([i % 256]) * 16, link)

    nomad_dl.sweep_stale_links()
    assert len(nomadnet_cached_links) <= MAX_CACHED_LINKS
    assert len(teardowns) >= 10


@pytest.mark.asyncio
async def test_nomad_download_reuses_cached_link(clean_link_cache, monkeypatch):
    """A warm cache means zero new link requests for repeat downloads."""
    dest = b"\x55" * 16
    cached = _fake_link()
    nomadnet_cached_links[dest] = cached
    _nomadnet_link_last_used[dest] = time.time()

    # Identity.recall only runs on the link-creation path; a cached-link hit
    # returns long before it. Explode loudly if a new link is attempted.
    monkeypatch.setattr(nomad_dl.RNS, "Identity", MagicMock())
    nomad_dl.RNS.Identity.recall.side_effect = AssertionError("new link attempted")

    for _ in range(10):
        d = NomadnetDownloader(
            dest,
            "/page.mu",
            None,
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        d.link_established = MagicMock()
        await d._download_inner()
        d.link_established.assert_called_once_with(cached)
        assert d.link is cached

    nomad_dl.RNS.Identity.recall.assert_not_called()
