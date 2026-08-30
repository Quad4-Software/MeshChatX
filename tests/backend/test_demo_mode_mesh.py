# SPDX-License-Identifier: 0BSD

"""Demo mode skips outbound announces."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_announce_noop_in_demo_mode(mock_app):
    mock_app.demo_mode = True
    ctx = mock_app.current_context
    ctx.message_router = MagicMock()
    ctx.telephone_manager = MagicMock()
    await mock_app.announce(context=ctx)
    ctx.message_router.announce.assert_not_called()
    ctx.telephone_manager.announce.assert_not_called()
