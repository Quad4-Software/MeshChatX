# SPDX-License-Identifier: 0BSD
"""Runtime helpers for WebSocket hardening: rate limits, caps, topics, seq, idle.

Kept separate from websocket_config_guard so auth classification stays small.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

# Inbound control: generous so normal UI never trips.
WS_RATE_RATE = 30.0
WS_RATE_BURST = 60.0
WS_RATE_ABUSE_STRIKES = 8
WS_RATE_RETRY_AFTER_SEC = 1.0

# Cost multipliers for expensive mutators (tokens consumed per message).
WS_RATE_COST_HEAVY = 5.0
WS_HEAVY_TYPES = frozenset(
    {
        "nomadnet.file.download",
        "nomadnet.page.download",
        "nomadnet.page.archive.add",
        "rns.link.request",
        "rns.link.open",
        "lxm.generate_paper_uri",
        "lxm.ingest_uri",
    },
)

# Application caps (bytes of decoded payload / string length). Global frame
# max stays 50 MiB until Nomad chunking ships.
WS_NOMAD_FILE_MAX_BYTES = 10 * 1024 * 1024
WS_NOMAD_PAGE_MAX_CHARS = 4 * 1024 * 1024
WS_ARCHIVE_CONTENT_MAX_CHARS = 4 * 1024 * 1024
WS_B64_FIELD_MAX_CHARS = 14 * 1024 * 1024
WS_PAPER_URI_MAX_CHARS = 12 * 1024 * 1024
WS_PLUGIN_EVENT_PAYLOAD_MAX_CHARS = 65_536

WS_IDLE_TIMEOUT_SEC = 90.0
WS_BROADCAST_SEND_TIMEOUT_SEC = 5.0
WS_SEQ_RING_SIZE = 256

WS_ALL_TOPICS = frozenset(
    {
        "lxmf",
        "announce",
        "nomad",
        "telephone",
        "rrc",
        "filesync",
        "rns.link",
        "plugin",
        "sessions",
        "config",
        "control",
        "other",
    },
)

_TYPE_TOPIC: dict[str, str] = {
    "config": "config",
    "config.changed": "config",
    "app.sessions.updated": "sessions",
    "pong": "control",
    "error": "control",
    "announce": "announce",
    "announced": "announce",
    "lxmf.delivery": "lxmf",
    "lxmf_message_created": "lxmf",
    "lxmf_message_state_updated": "lxmf",
    "lxmf.telemetry": "lxmf",
    "lxmf.forwarding.rules": "lxmf",
    "lxm.generate_paper_uri.result": "lxmf",
    "lxm.ingest_uri.result": "lxmf",
    "nomadnet.page.download": "nomad",
    "nomadnet.file.download": "nomad",
    "nomadnet.download.cancelled": "nomad",
    "nomadnet.page.archives": "nomad",
    "nomadnet.page.archive.added": "nomad",
    "telephone_ringing": "telephone",
    "telephone_call_ended": "telephone",
    "telephone_call_established": "telephone",
    "telephone_missed_call": "telephone",
    "rrc.message": "rrc",
    "rrc.change": "rrc",
    "rrc.server.change": "rrc",
    "plugin.event": "plugin",
    "rns.link.event": "rns.link",
    "rns.link.open": "rns.link",
    "rns.link.identify": "rns.link",
    "rns.link.request": "rns.link",
    "rns.link.send": "rns.link",
    "rns.link.close": "rns.link",
}

for _prefix in (
    "filesync.",
    "rncp.",
    "rnsh.",
    "rnx.",
):
    pass

COALESCE_TYPES = frozenset({"announce", "lxmf.telemetry"})
COALESCE_WINDOW_SEC = 0.08


class WsRuntimeCounters:
    """Process-wide WS debug counters."""

    __slots__ = (
        "broadcast_failures",
        "idle_closes",
        "msgs_in",
        "msgs_out",
        "rate_limit_hits",
        "slow_drops",
    )

    def __init__(self) -> None:
        self.msgs_in = 0
        self.msgs_out = 0
        self.rate_limit_hits = 0
        self.broadcast_failures = 0
        self.slow_drops = 0
        self.idle_closes = 0

    def snapshot(self, *, client_count: int = 0) -> dict[str, int]:
        return {
            "clients": int(client_count),
            "msgs_in": self.msgs_in,
            "msgs_out": self.msgs_out,
            "rate_limit_hits": self.rate_limit_hits,
            "broadcast_failures": self.broadcast_failures,
            "slow_drops": self.slow_drops,
            "idle_closes": self.idle_closes,
        }


class TokenBucket:
    """Per-connection token bucket."""

    __slots__ = ("burst", "rate", "tokens", "updated")

    def __init__(
        self, rate: float = WS_RATE_RATE, burst: float = WS_RATE_BURST
    ) -> None:
        self.rate = float(rate)
        self.burst = float(burst)
        self.tokens = float(burst)
        self.updated = time.monotonic()

    def consume(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.updated
        self.updated = now
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        if self.tokens < cost:
            return False
        self.tokens -= cost
        return True


def message_rate_cost(msg_type: str | None) -> float:
    if msg_type in WS_HEAVY_TYPES:
        return WS_RATE_COST_HEAVY
    return 1.0


def topic_for_type(msg_type: str | None) -> str:
    if not msg_type or not isinstance(msg_type, str):
        return "other"
    if msg_type in _TYPE_TOPIC:
        return _TYPE_TOPIC[msg_type]
    if msg_type.startswith("filesync."):
        return "filesync"
    if msg_type.startswith("rns.link."):
        return "rns.link"
    if msg_type.startswith("nomadnet."):
        return "nomad"
    if msg_type.startswith("lxmf") or msg_type.startswith("lxm."):
        return "lxmf"
    if msg_type.startswith("telephone"):
        return "telephone"
    if msg_type.startswith("rrc."):
        return "rrc"
    if msg_type.startswith(("rncp.", "rnsh.", "rnx.")):
        return "other"
    return "other"


def default_subscriptions() -> set[str]:
    return set(WS_ALL_TOPICS)


def client_allows_topic(client, topic: str) -> bool:
    subs = getattr(client, "_meshchatx_ws_topics", None)
    if subs is None:
        return True
    return topic in subs


def apply_subscribe(client, topics: object, *, subscribe: bool) -> list[str]:
    if not isinstance(topics, list):
        return []
    current = getattr(client, "_meshchatx_ws_topics", None)
    if current is None:
        current = default_subscriptions()
        client._meshchatx_ws_topics = current
    changed: list[str] = []
    for raw in topics:
        if not isinstance(raw, str):
            continue
        name = raw.strip()
        if name not in WS_ALL_TOPICS:
            continue
        if subscribe:
            if name not in current:
                current.add(name)
                changed.append(name)
        elif name in current:
            current.discard(name)
            changed.append(name)
    return changed


def touch_client_activity(client) -> None:
    try:
        client._meshchatx_last_activity = time.monotonic()
    except (AttributeError, TypeError):
        pass


def client_is_idle(
    client, *, now: float | None = None, timeout: float = WS_IDLE_TIMEOUT_SEC
) -> bool:
    try:
        last = getattr(client, "_meshchatx_last_activity", None)
    except Exception:
        return False
    if last is None:
        return False
    t = time.monotonic() if now is None else now
    return (t - float(last)) > timeout


def init_client_runtime(client) -> TokenBucket:
    bucket = TokenBucket()
    try:
        client._meshchatx_rate_bucket = bucket
        client._meshchatx_rate_strikes = 0
        client._meshchatx_ws_topics = None
        client._meshchatx_last_activity = time.monotonic()
        client._meshchatx_binary_rns_link = False
    except (AttributeError, TypeError):
        pass
    return bucket


def get_client_bucket(client) -> TokenBucket:
    bucket = getattr(client, "_meshchatx_rate_bucket", None)
    if bucket is None:
        bucket = init_client_runtime(client)
    return bucket


async def send_ws_error(
    client,
    *,
    message: str,
    code: str,
    request_id: object = None,
    retry_after: float | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "error",
        "message": message,
        "code": code,
    }
    if request_id is not None:
        payload["request_id"] = request_id
    if retry_after is not None:
        payload["retry_after"] = retry_after
    try:
        await client.send_str(json.dumps(payload))
    except Exception:
        logger.debug("failed to send ws error %s", code, exc_info=True)


def validate_ws_envelope(
    data: object, known_types: frozenset[str] | set[str]
) -> tuple[str | None, str | None]:
    """Return (msg_type, error_code). error_code set means reject."""
    if not isinstance(data, dict):
        return None, "invalid_envelope"
    msg_type = data.get("type")
    if not isinstance(msg_type, str) or not msg_type.strip():
        return None, "missing_type"
    msg_type = msg_type.strip()
    request_id = data.get("request_id")
    if request_id is not None and not isinstance(request_id, (str, int)):
        return msg_type, "invalid_request_id"
    if msg_type in known_types or msg_type in (
        "ws.subscribe",
        "ws.unsubscribe",
        "sync.subscribe",
        "ws.caps",
    ):
        err = _validate_known_fields(msg_type, data)
        if err:
            return msg_type, err
        return msg_type, None
    # Unknown types still dispatch for fail-closed auth; no field schema.
    return msg_type, None


def _validate_known_fields(msg_type: str, data: dict) -> str | None:
    if msg_type.startswith("rns.link."):
        dest = data.get("destination_hash")
        if dest is not None:
            if not isinstance(dest, str):
                return "invalid_destination_hash"
            try:
                raw = bytes.fromhex(dest)
            except ValueError:
                return "invalid_destination_hash"
            if len(raw) != 16:
                return "invalid_destination_hash"
        for key in ("data_b64", "payload_b64", "body_b64"):
            val = data.get(key)
            if val is not None:
                if not isinstance(val, str):
                    return "invalid_b64_field"
                if len(val) > WS_B64_FIELD_MAX_CHARS:
                    return "payload_too_large"
    if msg_type == "lxm.ingest_uri":
        uri = data.get("uri")
        if uri is not None:
            if not isinstance(uri, str):
                return "invalid_uri"
            if len(uri) > WS_PAPER_URI_MAX_CHARS:
                return "payload_too_large"
    if msg_type == "nomadnet.page.archive.add":
        content = data.get("content")
        if content is not None:
            if not isinstance(content, str):
                return "invalid_content"
            if len(content) > WS_ARCHIVE_CONTENT_MAX_CHARS:
                return "payload_too_large"
    if msg_type in ("ws.subscribe", "ws.unsubscribe"):
        topics = data.get("topics")
        if topics is not None and not isinstance(topics, list):
            return "invalid_topics"
    if msg_type == "sync.subscribe":
        since = data.get("since_seq")
        if since is not None and not isinstance(since, int):
            return "invalid_since_seq"
    return None


def websocket_origin_policy_allows(
    request,
    *,
    listen_host: str | None,
    auth_enabled: bool,
    trusted_proxy_cidrs: str | None,
    origin_allowed_fn,
    is_loopback_fn,
) -> bool:
    """Same-authority Origin check, plus require Origin on non-loopback when auth off."""
    if not origin_allowed_fn(request, trusted_proxy_cidrs):
        return False
    origin = request.headers.get("Origin")
    missing = origin is None or not str(origin).strip()
    if not missing:
        return True
    if auth_enabled:
        return True
    if is_loopback_fn(listen_host):
        return True
    logger.warning(
        "Rejected WebSocket upgrade with missing Origin on non-loopback bind %r",
        listen_host,
    )
    return False


class BroadcastSeqState:
    """Monotonic seq + small ring of recent critical event ids."""

    __slots__ = ("_lock", "ring", "seq")

    def __init__(self) -> None:
        self.seq = 0
        self.ring: deque[tuple[int, str]] = deque(maxlen=WS_SEQ_RING_SIZE)
        self._lock = asyncio.Lock()

    async def stamp(self, payload: dict[str, Any]) -> int:
        async with self._lock:
            self.seq += 1
            n = self.seq
            payload["seq"] = n
            t = payload.get("type")
            if isinstance(t, str):
                self.ring.append((n, t))
            return n

    def gap_hint(self, since_seq: int) -> dict[str, Any]:
        if since_seq >= self.seq:
            return {"status": "ok", "since_seq": since_seq, "current_seq": self.seq}
        known = [n for n, _ in self.ring if n > since_seq]
        return {
            "status": "gap",
            "since_seq": since_seq,
            "current_seq": self.seq,
            "buffered": len(known),
            "resync": True,
        }


class CoalesceBuffer:
    """Merge high-frequency announce/telemetry within a short window."""

    def __init__(self, flush_cb, window_sec: float = COALESCE_WINDOW_SEC) -> None:
        self._flush_cb = flush_cb
        self._window = window_sec
        self._pending: dict[str, Any] = {}
        self._task: asyncio.Task | None = None

    def offer(self, payload: dict[str, Any]) -> bool:
        t = payload.get("type")
        if t not in COALESCE_TYPES:
            return False
        self._pending[t] = payload
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._delayed_flush())
        return True

    async def _delayed_flush(self) -> None:
        try:
            await asyncio.sleep(self._window)
            pending = self._pending
            self._pending = {}
            for payload in pending.values():
                await self._flush_cb(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.debug("coalesce flush failed", exc_info=True)

    async def flush_now(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        pending = self._pending
        self._pending = {}
        for payload in pending.values():
            await self._flush_cb(payload)


def truncate_plugin_payload(payload: object) -> object:
    try:
        encoded = json.dumps(payload, default=str)
    except (TypeError, ValueError):
        return {}
    if len(encoded) <= WS_PLUGIN_EVENT_PAYLOAD_MAX_CHARS:
        return payload
    return {"_truncated": True, "size": len(encoded)}


def peek_json_type(raw: str, *, max_scan: int = 256) -> str | None:
    """Cheap type peek for Android notify filtering without full parse."""
    if not isinstance(raw, str) or not raw:
        return None
    head = raw[:max_scan]
    marker = '"type"'
    idx = head.find(marker)
    if idx < 0:
        return None
    rest = head[idx + len(marker) :]
    colon = rest.find(":")
    if colon < 0:
        return None
    rest = rest[colon + 1 :].lstrip()
    if not rest.startswith('"'):
        return None
    end = rest.find('"', 1)
    if end < 0:
        return None
    return rest[1:end]


NOTIFY_WORTHY_TYPES = frozenset(
    {
        "telephone_ringing",
        "telephone_call_ended",
        "telephone_call_established",
        "telephone_missed_call",
        "lxmf.delivery",
        "lxmf_message_created",
    },
)

# Chunked Nomad delivery (Phase 4): small payloads stay single-frame.
WS_NOMAD_CHUNK_THRESHOLD = 256 * 1024
WS_NOMAD_CHUNK_SIZE = 192 * 1024
WS_CONTROL_MAX_MSG_SIZE = 2 * 1024 * 1024
