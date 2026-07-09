# SPDX-License-Identifier: 0BSD

"""Incoming-call policy: blocked list, DND, contacts-only / block-strangers, voicemail + ring."""

from unittest.mock import MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat

CALLER_HASH_HEX = "a1" * 16
LXMF_DEST_HEX = "b2" * 16


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
    ctx.database.announces.get_announce_by_hash.return_value = None
    ctx.database.announces.get_announces_by_identity_hash.return_value = []
    ctx.voicemail_manager = MagicMock()
    app.current_context = ctx
    app.is_destination_blocked = MagicMock(return_value=False)
    app.websocket_broadcast = MagicMock()
    app.get_name_for_identity_hash = MagicMock(return_value="Caller")
    app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=None)
    app.get_lxst_telephony_hash_for_identity_hash = MagicMock(return_value=None)
    return app


def _run_incoming(app, caller, ctx=None):
    bound = ReticulumMeshChat.on_incoming_telephone_call.__get__(app, ReticulumMeshChat)
    bound(caller, context=ctx)


def test_incoming_rejects_when_blocked_uses_delayed_hangup(policy_app):
    policy_app.is_destination_blocked.return_value = True
    caller = _caller_identity()

    with patch("meshchatx.meshchat.threading.Timer") as mock_timer:

        def run_timer(delay, fn):
            assert delay == 0.5
            fn()
            t = MagicMock()
            t.start = MagicMock()
            return t

        mock_timer.side_effect = run_timer

        _run_incoming(policy_app, caller)

    policy_app.current_context.telephone_manager.telephone.hangup.assert_called_once()
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_not_called()


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

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_called()
    call_kwargs = policy_app.current_context.database.contacts.get_contact_by_identity_hash.call_args
    assert call_kwargs[0][0] == CALLER_HASH_HEX
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

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_called()
    assert (
        policy_app.current_context.database.contacts.get_contact_by_identity_hash.call_count
        >= 1
    )
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_called_once_with(
        caller
    )
    policy_app.current_context.telephone_manager.telephone.hangup.assert_not_called()
    async_utils.run_async.assert_called_once()


def test_contacts_only_accepts_contact_saved_under_lxmf_destination(policy_app):
    """Chat UI often stores LXMF destination hash as remote_identity_hash."""
    policy_app.is_destination_blocked.return_value = False
    policy_app.config.do_not_disturb_enabled.get.return_value = False
    policy_app.config.telephone_allow_calls_from_contacts_only.get.return_value = True
    policy_app.config.block_all_from_strangers.get.return_value = False
    policy_app.current_context.database.announces.get_announces_by_identity_hash.return_value = [
        {
            "destination_hash": LXMF_DEST_HEX,
            "identity_hash": CALLER_HASH_HEX,
            "aspect": "lxmf.delivery",
        },
    ]
    policy_app.get_lxmf_destination_hash_for_identity_hash.return_value = LXMF_DEST_HEX

    def lookup(primary, related_hashes=None):
        keys = {primary, *(related_hashes or ())}
        if LXMF_DEST_HEX in keys or CALLER_HASH_HEX in keys:
            return {"id": 1, "name": "Friend", "remote_identity_hash": LXMF_DEST_HEX}
        return None

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.side_effect = lookup

    caller = _caller_identity()

    with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
        async_utils.run_async = MagicMock()
        _run_incoming(policy_app, caller)

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

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_called()
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_not_called()


def test_when_policy_off_stranger_rings(policy_app):
    policy_app.is_destination_blocked.return_value = False
    policy_app.config.do_not_disturb_enabled.get.return_value = False
    policy_app.config.telephone_allow_calls_from_contacts_only.get.return_value = False
    policy_app.config.block_all_from_strangers.get.return_value = False
    policy_app.current_context.database.contacts.get_contact_by_identity_hash.return_value = None

    caller = _caller_identity()

    with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
        async_utils.run_async = MagicMock()
        _run_incoming(policy_app, caller)

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_called()
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_called_once_with(
        caller
    )
    async_utils.run_async.assert_called_once()


def test_rejects_incoming_while_outgoing_initiation(policy_app):
    policy_app.current_context.telephone_manager.initiation_status = "Dialing..."
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

    policy_app.current_context.telephone_manager.telephone.hangup.assert_called_once()
    policy_app.current_context.voicemail_manager.handle_incoming_call.assert_not_called()
    async_utils.run_async.assert_not_called()


def test_uses_passed_context_not_app_current_context(policy_app):
    """Ensure on_incoming_telephone_call uses the ctx parameter, not self.current_context."""
    policy_app.is_destination_blocked.return_value = False
    policy_app.config.do_not_disturb_enabled.get.return_value = False
    policy_app.config.telephone_allow_calls_from_contacts_only.get.return_value = True
    policy_app.config.block_all_from_strangers.get.return_value = False

    policy_app.current_context.database.contacts.get_contact_by_identity_hash.return_value = None

    other_ctx = MagicMock()
    other_ctx.telephone_manager = policy_app.current_context.telephone_manager
    other_ctx.config = policy_app.config
    other_ctx.database = MagicMock()
    other_ctx.database.announces.get_announce_by_hash.return_value = None
    other_ctx.database.announces.get_announces_by_identity_hash.return_value = []
    other_ctx.database.contacts.get_contact_by_identity_hash.return_value = {
        "id": 1,
        "name": "Friend",
    }
    other_ctx.voicemail_manager = MagicMock()

    caller = _caller_identity()

    with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
        async_utils.run_async = MagicMock()
        _run_incoming(policy_app, caller, ctx=other_ctx)

    other_ctx.database.contacts.get_contact_by_identity_hash.assert_called()
    policy_app.current_context.database.contacts.get_contact_by_identity_hash.assert_not_called()
    other_ctx.voicemail_manager.handle_incoming_call.assert_called_once_with(caller)
