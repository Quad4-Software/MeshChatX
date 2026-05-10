# SPDX-License-Identifier: 0BSD

"""Android (Chaquopy): mirror selected websocket payloads to OS notifications."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("meshchatx.android_push_bridge")

_ws_hook_installed = False


def _is_chaquopy_android() -> bool:
    try:
        import java  # noqa: F401
    except ImportError:
        return False
    return True


def _get_android_external_files_dir() -> str | None:
    """Return the Android app-specific external files directory, or None.

    This path is user-accessible via file managers (Android/data/<pkg>/files).
    """
    if not _is_chaquopy_android():
        return None
    try:
        from com.chaquo.python import Python
        context = Python.getPlatform().getApplication()
        external = context.getExternalFilesDir(None)
        if external is not None:
            return str(external.getAbsolutePath())
    except Exception:
        pass
    return None


def lxmf_delivery_notification_text(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Return (title, body) for a system notification, or None to skip."""
    if payload.get("type") != "lxmf.delivery":
        return None
    if payload.get("sieve_suppress_notifications"):
        return None
    msg = payload.get("lxmf_message")
    if not isinstance(msg, dict):
        return None
    if not msg.get("is_incoming"):
        return None
    sender = str(payload.get("remote_identity_name") or "").strip() or "Mesh"
    if msg.get("is_reaction"):
        emoji = str(msg.get("reaction_emoji") or "").strip()
        body = f"Reaction {emoji}".strip() if emoji else "Reaction"
        return (sender, body)
    fields = msg.get("fields")
    if isinstance(fields, dict) and not msg.get("title") and not msg.get("content"):
        keys = set(fields.keys())
        if keys <= {"telemetry"}:
            return None
    title = str(msg.get("title") or "").strip()
    content = str(msg.get("content") or "").strip()
    if len(content) > 200:
        content = content[:197] + "..."
    if title and content:
        return (sender, f"{title}\n{content}")
    if title:
        return (sender, title)
    if content:
        return (sender, content)
    if isinstance(fields, dict) and fields.get("image"):
        return (sender, "Image message")
    if isinstance(fields, dict) and fields.get("audio"):
        return (sender, "Audio message")
    if isinstance(fields, dict) and fields.get("file_attachments"):
        return (sender, "Attachment")
    return (sender, "New message")


def _notify_java(title: str, body: str, dedupe_hex: str | None) -> None:
    try:
        from com.meshchatx import AndroidNotificationBridge  # type: ignore[import-not-found,import-untyped]
    except Exception as exc:
        logger.debug("Android notification bridge unavailable: %s", exc)
        return
    try:
        AndroidNotificationBridge.showInboundMessage(title, body, dedupe_hex)
    except Exception as exc:
        logger.debug("showInboundMessage failed: %s", exc)


def _notify_incoming_call_java(caller_name: str, dedupe_hex: str | None) -> None:
    try:
        from com.meshchatx import AndroidNotificationBridge  # type: ignore[import-not-found,import-untyped]
    except Exception as exc:
        logger.debug("Android notification bridge unavailable: %s", exc)
        return
    try:
        AndroidNotificationBridge.showIncomingCall(caller_name, dedupe_hex)
    except Exception as exc:
        logger.debug("showIncomingCall failed: %s", exc)


def _notify_missed_call_java(title: str, body: str, dedupe_hex: str | None) -> None:
    try:
        from com.meshchatx import AndroidNotificationBridge  # type: ignore[import-not-found,import-untyped]
    except Exception as exc:
        logger.debug("Android notification bridge unavailable: %s", exc)
        return
    try:
        AndroidNotificationBridge.showMissedCall(title, body, dedupe_hex)
    except Exception as exc:
        logger.debug("showMissedCall failed: %s", exc)


def _cancel_incoming_call_notification_java() -> None:
    try:
        from com.meshchatx import AndroidNotificationBridge  # type: ignore[import-not-found,import-untyped]
    except Exception as exc:
        logger.debug("Android notification bridge unavailable: %s", exc)
        return
    try:
        AndroidNotificationBridge.cancelIncomingCallNotification()
    except Exception as exc:
        logger.debug("cancelIncomingCallNotification failed: %s", exc)


def _after_websocket_broadcast(data: object) -> None:
    if not isinstance(data, str):
        return
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    t = payload.get("type")
    if t in ("telephone_call_ended", "telephone_call_established"):
        _cancel_incoming_call_notification_java()
        return
    if t == "telephone_ringing":
        ch = payload.get("remote_identity_hash")
        name = (payload.get("remote_identity_name") or "").strip() or "Mesh"
        ded = ch if isinstance(ch, str) and len(ch) >= 8 else None
        _notify_incoming_call_java(name, ded)
        return
    if t == "telephone_missed_call":
        sender = (payload.get("remote_identity_name") or "").strip() or "Mesh"
        ch = payload.get("remote_identity_hash")
        h = ch if isinstance(ch, str) and len(ch) >= 8 else None
        if sender and sender != "Mesh":
            title = "Missed call"
            body = f"Missed call from {sender}"
        elif isinstance(ch, str) and ch:
            short_h = f"{ch[:6]}" if len(ch) > 6 else ch
            title = "Missed call"
            body = f"From {short_h}..."
        else:
            title = "Missed call"
            body = "Missed call"
        _notify_missed_call_java(title, body, h)
        return
    pair = lxmf_delivery_notification_text(payload)
    if not pair:
        return
    title, body = pair
    msg = payload.get("lxmf_message")
    dedupe = None
    if isinstance(msg, dict):
        h = msg.get("hash")
        if isinstance(h, str) and len(h) >= 8:
            dedupe = h
    _notify_java(title, body, dedupe)


def install_websocket_hook(reticulum_mesh_chat_cls: type) -> None:
    global _ws_hook_installed
    if not _is_chaquopy_android():
        return
    if _ws_hook_installed:
        return
    orig = reticulum_mesh_chat_cls.websocket_broadcast

    async def _wrapped(self, data):
        result = await orig(self, data)
        try:
            _after_websocket_broadcast(data)
        except Exception:
            logger.debug("android ws hook post-broadcast failed", exc_info=True)
        return result

    reticulum_mesh_chat_cls.websocket_broadcast = _wrapped
    _ws_hook_installed = True
