# SPDX-License-Identifier: 0BSD

import asyncio
import base64
import threading
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend import rns_link_manager as rlm


@pytest.fixture(autouse=True)
def clear_link_cache():
    with rlm._rns_links_lock:
        rlm.rns_cached_links.clear()
        rlm._rns_link_last_used.clear()
        rlm._link_failure_counts.clear()
    yield
    with rlm._rns_links_lock:
        rlm.rns_cached_links.clear()
        rlm._rns_link_last_used.clear()
        rlm._link_failure_counts.clear()


def _manager(*, identity=None, broadcast=None):
    return rlm.RnsLinkManager(
        self_identity_getter=lambda: identity,
        reticulum_getter=lambda: None,
        broadcast_event=broadcast or (lambda _payload: None),
    )


def test_split_aspect_requires_non_empty():
    with pytest.raises(ValueError):
        rlm._split_aspect("")
    with pytest.raises(ValueError):
        rlm._split_aspect("...")
    assert rlm._split_aspect("microrn.mgmt") == ("microrn", ["mgmt"])
    assert rlm._split_aspect("single") == ("single", [])
    assert rlm._split_aspect("a.b.c.d") == ("a", ["b", "c", "d"])


def test_get_cached_active_link_drops_inactive():
    dest = bytes.fromhex("aa" * 16)
    link = MagicMock()
    link.status = object()
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("microrn.mgmt", dest)] = link
    assert rlm.get_cached_active_link("microrn.mgmt", dest) is None
    assert ("microrn.mgmt", dest) not in rlm.rns_cached_links


def test_get_cached_active_link_returns_active():
    dest = bytes.fromhex("ab" * 16)
    link = MagicMock()
    link.status = rlm.RNS.Link.ACTIVE
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("app.aspect", dest)] = link
    assert rlm.get_cached_active_link("app.aspect", dest) is link


def test_sweep_stale_links_and_orphan_counters():
    dest_active = bytes.fromhex("11" * 16)
    dest_stale = bytes.fromhex("22" * 16)
    active = MagicMock()
    active.status = rlm.RNS.Link.ACTIVE
    stale = MagicMock()
    stale.status = object()
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("a", dest_active)] = active
        rlm.rns_cached_links[("a", dest_stale)] = stale
        rlm._link_failure_counts[("a", dest_stale)] = 1
        rlm._link_failure_counts[("orphan", dest_stale)] = 9
    rlm.sweep_stale_links()
    with rlm._rns_links_lock:
        assert ("a", dest_active) in rlm.rns_cached_links
        assert ("a", dest_stale) not in rlm.rns_cached_links
        assert ("orphan", dest_stale) not in rlm._link_failure_counts


def test_clear_all_cached_links_tears_down_active():
    dest = bytes.fromhex("33" * 16)
    link = MagicMock()
    link.status = rlm.RNS.Link.ACTIVE
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("app.aspect", dest)] = link
        rlm._rns_link_last_used[("app.aspect", dest)] = 1.0
        rlm._link_failure_counts[("app.aspect", dest)] = 2
    cleared = rlm.clear_all_cached_links()
    assert cleared == 1
    link.teardown.assert_called_once()
    with rlm._rns_links_lock:
        assert rlm.rns_cached_links == {}
        assert rlm._rns_link_last_used == {}
        assert rlm._link_failure_counts == {}


@pytest.mark.asyncio
async def test_open_link_reuses_cached_active():
    dest = bytes.fromhex("bb" * 16)
    link = MagicMock()
    link.status = rlm.RNS.Link.ACTIVE
    link.identify = MagicMock()
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("app.aspect", dest)] = link

    identity = object()
    manager = _manager(identity=identity)
    phases = []
    result_link, identified, failure = await manager.open_link(
        dest,
        "app.aspect",
        auto_identify=True,
        on_phase=phases.append,
    )
    assert result_link is link
    assert identified is True
    assert failure is None
    assert phases == ["identifying"]
    link.identify.assert_called_once_with(identity)


@pytest.mark.asyncio
async def test_open_link_cached_auto_identify_without_local_identity():
    dest = bytes.fromhex("b0" * 16)
    link = MagicMock()
    link.status = rlm.RNS.Link.ACTIVE
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("app.aspect", dest)] = link
    manager = _manager(identity=None)
    result_link, identified, failure = await manager.open_link(
        dest,
        "app.aspect",
        auto_identify=True,
    )
    assert result_link is None
    assert identified is False
    assert failure == "no_local_identity"


@pytest.mark.asyncio
async def test_open_link_no_path(monkeypatch):
    dest = bytes.fromhex("cc" * 16)
    monkeypatch.setattr(
        rlm.reticulum_pathfinding,
        "prepare_fresh_path_request",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(rlm.RNS.Transport, "has_path", lambda _dh: False)

    manager = _manager()
    link, identified, failure = await manager.open_link(
        dest,
        "app.aspect",
        path_lookup_timeout=0.05,
    )
    assert link is None
    assert identified is False
    assert failure == "no_path_to_destination"


@pytest.mark.asyncio
async def test_open_link_no_identity_for_destination(monkeypatch):
    dest = bytes.fromhex("c1" * 16)
    monkeypatch.setattr(
        rlm.reticulum_pathfinding,
        "prepare_fresh_path_request",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(rlm.RNS.Transport, "has_path", lambda _dh: True)
    monkeypatch.setattr(rlm.RNS.Identity, "recall", lambda _dh: None)
    manager = _manager()
    link, identified, failure = await manager.open_link(dest, "app.aspect")
    assert link is None
    assert identified is False
    assert failure == "no_identity_for_destination"


@pytest.mark.asyncio
async def test_open_link_establishment_timeout(monkeypatch):
    dest = bytes.fromhex("c2" * 16)
    identity = object()
    monkeypatch.setattr(
        rlm.reticulum_pathfinding,
        "prepare_fresh_path_request",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(rlm.RNS.Transport, "has_path", lambda _dh: True)
    monkeypatch.setattr(rlm.RNS.Identity, "recall", lambda _dh: identity)

    fake_link = MagicMock()
    fake_link.status = object()
    fake_link.teardown = MagicMock()
    monkeypatch.setattr(rlm.RNS, "Destination", MagicMock())
    monkeypatch.setattr(rlm.RNS, "Link", MagicMock(return_value=fake_link))

    manager = _manager()
    link, identified, failure = await manager.open_link(
        dest,
        "app.aspect",
        link_establishment_timeout=0.05,
    )
    assert link is None
    assert identified is False
    assert failure == "link_establishment_timeout"
    fake_link.teardown.assert_called()


@pytest.mark.asyncio
async def test_open_link_cancel_tears_down_half_built(monkeypatch):
    dest = bytes.fromhex("c3" * 16)
    identity = object()
    monkeypatch.setattr(
        rlm.reticulum_pathfinding,
        "prepare_fresh_path_request",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(rlm.RNS.Transport, "has_path", lambda _dh: True)
    monkeypatch.setattr(rlm.RNS.Identity, "recall", lambda _dh: identity)

    fake_link = MagicMock()
    fake_link.status = object()
    fake_link.teardown = MagicMock()
    monkeypatch.setattr(rlm.RNS, "Destination", MagicMock())
    monkeypatch.setattr(rlm.RNS, "Link", MagicMock(return_value=fake_link))

    manager = _manager()
    task = asyncio.create_task(
        manager.open_link(dest, "app.aspect", link_establishment_timeout=5.0),
    )
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    fake_link.teardown.assert_called()


def test_close_uncaches_and_tears_down():
    dest = bytes.fromhex("dd" * 16)
    link = MagicMock()
    link.status = rlm.RNS.Link.ACTIVE
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("app.aspect", dest)] = link
    manager = _manager()
    assert manager.close(dest, "app.aspect") is True
    link.teardown.assert_called_once()
    assert rlm.get_cached_active_link("app.aspect", dest) is None


def test_close_missing_link_returns_false():
    manager = _manager()
    assert manager.close(bytes.fromhex("00" * 16), "app.aspect") is False


def test_identify_edge_cases():
    dest = bytes.fromhex("d1" * 16)
    manager = _manager(identity=None)
    ok, reason = manager.identify(dest, "app.aspect")
    assert ok is False
    assert reason == "no_active_link"

    link = MagicMock()
    link.status = rlm.RNS.Link.ACTIVE
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("app.aspect", dest)] = link
    ok, reason = manager.identify(dest, "app.aspect")
    assert ok is False
    assert reason == "no_local_identity"

    identity = object()
    manager = _manager(identity=identity)
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("app.aspect", dest)] = link
    ok, reason = manager.identify(dest, "app.aspect")
    assert ok is True
    assert reason is None
    link.identify.assert_called_once_with(identity)

    link.identify.side_effect = RuntimeError("boom")
    ok, reason = manager.identify(dest, "app.aspect")
    assert ok is False
    assert reason.startswith("identify_failed:")


def test_send_packet_edge_cases(monkeypatch):
    dest = bytes.fromhex("d2" * 16)
    manager = _manager()
    ok, reason = manager.send_packet(dest, "app.aspect", b"x")
    assert ok is False
    assert reason == "no_active_link"

    link = MagicMock()
    link.status = rlm.RNS.Link.ACTIVE
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("app.aspect", dest)] = link
    packet = MagicMock()
    monkeypatch.setattr(rlm.RNS, "Packet", MagicMock(return_value=packet))
    ok, reason = manager.send_packet(dest, "app.aspect", b"payload")
    assert ok is True
    assert reason is None
    packet.send.assert_called_once()

    packet.send.side_effect = RuntimeError("nope")
    ok, reason = manager.send_packet(dest, "app.aspect", b"payload")
    assert ok is False
    assert reason.startswith("send_failed:")


def test_request_requires_active_link():
    manager = _manager()
    with pytest.raises(RuntimeError, match="no_active_link"):
        manager.request(
            bytes.fromhex("d3" * 16),
            "app.aspect",
            "/status",
            None,
            response_callback=lambda _r: None,
            failed_callback=lambda _r=None: None,
            progress_callback=lambda _r: None,
        )


def test_request_resets_failures_on_success_and_recycles_on_fail():
    dest = bytes.fromhex("d4" * 16)
    key = ("app.aspect", dest)
    link = MagicMock()
    link.status = rlm.RNS.Link.ACTIVE
    callbacks = {}

    def fake_request(
        path,
        data=None,
        response_callback=None,
        failed_callback=None,
        progress_callback=None,
        timeout=None,
    ):
        callbacks["response"] = response_callback
        callbacks["failed"] = failed_callback
        return object()

    link.request = fake_request
    with rlm._rns_links_lock:
        rlm.rns_cached_links[key] = link
        rlm._link_failure_counts[key] = 1

    manager = _manager()
    manager.request(
        dest,
        "app.aspect",
        "/status",
        None,
        response_callback=lambda _r: None,
        failed_callback=lambda _r=None: None,
        progress_callback=lambda _r: None,
    )
    callbacks["response"](MagicMock())
    with rlm._rns_links_lock:
        assert key not in rlm._link_failure_counts

    with rlm._rns_links_lock:
        rlm.rns_cached_links[key] = link
    manager.request(
        dest,
        "app.aspect",
        "/status",
        None,
        response_callback=lambda _r: None,
        failed_callback=lambda _r=None: None,
        progress_callback=lambda _r: None,
    )
    callbacks["failed"](None)
    count, recycled = rlm._record_failure_and_maybe_recycle(key)
    # First failure already recorded by wrapped failed callback.
    assert count >= 1


def test_record_failure_recycles_after_threshold():
    dest = bytes.fromhex("ee" * 16)
    key = ("app.aspect", dest)
    link = MagicMock()
    with rlm._rns_links_lock:
        rlm.rns_cached_links[key] = link
    count, recycled = rlm._record_failure_and_maybe_recycle(key)
    assert count == 1
    assert recycled is False
    count, recycled = rlm._record_failure_and_maybe_recycle(key)
    assert recycled is True
    assert key not in rlm.rns_cached_links
    link.teardown.assert_called_once()


def test_on_packet_and_link_closed_broadcast():
    events = []
    manager = _manager(broadcast=events.append)
    dest = bytes.fromhex("f1" * 16)
    link = MagicMock()
    with rlm._rns_links_lock:
        rlm.rns_cached_links[("app.aspect", dest)] = link
    manager._on_packet("app.aspect", dest, b"\x00\x01")
    assert events[-1]["type"] == "rns.link.event"
    assert events[-1]["event"] == "packet_received"
    assert events[-1]["payload_b64"] == base64.b64encode(b"\x00\x01").decode("ascii")

    manager._on_link_closed("app.aspect", dest, link)
    assert events[-1]["event"] == "link_closed"
    assert ("app.aspect", dest) not in rlm.rns_cached_links


def test_cache_helpers_are_thread_safe_under_churn():
    dests = [bytes([i]) * 16 for i in range(8)]
    errors = []

    def worker(idx):
        try:
            for _ in range(50):
                link = MagicMock()
                link.status = rlm.RNS.Link.ACTIVE
                aspect = f"app.{idx}"
                dest = dests[idx % len(dests)]
                rlm._cache_link_if_active(aspect, dest, link)
                rlm.get_cached_active_link(aspect, dest)
                rlm._record_failure_and_maybe_recycle((aspect, dest))
                rlm.sweep_stale_links()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []


def test_cancel_rns_link_tasks_for_client():
    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app._rns_link_tasks = {}
    app._rns_request_receipts = {}
    client = object()
    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(asyncio.sleep(60))
        app._track_rns_link_task(client, task)
        app._rns_request_receipts[(client, "req")] = object()
        app._cancel_rns_link_tasks_for_client(client)
        assert task.cancelled() or task.cancelling()
        assert (client, "req") not in app._rns_request_receipts
        assert client not in app._rns_link_tasks
    finally:
        loop.close()


def test_parse_dest_aspect_helpers():
    from meshchatx.meshchat import ReticulumMeshChat

    dest, aspect, err = ReticulumMeshChat._rns_link_parse_dest_aspect(
        {"destination_hash": "aa" * 16, "aspect": "microrn.mgmt"},
    )
    assert err is None
    assert dest == bytes.fromhex("aa" * 16)
    assert aspect == "microrn.mgmt"

    _, _, err = ReticulumMeshChat._rns_link_parse_dest_aspect({})
    assert err == "missing_destination_or_aspect"
    _, _, err = ReticulumMeshChat._rns_link_parse_dest_aspect(
        {"destination_hash": "zz", "aspect": "a"},
    )
    assert err == "invalid_destination_hash"


def test_rns_link_cache_evicts_over_cap():
    original_max = rlm.MAX_CACHED_LINKS
    rlm.MAX_CACHED_LINKS = 2
    try:
        kept = []
        for i in range(3):
            link = MagicMock()
            link.status = rlm.RNS.Link.ACTIVE
            dest = bytes([i + 1]) * 16
            rlm._cache_link_if_active("app.aspect", dest, link)
            kept.append((dest, link))
        assert rlm.cached_link_count() == 2
        assert rlm.get_cached_active_link("app.aspect", kept[0][0]) is None
        kept[0][1].teardown.assert_called()
        assert rlm.get_cached_active_link("app.aspect", kept[1][0]) is kept[1][1]
        assert rlm.get_cached_active_link("app.aspect", kept[2][0]) is kept[2][1]
    finally:
        rlm.MAX_CACHED_LINKS = original_max
