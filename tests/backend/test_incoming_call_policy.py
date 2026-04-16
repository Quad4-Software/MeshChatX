# SPDX-License-Identifier: 0BSD

"""Incoming-call policy: blocked list, DND, contacts-only / block-strangers, voicemail + ring."""

from unittest.mock import MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat

CALLER_HASH_HEX = "a1" * 16


def _caller_identity():
    ident = MagicMock()
    ident.hash = bytes.fromhex(CALLER_HASH_HEX)
    return ident


@pytest.fixture
def policy_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    tm = MagicMock()
    tm.initiation_status = None
    tm.telephone = MagicMock()
    ctx.telephone_manager = tm
    ctx.config = MagicMock()
    ctx.database = MagicMock()
    ctx.voicemail_manager = MagicMock()
    app.current_context = ctx
    app.is_destination_blocked = MagicMock(return_value=False)
    app.websocket_broadcast = MagicMock()
    return app


def _run_incoming(app, caller, ctx=None):
    bound = ReticulumMeshChat.on_incoming_telephone_call.__get__(app, ReticulumMeshChat)
    bound(caller, context=ctx)


def test_incoming_rejects_when_blocked_immediate_hangup(policy_app):
    policy_app.is_destination_blocked.return_value = True
    caller = _caller_identity()
    _run_incoming(policy_app, caller)

    policy_app.telephone_manager.telephone.hangup.assert_called_once()
    policy_app.voicemail_manager.handle_incoming_call.assert_not_called()


def test_incoming_dnd_rejects_before_contact_check(policy_app):
    policy_app.is_destination_blocked.return_value = False
    policy_app.config.do_not_disturb_enabled.get.return_value = True
    policy_app.config.telephone_allow_calls_from_contacts_only.get.return_value = True
    policy_app.current_context.database.contacts.get_contact_by_identity_hash.return_value = {
        "id": 1,
    }

    caller = _caller_identity()

    with patch("meshchatx.meshchat.threading.Timer") as mock_timer:

        def run_timer(delay, fn):
            assert delay == 0.5
            fn()
            t = MagicMock()
            t.start = MagicMock()
            return t

        mock_timer.side_effect = run_timer

        with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
            async_utils.run_async = MagicMock()
            _run_incoming(policy_app, caller)

    policy_app.current_context.telephone_manager.telephone.hangup.assert_called_once()
    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_not_called()
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_not_called()
    async_utils.run_async.assert_not_called()


def test_contacts_only_rejects_non_contact_uses_identity_lookup(policy_app):
    policy_app.is_destination_blocked.return_value = False
    policy_app.config.do_not_disturb_enabled.get.return_value = False
    policy_app.config.telephone_allow_calls_from_contacts_only.get.return_value = True
    policy_app.config.block_all_from_strangers.get.return_value = False
    policy_app.current_context.database.contacts.get_contact_by_identity_hash.return_value = None

    caller = _caller_identity()

    with patch("meshchatx.meshchat.threading.Timer") as mock_timer:

        def run_timer(delay, fn):
            assert delay == 0.5
            fn()
            t = MagicMock()
            t.start = MagicMock()
            return t

        mock_timer.side_effect = run_timer

        with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
            async_utils.run_async = MagicMock()
            _run_incoming(policy_app, caller)

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_called_once_with(
        CALLER_HASH_HEX,
    )
    policy_app.current_context.telephone_manager.telephone.hangup.assert_called_once()
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_not_called()
    async_utils.run_async.assert_not_called()


def test_contacts_only_accepts_matching_contact(policy_app):
    policy_app.is_destination_blocked.return_value = False
    policy_app.config.do_not_disturb_enabled.get.return_value = False
    policy_app.config.telephone_allow_calls_from_contacts_only.get.return_value = True
    policy_app.config.block_all_from_strangers.get.return_value = False
    policy_app.current_context.database.contacts.get_contact_by_identity_hash.return_value = {
        "id": 1,
        "name": "Friend",
    }

    caller = _caller_identity()

    with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
        async_utils.run_async = MagicMock()
        _run_incoming(policy_app, caller)

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_called_once_with(
        CALLER_HASH_HEX,
    )
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_called_once_with(
        caller
    )
    policy_app.current_context.telephone_manager.telephone.hangup.assert_not_called()
    async_utils.run_async.assert_called_once()


def test_block_all_strangers_uses_same_contact_gate(policy_app):
    policy_app.is_destination_blocked.return_value = False
    policy_app.config.do_not_disturb_enabled.get.return_value = False
    policy_app.config.telephone_allow_calls_from_contacts_only.get.return_value = False
    policy_app.config.block_all_from_strangers.get.return_value = True
    policy_app.current_context.database.contacts.get_contact_by_identity_hash.return_value = None

    caller = _caller_identity()

    with patch("meshchatx.meshchat.threading.Timer") as mock_timer:

        def run_timer(delay, fn):
            fn()
            t = MagicMock()
            t.start = MagicMock()
            return t

        mock_timer.side_effect = run_timer

        with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
            async_utils.run_async = MagicMock()
            _run_incoming(policy_app, caller)

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_called_once_with(
        CALLER_HASH_HEX,
    )
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_not_called()


def test_when_policy_off_stranger_rings(policy_app):
    policy_app.is_destination_blocked.return_value = False
    policy_app.config.do_not_disturb_enabled.get.return_value = False
    policy_app.config.telephone_allow_calls_from_contacts_only.get.return_value = False
    policy_app.config.block_all_from_strangers.get.return_value = False

    caller = _caller_identity()

    with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
        async_utils.run_async = MagicMock()
        _run_incoming(policy_app, caller)

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_not_called()
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_called_once_with(
        caller
    )
    async_utils.run_async.assert_called_once()


def test_ignores_incoming_while_outgoing_initiation(policy_app):
    policy_app.current_context.telephone_manager.initiation_status = "Dialing..."
    caller = _caller_identity()

    with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
        async_utils.run_async = MagicMock()
        _run_incoming(policy_app, caller)

    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_not_called()
    async_utils.run_async.assert_not_called()
