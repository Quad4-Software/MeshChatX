# SPDX-License-Identifier: 0BSD

import json

import pytest

from meshchatx import android_push_bridge
from meshchatx.android_push_bridge import (
    install_websocket_hook,
    lxmf_delivery_notification_text,
)


@pytest.fixture(autouse=True)
def reset_ws_hook_flag():
    android_push_bridge._ws_hook_installed = False
    yield
    android_push_bridge._ws_hook_installed = False


def test_lxmf_delivery_skips_wrong_type():
    assert lxmf_delivery_notification_text({"type": "config"}) is None


def test_lxmf_delivery_skips_when_sieve_suppresses():
    assert (
        lxmf_delivery_notification_text(
            {
                "type": "lxmf.delivery",
                "sieve_suppress_notifications": True,
                "remote_identity_name": "Alice",
                "lxmf_message": {"is_incoming": True, "title": "Hi", "content": "Body"},
            },
        )
        is None
    )


def test_lxmf_delivery_skips_outbound():
    assert (
        lxmf_delivery_notification_text(
            {
                "type": "lxmf.delivery",
                "remote_identity_name": "Bob",
                "lxmf_message": {
                    "is_incoming": False,
                    "title": "Hi",
                    "content": "Body",
                },
            },
        )
        is None
    )


def test_lxmf_delivery_skips_telemetry_only():
    assert (
        lxmf_delivery_notification_text(
            {
                "type": "lxmf.delivery",
                "remote_identity_name": "Peer",
                "lxmf_message": {
                    "is_incoming": True,
                    "title": "",
                    "content": "",
                    "fields": {"telemetry": {"lat": 1}},
                },
            },
        )
        is None
    )


def test_lxmf_delivery_incoming_title_and_body():
    assert lxmf_delivery_notification_text(
        {
            "type": "lxmf.delivery",
            "remote_identity_name": "Charlie",
            "lxmf_message": {
                "is_incoming": True,
                "title": "Subject",
                "content": "Hello there",
            },
        },
    ) == ("Charlie", "Subject\nHello there")


def test_lxmf_delivery_truncates_long_content():
    long_body = "x" * 250
    title, body = lxmf_delivery_notification_text(
        {
            "type": "lxmf.delivery",
            "remote_identity_name": "Dana",
            "lxmf_message": {
                "is_incoming": True,
                "title": "",
                "content": long_body,
            },
        },
    )
    assert title == "Dana"
    assert body.endswith("...")
    assert len(body) == 200


def test_lxmf_delivery_skips_reaction():
    assert (
        lxmf_delivery_notification_text(
            {
                "type": "lxmf.delivery",
                "remote_identity_name": "Eve",
                "lxmf_message": {
                    "is_incoming": True,
                    "is_reaction": True,
                    "reaction_emoji": "thumbsup",
                    "title": "",
                    "content": "",
                    "fields": {"reaction": {"reaction_to": "deadbeef"}},
                },
            },
        )
        is None
    )


def test_lxmf_delivery_default_sender():
    t, b = lxmf_delivery_notification_text(
        {
            "type": "lxmf.delivery",
            "lxmf_message": {
                "is_incoming": True,
                "title": "Only title",
                "content": "",
            },
        },
    )
    assert t == "Mesh"
    assert b == "Only title"


def test_lxmf_delivery_image_fields_only():
    assert lxmf_delivery_notification_text(
        {
            "type": "lxmf.delivery",
            "remote_identity_name": "Fran",
            "lxmf_message": {
                "is_incoming": True,
                "title": "",
                "content": "",
                "fields": {"image": {"image_type": "png", "image_size": 1}},
            },
        },
    ) == ("Fran", "Image message")


def test_lxmf_delivery_audio_fields_only():
    assert lxmf_delivery_notification_text(
        {
            "type": "lxmf.delivery",
            "remote_identity_name": "Gus",
            "lxmf_message": {
                "is_incoming": True,
                "title": "",
                "content": "",
                "fields": {"audio": {"audio_mode": 1, "audio_size": 1}},
            },
        },
    ) == ("Gus", "Audio message")


def test_lxmf_delivery_attachment_fields_only():
    assert lxmf_delivery_notification_text(
        {
            "type": "lxmf.delivery",
            "remote_identity_name": "Hal",
            "lxmf_message": {
                "is_incoming": True,
                "title": "",
                "content": "",
                "fields": {
                    "file_attachments": [{"file_name": "a.bin", "file_size": 1}],
                },
            },
        },
    ) == ("Hal", "Attachment")


def test_lxmf_delivery_skips_when_open_conversation(monkeypatch):
    monkeypatch.setattr(android_push_bridge, "_is_open_conversation", lambda _h: True)
    assert (
        lxmf_delivery_notification_text(
            {
                "type": "lxmf.delivery",
                "remote_identity_name": "Open",
                "lxmf_message": {
                    "is_incoming": True,
                    "source_hash": "a" * 32,
                    "title": "Hi",
                    "content": "Body",
                },
            },
        )
        is None
    )


def test_lxmf_delivery_skips_when_dnd(monkeypatch):
    monkeypatch.setattr(android_push_bridge, "_dnd_enabled", lambda: True)
    assert (
        lxmf_delivery_notification_text(
            {
                "type": "lxmf.delivery",
                "remote_identity_name": "Quiet",
                "lxmf_message": {
                    "is_incoming": True,
                    "source_hash": "b" * 32,
                    "title": "Hi",
                    "content": "Body",
                },
            },
        )
        is None
    )


def test_lxmf_delivery_notifies_other_peer_while_one_open(monkeypatch):
    monkeypatch.setattr(
        android_push_bridge,
        "_is_open_conversation",
        lambda h: h == "a" * 32,
    )
    monkeypatch.setattr(android_push_bridge, "_dnd_enabled", lambda: False)
    assert lxmf_delivery_notification_text(
        {
            "type": "lxmf.delivery",
            "remote_identity_name": "Other",
            "lxmf_message": {
                "is_incoming": True,
                "source_hash": "b" * 32,
                "title": "Hi",
                "content": "Body",
            },
        },
    ) == ("Other", "Hi\nBody")


def test_after_broadcast_passes_destination_hash(monkeypatch):
    calls = []

    def fake_notify(title, body, dedupe, destination_hash=None):
        calls.append((title, body, dedupe, destination_hash))

    monkeypatch.setattr(android_push_bridge, "_notify_java", fake_notify)
    monkeypatch.setattr(android_push_bridge, "_dnd_enabled", lambda: False)
    monkeypatch.setattr(android_push_bridge, "_is_open_conversation", lambda _h: False)
    payload = json.dumps(
        {
            "type": "lxmf.delivery",
            "remote_identity_name": "Zed",
            "lxmf_message": {
                "is_incoming": True,
                "hash": "cafebabe" + "0" * 24,
                "source_hash": "d" * 32,
                "title": "T",
                "content": "C",
            },
        },
    )
    android_push_bridge._after_websocket_broadcast(payload)
    assert calls
    assert calls[0][0] == "Zed"
    assert calls[0][3] == "d" * 32


def test_after_websocket_broadcast_ignores_non_string(monkeypatch):
    calls = []
    monkeypatch.setattr(android_push_bridge, "_notify_java", lambda *a: calls.append(a))
    android_push_bridge._after_websocket_broadcast(123)
    assert calls == []


def test_after_websocket_broadcast_ignores_invalid_json(monkeypatch):
    calls = []
    monkeypatch.setattr(android_push_bridge, "_notify_java", lambda *a: calls.append(a))
    android_push_bridge._after_websocket_broadcast("{not json")
    assert calls == []


def test_after_websocket_broadcast_skips_when_notification_text_none(monkeypatch):
    calls = []
    monkeypatch.setattr(android_push_bridge, "_notify_java", lambda *a: calls.append(a))
    android_push_bridge._after_websocket_broadcast(json.dumps({"type": "config"}))
    assert calls == []


def test_after_websocket_broadcast_incoming_call(monkeypatch):
    inc = []
    cancel = []
    monkeypatch.setattr(
        android_push_bridge,
        "_notify_incoming_call_java",
        lambda *a: inc.append(a),
    )
    monkeypatch.setattr(
        android_push_bridge,
        "_cancel_incoming_call_notification_java",
        lambda: cancel.append(1),
    )
    android_push_bridge._after_websocket_broadcast(
        json.dumps(
            {
                "type": "telephone_ringing",
                "remote_identity_hash": "aabbccdd",
                "remote_identity_name": "Zed",
            },
        ),
    )
    assert inc == [("Zed", "aabbccdd")]
    assert cancel == []


def test_after_websocket_broadcast_call_ended_cancels(monkeypatch):
    calls = []
    cancel = []
    monkeypatch.setattr(android_push_bridge, "_notify_java", lambda *a: calls.append(a))
    monkeypatch.setattr(
        android_push_bridge,
        "_cancel_incoming_call_notification_java",
        lambda: cancel.append(1),
    )
    android_push_bridge._after_websocket_broadcast(
        json.dumps({"type": "telephone_call_ended"}),
    )
    assert calls == []
    assert cancel == [1]


def test_after_websocket_broadcast_missed_call(monkeypatch):
    miss = []
    monkeypatch.setattr(
        android_push_bridge,
        "_notify_missed_call_java",
        lambda *a: miss.append(a),
    )
    android_push_bridge._after_websocket_broadcast(
        json.dumps(
            {
                "type": "telephone_missed_call",
                "remote_identity_hash": "00112233",
                "remote_identity_name": "Mara",
            },
        ),
    )
    assert len(miss) == 1
    assert miss[0][0] == "Missed call"
    assert "Mara" in miss[0][1]
    assert miss[0][2] == "00112233"


def test_after_websocket_broadcast_notifies_with_dedupe(monkeypatch):
    calls = []
    monkeypatch.setattr(android_push_bridge, "_notify_java", lambda *a: calls.append(a))
    payload = {
        "type": "lxmf.delivery",
        "remote_identity_name": "Jules",
        "lxmf_message": {
            "is_incoming": True,
            "title": "Hi",
            "content": "There",
            "hash": "abcdef0123456789",
        },
    }
    android_push_bridge._after_websocket_broadcast(json.dumps(payload))
    assert len(calls) == 1
    assert calls[0][0] == "Jules"
    assert calls[0][1] == "Hi\nThere"
    assert calls[0][2] == "abcdef0123456789"


def test_after_websocket_broadcast_short_hash_skips_dedupe(monkeypatch):
    calls = []
    monkeypatch.setattr(android_push_bridge, "_notify_java", lambda *a: calls.append(a))
    payload = {
        "type": "lxmf.delivery",
        "remote_identity_name": "Kim",
        "lxmf_message": {
            "is_incoming": True,
            "title": "T",
            "content": "",
            "hash": "short",
        },
    }
    android_push_bridge._after_websocket_broadcast(json.dumps(payload))
    assert calls[0][2] is None


def test_install_skips_when_not_chaquopy_android(monkeypatch):
    monkeypatch.setattr(android_push_bridge, "_is_chaquopy_android", lambda: False)

    class Rmc:
        async def websocket_broadcast(self, data):
            return data

    original = Rmc.websocket_broadcast
    install_websocket_hook(Rmc)
    assert Rmc.websocket_broadcast is original


@pytest.mark.asyncio
async def test_install_wraps_broadcast_and_notifies(monkeypatch):
    monkeypatch.setattr(android_push_bridge, "_is_chaquopy_android", lambda: True)
    calls = []
    monkeypatch.setattr(android_push_bridge, "_notify_java", lambda *a: calls.append(a))

    class Rmc:
        async def websocket_broadcast(self, data):
            return "ok"

    unwrapped = Rmc.websocket_broadcast
    install_websocket_hook(Rmc)
    payload = {
        "type": "lxmf.delivery",
        "remote_identity_name": "Lee",
        "lxmf_message": {"is_incoming": True, "title": "A", "content": "B"},
    }
    result = await Rmc().websocket_broadcast(json.dumps(payload))
    assert result == "ok"
    assert len(calls) == 1
    assert calls[0][:2] == ("Lee", "A\nB")
    Rmc.websocket_broadcast = unwrapped


@pytest.mark.asyncio
async def test_install_is_idempotent(monkeypatch):
    monkeypatch.setattr(android_push_bridge, "_is_chaquopy_android", lambda: True)
    invocations = []

    class Rmc:
        async def websocket_broadcast(self, data):
            invocations.append("orig")

    unwrapped = Rmc.websocket_broadcast
    install_websocket_hook(Rmc)
    install_websocket_hook(Rmc)
    monkeypatch.setattr(android_push_bridge, "_notify_java", lambda *a: None)
    await Rmc().websocket_broadcast(json.dumps({"type": "config"}))
    assert invocations == ["orig"]
    Rmc.websocket_broadcast = unwrapped
