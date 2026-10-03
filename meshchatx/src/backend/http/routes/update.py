# SPDX-License-Identifier: 0BSD
"""HTTP routes: signed update check, download, manual-file apply, staging."""

from __future__ import annotations

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
    write_field_to_path,
)
from meshchatx.src.backend.update_manager import (
    ARTIFACT_MAX_BYTES,
    UpdateError,
    UpdateUnavailable,
    UpdateVerifyError,
)


# Front-end apply modes: "relaunch" (Electron swaps the staged payload and
# restarts), "manual" (instructions only), "none".
def _apply_mode(kind: str, platform: str) -> dict:
    if kind == "appimage" and platform == "linux":
        return {"mode": "relaunch"}
    if kind == "apk" and platform == "android":
        return {
            "mode": "manual",
            "instructions": "Open the staged APK in the app files area to install; Android verifies the package signature.",
        }
    if kind in ("wheel", "pyz"):
        return {
            "mode": "manual",
            "instructions": "Install the verified file with your package manager, e.g. uv pip install <file>.",
        }
    return {
        "mode": "manual",
        "instructions": "Install the downloaded package with your OS package manager.",
    }


def register_update_routes(routes, app):

    def _manager():
        return app.update_manager

    def _status_payload(mgr):
        return {
            "enabled": mgr.enabled,
            "current_version": mgr.current_version,
            "channel": mgr.channel,
            "track": mgr.track,
            "pending": mgr.pending(),
        }

    @routes.get(API_V1_PREFIX + "/update/status")
    async def update_status(request):
        mgr = _manager()
        return web.json_response(_status_payload(mgr))

    @routes.post(API_V1_PREFIX + "/update/check")
    async def update_check(request):
        mgr = _manager()
        if not mgr.enabled:
            return web.json_response(_status_payload(mgr))
        try:
            result = await mgr.check()
        except UpdateError as e:
            return http_unavailable(str(e))
        except Exception as e:
            return http_error_from_exception(e)
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/update/download")
    async def update_download(request):
        mgr = _manager()
        if not mgr.enabled:
            return http_unavailable("updates are disabled for this install")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("invalid JSON body")
        wanted = (data.get("file") or "").strip() if isinstance(data, dict) else ""
        if not wanted:
            return http_bad_request("missing artifact file")
        try:
            manifest = await mgr.fetch_manifest()
        except UpdateError as e:
            return http_unavailable(str(e))
        matches = [
            a
            for a in mgr.matching_artifacts(manifest)
            if a["file"].rsplit("/", 1)[-1] == wanted or a["file"] == wanted
        ]
        if not matches:
            return http_bad_request("artifact not in manifest for this platform")
        entry = matches[0]
        try:
            tmp_path = await mgr.download(manifest, entry)
            marker = mgr.stage(tmp_path, entry, manifest)
        except UpdateVerifyError as e:
            return http_error_from_exception(e, fallback_status=422)
        except UpdateError as e:
            return http_unavailable(str(e))
        except Exception as e:
            return http_error_from_exception(e)
        marker["apply"] = _apply_mode(marker["kind"], marker["platform"])
        return web.json_response({"ok": True, "pending": marker})

    @routes.post(API_V1_PREFIX + "/update/apply-file")
    async def update_apply_file(request):
        """Manual update path: user supplies a file downloaded out of band.

        The file is streamed to a temp path, hashed, and matched against the
        signed manifest. On match it is staged exactly like a CDN download.
        """
        mgr = _manager()
        if not mgr.enabled:
            return http_unavailable("updates are disabled for this install")
        if not request.content_type.startswith("multipart/"):
            return http_bad_request("expected multipart upload")

        fd, tmp = tempfile.mkstemp(prefix="meshchatx-update-upload-", suffix=".part")
        os.close(fd)
        tmp_path = tmp
        staged = None
        try:
            reader = await request.multipart()
            field = await reader.next()
            while field is not None and getattr(field, "name", None) != "file":
                field = await reader.next()
            if field is None:
                return http_bad_request("missing file field")
            await write_field_to_path(field, tmp_path, ARTIFACT_MAX_BYTES)
            result = await mgr.verify_local_file(tmp_path)
            marker = mgr.stage(Path(tmp_path), result["entry"], result["manifest"])
            staged = tmp_path
            marker["apply"] = _apply_mode(marker["kind"], marker["platform"])
            return web.json_response({"ok": True, "pending": marker})
        except PayloadTooLargeError:
            return http_payload_too_large()
        except UpdateVerifyError as e:
            return http_error_from_exception(e, fallback_status=422)
        except UpdateUnavailable as e:
            return http_error_from_exception(e, fallback_status=409)
        except UpdateError as e:
            return http_unavailable(str(e))
        except Exception as e:
            return http_error_from_exception(e)
        finally:
            if staged is None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    @routes.get(API_V1_PREFIX + "/update/pending")
    async def update_pending(request):
        mgr = _manager()
        pending = mgr.pending()
        if pending:
            pending = dict(pending)
            pending["apply"] = _apply_mode(pending["kind"], pending["platform"])
        return web.json_response({"pending": pending})

    @routes.post(API_V1_PREFIX + "/update/discard")
    async def update_discard(request):
        mgr = _manager()
        mgr.clear_pending()
        return web.json_response({"ok": True})
