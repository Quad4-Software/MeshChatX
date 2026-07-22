# SPDX-License-Identifier: 0BSD

"""LiveMeshchatName injects meshchat bindings so patches stay effective."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from meshchatx.src.backend.http.live_names import (
    LiveMeshchatName,
    inject_meshchat_names,
)


@pytest.mark.asyncio
async def test_live_name_call_follows_meshchat_patch():
    g: dict = {}
    inject_meshchat_names(g)
    assert isinstance(g["get_session"], LiveMeshchatName)

    with patch(
        "meshchatx.meshchat.get_session",
        new_callable=AsyncMock,
    ) as mock_session:
        mock_session.return_value = {"token": "x"}
        result = await g["get_session"](object())
        assert result == {"token": "x"}
        mock_session.assert_awaited_once()


def test_exception_classes_remain_real_types():
    g: dict = {}
    inject_meshchat_names(g)
    exception_types = [
        value
        for value in g.values()
        if isinstance(value, type) and issubclass(value, BaseException)
    ]
    assert exception_types
    for exc_type in exception_types:
        assert not isinstance(exc_type, LiveMeshchatName)
        try:
            raise exc_type("probe")
        except exc_type:
            pass


def test_async_utils_attribute_access_follows_patch():
    g: dict = {}
    inject_meshchat_names(g)
    assert isinstance(g["AsyncUtils"], LiveMeshchatName)

    with patch("meshchatx.meshchat.AsyncUtils") as mock_async_utils:
        mock_async_utils.run_async.return_value = "ok"
        assert g["AsyncUtils"].run_async(object()) == "ok"
