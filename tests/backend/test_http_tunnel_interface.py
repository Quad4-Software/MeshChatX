# SPDX-License-Identifier: 0BSD

import threading
import time
from unittest.mock import MagicMock, patch

import RNS

from meshchatx.src.backend.data.interfaces.HTTPInterface import (
    HDLC,
    HTTPTunnelInterface,
)


def _reticulum_stub():
    inst = MagicMock()
    for name in (
        "_default_ic_max_held_announces",
        "_default_ic_burst_hold",
        "_default_ic_burst_freq_new",
        "_default_ic_burst_freq",
        "_default_ic_pr_burst_freq_new",
        "_default_ic_pr_burst_freq",
        "_default_ic_new_time",
        "_default_ic_burst_penalty",
        "_default_ic_held_release_interval",
        "_default_ec_pr_freq",
        "_default_ec_egress_control",
    ):
        getattr(inst, name).return_value = 0
    return inst


def _client_interface(poll_interval=0.1):
    cfg = {
        "name": "test-http-tunnel",
        "mode": "client",
        "server_url": "http://127.0.0.1:9/",
    }
    if poll_interval is not None:
        cfg["poll_interval"] = poll_interval
    with (
        patch.object(RNS.Reticulum, "get_instance", return_value=_reticulum_stub()),
        patch.object(HTTPTunnelInterface, "setup_client", lambda self: None),
    ):
        return HTTPTunnelInterface(MagicMock(), cfg)


def test_poll_interval_defaults_to_mesh_sane_value():
    iface = _client_interface(poll_interval=None)
    assert iface.poll_interval == HTTPTunnelInterface.DEFAULT_POLL_INTERVAL
    assert iface.poll_interval >= 2.0


def test_poll_interval_has_hard_floor_even_for_hand_edited_config():
    iface = _client_interface(poll_interval=0.1)
    assert iface.poll_interval == HTTPTunnelInterface.MIN_POLL_INTERVAL

    iface = _client_interface(poll_interval=0)
    assert iface.poll_interval == HTTPTunnelInterface.MIN_POLL_INTERVAL

    iface = _client_interface(poll_interval=2.5)
    assert iface.poll_interval == 2.5


def test_client_failure_backoff_still_grows_from_clamped_interval():
    iface = _client_interface(poll_interval=0.1)
    iface._consecutive_failures = 0
    iface._max_backoff = 30.0
    iface._client_exchange = MagicMock(side_effect=OSError("offline"))

    class StopAfterTwoWaits:
        def __init__(self):
            self.waits = []

        def is_set(self):
            return len(self.waits) >= 2

        def wait(self, delay):
            self.waits.append(delay)
            return True

    stop = StopAfterTwoWaits()
    iface._stop_event = stop
    iface.client_loop()

    assert stop.waits == [iface.poll_interval, iface.poll_interval * 2]


def test_long_poll_returns_queued_server_frame_promptly():
    iface = _client_interface(poll_interval=None)
    iface.online = True
    iface.check_user_agent = False
    iface.LONG_POLL_TIMEOUT = 0.5

    result = {}

    def call_handler():
        started = time.monotonic()
        status, content_type, body = iface._handle_tunnel_exchange(
            "POST",
            "/",
            {},
            b"",
        )
        result.update(
            status=status,
            content_type=content_type,
            body=body,
            elapsed=time.monotonic() - started,
        )

    worker = threading.Thread(target=call_handler, daemon=True)
    worker.start()
    time.sleep(0.03)
    iface.process_outgoing(b"abc")
    worker.join(timeout=1.0)

    assert not worker.is_alive()
    assert result["status"] == 200
    assert result["content_type"] == "application/octet-stream"
    assert result["body"] == HDLC.frame(b"abc")
    assert result["elapsed"] < 0.4
