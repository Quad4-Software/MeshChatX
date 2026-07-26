# SPDX-License-Identifier: 0BSD

"""ALTCHA proof-of-work verification for login and setup."""

from __future__ import annotations

import os
import time
from typing import Any

import altcha
from aiohttp import web

from meshchatx.src.env_utils import env_bool

ALTCHA_INVALID_CODE = "altcha_invalid"
ALTCHA_ALGORITHM = "PBKDF2/SHA-256"
ALTCHA_DEFAULT_COST = 2000


def altcha_enabled_from_env() -> bool:
    return env_bool("MESHCHAT_ALTCHA_ENABLED", False)


def altcha_hmac_secret() -> str | None:
    raw = os.environ.get("MESHCHAT_ALTCHA_HMAC_KEY", "").strip()
    return raw or None


def altcha_configured() -> bool:
    return altcha_enabled_from_env() and bool(altcha_hmac_secret())


def altcha_pow_cost() -> int:
    raw = os.environ.get("MESHCHAT_ALTCHA_COST", "").strip()
    if not raw:
        return ALTCHA_DEFAULT_COST
    try:
        return max(100, int(raw))
    except ValueError:
        return ALTCHA_DEFAULT_COST


def create_altcha_challenge_dict() -> dict[str, Any]:
    secret = altcha_hmac_secret()
    if not secret:
        msg = "MESHCHAT_ALTCHA_HMAC_KEY is required when ALTCHA is enabled"
        raise RuntimeError(msg)
    expires_at = int(time.time()) + 300
    challenge = altcha.create_challenge(
        ALTCHA_ALGORITHM,
        altcha_pow_cost(),
        hmac_secret=secret,
        expires_at=expires_at,
    )
    return challenge.to_dict()


def verify_altcha_submission(payload: Any) -> tuple[bool, str | None]:
    secret = altcha_hmac_secret()
    if not secret:
        return False, "altcha_not_configured"
    if payload is None:
        return False, ALTCHA_INVALID_CODE
    if isinstance(payload, dict):
        import json

        payload = json.dumps(payload)
    if not isinstance(payload, str) or not payload.strip():
        return False, ALTCHA_INVALID_CODE
    try:
        result = altcha.verify_solution(payload.strip(), secret)
    except Exception:
        return False, ALTCHA_INVALID_CODE
    if not result.verified:
        err = result.error or ALTCHA_INVALID_CODE
        return False, err
    return True, None


def altcha_error_response(code: str) -> web.Response:
    return web.json_response(
        {"error": "ALTCHA verification failed", "code": code},
        status=400,
    )


async def require_altcha_payload(request, data: dict) -> web.Response | None:
    if not altcha_enabled_from_env():
        return None
    payload = data.get("altcha")
    ok, code = verify_altcha_submission(payload)
    if not ok:
        return altcha_error_response(code or ALTCHA_INVALID_CODE)
    return None
