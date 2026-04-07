import asyncio
import io
import os
import threading
import time
from collections.abc import Callable

import RNS

# Global cache for Nomad Network links (reuse instead of reconnecting per request).
# Protected by _nomadnet_links_lock for callers that may touch Reticulum from multiple threads.
nomadnet_cached_links: dict[bytes, object] = {}
_nomadnet_links_lock = threading.Lock()

# Wait granularity while polling for path / link (seconds). Smaller = faster reaction, slightly more wakeups.
_POLL_INTERVAL_S = 0.02


def get_cached_active_link(destination_hash: bytes):
    """Return a cached link if present and ACTIVE; drop stale entries."""
    with _nomadnet_links_lock:
        link = nomadnet_cached_links.get(destination_hash)
        if link is None:
            return None
        if link.status is RNS.Link.ACTIVE:
            return link
        try:
            del nomadnet_cached_links[destination_hash]
        except KeyError:
            pass
        return None


def _cache_link_if_active(destination_hash: bytes, link) -> None:
    if link is None or link.status is not RNS.Link.ACTIVE:
        return
    with _nomadnet_links_lock:
        nomadnet_cached_links[destination_hash] = link


def _uncache_link_if_matches(destination_hash: bytes, link) -> None:
    if link is None:
        return
    with _nomadnet_links_lock:
        if nomadnet_cached_links.get(destination_hash) is link:
            try:
                del nomadnet_cached_links[destination_hash]
            except KeyError:
                pass


class NomadnetDownloader:
    def __init__(
        self,
        destination_hash: bytes,
        path: str,
        data: str | None,
        on_download_success: Callable[[RNS.RequestReceipt], None],
        on_download_failure: Callable[[str], None],
        on_progress_update: Callable[[float], None],
        timeout: int | None = None,
        *,
        on_phase: Callable[[str], None] | None = None,
    ):
        self.app_name = "nomadnetwork"
        self.aspects = "node"
        self.destination_hash = destination_hash
        self.path = path
        self.data = data
        self.timeout = timeout
        self._download_success_callback = on_download_success
        self._download_failure_callback = on_download_failure
        self.on_progress_update = on_progress_update
        self._on_phase = on_phase
        self.request_receipt = None
        self.is_cancelled = False
        self.link = None

    def _emit_phase(self, phase: str) -> None:
        if self._on_phase is None:
            return
        try:
            self._on_phase(phase)
        except Exception:
            pass

    def cancel(self):
        self.is_cancelled = True

        if self.request_receipt is not None:
            try:
                self.request_receipt.cancel()
            except Exception as e:
                print(f"Failed to cancel request: {e}")

        if self.link is not None:
            _uncache_link_if_matches(self.destination_hash, self.link)
            try:
                self.link.teardown()
            except Exception as e:
                print(f"Failed to teardown link: {e}")

        self._download_failure_callback("cancelled")

    async def download(
        self,
        path_lookup_timeout: int = 15,
        link_establishment_timeout: int = 15,
    ):
        if self.is_cancelled:
            return

        cached = get_cached_active_link(self.destination_hash)
        if cached is not None:
            print("[NomadnetDownloader] using existing link for request")
            self._emit_phase("requesting_page")
            self.link = cached
            self.link_established(cached)
            return

        timeout_after_seconds = time.time() + path_lookup_timeout

        if not RNS.Transport.has_path(self.destination_hash):
            self._emit_phase("finding_path")
            RNS.Transport.request_path(self.destination_hash)

            while (
                not RNS.Transport.has_path(self.destination_hash)
                and time.time() < timeout_after_seconds
            ):
                if self.is_cancelled:
                    return
                await asyncio.sleep(_POLL_INTERVAL_S)

        if not RNS.Transport.has_path(self.destination_hash):
            self._download_failure_callback("Could not find path to destination.")
            return

        cached = get_cached_active_link(self.destination_hash)
        if cached is not None:
            print("[NomadnetDownloader] using link cached while waiting for path")
            self._emit_phase("requesting_page")
            self.link = cached
            self.link_established(cached)
            return

        if self.is_cancelled:
            return

        self._emit_phase("establishing_link")
        identity = RNS.Identity.recall(self.destination_hash)
        destination = RNS.Destination(
            identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            self.app_name,
            self.aspects,
        )

        cached = get_cached_active_link(self.destination_hash)
        if cached is not None:
            print("[NomadnetDownloader] using link cached before establishing new link")
            self._emit_phase("requesting_page")
            self.link = cached
            self.link_established(cached)
            return

        print("[NomadnetDownloader] establishing new link for request")
        link = RNS.Link(destination, established_callback=self.link_established)
        self.link = link

        timeout_after_seconds = time.time() + link_establishment_timeout

        while link.status is not RNS.Link.ACTIVE and time.time() < timeout_after_seconds:
            if self.is_cancelled:
                return
            await asyncio.sleep(_POLL_INTERVAL_S)

        if link.status is not RNS.Link.ACTIVE:
            self._download_failure_callback("Could not establish link to destination.")

    def link_established(self, link):
        if self.is_cancelled:
            return

        self._emit_phase("transferring")

        _cache_link_if_active(self.destination_hash, link)

        self.request_receipt = link.request(
            self.path,
            data=self.data,
            response_callback=self.on_response,
            failed_callback=self.on_failed,
            progress_callback=self.on_progress,
            timeout=self.timeout,
        )

    def on_response(self, request_receipt: RNS.RequestReceipt):
        self._download_success_callback(request_receipt)

    def on_failed(self, request_receipt=None):
        self._download_failure_callback("request_failed")

    def on_progress(self, request_receipt):
        self.on_progress_update(request_receipt.progress)


class NomadnetPageDownloader(NomadnetDownloader):
    def __init__(
        self,
        destination_hash: bytes,
        page_path: str,
        data: str | None,
        on_page_download_success: Callable[[str], None],
        on_page_download_failure: Callable[[str], None],
        on_progress_update: Callable[[float], None],
        timeout: int | None = None,
        *,
        on_phase: Callable[[str], None] | None = None,
    ):
        self.on_page_download_success = on_page_download_success
        self.on_page_download_failure = on_page_download_failure
        super().__init__(
            destination_hash,
            page_path,
            data,
            self.on_download_success,
            self.on_download_failure,
            on_progress_update,
            timeout,
            on_phase=on_phase,
        )

    def on_download_success(self, request_receipt: RNS.RequestReceipt):
        raw = request_receipt.response
        if raw is None:
            self.on_page_download_failure("empty_response")
            return
        try:
            micron_markup_response = raw.decode("utf-8", errors="replace")
        except (AttributeError, TypeError):
            self.on_page_download_failure("invalid_response_body")
            return
        self.on_page_download_success(micron_markup_response)

    def on_download_failure(self, failure_reason):
        self.on_page_download_failure(failure_reason)


class NomadnetFileDownloader(NomadnetDownloader):
    def __init__(
        self,
        destination_hash: bytes,
        page_path: str,
        on_file_download_success: Callable[[str, bytes], None],
        on_file_download_failure: Callable[[str], None],
        on_progress_update: Callable[[float], None],
        timeout: int | None = None,
        *,
        on_phase: Callable[[str], None] | None = None,
    ):
        self.on_file_download_success = on_file_download_success
        self.on_file_download_failure = on_file_download_failure
        super().__init__(
            destination_hash,
            page_path,
            None,
            self.on_download_success,
            self.on_download_failure,
            on_progress_update,
            timeout,
            on_phase=on_phase,
        )

    def on_download_success(self, request_receipt: RNS.RequestReceipt):
        response = request_receipt.response

        if isinstance(response, io.BufferedReader):
            file_name = "downloaded_file"
            metadata = request_receipt.metadata
            if metadata is not None and "name" in metadata:
                try:
                    file_path = metadata["name"].decode("utf-8", errors="replace")
                    file_name = os.path.basename(file_path)
                except (AttributeError, TypeError):
                    pass

            file_data: bytes = response.read()

            self.on_file_download_success(file_name, file_data)
            return

        if isinstance(response, list) and len(response) > 1 and isinstance(response[1], dict):
            file_data: bytes = response[0]
            metadata: dict = response[1]

            file_name = "downloaded_file"
            if metadata is not None and "name" in metadata:
                try:
                    file_path = metadata["name"].decode("utf-8", errors="replace")
                    file_name = os.path.basename(file_path)
                except (AttributeError, TypeError):
                    pass

            self.on_file_download_success(file_name, file_data)
            return

        try:
            file_name: str = response[0]
            file_data: bytes = response[1]
            self.on_file_download_success(file_name, file_data)
        except Exception:
            self.on_download_failure("unsupported_response")

    def on_download_failure(self, failure_reason):
        self.on_file_download_failure(failure_reason)
