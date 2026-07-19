"""Embeddable FileSyncService for Reticulum hosts."""

from __future__ import annotations

import contextlib
import os
import tempfile
import threading
import time
from collections.abc import Callable
from typing import Any

import RNS

from rns_filesync import protocol
from rns_filesync.constants import (
    ANNOUNCE_INTERVAL_DEFAULT,
    APP_NAME,
    ASPECT,
    BLOCK_SIZE,
    LINK_TIMEOUT_DEFAULT,
    PATH_TIMEOUT_DEFAULT,
    RECONNECT_BASE_INTERVAL,
    RECONNECT_MAX_INTERVAL,
    SCAN_INTERVAL,
)
from rns_filesync.inventory import (
    Inventory,
    decide_sync_action,
    differing_block_nums,
    hash_blocks,
    hash_file,
)
from rns_filesync.paths import PathJailError, normalize_relpath, resolve_under_root
from rns_filesync.peers import (
    create_outbound_destination,
    establish_link,
    hex_hash,
    parse_hash,
    peer_id_from_link,
    resolve_peer_identity,
    wait_for_path,
)
from rns_filesync.permissions import PermissionStore
from rns_filesync.transfer import (
    build_delta_payload,
    commit_received_file,
    create_empty_file,
)


class FileSyncService:
    """Peer-to-peer directory sync over Reticulum.

    Host programs inject identity and optionally an existing Reticulum instance.
    The service never constructs a second Reticulum stack when one already exists.
    """

    def __init__(
        self,
        *,
        identity,
        sync_directory: str,
        storage_dir: str | None = None,
        reticulum=None,
        configpath: str | None = None,
        permissions: PermissionStore | dict | None = None,
        own_reticulum: bool = False,
    ):
        self.identity = identity
        self.sync_directory = os.path.realpath(os.path.expanduser(sync_directory))
        self.storage_dir = storage_dir
        self.configpath = configpath
        self._provided_reticulum = reticulum
        self._own_reticulum = own_reticulum
        self.reticulum = None

        if isinstance(permissions, PermissionStore):
            self.permissions = permissions
        elif isinstance(permissions, dict):
            self.permissions = PermissionStore(permissions)
        else:
            self.permissions = PermissionStore()

        self.inventory = Inventory(self.sync_directory)
        self.destination = None

        self._lock = threading.RLock()
        self._links: dict[str, Any] = {}
        self._desired_peers: set[str] = set()
        self._incoming: dict[str, float] = {}
        self._outgoing: dict[tuple[str, str], float] = {}
        self._resources: dict[tuple[str, str], Any] = {}
        self._browse_results: dict[str, list[dict[str, Any]]] = {}
        self._browse_events: dict[str, threading.Event] = {}
        self._connect_attempts: set[str] = set()
        self._reconnect_backoff: dict[str, float] = {}

        self._running = False
        self._monitor = False
        self._announce_interval = ANNOUNCE_INTERVAL_DEFAULT
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

        self.on_peer_connected: Callable[[dict], None] | None = None
        self.on_peer_disconnected: Callable[[dict], None] | None = None
        self.on_sync_progress: Callable[[dict], None] | None = None
        self.on_file_updated: Callable[[dict], None] | None = None
        self.on_file_deleted: Callable[[dict], None] | None = None
        self.on_error: Callable[[dict], None] | None = None

    def _emit(self, callback: Callable | None, payload: dict) -> None:
        if callback is None:
            return
        try:
            callback(payload)
        except Exception as exc:
            RNS.log(f"FileSync callback error: {exc}", RNS.LOG_DEBUG)

    def _ensure_reticulum(self):
        if self.reticulum is not None:
            return self.reticulum
        existing = None
        with contextlib.suppress(Exception):
            existing = RNS.Reticulum.get_instance()
        if self._provided_reticulum is not None:
            self.reticulum = self._provided_reticulum
            self._own_reticulum = False
            return self.reticulum
        if existing is not None:
            self.reticulum = existing
            self._own_reticulum = False
            return self.reticulum
        self.reticulum = RNS.Reticulum(self.configpath)
        self._own_reticulum = True
        return self.reticulum

    def start(
        self,
        *,
        monitor: bool = True,
        announce_interval: int = ANNOUNCE_INTERVAL_DEFAULT,
    ) -> str:
        """Register inbound destination and start background workers."""
        with self._lock:
            if self._running:
                return hex_hash(self.destination.hash)

            os.makedirs(self.sync_directory, exist_ok=True)
            self._ensure_reticulum()
            self.inventory.load()
            self.inventory.scan()
            self.inventory.save()

            self.destination = RNS.Destination(
                self.identity,
                RNS.Destination.IN,
                RNS.Destination.SINGLE,
                APP_NAME,
                ASPECT,
            )
            self.destination.set_link_established_callback(self._on_link_established)

            self._running = True
            self._monitor = monitor
            self._announce_interval = max(10, int(announce_interval))
            self._stop_event.clear()

            self.destination.announce()
            RNS.log(
                f"FileSync started dest={RNS.prettyhexrep(self.destination.hash)} "
                f"id={RNS.prettyhexrep(self.identity.hash)} dir={self.sync_directory}",
                RNS.LOG_NOTICE,
            )

            self._threads = [
                threading.Thread(
                    target=self._announce_loop,
                    name="filesync-announce",
                    daemon=True,
                ),
                threading.Thread(
                    target=self._reconnect_loop,
                    name="filesync-reconnect",
                    daemon=True,
                ),
            ]
            if monitor:
                self._threads.append(
                    threading.Thread(
                        target=self._monitor_loop,
                        name="filesync-monitor",
                        daemon=True,
                    ),
                )
            for thread in self._threads:
                thread.start()

            return hex_hash(self.destination.hash)

    def stop(self) -> None:
        """Tear down links, destination, and worker threads."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            self._stop_event.set()

            links = list(self._links.values())
            self._links.clear()
            dest = self.destination
            self.destination = None

        for link in links:
            with contextlib.suppress(Exception):
                link.teardown()

        if dest is not None:
            with contextlib.suppress(Exception):
                RNS.Transport.deregister_destination(dest)

        for thread in self._threads:
            thread.join(timeout=2.0)
        self._threads = []
        RNS.log("FileSync stopped", RNS.LOG_INFO)

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            peers = len(self._links)
            files = len(self.inventory.snapshot())
            dest = hex_hash(self.destination.hash) if self.destination else None
            identity = hex_hash(self.identity.hash)
            running = self._running
        return {
            "running": running,
            "sync_directory": self.sync_directory,
            "identity_hash": identity,
            "destination_hash": dest,
            "peers": peers,
            "files": files,
            "whitelist": self.permissions.enabled,
            "monitor": self._monitor,
        }

    def list_peers(self) -> list[dict[str, Any]]:
        result = []
        with self._lock:
            items = list(self._links.items())
        for peer_id, link in items:
            result.append(
                {
                    "peer_id": peer_id,
                    "destination_hash": hex_hash(link.destination.hash),
                    "status": link.status,
                    "permissions": self.permissions.get(peer_id),
                },
            )
        return result

    def list_files(self) -> list[dict[str, Any]]:
        snap = self.inventory.snapshot()
        return [
            {
                "path": path,
                "hash": info.get("hash"),
                "size": info.get("size"),
                "mtime": info.get("mtime"),
            }
            for path, info in sorted(snap.items())
        ]

    def announce_now(self) -> None:
        if self.destination is not None:
            self.destination.announce()

    def connect_peer(
        self,
        identity_hash: str | bytes,
        timeout: float = PATH_TIMEOUT_DEFAULT,
    ) -> dict[str, Any]:
        """Connect using identity hash (destination hash accepted as fallback)."""
        peer_hash = parse_hash(identity_hash)
        peer_hex = hex_hash(peer_hash)

        with self._lock:
            for pid, link in self._links.items():
                if link.status in (RNS.Link.ACTIVE, RNS.Link.HANDSHAKE) and (
                    pid == peer_hex or hex_hash(link.destination.hash) == peer_hex
                ):
                    return {"ok": True, "peer_id": pid, "reused": True}

        identity, how = resolve_peer_identity(peer_hash)
        if identity is None:
            # Path request may populate known destinations for destination hashes.
            wait_for_path(peer_hash, timeout=min(timeout, 5.0))
            identity, how = resolve_peer_identity(peer_hash)
        if identity is None:
            msg = f"could not recall identity for {peer_hex}"
            self._emit(self.on_error, {"error": msg})
            return {"ok": False, "error": msg}

        destination = create_outbound_destination(identity)
        if not wait_for_path(destination.hash, timeout=timeout):
            msg = f"path timeout for {peer_hex}"
            self._emit(self.on_error, {"error": msg})
            return {"ok": False, "error": msg}

        link = establish_link(
            destination,
            established_callback=self._on_link_established,
            closed_callback=self._on_link_closed,
            timeout=LINK_TIMEOUT_DEFAULT,
        )
        if link is None:
            msg = f"link failed for {peer_hex}"
            self._emit(self.on_error, {"error": msg})
            return {"ok": False, "error": msg}

        # Reveal our identity to the remote so inbound ACL and peer slots work.
        with contextlib.suppress(Exception):
            link.identify(self.identity)

        self._configure_link(link)
        peer_id = peer_id_from_link(link) or hex_hash(identity.hash)
        with self._lock:
            self._links[peer_id] = link
            self._desired_peers.add(hex_hash(identity.hash))
            self._reconnect_backoff.pop(hex_hash(identity.hash), None)

        self._maybe_exchange_lists(link, peer_id)
        RNS.log(
            f"Connected to peer {peer_id} via {how}",
            RNS.LOG_INFO,
        )
        return {"ok": True, "peer_id": peer_id, "via": how}

    def disconnect_peer(self, peer_id: str) -> None:
        with self._lock:
            link = self._links.pop(peer_id, None)
            self._desired_peers.discard(peer_id)
        if link is not None:
            with contextlib.suppress(Exception):
                link.teardown()

    def browse_peer(self, peer_id: str, timeout: float = 10.0) -> list[dict[str, Any]]:
        link = self._get_link(peer_id)
        if link is None:
            return []
        event = threading.Event()
        with self._lock:
            self._browse_events[peer_id] = event
            self._browse_results.pop(peer_id, None)
        self._send(link, protocol.make_file_list_request(browser=True))
        event.wait(timeout=timeout)
        with self._lock:
            self._browse_events.pop(peer_id, None)
            return list(self._browse_results.get(peer_id, []))

    def download_file(self, peer_id: str, path: str) -> dict[str, Any]:
        link = self._get_link(peer_id)
        if link is None:
            return {"ok": False, "error": "peer not connected"}
        try:
            safe = normalize_relpath(path)
        except PathJailError as exc:
            return {"ok": False, "error": str(exc)}
        self._request_file(link, safe)
        return {"ok": True, "path": safe}

    def _get_link(self, peer_id: str):
        with self._lock:
            link = self._links.get(peer_id)
            if link is not None and link.status == RNS.Link.ACTIVE:
                return link
            for pid, candidate in self._links.items():
                if pid.startswith(peer_id) or peer_id.startswith(pid):
                    if candidate.status == RNS.Link.ACTIVE:
                        return candidate
        return None

    def _peer_key(self, link) -> str | None:
        return peer_id_from_link(link)

    def _require_perm(self, link, permission: str) -> bool:
        """Return True if the peer may perform permission (or ACL is open)."""
        if not self.permissions.enabled:
            return True
        peer_id = self._peer_key(link)
        if not peer_id:
            return False
        return self.permissions.check(peer_id, permission)

    def _configure_link(self, link) -> None:
        link.set_packet_callback(self._on_packet)
        link.set_resource_strategy(RNS.Link.ACCEPT_APP)
        link.set_resource_callback(self._on_resource_advert)
        link.set_resource_started_callback(self._on_resource_started)
        link.set_resource_concluded_callback(self._on_resource_concluded)
        if not hasattr(link, "upload_buffers"):
            link.upload_buffers = {}

    def _on_link_established(self, link) -> None:
        remote = None
        with contextlib.suppress(Exception):
            remote = link.get_remote_identity()

        if remote is None:
            # Never key inbound links by local destination hash: that collapses
            # every unidentified peer onto one _links entry.
            link.set_remote_identified_callback(self._on_remote_identified)
            link.set_link_closed_callback(self._on_link_closed)
            if self.permissions.enabled:
                return
            self._activate_peer_link(link, None)
            return

        if self.permissions.enabled and not self.permissions.can_connect(remote.hash):
            RNS.log(
                f"Rejecting peer {RNS.prettyhexrep(remote.hash)}",
                RNS.LOG_WARNING,
            )
            link.teardown()
            return

        self._activate_peer_link(link, remote)

    def _on_remote_identified(self, link, identity) -> None:
        if self.permissions.enabled and not self.permissions.can_connect(identity.hash):
            RNS.log(
                f"Rejecting identified peer {RNS.prettyhexrep(identity.hash)}",
                RNS.LOG_WARNING,
            )
            link.teardown()
            return
        real_id = hex_hash(identity.hash)
        with self._lock:
            had_link = any(value is link for value in self._links.values())
            for key, value in list(self._links.items()):
                if value is link and key != real_id:
                    self._links.pop(key, None)
            self._links[real_id] = link
            self._desired_peers.add(real_id)
        if had_link:
            self._configure_link(link)
            self._emit(
                self.on_peer_connected,
                {
                    "peer_id": real_id,
                    "permissions": self.permissions.get(real_id),
                },
            )
            self._maybe_exchange_lists(link, real_id)
            return
        self._activate_peer_link(link, identity)

    def _activate_peer_link(self, link, remote) -> None:
        self._configure_link(link)
        peer_id = peer_id_from_link(link)
        if peer_id is None and remote is not None:
            peer_id = hex_hash(remote.hash)
        provisional = False
        if peer_id is None:
            # Unique until remote identity arrives. Do not use destination.hash.
            peer_id = f"pending:{id(link)}"
            provisional = True
            with contextlib.suppress(Exception):
                link.set_remote_identified_callback(self._on_remote_identified)

        with self._lock:
            for key, value in list(self._links.items()):
                if value is link and key != peer_id:
                    self._links.pop(key, None)
            self._links[peer_id] = link
            if remote is not None and not provisional:
                self._desired_peers.add(hex_hash(remote.hash))

        self._emit(
            self.on_peer_connected,
            {"peer_id": peer_id, "permissions": self.permissions.get(peer_id)},
        )
        if not provisional:
            self._maybe_exchange_lists(link, peer_id)

    def _on_link_closed(self, link) -> None:
        peer_id = peer_id_from_link(link)
        with self._lock:
            if peer_id and self._links.get(peer_id) is link:
                self._links.pop(peer_id, None)
            else:
                for key, value in list(self._links.items()):
                    if value is link:
                        peer_id = key
                        self._links.pop(key, None)
                        break
        if peer_id:
            self._emit(self.on_peer_disconnected, {"peer_id": peer_id})

    def _maybe_exchange_lists(self, link, peer_id: str) -> None:
        allow = (not self.permissions.enabled) or self.permissions.check(
            peer_id,
            "read",
        )
        if not allow:
            RNS.log(
                f"Skipping file list for {peer_id}: no read permission",
                RNS.LOG_INFO,
            )
            return
        self._send_file_list(link, browser=False)
        time.sleep(0.05)
        self._send(link, protocol.make_file_list_request(browser=False))

    def _send(self, link, payload: bytes) -> None:
        try:
            packet = RNS.Packet(link, payload)
            packet.send()
        except Exception as exc:
            RNS.log(f"Packet send failed: {exc}", RNS.LOG_ERROR)

    def _send_file_list(self, link, browser: bool = False) -> None:
        if not self._require_perm(link, "read"):
            RNS.log("Denied file list: no read permission", RNS.LOG_WARNING)
            return
        files = self.inventory.scan()
        self.inventory.save()
        self._send(link, protocol.make_file_list(files, browser=browser))

    def _on_packet(self, message, packet) -> None:
        try:
            data = protocol.decode_message(message)
        except protocol.ProtocolError as exc:
            RNS.log(f"Bad protocol message: {exc}", RNS.LOG_DEBUG)
            return

        link = packet.link
        msg_type = data["type"]
        if msg_type == protocol.MSG_FILE_LIST:
            self._handle_file_list(data, link)
        elif msg_type == protocol.MSG_FILE_LIST_REQUEST:
            self._send_file_list(link, browser=bool(data.get("browser", False)))
        elif msg_type == protocol.MSG_FILE_REQUEST:
            self._handle_file_request(data, link)
        elif msg_type == protocol.MSG_DELTA_REQUEST:
            self._handle_delta_request(data, link)
        elif msg_type == protocol.MSG_EMPTY_FILE:
            self._handle_empty_file(data, link)
        elif msg_type == protocol.MSG_FILE_UPDATE:
            self._handle_file_update(data, link)
        elif msg_type == protocol.MSG_FILE_DELETION:
            self._handle_file_deletion(data, link)

    def _handle_file_list(self, data: dict, link) -> None:
        # Inbound inventory drives local writes. Require write when ACL is on.
        if not self._require_perm(link, "write"):
            RNS.log("Ignored peer file list: no write permission", RNS.LOG_WARNING)
            return

        peer_files = data.get("files") or {}
        browser = bool(data.get("browser", False))
        peer_id = self._peer_key(link) or "unknown"

        if browser:
            remote = []
            for path, info in peer_files.items():
                try:
                    safe = normalize_relpath(str(path))
                except PathJailError:
                    continue
                if not isinstance(info, dict):
                    continue
                remote.append(
                    {
                        "path": safe,
                        "size": info.get("size", 0),
                        "hash": info.get("hash"),
                        "mtime": info.get("mtime"),
                    },
                )
            with self._lock:
                self._browse_results[peer_id] = remote
                event = self._browse_events.get(peer_id)
            if event:
                event.set()
            return

        local = self.inventory.scan()
        for filepath, peer_info in peer_files.items():
            if not isinstance(peer_info, dict):
                continue
            try:
                safe = normalize_relpath(str(filepath))
            except PathJailError:
                RNS.log(
                    f"Rejected unsafe path from peer: {filepath!r}",
                    RNS.LOG_WARNING,
                )
                continue
            action = decide_sync_action(local.get(safe), peer_info)
            if action == "request_full":
                self._request_file(link, safe)
            elif action == "request_delta":
                self._request_delta(link, safe)

    def _request_file(self, link, filepath: str) -> None:
        with self._lock:
            if filepath in self._incoming:
                return
            self._incoming[filepath] = time.time()
        self._send(link, protocol.make_file_request(filepath))

    def _request_delta(self, link, filepath: str) -> None:
        with self._lock:
            if filepath in self._incoming:
                return
            self._incoming[filepath] = time.time()
        try:
            full_path = resolve_under_root(self.sync_directory, filepath)
            local_blocks = hash_blocks(full_path) if os.path.exists(full_path) else []
        except PathJailError:
            with self._lock:
                self._incoming.pop(filepath, None)
            return
        self._send(
            link,
            protocol.make_delta_request(filepath, [b["hash"] for b in local_blocks]),
        )

    def _begin_outgoing(self, link, filepath: str) -> tuple[str, str] | None:
        # Never collapse concurrent sends onto a shared "unknown" key.
        peer_id = self._peer_key(link) or f"link:{id(link)}"
        key = (peer_id, filepath)
        with self._lock:
            started = self._outgoing.get(key)
            if started is not None and time.time() - started < 86400:
                return None
            self._outgoing[key] = time.time()
        return key

    def _end_outgoing(self, key: tuple[str, str] | None) -> None:
        if key is None:
            return
        with self._lock:
            self._outgoing.pop(key, None)
            self._resources.pop(key, None)

    def _handle_file_request(self, data: dict, link) -> None:
        filepath = data.get("path")
        if not filepath:
            return
        if not self._require_perm(link, "read"):
            return
        try:
            safe = normalize_relpath(str(filepath))
            full_path = resolve_under_root(self.sync_directory, safe)
        except PathJailError:
            return

        if not os.path.isfile(full_path):
            return

        key = self._begin_outgoing(link, safe)
        if key is None:
            return

        file_size = os.path.getsize(full_path)
        file_hash = self.inventory.get(safe)
        digest = file_hash.get("hash") if file_hash else hash_file(full_path)

        if file_size == 0:
            self._send(link, protocol.make_empty_file(safe, digest))
            self._end_outgoing(key)
            return

        metadata = {
            "filepath": safe.encode("utf-8"),
            "hash": (digest or "").encode("utf-8"),
            "size": file_size,
        }

        peer_id = self._peer_key(link) or "unknown"

        def concluded(resource):
            try:
                if hasattr(resource, "data") and hasattr(resource.data, "close"):
                    with contextlib.suppress(Exception):
                        resource.data.close()
            finally:
                self._end_outgoing(key)

        try:
            handle = open(full_path, "rb")
            resource = RNS.Resource(
                handle,
                link,
                metadata=metadata,
                auto_compress=True,
                callback=concluded,
            )

            def progress(res):
                self._emit(
                    self.on_sync_progress,
                    {
                        "path": safe,
                        "direction": "send",
                        "progress": res.get_progress(),
                        "peer_id": peer_id,
                    },
                )

            resource.progress_callback(progress)
            with self._lock:
                self._resources[key] = resource
        except Exception as exc:
            RNS.log(f"Send failed for {safe}: {exc}", RNS.LOG_ERROR)
            self._end_outgoing(key)

    def _handle_delta_request(self, data: dict, link) -> None:
        filepath = data.get("path")
        peer_blocks = data.get("local_blocks") or []
        if not filepath:
            return
        if not self._require_perm(link, "read"):
            return
        if not isinstance(peer_blocks, list):
            return
        try:
            safe = normalize_relpath(str(filepath))
            full_path = resolve_under_root(self.sync_directory, safe)
        except PathJailError:
            return

        if not os.path.isfile(full_path):
            return

        key = self._begin_outgoing(link, safe)
        if key is None:
            return

        local_blocks = hash_blocks(full_path)
        # Only accept string hashes from the peer.
        safe_peer_blocks = [b for b in peer_blocks if isinstance(b, str)]
        blocks_to_send = differing_block_nums(local_blocks, safe_peer_blocks)
        if len(blocks_to_send) == len(local_blocks):
            self._end_outgoing(key)
            self._handle_file_request({"path": safe}, link)
            return

        info = self.inventory.get(safe) or {}
        digest = info.get("hash") or hash_file(full_path)
        size = info.get("size")
        if size is None:
            size = os.path.getsize(full_path)

        payload = build_delta_payload(full_path, blocks_to_send, BLOCK_SIZE)
        metadata = {
            "filepath": safe.encode("utf-8"),
            "hash": (digest or "").encode("utf-8"),
            "mode": "delta",
            "blocks": blocks_to_send,
            "size": size,
        }

        tmp = tempfile.NamedTemporaryFile(prefix=".rns-delta-", delete=False)
        tmp_path = tmp.name
        try:
            tmp.write(payload)
            tmp.flush()
            tmp.seek(0)
        except Exception:
            tmp.close()
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

        def concluded(resource):
            with contextlib.suppress(Exception):
                tmp.close()
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            self._end_outgoing(key)

        try:
            RNS.Resource(
                tmp,
                link,
                metadata=metadata,
                callback=concluded,
            )
        except Exception as exc:
            RNS.log(f"Delta send failed for {safe}: {exc}", RNS.LOG_ERROR)
            with contextlib.suppress(Exception):
                tmp.close()
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            self._end_outgoing(key)

    def _on_resource_advert(self, advertisement) -> bool:
        try:
            if self.permissions.enabled:
                sender = advertisement.link.get_remote_identity()
                if sender is None:
                    return False
                return self.permissions.check(sender.hash, "write")
            return True
        except Exception:
            return False

    def _on_resource_started(self, resource) -> None:
        def progress(res):
            path = None
            if res.metadata and isinstance(res.metadata, dict):
                path = protocol.decode_metadata_value(res.metadata.get("filepath"))
            self._emit(
                self.on_sync_progress,
                {
                    "path": path,
                    "direction": "receive",
                    "progress": res.get_progress(),
                },
            )

        resource.progress_callback(progress)

    def _on_resource_concluded(self, resource) -> None:
        if resource.status != RNS.Resource.COMPLETE:
            filepath = None
            if resource.metadata and isinstance(resource.metadata, dict):
                filepath = protocol.decode_metadata_value(
                    resource.metadata.get("filepath"),
                )
            if filepath:
                with self._lock:
                    self._incoming.pop(filepath, None)
            RNS.log(f"Incoming resource failed status={resource.status}", RNS.LOG_ERROR)
            return

        if not resource.metadata or not isinstance(resource.metadata, dict):
            return
        if "filepath" not in resource.metadata:
            return

        filepath = protocol.decode_metadata_value(resource.metadata.get("filepath"))
        expected_hash = (
            protocol.decode_metadata_value(resource.metadata.get("hash")) or None
        )
        if isinstance(expected_hash, str) and not expected_hash.strip():
            expected_hash = None
        mode = protocol.decode_metadata_value(resource.metadata.get("mode")) or "full"
        expected_size = resource.metadata.get("size")
        blocks = resource.metadata.get("blocks") or []

        if not self._require_perm(resource.link, "write"):
            with self._lock:
                self._incoming.pop(str(filepath), None)
            RNS.log(
                "Rejected resource: no write permission or unidentified peer",
                RNS.LOG_WARNING,
            )
            return

        try:
            safe = normalize_relpath(str(filepath))
            if not isinstance(blocks, list):
                raise ValueError("invalid delta block list")
            safe_blocks = [
                b for b in blocks if isinstance(b, int) and not isinstance(b, bool)
            ]
            commit_received_file(
                self.sync_directory,
                safe,
                mode="delta" if mode == "delta" else "full",
                resource_data=resource.data,
                block_nums=safe_blocks if mode == "delta" else None,
                expected_hash=expected_hash,
                expected_size=int(expected_size) if expected_size is not None else None,
                require_hash=True,
            )
            info = self.inventory.update_from_path(safe)
            self.inventory.save()
            with self._lock:
                self._incoming.pop(safe, None)
            self._emit(self.on_file_updated, {"path": safe, "info": info})
            self._broadcast_update(safe, exclude_link=resource.link)
            RNS.log(f"Received {safe}", RNS.LOG_INFO)
        except Exception as exc:
            with self._lock:
                self._incoming.pop(str(filepath), None)
            RNS.log(f"Failed to commit {filepath}: {exc}", RNS.LOG_ERROR)
            self._emit(self.on_error, {"error": str(exc), "path": filepath})

    def _handle_empty_file(self, data: dict, link) -> None:
        filepath = data.get("path")
        expected_hash = data.get("hash")
        if not filepath:
            return
        if not self._require_perm(link, "write"):
            return
        try:
            safe = normalize_relpath(str(filepath))
            create_empty_file(self.sync_directory, safe)
            full = resolve_under_root(self.sync_directory, safe)
            actual = hash_file(full)
            if expected_hash and actual != expected_hash:
                with contextlib.suppress(OSError):
                    os.remove(full)
                RNS.log(f"Empty file hash mismatch for {safe}", RNS.LOG_WARNING)
                return
            info = self.inventory.update_from_path(safe)
            self.inventory.save()
            self._emit(self.on_file_updated, {"path": safe, "info": info})
            self._broadcast_update(safe, exclude_link=link)
        except Exception as exc:
            RNS.log(f"Empty file handle failed: {exc}", RNS.LOG_ERROR)

    def _handle_file_update(self, data: dict, link) -> None:
        filepath = data.get("path")
        peer_info = data.get("info")
        if not filepath or not isinstance(peer_info, dict):
            return
        if not self._require_perm(link, "write"):
            return
        try:
            safe = normalize_relpath(str(filepath))
        except PathJailError:
            return
        local = self.inventory.get(safe)
        action = decide_sync_action(local, peer_info)
        if action == "request_full":
            self._request_file(link, safe)
        elif action == "request_delta":
            full = os.path.join(self.sync_directory, safe)
            if os.path.exists(full):
                self._request_delta(link, safe)
            else:
                self._request_file(link, safe)

    def _handle_file_deletion(self, data: dict, link) -> None:
        filepath = data.get("path")
        if not filepath:
            return
        if not self._require_perm(link, "delete"):
            return
        try:
            safe = normalize_relpath(str(filepath))
            full = resolve_under_root(self.sync_directory, safe)
        except PathJailError:
            return
        if os.path.isfile(full):
            with contextlib.suppress(OSError):
                os.remove(full)
        self.inventory.remove_file(safe)
        self.inventory.save()
        self._emit(self.on_file_deleted, {"path": safe})
        self._broadcast_deletion(safe, exclude_link=link)

    def _broadcast_update(self, filepath: str, exclude_link=None) -> None:
        info = self.inventory.get(filepath)
        if not info:
            return
        payload = protocol.make_file_update(filepath, info)
        with self._lock:
            links = list(self._links.values())
        for link in links:
            if link is exclude_link or link.status != RNS.Link.ACTIVE:
                continue
            self._send(link, payload)

    def _broadcast_deletion(self, filepath: str, exclude_link=None) -> None:
        payload = protocol.make_file_deletion(filepath)
        with self._lock:
            links = list(self._links.values())
        for link in links:
            if link is exclude_link or link.status != RNS.Link.ACTIVE:
                continue
            self._send(link, payload)

    def _announce_loop(self) -> None:
        last = time.time()
        while not self._stop_event.wait(10):
            if time.time() - last >= self._announce_interval:
                with contextlib.suppress(Exception):
                    if self.destination is not None:
                        self.destination.announce()
                        last = time.time()

    def _monitor_loop(self) -> None:
        while not self._stop_event.wait(SCAN_INTERVAL):
            try:
                self._monitor_once()
            except Exception as exc:
                RNS.log(f"Monitor error: {exc}", RNS.LOG_DEBUG)

    def _monitor_once(self) -> None:
        previous = self.inventory.snapshot()
        current = self.inventory.scan()
        old_paths = set(previous)
        new_paths = set(current)
        added = new_paths - old_paths
        removed = old_paths - new_paths
        modified = [
            path
            for path in (old_paths & new_paths)
            if previous[path].get("hash") != current[path].get("hash")
        ]
        if not (added or removed or modified):
            return
        self.inventory.save()
        for path in added:
            self._broadcast_update(path)
            self._emit(
                self.on_file_updated,
                {"path": path, "info": current[path], "reason": "added"},
            )
        for path in modified:
            self._broadcast_update(path)
            self._emit(
                self.on_file_updated,
                {"path": path, "info": current[path], "reason": "modified"},
            )
        for path in removed:
            self._broadcast_deletion(path)
            self._emit(self.on_file_deleted, {"path": path, "reason": "removed"})

    def _reconnect_loop(self) -> None:
        while not self._stop_event.wait(RECONNECT_BASE_INTERVAL):
            try:
                self._reconnect_once()
            except Exception as exc:
                RNS.log(f"Reconnect error: {exc}", RNS.LOG_DEBUG)

    def _reconnect_once(self) -> None:
        with self._lock:
            desired = list(self._desired_peers)
            connected = set()
            for peer_id, link in self._links.items():
                if link.status in (RNS.Link.ACTIVE, RNS.Link.HANDSHAKE):
                    connected.add(peer_id)

        now = time.time()
        for peer_id in desired:
            if peer_id in connected:
                with self._lock:
                    self._reconnect_backoff.pop(peer_id, None)
                continue
            with self._lock:
                if peer_id in self._connect_attempts:
                    continue
                next_at = self._reconnect_backoff.get(peer_id, 0)
                if now < next_at:
                    continue
                self._connect_attempts.add(peer_id)

            def job(target=peer_id):
                try:
                    result = self.connect_peer(target, timeout=PATH_TIMEOUT_DEFAULT)
                    with self._lock:
                        if result.get("ok"):
                            self._reconnect_backoff.pop(target, None)
                        else:
                            prev = self._reconnect_backoff.get(
                                target,
                                RECONNECT_BASE_INTERVAL,
                            )
                            delay = min(
                                max(prev * 2, RECONNECT_BASE_INTERVAL),
                                RECONNECT_MAX_INTERVAL,
                            )
                            self._reconnect_backoff[target] = time.time() + delay
                finally:
                    with self._lock:
                        self._connect_attempts.discard(target)

            threading.Thread(target=job, daemon=True).start()
