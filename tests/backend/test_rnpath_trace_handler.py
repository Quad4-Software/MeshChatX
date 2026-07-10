# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.rnpath_trace_handler import RNPathTraceHandler


@pytest.mark.asyncio
async def test_trace_includes_destination_for_zero_hops():
    identity = MagicMock()
    identity.hash = bytes.fromhex("11" * 16)
    handler = RNPathTraceHandler(reticulum_instance=MagicMock(), identity=identity)
    dest = "22" * 16

    with patch("meshchatx.src.backend.rnpath_trace_handler.RNS.Transport") as transport:
        transport.has_path.return_value = True
        transport.hops_to.return_value = 0

        result = await handler.trace_path(dest)

    assert "error" not in result
    assert result["hops"] == 0
    assert any(
        hop.get("type") == "destination" and hop.get("hash") == dest
        for hop in result["path"]
    )
