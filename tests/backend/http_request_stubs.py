# SPDX-License-Identifier: 0BSD

"""Request stubs for route-handler tests.

read_json_limited reads request.content.iter_chunked, so a bare MagicMock
with only .json stubbed no longer exercises the handler body path. Use
json_request(payload) for MagicMock-style requests or JsonContent to add a
content attribute to custom request classes.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock


class JsonContent:
    """request.content stub that yields the payload via iter_chunked."""

    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def iter_chunked(self, _size):
        async def _aiter():
            yield self._body

        return _aiter()


def json_request(payload):
    """MagicMock request whose json() and content both serve payload."""
    request = MagicMock()
    request.json = AsyncMock(return_value=payload)
    request.content = JsonContent(payload)
    return request
