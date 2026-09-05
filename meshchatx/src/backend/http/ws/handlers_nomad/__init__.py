# SPDX-License-Identifier: 0BSD
"""Nomad WS handlers package."""

from __future__ import annotations

from meshchatx.src.backend.http.ws.handlers_nomad.archives import (
    HANDLERS as _ARCHIVES_HANDLERS,
)
from meshchatx.src.backend.http.ws.handlers_nomad.downloads import (
    HANDLERS as _DOWNLOADS_HANDLERS,
)
from meshchatx.src.backend.http.ws.handlers_nomad.file_download import (
    HANDLERS as _FILE_DOWNLOAD_HANDLERS,
)
from meshchatx.src.backend.http.ws.handlers_nomad.page_download import (
    HANDLERS as _PAGE_DOWNLOAD_HANDLERS,
)

HANDLERS = {
    **_DOWNLOADS_HANDLERS,
    **_ARCHIVES_HANDLERS,
    **_FILE_DOWNLOAD_HANDLERS,
    **_PAGE_DOWNLOAD_HANDLERS,
}

__all__ = ["HANDLERS"]
