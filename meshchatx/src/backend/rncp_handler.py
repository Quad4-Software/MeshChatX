# SPDX-License-Identifier: 0BSD

import asyncio
import contextlib
import os
import shutil
import time
from collections.abc import Callable

import RNS

from .path_utils import link_establishment_window, path_response_window

# Identity-storage tops that must not be RNCP-sent or used as fetch save dirs.
# rncp_received / rncp_shared stay allowed so a received file can be re-sent.
_RESERVED_RNCP_TOP = frozenset(
    {
        "identity",
        "identity.bak",
        "identities",
        "session_secret",
        "app_security.json",
        "ssl",
        "database.db",
        "lxmf",
        "lxmf_router",
        "plugins",
        "database-backups",
        "snapshots",
        "bots",
        "telephone",
        "rrc_history",
        "rrc_server",
        "page_nodes",
        "map_overlays",
        "reticulum-docs",
        "meshchatx-docs",
        "repository-server",
    },
)

_FORBIDDEN_RECEIVED_NAMES = frozenset(
    {
        "identity",
        "identity.bak",
        "session_secret",
        "app_security.json",
        "database.db",
    },
)

TERMINAL_TRANSFER_STATUSES = frozenset({"completed", "failed", "error", "cancelled"})
MAX_RETAINED_TRANSFERS = 32
MAX_CANCELLED_TRANSFER_IDS = 128


class RNCPHandler:
    APP_NAME = "rncp"
    REQ_FETCH_NOT_ALLOWED = 0xF0

    def __init__(self, reticulum_instance, identity, storage_dir):
        self.reticulum = reticulum_instance
        self.identity = identity
        self.storage_dir = storage_dir
        self.active_transfers = {}
        self.receive_destination = None
        self.fetch_jail = None
        self.fetch_auto_compress = True
        self.allow_overwrite_on_receive = False
        self.allowed_identity_hashes = []
        self._listener_fetch_registered = False
        self._listener_fetch_allowed = False
        self.on_receive_completed = None
        self._cancelled_transfers: set[str] = set()

    def _emit_receive_event(self, payload):
        if self.on_receive_completed:
            try:
                self.on_receive_completed(payload)
            except Exception:
                pass

    def _path_wait_seconds(
        self,
        destination_hash: bytes,
        timeout: float | None,
    ) -> float:
        window = path_response_window(destination_hash, self.reticulum)
        if timeout is None:
            return window
        return max(float(timeout), window)

    def _default_fetch_save_dir(self) -> str:
        path = os.path.join(self.storage_dir, "rncp", "downloads")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def _safe_received_filename(name) -> str:
        """Basename-only filename that cannot escape the receive directory."""
        try:
            if isinstance(name, (bytes, bytearray)):
                name = name.decode("utf-8", errors="replace")
            raw = str(name).replace("\\", "/")
            base = os.path.basename(raw)
        except (AttributeError, TypeError, ValueError):
            return "downloaded_file"
        if not base or base in {".", ".."} or "\x00" in base:
            return "downloaded_file"
        if base in _FORBIDDEN_RECEIVED_NAMES:
            return "downloaded_file"
        return base

    def _path_under_dir(self, directory: str, filename: str) -> str:
        """Join and require the final real path stays under directory."""
        directory = os.path.realpath(directory)
        candidate = os.path.realpath(os.path.join(directory, filename))
        if candidate != directory and not candidate.startswith(directory + os.sep):
            msg = "Refusing path escape outside receive directory"
            raise PermissionError(msg)
        return candidate

    def cancel_transfer(self, transfer_id: str | None = None) -> dict:
        """Mark one or all active transfers as cancelled."""
        if transfer_id:
            self._cancelled_transfers.add(transfer_id)
            transfer = self.active_transfers.get(transfer_id)
            if transfer is not None:
                transfer["status"] = "cancelled"
                self._on_transfer_terminal(transfer_id)
            return {"cancelled": [transfer_id]}
        ids = list(self.active_transfers.keys())
        for tid in ids:
            self._cancelled_transfers.add(tid)
            self.active_transfers[tid]["status"] = "cancelled"
            self._on_transfer_terminal(tid)
        return {"cancelled": ids}

    def _on_transfer_terminal(self, transfer_id: str | None) -> None:
        if not transfer_id:
            return
        entry = self.active_transfers.get(transfer_id)
        if entry is not None:
            entry.pop("resource", None)
        self.prune_terminal_transfers()

    def prune_terminal_transfers(self) -> int:
        """Drop Resource objects and cap finished transfer records."""
        dropped = 0
        terminal_ids = [
            tid
            for tid, entry in self.active_transfers.items()
            if entry.get("status") in TERMINAL_TRANSFER_STATUSES
        ]
        for tid in terminal_ids:
            entry = self.active_transfers.get(tid)
            if entry is not None and "resource" in entry:
                entry.pop("resource", None)
        overflow = len(terminal_ids) - MAX_RETAINED_TRANSFERS
        if overflow > 0:
            ranked = sorted(
                terminal_ids,
                key=lambda tid: float(
                    self.active_transfers.get(tid, {}).get("started_at") or 0.0,
                ),
            )
            for tid in ranked[:overflow]:
                if self.active_transfers.pop(tid, None) is not None:
                    dropped += 1
                self._cancelled_transfers.discard(tid)
        if len(self._cancelled_transfers) > MAX_CANCELLED_TRANSFER_IDS:
            live = set(self.active_transfers)
            stale = [tid for tid in list(self._cancelled_transfers) if tid not in live]
            for tid in stale:
                self._cancelled_transfers.discard(tid)
                if len(self._cancelled_transfers) <= MAX_CANCELLED_TRANSFER_IDS:
                    break
            if len(self._cancelled_transfers) > MAX_CANCELLED_TRANSFER_IDS:
                extra = list(self._cancelled_transfers)[MAX_CANCELLED_TRANSFER_IDS:]
                for tid in extra:
                    self._cancelled_transfers.discard(tid)
        return dropped

    def _is_cancelled(self, transfer_id: str | None) -> bool:
        if transfer_id and transfer_id in self._cancelled_transfers:
            return True
        return False

    def teardown_receive_destination(self):
        if self.receive_destination is None:
            self.allowed_identity_hashes = []
            return
        dest = self.receive_destination
        self.receive_destination = None
        if self._listener_fetch_registered:
            with contextlib.suppress(Exception):
                dest.deregister_request_handler("fetch_file")
            self._listener_fetch_registered = False
        self._listener_fetch_allowed = False
        self.allowed_identity_hashes = []
        with contextlib.suppress(Exception):
            RNS.Transport.deregister_destination(dest)

    def get_listener_status(self):
        receive_dir = os.path.join(self.storage_dir, "rncp_received")
        if self.receive_destination is None:
            return {
                "listening": False,
                "destination_hash": None,
                "allowed_hashes": [],
                "fetch_allowed": False,
                "fetch_jail": None,
                "allow_overwrite": False,
                "receive_directory": receive_dir,
            }
        return {
            "listening": True,
            "destination_hash": self.receive_destination.hash.hex(),
            "allowed_hashes": [h.hex() for h in self.allowed_identity_hashes],
            "fetch_allowed": self._listener_fetch_allowed,
            "fetch_jail": self.fetch_jail,
            "allow_overwrite": self.allow_overwrite_on_receive,
            "receive_directory": receive_dir,
        }

    def setup_receive_destination(
        self,
        allowed_hashes=None,
        fetch_allowed=False,
        fetch_jail=None,
        allow_overwrite=False,
    ):
        self.teardown_receive_destination()

        self.allowed_identity_hashes = []
        if allowed_hashes:
            self.allowed_identity_hashes = [
                bytes.fromhex(h) if isinstance(h, str) else h for h in allowed_hashes
            ]

        self.fetch_jail = fetch_jail
        self.allow_overwrite_on_receive = allow_overwrite
        self._listener_fetch_allowed = bool(fetch_allowed)

        # Never expose the whole filesystem: when fetch is enabled without an
        # explicit jail, confine reads to a dedicated shared directory instead
        # of resolving arbitrary absolute paths.
        if self._listener_fetch_allowed and not self.fetch_jail:
            self.fetch_jail = os.path.join(self.storage_dir, "rncp_shared")
        if self._listener_fetch_allowed and self.fetch_jail:
            with contextlib.suppress(OSError):
                os.makedirs(self.fetch_jail, exist_ok=True)

        identity_path = os.path.join(RNS.Reticulum.identitypath, self.APP_NAME)
        if os.path.isfile(identity_path):
            receive_identity = RNS.Identity.from_file(identity_path)
        else:
            receive_identity = RNS.Identity()
            receive_identity.to_file(identity_path)

        self.receive_destination = RNS.Destination(
            receive_identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            self.APP_NAME,
            "receive",
        )

        self.receive_destination.set_link_established_callback(
            self._client_link_established,
        )

        if fetch_allowed:
            self.receive_destination.register_request_handler(
                "fetch_file",
                response_generator=self._fetch_request,
                allow=RNS.Destination.ALLOW_LIST,
                allowed_list=self.allowed_identity_hashes,
            )
            self._listener_fetch_registered = True

        return self.receive_destination.hash.hex()

    def _client_link_established(self, link):
        link.set_remote_identified_callback(self._receive_sender_identified)
        link.set_resource_strategy(RNS.Link.ACCEPT_APP)
        link.set_resource_callback(self._receive_resource_callback)
        link.set_resource_started_callback(self._receive_resource_started)
        link.set_resource_concluded_callback(self._receive_resource_concluded)

    def _receive_sender_identified(self, link, identity):
        if identity.hash not in self.allowed_identity_hashes:
            link.teardown()

    def _receive_resource_callback(self, resource):
        sender_identity = resource.link.get_remote_identity()
        if sender_identity and sender_identity.hash in self.allowed_identity_hashes:
            return True
        return False

    def _receive_resource_started(self, resource):
        transfer_id = resource.hash.hex()
        self.active_transfers[transfer_id] = {
            "resource": resource,
            "status": "receiving",
            "started_at": time.time(),
        }

    def _receive_resource_concluded(self, resource):
        transfer_id = resource.hash.hex()
        if resource.status == RNS.Resource.COMPLETE:
            if resource.metadata:
                try:
                    filename = self._safe_received_filename(
                        resource.metadata["name"],
                    )
                    save_dir = os.path.join(self.storage_dir, "rncp_received")
                    os.makedirs(save_dir, exist_ok=True)

                    saved_filename = self._path_under_dir(save_dir, filename)
                    counter = 0

                    if self.allow_overwrite_on_receive:
                        if os.path.isfile(saved_filename):
                            try:
                                os.unlink(saved_filename)
                            except OSError:
                                # Failed to delete existing file, which is fine,
                                # we'll just fall through to the naming loop
                                pass

                    while os.path.isfile(saved_filename):
                        counter += 1
                        base, ext = os.path.splitext(filename)
                        saved_filename = self._path_under_dir(
                            save_dir,
                            f"{base}.{counter}{ext}",
                        )

                    shutil.move(resource.data.name, saved_filename)

                    if transfer_id in self.active_transfers:
                        self.active_transfers[transfer_id]["status"] = "completed"
                        self.active_transfers[transfer_id]["saved_path"] = (
                            saved_filename
                        )
                        self.active_transfers[transfer_id]["filename"] = filename
                    self._emit_receive_event(
                        {
                            "transfer_id": transfer_id,
                            "status": "completed",
                            "saved_path": saved_filename,
                            "filename": filename,
                            "error": None,
                        },
                    )
                except Exception as e:
                    if transfer_id in self.active_transfers:
                        self.active_transfers[transfer_id]["status"] = "error"
                        self.active_transfers[transfer_id]["error"] = str(e)
                    self._emit_receive_event(
                        {
                            "transfer_id": transfer_id,
                            "status": "error",
                            "saved_path": None,
                            "filename": None,
                            "error": str(e),
                        },
                    )
        elif transfer_id in self.active_transfers:
            self.active_transfers[transfer_id]["status"] = "failed"
            self._emit_receive_event(
                {
                    "transfer_id": transfer_id,
                    "status": "failed",
                    "saved_path": None,
                    "filename": None,
                    "error": None,
                },
            )
        self._on_transfer_terminal(transfer_id)

    def _fetch_request(
        self,
        path,
        data,
        request_id,
        link_id,
        remote_identity,
        requested_at,
    ):
        if not self.fetch_jail:
            return self.REQ_FETCH_NOT_ALLOWED

        if not isinstance(data, str) or "\x00" in data:
            return self.REQ_FETCH_NOT_ALLOWED

        if data.startswith(self.fetch_jail + "/"):
            data = data.replace(self.fetch_jail + "/", "")
        try:
            file_path = os.path.realpath(
                os.path.join(self.fetch_jail, data.lstrip("/")),
            )
        except (OSError, ValueError):
            return self.REQ_FETCH_NOT_ALLOWED
        jail_real = os.path.realpath(self.fetch_jail)
        if file_path != jail_real and not file_path.startswith(jail_real + os.sep):
            return self.REQ_FETCH_NOT_ALLOWED

        target_link = None
        for link in RNS.Transport.active_links:
            if link.link_id == link_id:
                target_link = link
                break

        if not os.path.isfile(file_path):
            return False

        if target_link:
            try:
                metadata = {"name": os.path.basename(file_path).encode("utf-8")}
                RNS.Resource(
                    open(file_path, "rb"),
                    target_link,
                    metadata=metadata,
                    auto_compress=self.fetch_auto_compress,
                )
                return True
            except Exception:
                return False

        return None

    def _is_reserved_storage_path(self, real: str) -> bool:
        root = os.path.realpath(self.storage_dir)
        if real == root:
            return True
        if not real.startswith(root + os.sep):
            return False
        first = os.path.relpath(real, root).split(os.sep, 1)[0]
        return first in _RESERVED_RNCP_TOP or first.endswith(".db")

    def _resolve_fetch_save_dir(self, save_path: str) -> str:
        """Jail fetch downloads under identity storage (or default downloads dir)."""
        if (
            not isinstance(save_path, str)
            or not save_path.strip()
            or "\x00" in save_path
        ):
            msg = "Invalid save path"
            raise ValueError(msg)
        expanded = os.path.expanduser(save_path.strip())
        if not os.path.isabs(expanded):
            expanded = os.path.join(self.storage_dir, expanded)
        real = os.path.realpath(expanded)
        root = os.path.realpath(self.storage_dir)
        if real != root and not real.startswith(root + os.sep):
            msg = "Save path is outside the RNCP download jail"
            raise PermissionError(msg)
        parts = {part for part in real.split(os.sep) if part}
        if parts & {".ssh", ".gnupg"}:
            msg = "Refusing to save into credential directories"
            raise PermissionError(msg)
        if self._is_reserved_storage_path(real):
            msg = "Save path is a reserved identity-storage top"
            raise PermissionError(msg)
        os.makedirs(real, exist_ok=True)
        return real

    def _resolve_send_path(self, file_path: str) -> str:
        """Resolve a local send path under storage or home, never identity keys."""
        if not isinstance(file_path, str) or not file_path or "\x00" in file_path:
            msg = "Invalid file path"
            raise ValueError(msg)
        expanded = os.path.expanduser(file_path)
        if not os.path.isabs(expanded):
            expanded = os.path.join(self.storage_dir, expanded)
        real = os.path.realpath(expanded)
        allowed_roots = [os.path.realpath(self.storage_dir)]
        home = os.path.expanduser("~")
        if home and home != "~":
            allowed_roots.append(os.path.realpath(home))
        if not any(
            real == root or real.startswith(root + os.sep) for root in allowed_roots
        ):
            msg = "File path is outside the RNCP send jail"
            raise PermissionError(msg)
        base = os.path.basename(real)
        if base in _FORBIDDEN_RECEIVED_NAMES:
            msg = "Refusing to send identity private key material"
            raise PermissionError(msg)
        parts = {part for part in real.split(os.sep) if part}
        if parts & {".ssh", ".gnupg"}:
            msg = "Refusing to send credential material"
            raise PermissionError(msg)
        if self._is_reserved_storage_path(real):
            msg = "Refusing to send reserved identity-storage material"
            raise PermissionError(msg)
        if not os.path.isfile(real):
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)
        return real

    async def send_file(
        self,
        destination_hash: bytes,
        file_path: str,
        timeout: float | None = None,
        on_progress: Callable[[float], None] | None = None,
        no_compress: bool = False,
        on_transfer_started: Callable[[str], None] | None = None,
    ):
        file_path = self._resolve_send_path(file_path)

        if not RNS.Transport.has_path(destination_hash):
            RNS.Transport.request_path(destination_hash)

        path_wait = self._path_wait_seconds(destination_hash, timeout)
        timeout_after = time.time() + path_wait
        while (
            not RNS.Transport.has_path(destination_hash) and time.time() < timeout_after
        ):
            await asyncio.sleep(0.1)

        if not RNS.Transport.has_path(destination_hash):
            msg = "Path not found to destination"
            raise TimeoutError(msg)

        receiver_identity = RNS.Identity.recall(destination_hash)
        receiver_destination = RNS.Destination(
            receiver_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            self.APP_NAME,
            "receive",
        )

        link = RNS.Link(receiver_destination)
        timeout_after = time.time() + link_establishment_window(
            link,
            destination_hash,
            self.reticulum,
        )
        while link.status != RNS.Link.ACTIVE and time.time() < timeout_after:
            await asyncio.sleep(0.1)

        if link.status != RNS.Link.ACTIVE:
            msg = "Could not establish link to destination"
            raise TimeoutError(msg)

        link.identify(self.identity)

        auto_compress = not no_compress
        metadata = {"name": os.path.basename(file_path).encode("utf-8")}

        def progress_callback(resource):
            if on_progress:
                progress = resource.get_progress()
                on_progress(progress)

        resource = RNS.Resource(
            open(file_path, "rb"),
            link,
            metadata=metadata,
            callback=progress_callback,
            progress_callback=progress_callback,
            auto_compress=auto_compress,
        )

        transfer_id = resource.hash.hex()
        self.active_transfers[transfer_id] = {
            "resource": resource,
            "status": "sending",
            "started_at": time.time(),
            "file_path": file_path,
        }
        if on_transfer_started:
            try:
                on_transfer_started(transfer_id)
            except Exception:
                pass

        while resource.status < RNS.Resource.COMPLETE:
            if self._is_cancelled(transfer_id):
                with contextlib.suppress(Exception):
                    link.teardown()
                if transfer_id in self.active_transfers:
                    self.active_transfers[transfer_id]["status"] = "cancelled"
                    self._on_transfer_terminal(transfer_id)
                msg = "Transfer cancelled"
                raise InterruptedError(msg)
            await asyncio.sleep(0.1)
            if resource.status > RNS.Resource.COMPLETE:
                msg = "File was not accepted by destination"
                raise Exception(msg)

        if resource.status == RNS.Resource.COMPLETE:
            if transfer_id in self.active_transfers:
                self.active_transfers[transfer_id]["status"] = "completed"
                self._on_transfer_terminal(transfer_id)
            link.teardown()
            return {
                "transfer_id": transfer_id,
                "status": "completed",
                "file_path": file_path,
            }
        if transfer_id in self.active_transfers:
            self.active_transfers[transfer_id]["status"] = "failed"
            self._on_transfer_terminal(transfer_id)
        link.teardown()
        msg = "Transfer failed"
        raise Exception(msg)

    async def fetch_file(
        self,
        destination_hash: bytes,
        file_path: str,
        timeout: float | None = None,
        on_progress: Callable[[float], None] | None = None,
        save_path: str | None = None,
        allow_overwrite: bool = False,
        on_transfer_started: Callable[[str], None] | None = None,
    ):
        if not RNS.Transport.has_path(destination_hash):
            RNS.Transport.request_path(destination_hash)

        path_wait = self._path_wait_seconds(destination_hash, timeout)
        timeout_after = time.time() + path_wait
        while (
            not RNS.Transport.has_path(destination_hash) and time.time() < timeout_after
        ):
            await asyncio.sleep(0.1)

        if not RNS.Transport.has_path(destination_hash):
            msg = "Path not found to destination"
            raise TimeoutError(msg)

        listener_identity = RNS.Identity.recall(destination_hash)
        listener_destination = RNS.Destination(
            listener_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            self.APP_NAME,
            "receive",
        )

        link = RNS.Link(listener_destination)
        timeout_after = time.time() + link_establishment_window(
            link,
            destination_hash,
            self.reticulum,
        )
        while link.status != RNS.Link.ACTIVE and time.time() < timeout_after:
            await asyncio.sleep(0.1)

        if link.status != RNS.Link.ACTIVE:
            msg = "Could not establish link to destination"
            raise TimeoutError(msg)

        link.identify(self.identity)

        request_resolved = False
        request_status = "unknown"
        resource_resolved = False
        resource_status = "unrequested"
        current_resource = None

        def request_response(request_receipt):
            nonlocal request_resolved, request_status
            if not request_receipt.response:
                request_status = "not_found"
            elif request_receipt.response is None:
                request_status = "remote_error"
            elif request_receipt.response == self.REQ_FETCH_NOT_ALLOWED:
                request_status = "fetch_not_allowed"
            else:
                request_status = "found"
            request_resolved = True

        def request_failed(request_receipt):
            nonlocal request_resolved, request_status
            request_status = "unknown"
            request_resolved = True

        def fetch_resource_started(resource):
            nonlocal resource_status, current_resource
            current_resource = resource
            if on_transfer_started and hasattr(resource, "hash") and resource.hash:
                try:
                    on_transfer_started(resource.hash.hex())
                except Exception:
                    pass

            def progress_callback(resource):
                if on_progress:
                    progress = resource.get_progress()
                    on_progress(progress)

            current_resource.progress_callback(progress_callback)
            resource_status = "started"

        saved_filename = None
        save_error = None
        if isinstance(save_path, str) and save_path.strip():
            try:
                effective_save_path = self._resolve_fetch_save_dir(save_path)
            except (OSError, PermissionError, ValueError) as exc:
                link.teardown()
                raise PermissionError(str(exc)) from exc
        else:
            effective_save_path = self._default_fetch_save_dir()

        def fetch_resource_concluded(resource):
            nonlocal resource_resolved, resource_status, saved_filename, save_error
            try:
                if resource.status == RNS.Resource.COMPLETE:
                    if resource.metadata:
                        try:
                            filename = self._safe_received_filename(
                                resource.metadata["name"],
                            )
                            save_dir = effective_save_path
                            os.makedirs(save_dir, exist_ok=True)
                            saved_filename = self._path_under_dir(save_dir, filename)

                            counter = 0
                            if allow_overwrite:
                                if os.path.isfile(saved_filename):
                                    try:
                                        os.unlink(saved_filename)
                                    except OSError:
                                        pass

                            while os.path.isfile(saved_filename):
                                counter += 1
                                base, ext = os.path.splitext(filename)
                                saved_filename = self._path_under_dir(
                                    save_dir,
                                    f"{base}.{counter}{ext}",
                                )

                            shutil.move(resource.data.name, saved_filename)
                            resource_status = "completed"
                        except Exception as e:
                            resource_status = "error"
                            save_error = str(e)
                    else:
                        resource_status = "error"
                        save_error = "missing resource metadata"
                else:
                    resource_status = "failed"
            finally:
                resource_resolved = True

        link.set_resource_strategy(RNS.Link.ACCEPT_ALL)
        link.set_resource_started_callback(fetch_resource_started)
        link.set_resource_concluded_callback(fetch_resource_concluded)
        link.request(
            "fetch_file",
            data=file_path,
            response_callback=request_response,
            failed_callback=request_failed,
        )

        while not request_resolved:
            await asyncio.sleep(0.1)

        if request_status == "fetch_not_allowed":
            link.teardown()
            msg = "Fetch request not allowed by remote"
            raise PermissionError(msg)
        if request_status == "not_found":
            link.teardown()
            msg = f"File not found on remote: {file_path}"
            raise FileNotFoundError(msg)
        if request_status == "remote_error":
            link.teardown()
            msg = "Remote error during fetch request"
            raise Exception(msg)
        if request_status == "unknown":
            link.teardown()
            msg = "Unknown error during fetch request"
            raise Exception(msg)

        while not resource_resolved:
            if current_resource is not None and hasattr(current_resource, "hash"):
                tid = getattr(current_resource, "hash", None)
                if tid is not None and self._is_cancelled(tid.hex()):
                    with contextlib.suppress(Exception):
                        link.teardown()
                    msg = "Transfer cancelled"
                    raise InterruptedError(msg)
            await asyncio.sleep(0.1)

        if resource_status == "completed":
            link.teardown()
            return {
                "status": "completed",
                "file_path": saved_filename,
            }
        link.teardown()
        if save_error:
            msg = f"Transfer failed: {resource_status}: {save_error}"
        else:
            msg = f"Transfer failed: {resource_status}"
        raise Exception(msg)

    def get_transfer_status(self, transfer_id: str):
        if transfer_id in self.active_transfers:
            transfer = self.active_transfers[transfer_id]
            resource = transfer.get("resource")
            if resource:
                progress = resource.get_progress()
                return {
                    "transfer_id": transfer_id,
                    "status": transfer["status"],
                    "progress": progress,
                    "file_path": transfer.get("file_path"),
                    "saved_path": transfer.get("saved_path"),
                    "filename": transfer.get("filename"),
                    "error": transfer.get("error"),
                }
        return None
