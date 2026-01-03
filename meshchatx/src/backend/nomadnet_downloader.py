import asyncio
import io
import os
import time
from collections.abc import Callable

import RNS

# global cache for nomadnet links to avoid re-establishing them for every request
nomadnet_cached_links = {}


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
        self.request_receipt = None
        self.is_cancelled = False
        self.link = None

    # cancel the download
    def cancel(self):
        self.is_cancelled = True

        # cancel the request if it exists
        if self.request_receipt is not None:
            try:
                self.request_receipt.cancel()
            except Exception as e:
                print(f"Failed to cancel request: {e}")

        # clean up the link if we created it
        if self.link is not None:
            try:
                self.link.teardown()
            except Exception as e:
                print(f"Failed to teardown link: {e}")

        # notify that download was cancelled
        self._download_failure_callback("cancelled")

    # setup link to destination and request download
    async def download(
        self,
        path_lookup_timeout: int = 15,
        link_establishment_timeout: int = 15,
    ):
        # check if cancelled before starting
        if self.is_cancelled:
            return

        # use existing established link if it's active
        if self.destination_hash in nomadnet_cached_links:
            link = nomadnet_cached_links[self.destination_hash]
            if link.status is RNS.Link.ACTIVE:
                print("[NomadnetDownloader] using existing link for request")
                self.link_established(link)
                return

        # determine when to timeout
        timeout_after_seconds = time.time() + path_lookup_timeout

        # check if we have a path to the destination
        if not RNS.Transport.has_path(self.destination_hash):
            # we don't have a path, so we need to request it
            RNS.Transport.request_path(self.destination_hash)

            # wait until we have a path, or give up after the configured timeout
            while (
                not RNS.Transport.has_path(self.destination_hash)
                and time.time() < timeout_after_seconds
            ):
                # check if cancelled during path lookup
                if self.is_cancelled:
                    return
                await asyncio.sleep(0.1)

        # if we still don't have a path, we can't establish a link, so bail out
        if not RNS.Transport.has_path(self.destination_hash):
            self._download_failure_callback("Could not find path to destination.")
            return

        # check if cancelled before establishing link
        if self.is_cancelled:
            return

        # create destination to nomadnet node
        identity = RNS.Identity.recall(self.destination_hash)
        destination = RNS.Destination(
            identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            self.app_name,
            self.aspects,
        )

        # create link to destination
        print("[NomadnetDownloader] establishing new link for request")
        link = RNS.Link(destination, established_callback=self.link_established)
        self.link = link

        # determine when to timeout
        timeout_after_seconds = time.time() + link_establishment_timeout

        # wait until we have established a link, or give up after the configured timeout
        while (
            link.status is not RNS.Link.ACTIVE and time.time() < timeout_after_seconds
        ):
            # check if cancelled during link establishment
            if self.is_cancelled:
                return
            await asyncio.sleep(0.1)

        # if we still haven't established a link, bail out
        if link.status is not RNS.Link.ACTIVE:
            self._download_failure_callback("Could not establish link to destination.")

    # link to destination was established, we should now request the download
    def link_established(self, link):
        # check if cancelled before requesting
        if self.is_cancelled:
            return

        # cache link for using in future requests
        nomadnet_cached_links[self.destination_hash] = link

        # request download over link
        self.request_receipt = link.request(
            self.path,
            data=self.data,
            response_callback=self.on_response,
            failed_callback=self.on_failed,
            progress_callback=self.on_progress,
            timeout=self.timeout,
        )

    # handle successful download
    def on_response(self, request_receipt: RNS.RequestReceipt):
        self._download_success_callback(request_receipt)

    # handle failure
    def on_failed(self, request_receipt=None):
        self._download_failure_callback("request_failed")

    # handle download progress
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
        )

    # page download was successful, decode the response and send to provided callback
    def on_download_success(self, request_receipt: RNS.RequestReceipt):
        micron_markup_response = request_receipt.response.decode("utf-8")
        self.on_page_download_success(micron_markup_response)

    # page download failed, send error to provided callback
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
        )

    # file download was successful, decode the response and send to provided callback
    def on_download_success(self, request_receipt: RNS.RequestReceipt):
        # get response
        response = request_receipt.response

        # handle buffered reader response
        if isinstance(response, io.BufferedReader):
            # get file name from metadata
            file_name = "downloaded_file"
            metadata = request_receipt.metadata
            if metadata is not None and "name" in metadata:
                file_path = metadata["name"].decode("utf-8")
                file_name = os.path.basename(file_path)

            # get file data
            file_data: bytes = response.read()

            self.on_file_download_success(file_name, file_data)
            return

        # check for list response with bytes in position 0, and metadata dict in position 1
        # e.g: [file_bytes, {name: "filename.ext"}]
        if isinstance(response, list) and isinstance(response[1], dict):
            file_data: bytes = response[0]
            metadata: dict = response[1]

            # get file name from metadata
            file_name = "downloaded_file"
            if metadata is not None and "name" in metadata:
                file_path = metadata["name"].decode("utf-8")
                file_name = os.path.basename(file_path)

            self.on_file_download_success(file_name, file_data)
            return

        # try using original response format
        # unsure if this is actually used anymore now that a buffered reader is provided
        # have left here just in case...
        try:
            file_name: str = response[0]
            file_data: bytes = response[1]
            self.on_file_download_success(file_name, file_data)
        except Exception:
            self.on_download_failure("unsupported_response")

    # page download failed, send error to provided callback
    def on_download_failure(self, failure_reason):
        self.on_file_download_failure(failure_reason)
