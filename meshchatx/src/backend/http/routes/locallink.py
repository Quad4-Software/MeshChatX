# SPDX-License-Identifier: 0BSD
"""HTTP routes: local link transports (hotspot, WiFi join, capabilities)."""

from __future__ import annotations

import asyncio

from aiohttp import web

from meshchatx.src.backend import android_locallink
from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_unavailable,
)
from meshchatx.src.backend.http.uploads import read_json_limited

_MAX_SSID_LEN = 32
_MAX_PSK_LEN = 63
_MAX_NFC_PAYLOAD = 512


def _validate_join_params(data: dict) -> tuple[str | None, str | None, str | None]:
    """Return (ssid, passphrase, error). error is a message string or None."""
    ssid = data.get("ssid")
    if not isinstance(ssid, str) or not ssid.strip():
        return None, None, "ssid is required"
    ssid = ssid.strip()
    if len(ssid.encode("utf-8")) > _MAX_SSID_LEN:
        return None, None, "ssid too long"
    passphrase = data.get("passphrase")
    if passphrase is not None:
        if not isinstance(passphrase, str):
            return None, None, "passphrase must be a string"
        if passphrase and not 8 <= len(passphrase) <= _MAX_PSK_LEN:
            return None, None, "passphrase must be 8-63 characters"
        if passphrase == "":
            passphrase = None
    return ssid, passphrase, None


def register_locallink_routes(routes, app):

    @routes.get(API_V1_PREFIX + "/locallink/capabilities")
    async def locallink_capabilities(request):
        data = await asyncio.to_thread(android_locallink.probe_capabilities)
        return web.json_response(data)

    @routes.get(API_V1_PREFIX + "/locallink/hotspot/status")
    async def locallink_hotspot_status(request):
        return web.json_response(android_locallink.hotspot_status())

    @routes.post(API_V1_PREFIX + "/locallink/hotspot/start")
    async def locallink_hotspot_start(request):
        result = await asyncio.to_thread(android_locallink.start_hotspot)
        if not result.get("supported"):
            return http_unavailable("Local link is only supported on Android")
        if not result.get("ok"):
            return http_error(
                502,
                result.get("error") or "hotspot start failed",
                ok=False,
            )
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/locallink/hotspot/stop")
    async def locallink_hotspot_stop(request):
        result = await asyncio.to_thread(android_locallink.stop_hotspot)
        if not result.get("supported"):
            return http_unavailable("Local link is only supported on Android")
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/locallink/wifi/join")
    async def locallink_wifi_join(request):
        data = await read_json_limited(request)
        ssid, passphrase, err = _validate_join_params(data)
        if err or ssid is None:
            return http_bad_request(err or "ssid is required")
        result = await asyncio.to_thread(
            android_locallink.join_wifi,
            ssid,
            passphrase,
        )
        if not result.get("supported"):
            return http_unavailable("Local link is only supported on Android")
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/locallink/wifi/leave")
    async def locallink_wifi_leave(request):
        result = await asyncio.to_thread(android_locallink.leave_wifi)
        if not result.get("supported"):
            return http_unavailable("Local link is only supported on Android")
        return web.json_response(result)

    @routes.get(API_V1_PREFIX + "/locallink/p2p/status")
    async def locallink_p2p_status(request):
        return web.json_response(android_locallink.p2p_status())

    @routes.post(API_V1_PREFIX + "/locallink/p2p/start")
    async def locallink_p2p_start(request):
        result = await asyncio.to_thread(android_locallink.start_p2p_group)
        if not result.get("supported"):
            return http_unavailable("Local link is only supported on Android")
        if not result.get("ok"):
            return http_error(
                502,
                result.get("error") or "group start failed",
                ok=False,
            )
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/locallink/p2p/stop")
    async def locallink_p2p_stop(request):
        result = await asyncio.to_thread(android_locallink.stop_p2p_group)
        if not result.get("supported"):
            return http_unavailable("Local link is only supported on Android")
        return web.json_response(result)

    @routes.get(API_V1_PREFIX + "/locallink/aware/status")
    async def locallink_aware_status(request):
        return web.json_response(android_locallink.aware_status())

    @routes.post(API_V1_PREFIX + "/locallink/aware/start")
    async def locallink_aware_start(request):
        data = await read_json_limited(request)
        role = data.get("mode", "subscribe")
        if role not in ("publish", "subscribe"):
            return http_bad_request("mode must be publish or subscribe")
        result = await asyncio.to_thread(android_locallink.aware_start, role)
        if not result.get("supported"):
            return http_unavailable("Local link is only supported on Android")
        if not result.get("ok"):
            return http_error(
                502,
                result.get("error") or "aware start failed",
                ok=False,
            )
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/locallink/aware/stop")
    async def locallink_aware_stop(request):
        result = await asyncio.to_thread(android_locallink.aware_stop)
        if not result.get("supported"):
            return http_unavailable("Local link is only supported on Android")
        return web.json_response(result)

    @routes.get(API_V1_PREFIX + "/locallink/nfc/status")
    async def locallink_nfc_status(request):
        return web.json_response(android_locallink.nfc_status())

    @routes.post(API_V1_PREFIX + "/locallink/nfc/share")
    async def locallink_nfc_share(request):
        data = await read_json_limited(request)
        payload = data.get("payload")
        if payload is not None and not isinstance(payload, str):
            return http_bad_request("payload must be a string")
        if payload is not None and len(payload.encode("utf-8")) > _MAX_NFC_PAYLOAD:
            return http_bad_request("payload too large")
        result = await asyncio.to_thread(android_locallink.nfc_share, payload)
        if not result.get("supported"):
            return http_unavailable("NFC is only supported on Android")
        if not result.get("ok"):
            return http_error(
                502,
                result.get("error") or "nfc share failed",
                ok=False,
            )
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/locallink/nfc/read/start")
    async def locallink_nfc_read_start(request):
        result = await asyncio.to_thread(android_locallink.nfc_read, True)
        if not result.get("supported"):
            return http_unavailable("NFC is only supported on Android")
        if not result.get("ok"):
            return http_error(
                502,
                result.get("error") or "nfc read failed",
                ok=False,
            )
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/locallink/nfc/read/stop")
    async def locallink_nfc_read_stop(request):
        result = await asyncio.to_thread(android_locallink.nfc_read, False)
        if not result.get("supported"):
            return http_unavailable("NFC is only supported on Android")
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/locallink/nfc/clear")
    async def locallink_nfc_clear(request):
        return web.json_response(
            await asyncio.to_thread(android_locallink.nfc_clear_last)
        )
