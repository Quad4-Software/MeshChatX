# SPDX-License-Identifier: 0BSD
"""Stateful Hypothesis tests for the RRC hub connect lifecycle.

Drives randomized connect/disconnect/path-loss sequences through
RRCHub with the RNS boundary mocked, asserting the invariants behind
recent connect bugs:

* after a bounded window the hub is never parked in CONNECTING with no
  live link (the dead-link stall fixed in 4dd36c06)
* path requests stay deduplicated across rapid attempts
* disconnect() always tears the link down
"""

import contextlib
import threading
import time
from typing import ClassVar

import pytest
import RNS
from hypothesis import HealthCheck, settings
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)

import meshchatx.src.backend.rrc.manager as rrc_manager
from meshchatx.src.backend.rrc.manager import RRCHub, RRCManager


class FakeIdentity:
    def __init__(self, h=b"\x01" * 16):
        self.hash = h


class FakeLink:
    """Stand-in RNS Link; establishment driven by test flags."""

    made: ClassVar[list] = []
    _establish: ClassVar[threading.Event] = threading.Event()

    def __init__(self, dest, established_callback=None, closed_callback=None, **kw):
        self.destination = dest
        self.status = RNS.Link.PENDING
        self.established_callback = established_callback
        self.closed_callback = closed_callback
        self.torn_down = False
        FakeLink.made.append(self)
        if FakeLink._establish.is_set():
            self.status = RNS.Link.ACTIVE
            if established_callback:
                try:
                    established_callback(self)
                except Exception:
                    pass

    def set_packet_callback(self, cb):
        pass

    def identify(self, identity):
        pass

    def teardown(self):
        self.status = RNS.Link.CLOSED
        self.torn_down = True


def _install_fakes(monkeypatch, fake):
    state = {"path": False, "identity": False, "path_requests": 0}

    def has_path(h):
        return state["path"]

    def request_path(h):
        state["path_requests"] += 1

    def recall(h):
        return fake["identity"] if state["identity"] else None

    def fake_link(dest, **kw):
        return FakeLink(dest, **kw)

    monkeypatch.setattr(rrc_manager, "slowest_online_bitrate", lambda *a, **k: None)
    monkeypatch.setattr(rrc_manager, "path_response_window", lambda *a, **k: 0.05)
    monkeypatch.setattr(rrc_manager, "CONNECT_LINK_WATCHDOG_S", 0.5)
    monkeypatch.setattr(rrc_manager, "CONNECT_PATH_RETRY_S", 0.05)
    monkeypatch.setattr(RNS.Transport, "has_path", staticmethod(has_path))
    monkeypatch.setattr(RNS.Transport, "request_path", staticmethod(request_path))
    monkeypatch.setattr(RNS.Identity, "recall", staticmethod(recall))
    monkeypatch.setattr(RNS, "Link", fake_link)
    return state


class HubMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.tmp = self._tmpdir()
        self.manager = RRCManager(
            identity=FakeIdentity(),
            storage_dir=str(self.tmp),
            get_nickname=lambda: None,
        )
        self.hub = self.manager.add_hub(bytes(range(16)))
        self.hub.auto_reconnect = False
        self.state = self._install()
        self.workers = 0

    def _tmpdir(self):
        import tempfile

        return tempfile.mkdtemp(prefix="rrc-sm-")

    def _install(self):
        self._mp = pytest.MonkeyPatch.context()
        mp = self._mp.__enter__()
        fake = {"identity": FakeIdentity()}
        return _install_fakes(mp, fake)

    def teardown(self):
        with contextlib.suppress(Exception):
            self.hub.disconnect()
        with contextlib.suppress(Exception):
            self._mp.__exit__(None, None, None)

    # -- rules ---------------------------------------------------------

    @rule()
    def announce_arrives(self):
        """Announce delivers path + identity together."""
        self.state["path"] = True
        self.state["identity"] = True

    @rule()
    def announce_stops(self):
        self.state["path"] = False
        self.state["identity"] = False

    @rule()
    def attempt_connect(self):
        self.workers += 1
        self.hub._connect_worker()
        # Post-worker CONNECTING is only legitimate while a link exists.
        if self.hub.status == RRCHub.STATUS_CONNECTING:
            assert self.hub.link is not None
        else:
            assert self.hub.status in (
                RRCHub.STATUS_FAILED,
                RRCHub.STATUS_CONNECTED,
                RRCHub.STATUS_DISCONNECTED,
            )

    @rule()
    def link_never_establishes(self):
        """The dead-path case: link is created but never answers."""
        FakeLink._establish.clear()

    @rule()
    def link_establishes_fast(self):
        FakeLink._establish.set()

    @rule()
    def disconnect(self):
        self.hub.disconnect()
        assert self.hub.status == RRCHub.STATUS_DISCONNECTED
        with self.hub._lock:
            assert self.hub.link is None

    @rule()
    def wait_for_watchdog(self):
        """A PENDING link must be torn down by the establishment watchdog."""
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            with self.hub._lock:
                link = self.hub.link
            if link is None or link.status != RNS.Link.PENDING:
                break
            time.sleep(0.05)
        with self.hub._lock:
            link = self.hub.link
        if link is not None and link.status == RNS.Link.PENDING:
            pytest.fail("watchdog did not tear down a pending link")

    # -- invariants ------------------------------------------------------

    @invariant()
    def status_is_valid(self):
        assert self.hub.status in (0, 1, 2, 3)

    @invariant()
    def path_requests_bounded(self):
        # ~1 request per CONNECT_PATH_RETRY_S (mocked 0.05s) per ~0.05s
        # window plus slack: bound at 4 per worker call.
        assert self.state["path_requests"] <= max(1, self.workers * 4)

    @invariant()
    def connecting_implies_link_or_worker(self):
        if self.hub.status == RRCHub.STATUS_CONNECTING:
            assert self.hub.link is not None or self.workers == 0


TestHubMachine = HubMachine.TestCase
TestHubMachine.settings = settings(
    max_examples=40,
    stateful_step_count=25,
    deadline=None,
    suppress_health_check=(HealthCheck.data_too_large,),
)
