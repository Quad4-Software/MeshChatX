# SPDX-License-Identifier: 0BSD
"""HTTP routes for the opt-in update system.

Everything is off by default: status reports settings and disclosure
without touching any transport. check/download run the signed-manifest
flow in a worker thread. apply-file verifies a user-supplied artifact
(multipart upload or local path) against a stored signed manifest so
sneakernet and RNS filesync imports work fully offline.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_payload_too_large,
    http_unavailable,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.backend.update_manager import (
    UpdateError,
    UpdateUnavailable,
    UpdateVerifyError,
)
from meshchatx.src.backend.update_types import ARTIFACT_MAX_BYTES
from meshchatx.src.backend.update_types import install_kind


def _apply_mode(kind: str, platform: str) -> dict:
    if kind == "oci":
        return {
            "mode": "external",
            "instructions": (
                "Pull the new image with your container runtime, "
                "e.g. docker pull <image>."
            ),
        }
    if kind == "flatpak":
        return {
            "mode": "external",
            "instructions": "Update the app with flatpak update.",
        }
    if kind == "appimage" and platform == "linux":
        return {"mode": "relaunch"}
    if kind == "apk" and platform == "android":
        return {
            "mode": "manual",
            "instructions": (
                "Open the staged APK in the app files area to install; "
                "Android verifies the package signature."
            ),
        }
    if kind in ("zip", "tarball") and install_kind() == "portable":
        return {"mode": "relaunch"}
    if kind in ("wheel", "pyz"):
        return {
            "mode": "manual",
            "instructions": (
                "Install the verified file with your package manager, "
                "e.g. uv pip install <file>."
            ),
        }
    return {
        "mode": "manual",
        "instructions": (
            "Install the downloaded package with your OS package manager."
        ),
    }


def _pending_payload(mgr, pending):
    if not pending:
        return {"pending": None}
    arts = pending.get("artifacts") or []
    out_arts = []
    for a in arts:
        kind = a.get("kind") or "other"
        out_arts.append(
            {
                **a,
                "apply": _apply_mode(kind, a.get("platform") or ""),
            }
        )
    return {"pending": {**pending, "artifacts": out_arts}}


class _DisabledManager:
    """Stand-in when no UpdateManager could be constructed."""

    def status(self):
        return {
            "enabled": False,
            "unavailable": True,
            "current_version": "",
            "channel": "stable",
            "settings": {},
            "disclosure": {},
            "last_check": None,
            "progress": {"phase": "idle"},
            "pending": None,
            "peer_relay_active": False,
        }

    def get_pending(self):
        return {"pending": None}

    def get_progress(self):
        return {"phase": "idle"}

    def update_settings(self, patch):
        raise UpdateError("update manager unavailable")

    def check_now(self, manual=True, allow_downgrade=False):
        return {"status": "disabled", "update": None}

    def download(self, artifact, **kw):
        raise UpdateUnavailable("update manager unavailable")

    def apply_file(self, path, **kw):
        raise UpdateUnavailable("update manager unavailable")

    def discard(self):
        return {"status": "discarded"}


_DISABLED = _DisabledManager()


def register_update_routes(routes, app):

    def _manager():
        return getattr(app, "update_manager", None) or _DISABLED

    @routes.get(API_V1_PREFIX + "/update/status")
    async def update_status(request):
        mgr = _manager()
        return web.json_response(await asyncio.to_thread(mgr.status))

    @routes.get(API_V1_PREFIX + "/update/pending")
    async def update_pending(request):
        mgr = _manager()
        pending = await asyncio.to_thread(mgr.get_pending)
        return web.json_response(_pending_payload(mgr, pending.get("pending")))

    @routes.get(API_V1_PREFIX + "/update/progress")
    async def update_progress(request):
        mgr = _manager()
        return web.json_response(await asyncio.to_thread(mgr.get_progress))

    @routes.post(API_V1_PREFIX + "/update/settings")
    async def update_settings(request):
        mgr = _manager()
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("invalid JSON body")
        if not isinstance(data, dict):
            return http_bad_request("expected JSON object")
        try:
            status = await asyncio.to_thread(mgr.update_settings, data)
        except UpdateError as e:
            return http_bad_request(str(e))
        except Exception as e:
            return http_error_from_exception(e)
        return web.json_response(status)

    @routes.post(API_V1_PREFIX + "/update/check")
    async def update_check(request):
        mgr = _manager()
        try:
            data = {}
            if request.can_read_body:
                try:
                    data = await read_json_limited(request)
                except Exception:
                    data = {}
            allow_downgrade = bool(
                isinstance(data, dict) and data.get("allow_downgrade")
            )
            result = await asyncio.to_thread(mgr.check_now, True, allow_downgrade)
        except UpdateError as e:
            return http_unavailable(str(e))
        except Exception as e:
            return http_error_from_exception(e)
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/update/download")
    async def update_download(request):
        mgr = _manager()
        try:
            data = {}
            if request.can_read_body:
                try:
                    data = await read_json_limited(request)
                except Exception:
                    data = {}
        except PayloadTooLargeError:
            return http_payload_too_large()
        artifact = None
        if isinstance(data, dict) and isinstance(data.get("artifact"), dict):
            artifact = data["artifact"]
        try:
            if artifact is None:
                # check first, then download the offered artifact
                check = await asyncio.to_thread(mgr.check_now, True, False)
                update = (check or {}).get("update")
                if not update or not update.get("artifact"):
                    return web.json_response(
                        {
                            "status": check.get("status") if check else "error",
                            "update": None,
                            "detail": "no update available",
                        }
                    )
                artifact = update["artifact"]
            result = await asyncio.to_thread(mgr.download, artifact)
        except UpdateVerifyError as e:
            return http_error_from_exception(e, fallback_status=422)
        except UpdateUnavailable as e:
            return http_unavailable(str(e))
        except UpdateError as e:
            return http_unavailable(str(e))
        except Exception as e:
            return http_error_from_exception(e)
        pending = await asyncio.to_thread(mgr.get_pending)
        return web.json_response(
            {
                "status": result.get("status") or "staged",
                "download": result,
                "pending": _pending_payload(mgr, pending.get("pending"))["pending"],
            }
        )

    @routes.post(API_V1_PREFIX + "/update/apply-file")
    async def update_apply_file(request):
        """Verify a user-supplied artifact against a stored manifest.

        Accepts multipart upload (any file picker) or JSON {"path": ...}
        for a file already on disk (sneakernet / RNS filesync import).
        """
        mgr = _manager()
        tmp_path = None
        try:
            ctype = request.content_type or ""
            if ctype.startswith("multipart/"):
                fd, tmp = tempfile.mkstemp(
                    prefix="meshchatx-update-upload-", suffix=".part"
                )
                os.close(fd)
                tmp_path = tmp
                reader = await request.multipart()
                field = await reader.next()
                if field is None or not getattr(field, "filename", None):
                    return http_bad_request("missing file field")
                name = Path(field.filename).name
                out = Path(tmp_path).with_name(name + ".part")
                written = 0
                with open(out, "wb") as fh:  # noqa: ASYNC230 - bounded by ARTIFACT_MAX_BYTES
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > ARTIFACT_MAX_BYTES:
                            raise PayloadTooLargeError()
                        fh.write(chunk)
                os.replace(out, tmp_path)
                apply_path = tmp_path
            else:
                try:
                    data = await read_json_limited(request)
                except PayloadTooLargeError:
                    return http_payload_too_large()
                except Exception:
                    return http_bad_request("invalid JSON body")
                if not isinstance(data, dict):
                    return http_bad_request("expected JSON object")
                raw_path = data.get("path")
                if not isinstance(raw_path, str) or not raw_path:
                    return http_bad_request("missing path")
                apply_path = raw_path
            channel = data.get("channel") if isinstance(data, dict) else None
            result = await asyncio.to_thread(
                mgr.apply_file, apply_path, channel=channel
            )
        except PayloadTooLargeError:
            return http_payload_too_large()
        except UpdateVerifyError as e:
            return http_error_from_exception(e, fallback_status=422)
        except UpdateUnavailable as e:
            return http_unavailable(str(e))
        except UpdateError as e:
            return http_bad_request(str(e))
        except Exception as e:
            return http_error_from_exception(e)
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    pass
        pending = await asyncio.to_thread(mgr.get_pending)
        return web.json_response(
            {
                "status": "staged",
                "apply": result,
                "pending": _pending_payload(mgr, pending.get("pending"))["pending"],
            }
        )

    @routes.post(API_V1_PREFIX + "/update/discard")
    async def update_discard(request):
        mgr = _manager()
        return web.json_response(await asyncio.to_thread(mgr.discard))
