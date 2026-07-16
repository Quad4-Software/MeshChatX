# SPDX-License-Identifier: 0BSD

import asyncio
import base64
import threading
import time
from collections.abc import Callable
from typing import Optional

import RNS

from meshchatx.src.backend import reticulum_pathfinding
from meshchatx.src.backend.reticulum_pathfinding import ReticulumLike

# Cache of established RNS Links keyed by (aspect_str, destination_hash_bytes).
# Kept separate from nomadnet_downloader.nomadnet_cached_links, as the two caches
# may merge in the future if NomadNet is ported onto this generic Links API.
rns_cached_links: dict[tuple[str, bytes], "RNS.Link"] = {}
_rns_link_last_used: dict[tuple[str, bytes], float] = {}
_rns_links_lock = threading.Lock()

# Per-cache-key count of consecutive RNS.Link request failures. Reset on
# successful response, and cleared whenever the cached link at the key is
# replaced or evicted. Guarded by _rns_links_lock (same lock as the cache,
# as the two are mutated together).
_link_failure_counts: dict[tuple[str, bytes], int] = {}

# Number of consecutive request failures on a cached link that triggers a
# teardown + cache eviction. The next request to the same destination will
# then go through the full open_link path and re-establish.
_LINK_RECYCLE_FAILURE_THRESHOLD = 2

# Cap active RNS links retained in process memory.
MAX_CACHED_LINKS = 64
LINK_IDLE_TTL_S = 30 * 60

# Wait granularity while polling for path / link (seconds).
_POLL_INTERVAL_S = 0.02


def cached_link_count() -> int:
    with _rns_links_lock:
        return len(rns_cached_links)


def get_cached_active_link(aspect: str, destination_hash: bytes):
    """Return a cached link if present and ACTIVE; drop stale entries."""
    key = (aspect, destination_hash)
    with _rns_links_lock:
        link = rns_cached_links.get(key)
        if link is None:
            return None
        if link.status is RNS.Link.ACTIVE:
            _rns_link_last_used[key] = time.time()
            return link
        try:
            del rns_cached_links[key]
        except KeyError:
            pass
        _rns_link_last_used.pop(key, None)
        _link_failure_counts.pop(key, None)
        return None


def _teardown_links(links) -> None:
    for link in links:
        if link is None:
            continue
        try:
            link.teardown()
        except Exception:
            pass


def _evict_over_cap_locked(preserve_key=None):
    """Evict oldest links until at or under MAX_CACHED_LINKS. Caller holds lock."""
    to_teardown = []
    while len(rns_cached_links) > MAX_CACHED_LINKS:
        candidates = [
            k for k in rns_cached_links if preserve_key is None or k != preserve_key
        ]
        if not candidates:
            break
        oldest_key = min(
            candidates,
            key=lambda k: _rns_link_last_used.get(k, 0.0),
        )
        to_teardown.append(rns_cached_links.pop(oldest_key, None))
        _rns_link_last_used.pop(oldest_key, None)
        _link_failure_counts.pop(oldest_key, None)
    return to_teardown


def sweep_stale_links():
    now = time.time()
    to_teardown = []
    with _rns_links_lock:
        stale = [
            k for k, v in rns_cached_links.items() if v.status is not RNS.Link.ACTIVE
        ]
        for k in stale:
            to_teardown.append(rns_cached_links.pop(k, None))
            _rns_link_last_used.pop(k, None)
            _link_failure_counts.pop(k, None)

        idle = [
            k
            for k, last in _rns_link_last_used.items()
            if k in rns_cached_links and now - last > LINK_IDLE_TTL_S
        ]
        for k in idle:
            to_teardown.append(rns_cached_links.pop(k, None))
            _rns_link_last_used.pop(k, None)
            _link_failure_counts.pop(k, None)

        to_teardown.extend(_evict_over_cap_locked())

        # Drop counter entries whose link is no longer cached so the dict
        # cannot grow unbounded across link churn.
        orphans = [k for k in _link_failure_counts if k not in rns_cached_links]
        for k in orphans:
            del _link_failure_counts[k]
        used_orphans = [k for k in _rns_link_last_used if k not in rns_cached_links]
        for k in used_orphans:
            del _rns_link_last_used[k]
    _teardown_links(to_teardown)


def clear_all_cached_links() -> int:
    """Tear down every cached RNS link (used after RNS hot reload).

    ``sweep_stale_links`` leaves ACTIVE links alone. After Transport reset those
    objects are tied to the old stack and must be dropped.
    """
    with _rns_links_lock:
        to_teardown = list(rns_cached_links.values())
        rns_cached_links.clear()
        _rns_link_last_used.clear()
        _link_failure_counts.clear()
    _teardown_links(to_teardown)
    return len(to_teardown)


def _cache_link_if_active(aspect: str, destination_hash: bytes, link) -> None:
    if link is None or link.status is not RNS.Link.ACTIVE:
        return
    key = (aspect, destination_hash)
    to_teardown = []
    with _rns_links_lock:
        rns_cached_links[key] = link
        _rns_link_last_used[key] = time.time()
        # A freshly cached link starts with a clean failure count, even if
        # an older link at the same key died with a non-zero count.
        _link_failure_counts.pop(key, None)
        to_teardown.extend(_evict_over_cap_locked(preserve_key=key))
    _teardown_links(to_teardown)


def _uncache_link_if_matches(aspect: str, destination_hash: bytes, link) -> None:
    if link is None:
        return
    key = (aspect, destination_hash)
    with _rns_links_lock:
        if rns_cached_links.get(key) is link:
            try:
                del rns_cached_links[key]
            except KeyError:
                pass
            _rns_link_last_used.pop(key, None)
            _link_failure_counts.pop(key, None)


def _reset_failure_count(key: tuple[str, bytes]) -> None:
    with _rns_links_lock:
        _link_failure_counts.pop(key, None)


def _record_failure_and_maybe_recycle(key: tuple[str, bytes]) -> tuple[int, bool]:
    """Increment the failure counter for `key`.

    If the threshold is reached, pop the cached link, clear the counter,
    and tear the link down outside the lock (teardown synchronously
    re-enters via _on_link_closed → _uncache_link_if_matches).
    Returns (new_count, recycled).
    """
    link_to_teardown = None
    with _rns_links_lock:
        n = _link_failure_counts.get(key, 0) + 1
        if n < _LINK_RECYCLE_FAILURE_THRESHOLD:
            _link_failure_counts[key] = n
            return n, False
        link_to_teardown = rns_cached_links.pop(key, None)
        _link_failure_counts.pop(key, None)
    if link_to_teardown is not None:
        try:
            link_to_teardown.teardown()
        except Exception as e:
            print(f"[rns_link_manager] recycle teardown raised: {e}")
    return n, True


def _split_aspect(aspect: str) -> tuple[str, list[str]]:
    parts = [p for p in aspect.split(".") if p]
    if not parts:
        raise ValueError("aspect must be a non-empty dot-separated string")
    return parts[0], parts[1:]


class RnsLinkManager:
    """Generic RNS Link lifecycle / request / packet helper.

    The web layer wires three callables:
      - self_identity_getter: returns the local RNS.Identity (or None).
      - reticulum_getter: returns the MeshChat reticulum-like (used by
        reticulum_pathfinding.prepare_fresh_path_request).
      - broadcast_event: called with a JSON-serializable dict; expected to
        forward to all interested /ws clients.
    """

    def __init__(
        self,
        *,
        self_identity_getter: Callable[[], Optional["RNS.Identity"]],
        reticulum_getter: Callable[[], ReticulumLike | None],
        broadcast_event: Callable[[dict], None],
    ):
        self._get_identity = self_identity_getter
        self._get_reticulum = reticulum_getter
        self._broadcast = broadcast_event

    async def open_link(
        self,
        destination_hash: bytes,
        aspect: str,
        *,
        auto_identify: bool = False,
        on_phase: Callable[[str], None] | None = None,
        path_lookup_timeout: float = 15.0,
        link_establishment_timeout: float = 15.0,
    ) -> tuple[Optional["RNS.Link"], bool, str | None]:
        """Open (or reuse) a Link to (aspect, destination_hash).

        Returns (link, identified, failure_reason). On failure link is None
        and failure_reason is set; otherwise failure_reason is None.
        """
        app_name, sub_aspects = _split_aspect(aspect)

        def _phase(p: str) -> None:
            if on_phase is not None:
                try:
                    on_phase(p)
                except Exception:
                    pass

        cached = get_cached_active_link(aspect, destination_hash)
        if cached is not None:
            identified = False
            if auto_identify:
                identity = self._get_identity()
                if identity is None:
                    return None, False, "no_local_identity"
                _phase("identifying")
                try:
                    cached.identify(identity)
                    identified = True
                except Exception as e:
                    return None, False, f"identify_failed: {e}"
            return cached, identified, None

        # Path lookup
        reticulum_pathfinding.prepare_fresh_path_request(
            self._get_reticulum(),
            destination_hash,
        )
        if not RNS.Transport.has_path(destination_hash):
            _phase("finding_path")
            deadline = time.time() + path_lookup_timeout
            try:
                while (
                    not RNS.Transport.has_path(destination_hash)
                    and time.time() < deadline
                ):
                    await asyncio.sleep(_POLL_INTERVAL_S)
            except asyncio.CancelledError:
                # No link object yet, so there is nothing to tear down. Just propagate.
                raise
        if not RNS.Transport.has_path(destination_hash):
            return None, False, "no_path_to_destination"

        # Re-check cache after path discovery (some other request may have
        # established a link in parallel).
        cached = get_cached_active_link(aspect, destination_hash)
        if cached is not None:
            identified = False
            if auto_identify:
                identity = self._get_identity()
                if identity is None:
                    return None, False, "no_local_identity"
                _phase("identifying")
                try:
                    cached.identify(identity)
                    identified = True
                except Exception as e:
                    return None, False, f"identify_failed: {e}"
            return cached, identified, None

        _phase("establishing_link")
        identity = RNS.Identity.recall(destination_hash)
        if identity is None:
            return None, False, "no_identity_for_destination"
        destination = RNS.Destination(
            identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            app_name,
            *sub_aspects,
        )

        link = RNS.Link(destination)
        link.set_packet_callback(
            lambda data, packet, _aspect=aspect, _dh=destination_hash: self._on_packet(
                _aspect,
                _dh,
                data,
            ),
        )
        link.set_link_closed_callback(
            lambda lnk, _aspect=aspect, _dh=destination_hash: self._on_link_closed(
                _aspect,
                _dh,
                lnk,
            ),
        )

        deadline = time.time() + link_establishment_timeout
        try:
            while link.status is not RNS.Link.ACTIVE and time.time() < deadline:
                await asyncio.sleep(_POLL_INTERVAL_S)
        except asyncio.CancelledError:
            # Caller bailed (typically: WS client disconnected). Tear down the
            # half-built link so it doesn't sit half-established consuming
            # RNS bookkeeping for the destination.
            try:
                link.teardown()
            except Exception:
                pass
            raise
        if link.status is not RNS.Link.ACTIVE:
            try:
                link.teardown()
            except Exception:
                pass
            return None, False, "link_establishment_timeout"

        _cache_link_if_active(aspect, destination_hash, link)

        identified = False
        if auto_identify:
            identity_local = self._get_identity()
            if identity_local is None:
                return None, False, "no_local_identity"
            _phase("identifying")
            try:
                link.identify(identity_local)
                identified = True
            except Exception as e:
                return None, False, f"identify_failed: {e}"

        return link, identified, None

    def identify(
        self,
        destination_hash: bytes,
        aspect: str,
    ) -> tuple[bool, str | None]:
        link = get_cached_active_link(aspect, destination_hash)
        if link is None:
            return False, "no_active_link"
        identity = self._get_identity()
        if identity is None:
            return False, "no_local_identity"
        try:
            link.identify(identity)
        except Exception as e:
            return False, f"identify_failed: {e}"
        return True, None

    def request(
        self,
        destination_hash: bytes,
        aspect: str,
        path: str,
        data,
        response_callback,
        failed_callback,
        progress_callback,
        timeout: float | None = None,
    ):
        link = get_cached_active_link(aspect, destination_hash)
        if link is None:
            raise RuntimeError("no_active_link")

        key = (aspect, destination_hash)

        def _wrapped_response(receipt, _cb=response_callback, _key=key):
            _reset_failure_count(_key)
            _cb(receipt)

        def _wrapped_failed(receipt=None, _cb=failed_callback, _key=key):
            _count, recycled = _record_failure_and_maybe_recycle(_key)
            if recycled:
                # The cached link has been torn down and evicted, so the next
                # rns.link.request to this destination will re-establish.
                # The existing link_closed event already fires from
                # _on_link_closed via link.teardown(), so clients that watch
                # for it can react.
                #
                # Future enhancement (option B from design): broadcast a
                # dedicated rns.link.event with
                # event="link_recycled_after_failures", failures=_count,
                # destination_hash=_key[1].hex(), aspect=_key[0], which is useful
                # for UIs that want to surface "link reset after N failures"
                # diagnostics distinct from a plain link_closed.
                pass
            _cb(receipt)

        return link.request(
            path,
            data=data,
            response_callback=_wrapped_response,
            failed_callback=_wrapped_failed,
            progress_callback=progress_callback,
            timeout=timeout,
        )

    def send_packet(
        self,
        destination_hash: bytes,
        aspect: str,
        payload: bytes,
    ) -> tuple[bool, str | None]:
        link = get_cached_active_link(aspect, destination_hash)
        if link is None:
            return False, "no_active_link"
        try:
            RNS.Packet(link, payload).send()
        except Exception as e:
            return False, f"send_failed: {e}"
        return True, None

    def close(self, destination_hash: bytes, aspect: str) -> bool:
        link = get_cached_active_link(aspect, destination_hash)
        if link is None:
            return False
        _uncache_link_if_matches(aspect, destination_hash, link)
        try:
            link.teardown()
        except Exception as e:
            print(f"[rns_link_manager] close teardown raised: {e}")
        return True

    def _on_packet(self, aspect: str, destination_hash: bytes, data: bytes) -> None:
        try:
            self._broadcast(
                {
                    "type": "rns.link.event",
                    "event": "packet_received",
                    "destination_hash": destination_hash.hex(),
                    "aspect": aspect,
                    "payload_b64": base64.b64encode(bytes(data)).decode("ascii"),
                },
            )
        except Exception:
            pass

    def _on_link_closed(self, aspect: str, destination_hash: bytes, link) -> None:
        _uncache_link_if_matches(aspect, destination_hash, link)
        try:
            self._broadcast(
                {
                    "type": "rns.link.event",
                    "event": "link_closed",
                    "destination_hash": destination_hash.hex(),
                    "aspect": aspect,
                },
            )
        except Exception:
            pass
