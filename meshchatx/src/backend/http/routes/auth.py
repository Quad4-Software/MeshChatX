# SPDX-License-Identifier: 0BSD
"""HTTP routes: auth."""

from __future__ import annotations

import json

import bcrypt
from aiohttp import web
from aiohttp_session import get_session

from meshchatx.src.backend.app_security_settings import (
    get_trusted_proxy_cidrs,
    load_app_security_settings,
    save_app_security_settings,
)
from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.csrf import (
    ensure_session_csrf_token,
    rotate_session_csrf_token,
)
from meshchatx.src.backend.database.access_attempts import (
    LOGIN_PATH,
    SETUP_PATH,
    user_agent_hash,
)
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_forbidden,
    http_payload_too_large,
    http_unauthorized,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.backend.privacy_mode import privacy_mode_enabled
from meshchatx.src.path_utils import is_loopback_bind_host, request_client_ip


def register_auth_routes(routes, app):
    @routes.get(API_V1_PREFIX + "/server/security")
    async def server_security_get(request):
        settings = load_app_security_settings(app.storage_dir)
        return web.json_response(
            {
                "listen_host": app.listen_host,
                "listen_port": app.listen_port,
                "https_enabled": app.use_https,
                "is_loopback_bind": is_loopback_bind_host(app.listen_host),
                "web_ui_ip_allowlist": settings.get("web_ui_ip_allowlist", ""),
                "trusted_proxy_cidrs": settings.get("trusted_proxy_cidrs", ""),
                **app._landlock_status_dict(),
                "privacy_mode_enabled": privacy_mode_enabled(app.config),
                "auth_enabled": app.auth_enabled,
            },
        )

    @routes.patch(API_V1_PREFIX + "/server/security")
    async def server_security_patch(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return http_bad_request("Invalid JSON body")
        if not isinstance(data, dict):
            return http_bad_request("Invalid request body")
        try:
            updates = {}
            if "web_ui_ip_allowlist" in data:
                updates["web_ui_ip_allowlist"] = data.get("web_ui_ip_allowlist")
            if "trusted_proxy_cidrs" in data:
                updates["trusted_proxy_cidrs"] = data.get("trusted_proxy_cidrs")
            if updates:
                settings = save_app_security_settings(app.storage_dir, updates)
            else:
                settings = load_app_security_settings(app.storage_dir)
        except ValueError as exc:
            return http_bad_request(str(exc))
        return web.json_response(
            {
                "listen_host": app.listen_host,
                "listen_port": app.listen_port,
                "https_enabled": app.use_https,
                "is_loopback_bind": is_loopback_bind_host(app.listen_host),
                "web_ui_ip_allowlist": settings.get("web_ui_ip_allowlist", ""),
                "trusted_proxy_cidrs": settings.get("trusted_proxy_cidrs", ""),
                **app._landlock_status_dict(),
                "privacy_mode_enabled": privacy_mode_enabled(app.config),
                "auth_enabled": app.auth_enabled,
            },
        )

    @routes.get(API_V1_PREFIX + "/auth/csrf")
    async def auth_csrf(request):
        try:
            session = await get_session(request)
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)
        token = ensure_session_csrf_token(session)
        return web.json_response({"csrf_token": token})

    # auth status

    # auth status
    @routes.get(API_V1_PREFIX + "/auth/status")
    async def auth_status(request):
        if not app.current_context or not app.current_context.running:
            return web.json_response(
                {
                    "auth_enabled": app.auth_enabled,
                    "password_set": False,
                    "authenticated": False,
                    "network_ready": False,
                    "status": "starting",
                    "stage": app._startup_stage,
                    "demo_mode": app.demo_mode,
                    "auth_page_hint": app.auth_page_hint,
                },
            )
        try:
            session = await get_session(request)
            is_authenticated = session.get("authenticated", False)
            session_identity = session.get("identity_hash")

            # Verify that authentication is for the CURRENT active identity
            actually_authenticated = is_authenticated and (
                session_identity == app.identity.hash.hex()
            )

            return web.json_response(
                {
                    "auth_enabled": app.auth_enabled,
                    "password_set": app.config.auth_password_hash.get() is not None,
                    "authenticated": actually_authenticated,
                    "network_ready": True,
                    "demo_mode": app.demo_mode,
                    "auth_page_hint": app.auth_page_hint,
                },
            )
        except Exception:
            # Handle decryption failure gracefully by reporting as unauthenticated
            return web.json_response(
                {
                    "auth_enabled": app.auth_enabled,
                    "password_set": (
                        app.config.auth_password_hash.get() is not None
                        if app.config
                        else False
                    ),
                    "authenticated": False,
                    "network_ready": bool(
                        app.current_context and app.current_context.running,
                    ),
                    "demo_mode": app.demo_mode,
                    "auth_page_hint": app.auth_page_hint,
                    "error": "Status unavailable",
                },
            )

    # auth setup

    # auth setup
    @routes.post(API_V1_PREFIX + "/auth/setup")
    async def auth_setup(request):
        blocked = app._enforce_login_access(request, SETUP_PATH)
        if blocked is not None:
            return blocked
        ip = request_client_ip(request, get_trusted_proxy_cidrs(app.storage_dir))
        ua = request.headers.get("User-Agent", "") or ""
        ua_h = user_agent_hash(ua)
        id_hash = app.identity.hash.hex()
        dao = app.database.access_attempts if app.database else None

        if app.config.auth_password_hash.get() is not None:
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    SETUP_PATH,
                    request.method,
                    "setup_already_done",
                    "",
                )
            return http_forbidden("Initial setup already completed")

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    SETUP_PATH,
                    request.method,
                    "invalid_json",
                    "",
                )
            return http_bad_request("Invalid JSON body")
        if not isinstance(data, dict):
            return http_bad_request("Invalid request body")
        password = data.get("password")

        if not password or len(password) < 8:
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    SETUP_PATH,
                    request.method,
                    "weak_password",
                    "",
                )
            return http_bad_request("Password must be at least 8 characters long")

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        app.config.auth_password_hash.set(password_hash)

        session = await get_session(request)
        session.invalidate()
        session = await get_session(request)
        session["authenticated"] = True
        session["identity_hash"] = app.identity.hash.hex()
        rotate_session_csrf_token(session)

        if dao:
            dao.insert(
                id_hash,
                ip,
                ua,
                SETUP_PATH,
                request.method,
                "success",
                "",
            )
            dao.upsert_trusted(id_hash, ip, ua_h)

        return web.json_response({"message": "Setup completed successfully"})

    # auth login

    # auth login
    @routes.post(API_V1_PREFIX + "/auth/login")
    async def auth_login(request):
        blocked = app._enforce_login_access(request, LOGIN_PATH)
        if blocked is not None:
            return blocked
        ip = request_client_ip(request, get_trusted_proxy_cidrs(app.storage_dir))
        ua = request.headers.get("User-Agent", "") or ""
        ua_h = user_agent_hash(ua)
        id_hash = app.identity.hash.hex()
        dao = app.database.access_attempts if app.database else None

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    LOGIN_PATH,
                    request.method,
                    "invalid_json",
                    "",
                )
            return http_bad_request("Invalid JSON body")
        if not isinstance(data, dict):
            return http_bad_request("Invalid request body")
        password = data.get("password")

        password_hash = app.config.auth_password_hash.get()
        if password_hash is None:
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    LOGIN_PATH,
                    request.method,
                    "auth_not_setup",
                    "",
                )
            return http_forbidden("Auth not setup")

        if not password:
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    LOGIN_PATH,
                    request.method,
                    "password_required",
                    "",
                )
            return http_bad_request("Password required")

        if bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        ):
            session = await get_session(request)
            session.invalidate()
            session = await get_session(request)
            session["authenticated"] = True
            session["identity_hash"] = app.identity.hash.hex()
            rotate_session_csrf_token(session)
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    LOGIN_PATH,
                    request.method,
                    "success",
                    "",
                )
                dao.upsert_trusted(id_hash, ip, ua_h)
            return web.json_response({"message": "Login successful"})

        if dao:
            dao.insert(
                id_hash,
                ip,
                ua,
                LOGIN_PATH,
                request.method,
                "failed_password",
                "",
            )
        return http_unauthorized("Invalid password")

    # auth logout

    # auth logout
    @routes.post(API_V1_PREFIX + "/auth/logout")
    async def auth_logout(request):
        session = await get_session(request)
        session.invalidate()
        return web.json_response({"message": "Logged out successfully"})

    # fetch com ports
