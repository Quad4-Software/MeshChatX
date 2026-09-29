# SPDX-License-Identifier: 0BSD
"""References for pre-transfer inbound LXMF delivery resource policy."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.lxmf_inbound_policy import (
    evaluate_inbound_delivery_resource_policy,
    install_lxmf_inbound_delivery_policy,
    source_hash_from_delivery_resource,
)
from tests.backend.lxmf_tools_support import PEER_FRIEND, PEER_SPAMMER


def _resource_for_peer(peer_hash: str):
    identity = SimpleNamespace(hash=bytes.fromhex(peer_hash))
    link = SimpleNamespace(get_remote_identity=lambda: identity)
    return SimpleNamespace(
        link=link,
        hash=bytes.fromhex("aa" * 16),
        status=0,
        cancel=MagicMock(),
    )


def _policy_app(*, is_contact=False, is_blocked=False):
    app = MagicMock()
    app._is_contact = MagicMock(return_value=is_contact)  # skipcq: PYL-W0212
    app.is_destination_blocked = MagicMock(return_value=is_blocked)
    return app


def _policy_ctx(*, block_all=False, block_attachments=False):
    ctx = MagicMock()
    ctx.config.block_all_from_strangers.get.return_value = block_all
    ctx.config.block_attachments_from_strangers.get.return_value = block_attachments
    return ctx


def test_source_hash_from_delivery_resource():
    resource = _resource_for_peer(PEER_SPAMMER)
    assert (
        source_hash_from_delivery_resource(resource) == PEER_SPAMMER
    )  # skipcq: BAN-B101
    assert (
        source_hash_from_delivery_resource(SimpleNamespace(link=None)) is None
    )  # skipcq: BAN-B101


@pytest.mark.parametrize(
    ("block_all", "block_attachments", "is_contact", "expected_reason"),
    [
        (True, False, False, "block_all_strangers"),
        (False, True, False, "block_stranger_attachments"),
        (True, True, True, None),
        (False, True, True, None),
        (False, False, False, None),
    ],
)
def test_evaluate_inbound_delivery_resource_policy(
    block_all,
    block_attachments,
    is_contact,
    expected_reason,
):
    app = _policy_app(is_contact=is_contact)
    ctx = _policy_ctx(block_all=block_all, block_attachments=block_attachments)
    resource = _resource_for_peer(PEER_SPAMMER)

    reject, reason = evaluate_inbound_delivery_resource_policy(app, ctx, resource)
    if expected_reason is None:
        assert reject is False  # skipcq: BAN-B101
        assert reason is None  # skipcq: BAN-B101
    else:
        assert reject is True  # skipcq: BAN-B101
        assert reason == expected_reason  # skipcq: BAN-B101


def test_blocked_peer_rejects_before_transfer():
    app = _policy_app(is_blocked=True)
    ctx = _policy_ctx()
    resource = _resource_for_peer(PEER_SPAMMER)

    reject, reason = evaluate_inbound_delivery_resource_policy(app, ctx, resource)
    assert reject is True  # skipcq: BAN-B101
    assert reason == "blocked"  # skipcq: BAN-B101


def test_unknown_identity_does_not_reject_attachment_block():
    """Fresh LXMF delivery links often lack remote identity at advertise.

    Rejecting unknown identity marked contact attachments REJECTED on the
    sender while packet-sized messages still arrived. Defer to delivery.
    """
    app = _policy_app(is_contact=False)
    ctx = _policy_ctx(block_attachments=True, block_all=True)
    resource = SimpleNamespace(
        link=SimpleNamespace(get_remote_identity=lambda: None, destination=None),
        hash=bytes.fromhex("aa" * 16),
        status=0,
        cancel=MagicMock(),
    )

    reject, reason = evaluate_inbound_delivery_resource_policy(app, ctx, resource)
    assert reject is False  # skipcq: BAN-B101
    assert reason is None  # skipcq: BAN-B101
    app._is_contact.assert_not_called()  # skipcq: PYL-W0212
    app.is_destination_blocked.assert_not_called()


def test_inbound_link_local_destination_identity_is_not_peer():
    """Inbound links carry the local lxmf.delivery destination.

    When the remote has not identified, destination.identity is our own
    identity, not the sender's. Using it as the peer hash makes every
    unidentified sender a known stranger and rejects all resource deliveries.
    """
    local_identity = SimpleNamespace(hash=bytes.fromhex("11" * 16))
    resource = SimpleNamespace(
        link=SimpleNamespace(
            get_remote_identity=lambda: None,
            destination=SimpleNamespace(identity=local_identity),
        ),
        hash=bytes.fromhex("aa" * 16),
        status=0,
        cancel=MagicMock(),
    )

    assert source_hash_from_delivery_resource(resource) is None  # skipcq: BAN-B101

    app = _policy_app(is_contact=False)
    ctx = _policy_ctx(block_attachments=True, block_all=True)
    reject, reason = evaluate_inbound_delivery_resource_policy(app, ctx, resource)
    assert reject is False  # skipcq: BAN-B101
    assert reason is None  # skipcq: BAN-B101
    app._is_contact.assert_not_called()  # skipcq: PYL-W0212
    app.is_destination_blocked.assert_not_called()


def test_install_rejects_stranger_resource_at_advertise():
    router = SimpleNamespace()
    router.delivery_resource_advertised = MagicMock(return_value=True)
    router.delivery_resource_transfer_began = MagicMock()
    app = _policy_app(is_contact=False)
    ctx = _policy_ctx(block_attachments=True)

    install_lxmf_inbound_delivery_policy(router, app, lambda: ctx)

    resource = _resource_for_peer(PEER_SPAMMER)
    accepted = router.delivery_resource_advertised(resource)
    assert accepted is False  # skipcq: BAN-B101

    app._is_contact.return_value = True  # skipcq: PYL-W0212
    accepted_contact = router.delivery_resource_advertised(
        _resource_for_peer(PEER_FRIEND),
    )
    assert accepted_contact is True  # skipcq: BAN-B101


def test_install_accepts_unknown_identity_at_advertise():
    router = SimpleNamespace()
    original_advertised = MagicMock(return_value=True)
    router.delivery_resource_advertised = original_advertised
    router.delivery_resource_transfer_began = MagicMock()
    app = _policy_app(is_contact=False)
    ctx = _policy_ctx(block_attachments=True, block_all=True)

    install_lxmf_inbound_delivery_policy(router, app, lambda: ctx)

    resource = SimpleNamespace(
        link=SimpleNamespace(get_remote_identity=lambda: None, destination=None),
        hash=bytes.fromhex("cc" * 16),
        status=0,
        cancel=MagicMock(),
    )
    accepted = router.delivery_resource_advertised(resource)
    assert accepted is True  # skipcq: BAN-B101
    original_advertised.assert_called_once_with(resource)
    app._is_contact.assert_not_called()  # skipcq: PYL-W0212


def test_install_cancels_stranger_resource_when_transfer_begins():
    router = SimpleNamespace()
    router.delivery_resource_advertised = MagicMock(return_value=True)
    began_calls = []

    def _record_began(resource):
        began_calls.append(resource)

    router.delivery_resource_transfer_began = _record_began
    app = _policy_app(is_contact=False)
    ctx = _policy_ctx(block_all=True)

    install_lxmf_inbound_delivery_policy(router, app, lambda: ctx)

    resource = _resource_for_peer(PEER_SPAMMER)
    router.delivery_resource_transfer_began(resource)
    resource.cancel.assert_called_once()
    assert began_calls == []  # skipcq: BAN-B101


def test_install_does_not_cancel_when_identity_unknown_at_transfer_began():
    router = SimpleNamespace()
    router.delivery_resource_advertised = MagicMock(return_value=True)
    began_calls = []

    def _record_began(resource):
        began_calls.append(resource)

    router.delivery_resource_transfer_began = _record_began
    app = _policy_app(is_contact=False)
    ctx = _policy_ctx(block_attachments=True, block_all=True)

    install_lxmf_inbound_delivery_policy(router, app, lambda: ctx)

    resource = SimpleNamespace(
        link=SimpleNamespace(get_remote_identity=lambda: None, destination=None),
        hash=bytes.fromhex("bb" * 16),
        status=0,
        cancel=MagicMock(),
    )
    router.delivery_resource_transfer_began(resource)
    resource.cancel.assert_not_called()
    assert began_calls == [resource]  # skipcq: BAN-B101


def test_install_is_idempotent():
    router = SimpleNamespace()
    router.delivery_resource_advertised = MagicMock(return_value=True)
    router.delivery_resource_transfer_began = MagicMock()
    app = _policy_app()
    ctx = _policy_ctx()

    install_lxmf_inbound_delivery_policy(router, app, lambda: ctx)
    first = router.delivery_resource_advertised
    install_lxmf_inbound_delivery_policy(router, app, lambda: ctx)
    assert router.delivery_resource_advertised is first  # skipcq: BAN-B101


def test_policy_does_not_reject_on_blocklist_error():
    """A broken blocklist lookup must not produce a false blocked verdict."""
    from meshchatx.src.backend.lxmf_inbound_policy import (
        evaluate_inbound_delivery_resource_policy,
    )

    class BrokenApp:
        def is_destination_blocked(self, *a, **kw):
            return True  # fail-closed variant would reject here

        def _is_contact(self, *a, **kw):
            return False

    class FakeLink:
        def get_remote_identity(self):
            from types import SimpleNamespace

            return SimpleNamespace(hash=b"\x55" * 16)

    resource = SimpleNamespace(link=FakeLink())
    ctx = SimpleNamespace(
        config=SimpleNamespace(
            block_all_from_strangers=SimpleNamespace(get=lambda: False),
            block_attachments_from_strangers=SimpleNamespace(get=lambda: False),
        )
    )
    # is_destination_blocked that honours the fail_closed kwarg
    class App(BrokenApp):
        def is_destination_blocked(self, h, context=None, fail_closed=True):
            return fail_closed

    reject, _ = evaluate_inbound_delivery_resource_policy(App(), ctx, resource)
    assert reject is False

    # Same story for a failing contact lookup under block_all_from_strangers.
    class App2(BrokenApp):
        def is_destination_blocked(self, h, context=None, fail_closed=True):
            return False

        def _is_contact(self, *a, **kw):
            raise RuntimeError("db busy")

    ctx2 = SimpleNamespace(
        config=SimpleNamespace(
            block_all_from_strangers=SimpleNamespace(get=lambda: True),
            block_attachments_from_strangers=SimpleNamespace(get=lambda: True),
        )
    )
    reject, _ = evaluate_inbound_delivery_resource_policy(App2(), ctx2, resource)
    assert reject is False
