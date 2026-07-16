# SPDX-License-Identifier: 0BSD

"""Remote Reticulum management client for status and path queries.

Uses the same ``rnstransport.remote.management`` destination and request paths
as the bundled ``rnstatus`` / ``rnpath`` utilities (``-R`` / ``-i``).
"""

from __future__ import annotations

import contextlib
import threading
import time
from typing import Any

import RNS

from meshchatx.src.backend.management_identities import resolve_identity_path


def _truncated_hash_len() -> int:
    try:
        expected = int(RNS.Reticulum.TRUNCATED_HASHLENGTH) // 8 * 2
    except Exception:
        expected = 32
    return expected if expected > 0 else 32


def parse_remote_transport_hash(remote: str) -> bytes:
    """Parse a remote transport identity hash (hex)."""
    value = (remote or "").strip().lower()
    expected = _truncated_hash_len()
    if len(value) != expected:
        raise ValueError(
            f"Remote transport hash must be {expected} hexadecimal characters",
        )
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("Invalid remote transport hash") from exc


def management_destination_hash(transport_identity_hash: bytes) -> bytes:
    """Destination hash for remote management on a transport identity."""
    return RNS.Destination.hash_from_name_and_identity(
        "rnstransport.remote.management",
        transport_identity_hash,
    )


def _wait_for_path(destination_hash: bytes, timeout: float) -> None:
    if RNS.Transport.has_path(destination_hash):
        return
    RNS.Transport.request_path(destination_hash)
    started = time.time()
    while not RNS.Transport.has_path(destination_hash):
        if time.time() - started > timeout:
            raise TimeoutError("Path request timed out")
        time.sleep(0.05)


def _teardown_link(link: RNS.Link | None) -> None:
    if link is None:
        return
    with contextlib.suppress(Exception):
        link.teardown()


class _RemoteRequest:
    """One-shot authenticated request over a remote management link."""

    def __init__(
        self,
        destination_hash: bytes,
        identity: RNS.Identity,
        path: str,
        data: list[Any],
        timeout: float,
    ):
        self.destination_hash = destination_hash
        self.identity = identity
        self.path = path
        self.data = data
        self.timeout = timeout
        self._event = threading.Event()
        self._result: Any = None
        self._error: Exception | None = None
        self._link: RNS.Link | None = None

    def run(self) -> Any:
        _wait_for_path(self.destination_hash, self.timeout)
        remote_identity = RNS.Identity.recall(self.destination_hash)
        if remote_identity is None:
            raise RuntimeError("Could not recall remote transport identity")

        destination = RNS.Destination(
            remote_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "rnstransport",
            "remote",
            "management",
        )

        def on_response(receipt):
            self._result = receipt.response
            self._event.set()

        def on_failed(_receipt):
            self._error = RuntimeError(
                "Remote management request failed (likely authentication failure)",
            )
            self._event.set()

        def on_established(link):
            try:
                link.identify(self.identity)
                link.request(
                    self.path,
                    data=self.data,
                    response_callback=on_response,
                    failed_callback=on_failed,
                )
            except Exception as exc:
                self._error = exc
                self._event.set()

        def on_closed(link):
            if self._event.is_set():
                return
            reason = getattr(link, "teardown_reason", None)
            if reason == RNS.Link.TIMEOUT:
                self._error = TimeoutError("Remote management link timed out")
            elif reason == RNS.Link.DESTINATION_CLOSED:
                self._error = RuntimeError("Remote closed the management link")
            else:
                self._error = RuntimeError("Remote management link closed")
            self._event.set()

        self._link = RNS.Link(destination)
        self._link.set_link_established_callback(on_established)
        self._link.set_link_closed_callback(on_closed)

        try:
            if not self._event.wait(timeout=max(1.0, float(self.timeout))):
                raise TimeoutError("Remote management request timed out")
            if self._error is not None:
                raise self._error
            return self._result
        finally:
            _teardown_link(self._link)


def remote_request(
    *,
    remote_transport_hash: str,
    identity_path: str | None = None,
    identity_name: str | None = None,
    reticulum_config_dir: str | None = None,
    path: str,
    data: list[Any],
    timeout: float | None = None,
) -> Any:
    """Perform an authenticated remote management request."""
    transport_hash = parse_remote_transport_hash(remote_transport_hash)
    dest_hash = management_destination_hash(transport_hash)
    resolved = resolve_identity_path(
        reticulum_config_dir,
        identity_path=identity_path,
        identity_name=identity_name,
    )
    identity = RNS.Identity.from_file(resolved)
    if identity is None:
        raise ValueError(f"Could not load management identity from {resolved}")
    wait = (
        float(timeout)
        if timeout not in (None, "")
        else float(RNS.Transport.PATH_REQUEST_TIMEOUT)
    )
    return _RemoteRequest(dest_hash, identity, path, data, wait).run()


def fetch_remote_status(
    *,
    remote_transport_hash: str,
    identity_path: str | None = None,
    identity_name: str | None = None,
    reticulum_config_dir: str | None = None,
    include_link_stats: bool = False,
    timeout: float | None = None,
) -> tuple[dict[str, Any] | None, int | None]:
    """Fetch interface stats from a remote transport instance."""
    response = remote_request(
        remote_transport_hash=remote_transport_hash,
        identity_path=identity_path,
        identity_name=identity_name,
        reticulum_config_dir=reticulum_config_dir,
        path="/status",
        data=[bool(include_link_stats)],
        timeout=timeout,
    )
    if not isinstance(response, list) or not response:
        return None, None
    stats = response[0] if isinstance(response[0], dict) else None
    link_count = response[1] if len(response) > 1 else None
    try:
        link_count = int(link_count) if link_count is not None else None
    except (TypeError, ValueError):
        link_count = None
    return stats, link_count


def fetch_remote_path_table(
    *,
    remote_transport_hash: str,
    identity_path: str | None = None,
    identity_name: str | None = None,
    reticulum_config_dir: str | None = None,
    max_hops: int | None = None,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """Fetch the path table from a remote transport instance."""
    response = remote_request(
        remote_transport_hash=remote_transport_hash,
        identity_path=identity_path,
        identity_name=identity_name,
        reticulum_config_dir=reticulum_config_dir,
        path="/path",
        data=["table", None, max_hops],
        timeout=timeout,
    )
    if not isinstance(response, list):
        return []
    return [entry for entry in response if isinstance(entry, dict)]


def fetch_remote_rate_table(
    *,
    remote_transport_hash: str,
    identity_path: str | None = None,
    identity_name: str | None = None,
    reticulum_config_dir: str | None = None,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """Fetch the announce rate table from a remote transport instance."""
    response = remote_request(
        remote_transport_hash=remote_transport_hash,
        identity_path=identity_path,
        identity_name=identity_name,
        reticulum_config_dir=reticulum_config_dir,
        path="/path",
        data=["rates", None],
        timeout=timeout,
    )
    if not isinstance(response, list):
        return []
    return [entry for entry in response if isinstance(entry, dict)]
