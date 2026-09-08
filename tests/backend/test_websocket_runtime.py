# SPDX-License-Identifier: 0BSD

"""Oracles for websocket_runtime helpers (rate limit, origin policy, envelope, peek)."""

from __future__ import annotations


from meshchatx.src.backend.websocket_runtime import (
    NOTIFY_WORTHY_TYPES,
    TokenBucket,
    apply_subscribe,
    client_allows_topic,
    default_subscriptions,
    message_rate_cost,
    peek_json_type,
    topic_for_type,
    truncate_plugin_payload,
    validate_ws_envelope,
    websocket_origin_policy_allows,
)


def test_token_bucket_allows_burst_then_rejects():
    bucket = TokenBucket(rate=1.0, burst=3.0)
    assert bucket.consume(1.0) is True
    assert bucket.consume(1.0) is True
    assert bucket.consume(1.0) is True
    assert bucket.consume(1.0) is False


def test_message_rate_cost_heavy_types():
    assert message_rate_cost("ping") == 1.0
    assert message_rate_cost("nomadnet.file.download") == 5.0
    assert message_rate_cost("rns.link.request") == 5.0


def test_validate_ws_envelope_rejects_bad_shapes():
    known = frozenset({"ping", "rns.link.open"})
    assert validate_ws_envelope([], known)[1] == "invalid_envelope"
    assert validate_ws_envelope({}, known)[1] == "missing_type"
    bad_dest = {
        "type": "rns.link.open",
        "destination_hash": "deadbeef",
        "aspect": "x",
        "request_id": "1",
    }
    assert validate_ws_envelope(bad_dest, known)[1] == "invalid_destination_hash"
    good = {
        "type": "rns.link.open",
        "destination_hash": "aa" * 16,
        "aspect": "x",
        "request_id": "1",
    }
    assert validate_ws_envelope(good, known) == ("rns.link.open", None)


def test_validate_rejects_oversized_b64():
    known = frozenset({"rns.link.send"})
    huge = "A" * (14 * 1024 * 1024 + 1)
    data = {
        "type": "rns.link.send",
        "destination_hash": "aa" * 16,
        "aspect": "x",
        "request_id": "1",
        "payload_b64": huge,
    }
    assert validate_ws_envelope(data, known)[1] == "payload_too_large"


class _Req:
    def __init__(self, origin=None, host="127.0.0.1:8000"):
        self.host = host
        self.scheme = "http"
        self.remote = "127.0.0.1"
        self.headers = {}
        if origin is not None:
            self.headers["Origin"] = origin


def test_origin_policy_requires_origin_on_non_loopback_without_auth():
    def origin_ok(request, _cidrs):
        return True

    def is_loopback(host):
        return host in ("127.0.0.1", "localhost")

    assert (
        websocket_origin_policy_allows(
            _Req(),
            listen_host="127.0.0.1",
            auth_enabled=False,
            trusted_proxy_cidrs=None,
            origin_allowed_fn=origin_ok,
            is_loopback_fn=is_loopback,
        )
        is True
    )
    assert (
        websocket_origin_policy_allows(
            _Req(),
            listen_host="0.0.0.0",  # nosec: BAN-B104
            auth_enabled=False,
            trusted_proxy_cidrs=None,
            origin_allowed_fn=origin_ok,
            is_loopback_fn=is_loopback,
        )
        is False
    )
    assert (
        websocket_origin_policy_allows(
            _Req(),
            listen_host="0.0.0.0",  # nosec: BAN-B104
            auth_enabled=True,
            trusted_proxy_cidrs=None,
            origin_allowed_fn=origin_ok,
            is_loopback_fn=is_loopback,
        )
        is True
    )


def test_topic_subscribe_defaults_allow_all():
    class C:
        pass

    c = C()
    assert client_allows_topic(c, "lxmf") is True
    apply_subscribe(c, ["lxmf"], subscribe=True)
    assert "lxmf" in c._meshchatx_ws_topics
    apply_subscribe(c, ["announce"], subscribe=False)
    # announce was in default set after first subscribe init
    assert "announce" not in c._meshchatx_ws_topics
    assert client_allows_topic(c, "announce") is False
    assert client_allows_topic(c, "lxmf") is True


def test_topic_for_type_mapping():
    assert topic_for_type("lxmf.delivery") == "lxmf"
    assert topic_for_type("nomadnet.page.download") == "nomad"
    assert topic_for_type("filesync.progress") == "filesync"
    assert topic_for_type("unknown.thing") == "other"


def test_peek_json_type_and_notify_allowlist():
    assert peek_json_type('{"type":"announce","x":1}') == "announce"
    assert peek_json_type('{"type":"telephone_ringing"}') == "telephone_ringing"
    assert "telephone_ringing" in NOTIFY_WORTHY_TYPES
    assert "announce" not in NOTIFY_WORTHY_TYPES


def test_truncate_plugin_payload():
    small = {"a": 1}
    assert truncate_plugin_payload(small) == small
    huge = {"blob": "x" * 70_000}
    out = truncate_plugin_payload(huge)
    assert isinstance(out, dict)
    assert out.get("_truncated") is True


def test_default_subscriptions_complete():
    subs = default_subscriptions()
    assert "config" in subs
    assert "lxmf" in subs
    assert "control" in subs
