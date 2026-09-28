# SPDX-License-Identifier: 0BSD
"""FileResponse that avoids CPython's broken SSL sendfile fallback.

``loop.sendfile`` on an SSL transport uses ``_sendfile_fallback``, which
crashes with ``AttributeError`` when the peer tears down mid-write
(the ``_ssl_protocol`` member is already ``None``). The exception escapes
aiohttp as an unhandled request failure and kills the response mid-flight,
which can poison iframe/subresource loads that never retry.

This subclass always streams through aiohttp's own chunked writer, which
is robust against the same teardown. The plaintext sendfile fast path is
not used; loopback/LAN latency does not benefit from it measurably.
"""

from __future__ import annotations

from typing import IO, Any

from aiohttp import web


class SafeFileResponse(web.FileResponse):
    """web.FileResponse that skips loop.sendfile entirely."""

    async def _sendfile(
        self,
        request: web.BaseRequest,
        fobj: IO[Any],
        offset: int,
        count: int,
    ) -> Any:
        writer = await super(web.FileResponse, self).prepare(request)
        if writer is None:
            msg = "response prepare returned no writer"
            raise RuntimeError(msg)
        return await self._sendfile_fallback(writer, fobj, offset, count)


def file_response(*args: Any, **kwargs: Any) -> web.FileResponse:
    return SafeFileResponse(*args, **kwargs)
