# SPDX-License-Identifier: 0BSD

"""Android local-link bridge: hotspot, WiFi join, capability probing.

Wraps org.meshchatx.locallink.LocalLink over Chaquopy java.jclass and
dynamic_proxy, following the same pattern as android_rnode. All functions
are safe to call on desktop: they degrade to supported=False responses when
no Android runtime is present.
"""

from __future__ import annotations

import json
import logging
import threading

logger = logging.getLogger(__name__)

_bridge = None
_bridge_lock = threading.Lock()
_state_lock = threading.Lock()
_hotspot_event = threading.Event()
_p2p_event = threading.Event()
_activity = None
_nfc = None
_aware = None
_aware_lock = threading.Lock()
_aware_listeners = []
_state = {
    "hotspot_active": False,
    "hotspot_ssid": None,
    "hotspot_passphrase": None,
    "join_status": "idle",
    "join_network_connected": False,
    "p2p_active": False,
    "p2p_ssid": None,
    "p2p_passphrase": None,
    "nfc_sharing": False,
    "nfc_reading": False,
    "nfc_last_payload": None,
}
_aware_state = {
    "role": "off",
    "session": False,
    "peers": {},
    "links": {},
}

_ANDROID_UNAVAILABLE = {
    "supported": False,
    "reason": "android_only",
}


def _unsupported(extra=None):
    out = dict(_ANDROID_UNAVAILABLE)
    if extra:
        out.update(extra)
    return out


def _dispatch_aware(event: str, peer_id: int = 0, data: bytes | None = None) -> None:
    with _aware_lock:
        listeners = list(_aware_listeners)
    for listener in listeners:
        try:
            listener(event, peer_id, data)
        except Exception:
            logger.exception("aware listener failed for %s", event)


def install_android_locallink(activity=None) -> bool:
    """Wire the Activity context into org.meshchatx.locallink.LocalLink.

    Returns True when the Android local-link path was configured.
    Safe no-op on desktop (java APIs missing).
    """
    global _bridge, _activity, _nfc, _aware
    if activity is None:
        logger.warning("install_android_locallink called without Activity")
        return False

    try:
        from java import dynamic_proxy, jclass

        link_cls = jclass("org.meshchatx.locallink.LocalLink")
        link_cls.setAppContext(activity)

        iface = jclass("org.meshchatx.locallink.PythonLocalLink")

        class _PythonLocalLinkProxy(dynamic_proxy(iface)):
            def __init__(self):
                super().__init__()

            def on_hotspot_started(self, ssid, passphrase, security_type):
                with _state_lock:
                    _state["hotspot_active"] = True
                    _state["hotspot_ssid"] = ssid
                    _state["hotspot_passphrase"] = passphrase
                _hotspot_event.set()
                logger.info("Local-only hotspot started (ssid=%s)", ssid)

            def on_hotspot_failed(self, error_code):
                with _state_lock:
                    _state["hotspot_active"] = False
                    _state["hotspot_error"] = error_code
                _hotspot_event.set()
                logger.warning("Local-only hotspot failed: %s", error_code)

            def on_hotspot_stopped(self):
                with _state_lock:
                    _state["hotspot_active"] = False
                    _state["hotspot_ssid"] = None
                    _state["hotspot_passphrase"] = None
                logger.info("Local-only hotspot stopped")

            def on_p2p_group_started(self, ssid, passphrase):
                with _state_lock:
                    _state["p2p_active"] = True
                    _state["p2p_ssid"] = ssid
                    _state["p2p_passphrase"] = passphrase
                _p2p_event.set()
                logger.info("WiFi Direct group started (ssid=%s)", ssid)

            def on_p2p_group_failed(self, reason):
                with _state_lock:
                    _state["p2p_active"] = False
                    _state["p2p_error"] = reason
                _p2p_event.set()
                logger.warning("WiFi Direct group failed: %s", reason)

            def on_p2p_group_stopped(self):
                with _state_lock:
                    _state["p2p_active"] = False
                    _state["p2p_ssid"] = None
                    _state["p2p_passphrase"] = None
                logger.info("WiFi Direct group stopped")

            def on_join_status(self, status):
                with _state_lock:
                    _state["join_status"] = status
                    if status == "available":
                        _state["join_network_connected"] = True
                    elif status in ("lost", "unavailable", "cancelled"):
                        _state["join_network_connected"] = False
                logger.info("WiFi join status: %s", status)

            def on_error(self, where, message):
                logger.warning("LocalLink %s error: %s", where, message)

        with _bridge_lock:
            _bridge = link_cls(_PythonLocalLinkProxy())
        _activity = activity
        # Drop bridges bound to a previous Activity or identity context.
        # Stop a live Aware session first: it holds the old context and its
        # discovery sessions would linger in the system with dead callbacks.
        old_aware = _aware
        if old_aware is not None:
            try:
                old_aware.stop()
            except Exception:
                logger.debug("stale AwareSession stop failed", exc_info=True)
        _nfc = None
        _aware = None
        with _state_lock:
            _aware_state["role"] = "off"
            _aware_state["session"] = False
            _aware_state["peers"] = {}
            _aware_state["links"] = {}
        logger.info("Configured org.meshchatx.locallink.LocalLink app context")
        return True
    except Exception as exc:
        logger.warning("Could not configure LocalLink context: %s", exc)
        return False


def is_available() -> bool:
    with _bridge_lock:
        return _bridge is not None


def probe_capabilities() -> dict:
    """Return the LocalLink capability probe as a dict."""
    with _bridge_lock:
        bridge = _bridge
    if bridge is None:
        return _unsupported(
            {
                "hotspot": False,
                "wifi_join_specifier": False,
                "wifi_aware": False,
                "wifi_aware_available": False,
                "wifi_direct": False,
                "nfc": False,
                "satellite": {"feature": False, "enabled": None},
            }
        )
    try:
        raw = bridge.probeCapabilities()
        data = json.loads(raw) if isinstance(raw, str) else dict(raw)
        data["supported"] = True
        with _state_lock:
            data["hotspot_active"] = _state["hotspot_active"]
            data["join_status"] = _state["join_status"]
            data["join_network_connected"] = _state["join_network_connected"]
        return data
    except Exception as exc:
        logger.warning("probe_capabilities failed: %s", exc)
        return _unsupported({"error": str(exc)})


def hotspot_status() -> dict:
    with _state_lock:
        return {
            "supported": _bridge is not None,
            "active": _state["hotspot_active"],
            "ssid": _state["hotspot_ssid"],
            "join_status": _state["join_status"],
            "join_network_connected": _state["join_network_connected"],
        }


def start_hotspot(timeout: float = 15.0) -> dict:
    """Start the local-only hotspot and wait for credentials."""
    with _bridge_lock:
        bridge = _bridge
    if bridge is None:
        return _unsupported()
    _hotspot_event.clear()
    with _state_lock:
        _state["hotspot_error"] = None
    try:
        bridge.startHotspot()
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}

    if not _hotspot_event.wait(timeout):
        return {"supported": True, "ok": False, "error": "hotspot start timed out"}

    with _state_lock:
        return {
            "supported": True,
            "ok": _state["hotspot_active"],
            "ssid": _state["hotspot_ssid"],
            "passphrase": _state["hotspot_passphrase"],
            "error": _state.get("hotspot_error"),
        }


def stop_hotspot() -> dict:
    with _bridge_lock:
        bridge = _bridge
    if bridge is None:
        return _unsupported()
    try:
        bridge.stopHotspot()
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}
    with _state_lock:
        _state["hotspot_active"] = False
        _state["hotspot_ssid"] = None
        _state["hotspot_passphrase"] = None
    return {"supported": True, "ok": True, "active": False}


def join_wifi(ssid: str, passphrase: str | None) -> dict:
    """Request a WifiNetworkSpecifier join. System shows the picker dialog."""
    with _bridge_lock:
        bridge = _bridge
    if bridge is None:
        return _unsupported()
    try:
        bridge.joinWifiNetwork(ssid, passphrase or "")
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}
    with _state_lock:
        _state["join_status"] = "requested"
    return {"supported": True, "ok": True, "status": "requested"}


def leave_wifi() -> dict:
    with _bridge_lock:
        bridge = _bridge
    if bridge is None:
        return _unsupported()
    try:
        bridge.cancelJoin()
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}
    with _state_lock:
        _state["join_status"] = "idle"
        _state["join_network_connected"] = False
    return {"supported": True, "ok": True, "status": "idle"}


def get_hotspot_credentials() -> tuple[str | None, str | None]:
    """Return (ssid, passphrase) for the active hotspot, if any."""
    with _state_lock:
        return _state["hotspot_ssid"], _state["hotspot_passphrase"]


# ---------------------------------------------------------------------------
# WiFi Direct named group
# ---------------------------------------------------------------------------


def start_p2p_group(timeout: float = 20.0) -> dict:
    """Create a WiFi Direct group owner with deterministic credentials."""
    with _bridge_lock:
        bridge = _bridge
    if bridge is None:
        return _unsupported()
    _p2p_event.clear()
    with _state_lock:
        _state["p2p_error"] = None
    try:
        bridge.p2pGroupCreate()
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}

    if not _p2p_event.wait(timeout):
        return {"supported": True, "ok": False, "error": "group start timed out"}

    with _state_lock:
        return {
            "supported": True,
            "ok": _state["p2p_active"],
            "ssid": _state["p2p_ssid"],
            "passphrase": _state["p2p_passphrase"],
            "error": _state.get("p2p_error"),
        }


def stop_p2p_group() -> dict:
    with _bridge_lock:
        bridge = _bridge
    if bridge is None:
        return _unsupported()
    try:
        bridge.p2pGroupRemove()
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}
    with _state_lock:
        _state["p2p_active"] = False
        _state["p2p_ssid"] = None
        _state["p2p_passphrase"] = None
    return {"supported": True, "ok": True, "active": False}


def p2p_status() -> dict:
    with _state_lock:
        return {
            "supported": _bridge is not None,
            "active": _state["p2p_active"],
            "ssid": _state["p2p_ssid"],
        }


# ---------------------------------------------------------------------------
# NFC share (HCE emit + reader mode)
# ---------------------------------------------------------------------------


def _nfc_bridge():
    """Lazily construct the NfcShare bridge. Needs the foreground Activity."""
    global _nfc
    if _nfc is not None:
        return _nfc
    if _activity is None:
        return None
    try:
        from java import dynamic_proxy, jclass

        nfc_cls = jclass("org.meshchatx.locallink.NfcShare")
        iface = jclass("org.meshchatx.locallink.PythonNfc")

        class _PythonNfcProxy(dynamic_proxy(iface)):
            def __init__(self):
                super().__init__()

            def on_nfc_payload(self, payload):
                with _state_lock:
                    _state["nfc_last_payload"] = payload
                logger.info("NFC payload received (%d bytes)", len(payload or ""))

            def on_nfc_state(self, state):
                with _state_lock:
                    _state["nfc_sharing"] = state == "share_active"
                    _state["nfc_reading"] = state == "read_active"
                logger.info("NFC state: %s", state)

            def on_nfc_error(self, message):
                with _state_lock:
                    _state["nfc_error"] = message
                logger.warning("NFC error: %s", message)

        _nfc = nfc_cls(_activity, _PythonNfcProxy())
        return _nfc
    except Exception as exc:
        logger.warning("NfcShare unavailable: %s", exc)
        return None


def nfc_share(payload: str | None) -> dict:
    nfc = _nfc_bridge()
    if nfc is None:
        return _unsupported()
    try:
        if payload:
            nfc.setSharePayload(payload)
            with _state_lock:
                _state["nfc_sharing"] = True
        else:
            nfc.clearSharePayload()
            with _state_lock:
                _state["nfc_sharing"] = False
        return {"supported": True, "ok": True, "sharing": bool(payload)}
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}


def nfc_read(start: bool) -> dict:
    nfc = _nfc_bridge()
    if nfc is None:
        return _unsupported()
    try:
        if start:
            nfc.startReader()
            with _state_lock:
                _state["nfc_reading"] = True
                _state["nfc_last_payload"] = None
        else:
            nfc.stopReader()
            with _state_lock:
                _state["nfc_reading"] = False
        return {"supported": True, "ok": True, "reading": bool(start)}
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}


def nfc_status() -> dict:
    with _state_lock:
        return {
            "supported": _nfc is not None,
            "sharing": _state["nfc_sharing"],
            "reading": _state["nfc_reading"],
            "last_payload": _state["nfc_last_payload"],
        }


def nfc_clear_last() -> dict:
    with _state_lock:
        _state["nfc_last_payload"] = None
    return {"supported": _nfc is not None, "ok": True}


# ---------------------------------------------------------------------------
# WiFi Aware session
# ---------------------------------------------------------------------------


def _aware_bridge():
    """Lazily construct the AwareSession bridge. Needs API 26+ and the feature."""
    global _aware
    if _aware is not None:
        return _aware
    with _bridge_lock:
        link = _bridge
    if link is None:
        return None
    try:
        from java import dynamic_proxy, jclass

        context = jclass("org.meshchatx.locallink.LocalLink").getAppContext()
        if context is None:
            return None
        aware_cls = jclass("org.meshchatx.locallink.AwareSession")
        iface = jclass("org.meshchatx.locallink.PythonAware")

        class _PythonAwareProxy(dynamic_proxy(iface)):
            def __init__(self):
                super().__init__()

            def on_aware_event(self, what):
                with _state_lock:
                    if what in ("publish_started", "subscribe_started"):
                        _aware_state["session"] = True
                    elif what in ("session_lost", "stopped"):
                        _aware_state["session"] = False
                _dispatch_aware(what, 0, None)

            def on_aware_peer(self, peer_id):
                with _state_lock:
                    _aware_state["peers"][peer_id] = True
                _dispatch_aware("peer", peer_id, None)

            def on_aware_link_up(self, peer_id):
                with _state_lock:
                    _aware_state["links"][peer_id] = True
                _dispatch_aware("link_up", peer_id, None)

            def on_aware_data(self, peer_id, data):
                payload = bytes(data) if data is not None else b""
                _dispatch_aware("data", peer_id, payload)

            def on_aware_link_down(self, peer_id):
                with _state_lock:
                    _aware_state["links"].pop(peer_id, None)
                    _aware_state["peers"].pop(peer_id, None)
                _dispatch_aware("link_down", peer_id, None)

            def on_aware_error(self, where, message):
                logger.warning("Aware %s error: %s", where, message)
                _dispatch_aware("error", 0, None)

        _aware = aware_cls(context, _PythonAwareProxy())
        return _aware
    except Exception as exc:
        logger.warning("AwareSession unavailable: %s", exc)
        return None


def aware_start(role: str) -> dict:
    aware = _aware_bridge()
    if aware is None:
        return _unsupported()
    try:
        if role == "publish":
            aware.startPublish()
        elif role == "subscribe":
            aware.startSubscribe()
        else:
            return {"supported": True, "ok": False, "error": "invalid role"}
        with _state_lock:
            _aware_state["role"] = role
        return {"supported": True, "ok": True, "role": role}
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}


def aware_stop() -> dict:
    aware = _aware_bridge()
    if aware is None:
        return _unsupported()
    try:
        aware.stop()
    except Exception as exc:
        return {"supported": True, "ok": False, "error": str(exc)}
    with _state_lock:
        _aware_state["role"] = "off"
        _aware_state["session"] = False
        _aware_state["peers"] = {}
        _aware_state["links"] = {}
    return {"supported": True, "ok": True}


def aware_status() -> dict:
    with _state_lock:
        return {
            "supported": _aware is not None,
            "role": _aware_state["role"],
            "session": _aware_state["session"],
            "peers": len(_aware_state["peers"]),
            "links": len(_aware_state["links"]),
        }


def aware_send(peer_id: int, data: bytes) -> bool:
    aware = _aware_bridge()
    if aware is None:
        return False
    try:
        return bool(aware.sendToPeer(int(peer_id), data))
    except Exception:
        return False


def aware_close_peer(peer_id: int) -> None:
    aware = _aware_bridge()
    if aware is None:
        return
    try:
        aware.closePeer(int(peer_id))
    except Exception:
        logger.debug("aware closePeer failed", exc_info=True)


def register_aware_listener(listener) -> None:
    """Subscribe to aware events: fn(event, peer_id, data)."""
    with _aware_lock:
        if listener not in _aware_listeners:
            _aware_listeners.append(listener)


def unregister_aware_listener(listener) -> None:
    with _aware_lock:
        if listener in _aware_listeners:
            _aware_listeners.remove(listener)
