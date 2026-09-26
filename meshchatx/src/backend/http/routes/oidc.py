# SPDX-License-Identifier: 0BSD

"""HTTP routes: OIDC single sign-on login and callback."""

from __future__ import annotations

import logging
import secrets
import time

from aiohttp import web
from aiohttp_session import get_session

from meshchatx.src.backend import oidc
from meshchatx.src.backend.app_security_settings import get_trusted_proxy_cidrs
from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.csrf import rotate_session_csrf_token
from meshchatx.src.backend.database.access_attempts import (
    OIDC_PATH,
    user_agent_hash,
)
from meshchatx.src.backend.http.errors import http_not_found
from meshchatx.src.backend.privacy_mode import OutboundHttpBlockedError
from meshchatx.src.path_utils import request_client_ip

logger = logging.getLogger(__name__)

OIDC_CALLBACK_PATH = API_V1_PREFIX + "/auth/oidc/callback"

_PROVIDER_ERROR_SLUGS = frozenset(
    {
        "access_denied",
        "account_selection_required",
        "consent_required",
        "interaction_required",
        "invalid_request",
        "invalid_scope",
        "login_required",
        "server_error",
        "temporarily_unavailable",
        "unauthorized_client",
        "unsupported_response_type",
    },
)


def _redirect(location: str) -> web.Response:
    return web.Response(status=302, headers={"Location": location})


def _redirect_auth_error(slug: str) -> web.Response:
    return _redirect(f"/#/auth?oidc_error={slug}")


def _provider_error_slug(raw) -> str:
    if isinstance(raw, str) and raw in _PROVIDER_ERROR_SLUGS:
        return raw
    return "failed"


def _access_attempt_dao(app):
    return app.database.access_attempts if app.database else None


def _log_attempt(app, request, result: str) -> None:
    dao = _access_attempt_dao(app)
    if not dao:
        return
    try:
        dao.insert(
            app.identity.hash.hex(),
            request_client_ip(request, get_trusted_proxy_cidrs(app.storage_dir)),
            request.headers.get("User-Agent", "") or "",
            OIDC_PATH,
            request.method,
            result,
            "",
        )
    except Exception as exc:
        logger.warning("Failed to record OIDC access attempt: %s", exc)


def register_oidc_routes(routes, app):
    @routes.get(API_V1_PREFIX + "/auth/oidc/login")
    async def oidc_login(request):
        if not app._oidc_ready():
            return http_not_found("OIDC is not configured")
        blocked = app._enforce_login_access(request, OIDC_PATH)
        if blocked is not None:
            return blocked

        settings = app._oidc_settings()
        try:
            metadata = await oidc.fetch_discovery_cached(
                app,
                app.config,
                settings.issuer,
            )
        except OutboundHttpBlockedError:
            _log_attempt(app, request, "oidc_blocked_privacy_mode")
            return _redirect_auth_error("blocked")
        except oidc.OidcError as exc:
            logger.warning("OIDC discovery failed: %s", exc)
            _log_attempt(app, request, "oidc_discovery_failed")
            return _redirect_auth_error("unreachable")

        trusted = get_trusted_proxy_cidrs(app.storage_dir)
        base_url = oidc.public_request_base_url(request, trusted)
        redirect_uri = base_url + OIDC_CALLBACK_PATH

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier, challenge = oidc.build_pkce_pair()

        session = await get_session(request)
        session["oidc_state"] = state
        session["oidc_nonce"] = nonce
        session["oidc_pkce_verifier"] = verifier
        session["oidc_issuer"] = settings.issuer
        session["oidc_started_at"] = time.time()

        location = oidc.authorization_url(
            metadata,
            {
                "response_type": "code",
                "client_id": settings.client_id,
                "redirect_uri": redirect_uri,
                "scope": settings.scopes,
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
        )
        _log_attempt(app, request, "oidc_login_start")
        return _redirect(location)

    @routes.get(API_V1_PREFIX + "/auth/oidc/callback")
    async def oidc_callback(request):
        if not app._oidc_ready():
            return http_not_found("OIDC is not configured")
        session = await get_session(request)

        provider_error = request.query.get("error")
        if provider_error is not None:
            _log_attempt(app, request, "oidc_provider_error")
            return _redirect_auth_error(_provider_error_slug(provider_error))

        code = request.query.get("code")
        state = request.query.get("state")
        expected_state = session.get("oidc_state")
        nonce = session.get("oidc_nonce")
        verifier = session.get("oidc_pkce_verifier")
        flow_issuer = session.get("oidc_issuer")
        started_at = session.get("oidc_started_at")
        if (
            not code
            or not state
            or not isinstance(expected_state, str)
            or not isinstance(nonce, str)
            or not isinstance(verifier, str)
            or not secrets.compare_digest(state, expected_state)
            or not isinstance(started_at, (int, float))
            or time.time() - started_at > oidc.OIDC_STATE_MAX_AGE_SECONDS
        ):
            _log_attempt(app, request, "oidc_state_invalid")
            return _redirect_auth_error("invalid_state")

        settings = app._oidc_settings()
        if flow_issuer != settings.issuer:
            _log_attempt(app, request, "oidc_issuer_changed")
            return _redirect_auth_error("invalid_state")

        trusted = get_trusted_proxy_cidrs(app.storage_dir)
        redirect_uri = (
            oidc.public_request_base_url(request, trusted) + OIDC_CALLBACK_PATH
        )

        try:
            metadata = await oidc.fetch_discovery_cached(
                app,
                app.config,
                settings.issuer,
            )
            token_response = await oidc.exchange_code(
                app.config,
                metadata["token_endpoint"],
                code=code,
                redirect_uri=redirect_uri,
                client_id=settings.client_id,
                client_secret=settings.client_secret,
                code_verifier=verifier,
            )
            id_token = token_response["id_token"]
            jwks = await oidc.fetch_jwks_cached(app, app.config, metadata["jwks_uri"])
            try:
                claims = oidc.verify_id_token(
                    id_token,
                    jwks,
                    issuer=settings.issuer,
                    client_id=settings.client_id,
                    nonce=nonce,
                )
            except oidc.OidcVerifyError as exc:
                # Provider may have rotated signing keys between flow start and
                # callback. Refresh the JWKS once before giving up.
                if "unknown signing key" not in str(exc):
                    raise
                jwks = await oidc.fetch_jwks_cached(
                    app,
                    app.config,
                    metadata["jwks_uri"],
                    refresh=True,
                )
                claims = oidc.verify_id_token(
                    id_token,
                    jwks,
                    issuer=settings.issuer,
                    client_id=settings.client_id,
                    nonce=nonce,
                )
        except OutboundHttpBlockedError:
            _log_attempt(app, request, "oidc_blocked_privacy_mode")
            return _redirect_auth_error("blocked")
        except oidc.OidcTokenError as exc:
            logger.warning("OIDC token exchange failed: %s", exc)
            _log_attempt(app, request, "oidc_exchange_failed")
            return _redirect_auth_error("exchange_failed")
        except oidc.OidcVerifyError as exc:
            logger.warning("OIDC ID token rejected: %s", exc)
            _log_attempt(app, request, "oidc_verify_failed")
            return _redirect_auth_error("verify_failed")
        except oidc.OidcError as exc:
            logger.warning("OIDC callback failed: %s", exc)
            _log_attempt(app, request, "oidc_callback_failed")
            return _redirect_auth_error("unreachable")

        session.invalidate()
        session = await get_session(request)
        session["authenticated"] = True
        session["identity_hash"] = app.identity.hash.hex()
        session["auth_method"] = "oidc"
        session["session_epoch"] = app._current_auth_session_epoch()
        if isinstance(claims.get("sub"), str):
            session["oidc_sub"] = claims["sub"]
        rotate_session_csrf_token(session)

        dao = _access_attempt_dao(app)
        if dao:
            ip = request_client_ip(request, trusted)
            ua = request.headers.get("User-Agent", "") or ""
            dao.upsert_trusted(app.identity.hash.hex(), ip, user_agent_hash(ua))
        _log_attempt(app, request, "oidc_success")
        return _redirect("/")
