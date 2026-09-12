# SPDX-License-Identifier: 0BSD

"""Request stubs for route-handler tests.

read_json_limited reads request.content.iter_chunked, so a bare MagicMock
with only .json stubbed no longer exercises the handler body path. Use
json_request(payload) for MagicMock-style requests, JsonContent to add a
content attribute to custom request classes, or RawContent to feed raw
bytes such as an empty or malformed body.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock


class RawContent:
    """request.content stub that yields the given chunks via iter_chunked."""

    def __init__(self, chunks):
        self._chunks = list(chunks)

    def iter_chunked(self, _size):
        async def _aiter():
            for chunk in self._chunks:
                yield chunk

        return _aiter()


class JsonContent(RawContent):
    """request.content stub that yields the payload via iter_chunked."""

    def __init__(self, payload):
        super().__init__([json.dumps(payload).encode()])


def json_request(payload):
    """MagicMock request whose json() and content both serve payload."""
    request = MagicMock()
    request.json = AsyncMock(return_value=payload)
    request.content = JsonContent(payload)
    return request
