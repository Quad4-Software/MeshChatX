# SPDX-License-Identifier: 0BSD
"""HTTP routes: auth session lifecycle."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_forbidden,
    http_payload_too_large,
    http_unauthorized,
)

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.routes.auth._names import *
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.path_utils import request_client_ip


def register_auth_session_routes(routes: Any, app: Any) -> None:
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
                    "oidc_enabled": app._oidc_ready(),
                    "oidc_display_name": app._oidc_settings().display_name,
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

            oidc_settings = app._oidc_settings()
            return web.json_response(
                {
                    "auth_enabled": app.auth_enabled,
                    "password_set": app.config.auth_password_hash.get() is not None,
                    "authenticated": actually_authenticated,
                    "network_ready": True,
                    "demo_mode": app.demo_mode,
                    "auth_page_hint": app.auth_page_hint,
                    "oidc_enabled": app._oidc_ready(),
                    "oidc_display_name": oidc_settings.display_name,
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
                    "oidc_enabled": app._oidc_ready(),
                    "oidc_display_name": app._oidc_settings().display_name,
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

        # On an OIDC-only deployment (no local password) a public setup
        # endpoint would let any caller bootstrap a credential and session,
        # bypassing the SSO boundary. Local password setup must instead run
        # after an OIDC login or through config/env.
        if app._oidc_ready():
            if dao:
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    SETUP_PATH,
                    request.method,
                    "setup_oidc_managed",
                    "",
                )
            return http_forbidden("Instance is managed by single sign-on")

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
