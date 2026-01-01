import asyncio
import os
import shutil
import time
from collections.abc import Callable

import RNS


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

    def setup_receive_destination(self, allowed_hashes=None, fetch_allowed=False, fetch_jail=None, allow_overwrite=False):
        if allowed_hashes:
            self.allowed_identity_hashes = [bytes.fromhex(h) if isinstance(h, str) else h for h in allowed_hashes]

        self.fetch_jail = fetch_jail
        self.allow_overwrite_on_receive = allow_overwrite

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

        self.receive_destination.set_link_established_callback(self._client_link_established)

        if fetch_allowed:
            self.receive_destination.register_request_handler(
                "fetch_file",
                response_generator=self._fetch_request,
                allow=RNS.Destination.ALLOW_LIST,
                allowed_list=self.allowed_identity_hashes,
            )

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
                    filename = os.path.basename(resource.metadata["name"].decode("utf-8"))
                    save_dir = os.path.join(self.storage_dir, "rncp_received")
                    os.makedirs(save_dir, exist_ok=True)

                    saved_filename = os.path.join(save_dir, filename)
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
                        saved_filename = os.path.join(save_dir, f"{base}.{counter}{ext}")

                    shutil.move(resource.data.name, saved_filename)

                    if transfer_id in self.active_transfers:
                        self.active_transfers[transfer_id]["status"] = "completed"
                        self.active_transfers[transfer_id]["saved_path"] = saved_filename
                        self.active_transfers[transfer_id]["filename"] = filename
                except Exception as e:
                    if transfer_id in self.active_transfers:
                        self.active_transfers[transfer_id]["status"] = "error"
                        self.active_transfers[transfer_id]["error"] = str(e)
        elif transfer_id in self.active_transfers:
            self.active_transfers[transfer_id]["status"] = "failed"

    def _fetch_request(self, path, data, request_id, link_id, remote_identity, requested_at):
        if self.fetch_jail:
            if data.startswith(self.fetch_jail + "/"):
                data = data.replace(self.fetch_jail + "/", "")
            file_path = os.path.abspath(os.path.expanduser(f"{self.fetch_jail}/{data}"))
            if not file_path.startswith(self.fetch_jail + "/"):
                return self.REQ_FETCH_NOT_ALLOWED
        else:
            file_path = os.path.abspath(os.path.expanduser(data))

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

    async def send_file(
        self,
        destination_hash: bytes,
        file_path: str,
        timeout: float = RNS.Transport.PATH_REQUEST_TIMEOUT,
        on_progress: Callable[[float], None] | None = None,
        no_compress: bool = False,
    ):
        file_path = os.path.expanduser(file_path)
        if not os.path.isfile(file_path):
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        if not RNS.Transport.has_path(destination_hash):
            RNS.Transport.request_path(destination_hash)

        timeout_after = time.time() + timeout
        while not RNS.Transport.has_path(destination_hash) and time.time() < timeout_after:
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
        timeout_after = time.time() + timeout
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

        while resource.status < RNS.Resource.COMPLETE:
            await asyncio.sleep(0.1)
            if resource.status > RNS.Resource.COMPLETE:
                msg = "File was not accepted by destination"
                raise Exception(msg)

        if resource.status == RNS.Resource.COMPLETE:
            if transfer_id in self.active_transfers:
                self.active_transfers[transfer_id]["status"] = "completed"
            link.teardown()
            return {
                "transfer_id": transfer_id,
                "status": "completed",
                "file_path": file_path,
            }
        if transfer_id in self.active_transfers:
            self.active_transfers[transfer_id]["status"] = "failed"
        link.teardown()
        msg = "Transfer failed"
        raise Exception(msg)

    async def fetch_file(
        self,
        destination_hash: bytes,
        file_path: str,
        timeout: float = RNS.Transport.PATH_REQUEST_TIMEOUT,
        on_progress: Callable[[float], None] | None = None,
        save_path: str | None = None,
        allow_overwrite: bool = False,
    ):
        if not RNS.Transport.has_path(destination_hash):
            RNS.Transport.request_path(destination_hash)

        timeout_after = time.time() + timeout
        while not RNS.Transport.has_path(destination_hash) and time.time() < timeout_after:
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
        timeout_after = time.time() + timeout
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

            def progress_callback(resource):
                if on_progress:
                    progress = resource.get_progress()
                    on_progress(progress)

            current_resource.progress_callback(progress_callback)
            resource_status = "started"

        saved_filename = None

        def fetch_resource_concluded(resource):
            nonlocal resource_resolved, resource_status, saved_filename
            if resource.status == RNS.Resource.COMPLETE:
                if resource.metadata:
                    try:
                        filename = os.path.basename(resource.metadata["name"].decode("utf-8"))
                        if save_path:
                            save_dir = os.path.abspath(os.path.expanduser(save_path))
                            os.makedirs(save_dir, exist_ok=True)
                            saved_filename = os.path.join(save_dir, filename)
                        else:
                            saved_filename = filename

                        counter = 0
                        if allow_overwrite:
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
                            saved_filename = os.path.join(
                                os.path.dirname(saved_filename) if save_path else ".",
                                f"{base}.{counter}{ext}",
                            )

                        shutil.move(resource.data.name, saved_filename)
                        resource_status = "completed"
                    except Exception as e:
                        resource_status = "error"
                        raise e
                else:
                    resource_status = "error"
            else:
                resource_status = "failed"

            resource_resolved = True

        link.set_resource_strategy(RNS.Link.ACCEPT_ALL)
        link.set_resource_started_callback(fetch_resource_started)
        link.set_resource_concluded_callback(fetch_resource_concluded)
        link.request("fetch_file", data=file_path, response_callback=request_response, failed_callback=request_failed)

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
            await asyncio.sleep(0.1)

        if resource_status == "completed":
            link.teardown()
            return {
                "status": "completed",
                "file_path": saved_filename,
            }
        link.teardown()
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

