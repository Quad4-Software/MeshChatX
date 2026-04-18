# SPDX-License-Identifier: 0BSD

"""Integration-style tests for LXMF handle_forwarding (rule path and reply path)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.async_utils import AsyncUtils


def _run_async_immediate(coro):
    asyncio.run(coro)


@pytest.fixture
def forwarding_app():
    app = MagicMock(spec=ReticulumMeshChat)
    app.current_context = MagicMock()
    app.current_context.database = MagicMock()
    app.current_context.database.messages = MagicMock()
    app.current_context.database.misc = MagicMock()
    app.current_context.forwarding_manager = MagicMock()

    app.send_message = AsyncMock()

    app.handle_forwarding = ReticulumMeshChat.handle_forwarding.__get__(
        app,
        ReticulumMeshChat,
    )
    return app


def _make_lxmf_message(source_hex: str, dest_hex: str):
    msg = MagicMock()
    msg.source_hash = bytes.fromhex(source_hex)
    msg.destination_hash = bytes.fromhex(dest_hex)
    msg.content = "body"
    msg.title = "t"
    msg.get_fields = MagicMock(return_value={})
    return msg


@pytest.mark.integration
def test_handle_forwarding_forward_path_sends_via_alias(forwarding_app):
    app = forwarding_app
    ctx = app.current_context

    src = "aa" * 16
    dest_identity = "bb" * 16
    forward_to = "cc" * 16
    alias = "dd" * 16

    ctx.database.messages.get_forwarding_mapping.return_value = None
    ctx.database.misc.get_forwarding_rules.return_value = [
        {
            "source_filter_hash": None,
            "forward_to_hash": forward_to,
        },
    ]
    ctx.forwarding_manager.get_or_create_mapping.return_value = {
        "alias_hash": alias,
    }

    msg = _make_lxmf_message(src, dest_identity)

    with patch.object(AsyncUtils, "run_async", side_effect=_run_async_immediate):
        app.handle_forwarding(msg, context=ctx)

    app.send_message.assert_called_once()
    kwargs = app.send_message.call_args[1]
    assert kwargs["destination_hash"] == forward_to
    assert kwargs["sender_identity_hash"] == alias
    assert kwargs["content"] == "body"


@pytest.mark.integration
def test_handle_forwarding_reply_path_sends_to_original_sender(forwarding_app):
    app = forwarding_app
    ctx = app.current_context

    original = "ee" * 16
    alias = "ff" * 16

    ctx.database.messages.get_forwarding_mapping.return_value = {
        "original_sender_hash": original,
    }
    msg = _make_lxmf_message("aa" * 16, alias)

    with patch.object(AsyncUtils, "run_async", side_effect=_run_async_immediate):
        app.handle_forwarding(msg, context=ctx)

    ctx.database.misc.get_forwarding_rules.assert_not_called()
    app.send_message.assert_called_once()
    kwargs = app.send_message.call_args[1]
    assert kwargs["destination_hash"] == original
    assert "sender_identity_hash" not in kwargs


@pytest.mark.integration
def test_handle_forwarding_skips_rule_when_source_filter_mismatches(forwarding_app):
    app = forwarding_app
    ctx = app.current_context

    src = "aa" * 16
    dest_identity = "bb" * 16
    other = "99" * 16

    ctx.database.messages.get_forwarding_mapping.return_value = None
    ctx.database.misc.get_forwarding_rules.return_value = [
        {
            "source_filter_hash": other,
            "forward_to_hash": "cc" * 16,
        },
    ]

    msg = _make_lxmf_message(src, dest_identity)

    with patch.object(AsyncUtils, "run_async", side_effect=_run_async_immediate):
        app.handle_forwarding(msg, context=ctx)

    app.send_message.assert_not_called()
    ctx.forwarding_manager.get_or_create_mapping.assert_not_called()
