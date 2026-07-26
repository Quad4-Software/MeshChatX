# SPDX-License-Identifier: 0BSD

"""Oracle: ALTCHA challenge round-trip and login rejection without payload."""

from __future__ import annotations

import base64
import json
import os
import time
from unittest.mock import patch

import altcha
import bcrypt
import pytest
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.altcha_auth import (
    ALTCHA_INVALID_CODE,
    verify_altcha_submission,
)
from tests.backend.demo_http_support import build_test_aio_app
from tests.backend.conftest import fetch_api_csrf_headers

_TEST_SECRET = "test-secret-key-32chars-minimum!!"


def _solved_payload_b64(secret: str) -> str:
    challenge = altcha.create_challenge(
        "PBKDF2/SHA-256",
        200,
        hmac_secret=secret,
        expires_at=int(time.time()) + 300,
    )
    solution = altcha.solve_challenge(challenge, counter_step=1)
    assert solution is not None
    payload = altcha.Payload(challenge, solution)
    raw = json.dumps(payload.to_dict())
    return base64.b64encode(raw.encode()).decode()


def test_altcha_verify_round_trip():
    with patch.dict(
        os.environ, {"MESHCHAT_ALTCHA_HMAC_KEY": _TEST_SECRET}, clear=False
    ):
        ok, code = verify_altcha_submission(_solved_payload_b64(_TEST_SECRET))
        assert ok is True
        assert code is None


def test_altcha_rejects_tampered_payload():
    with patch.dict(
        os.environ, {"MESHCHAT_ALTCHA_HMAC_KEY": _TEST_SECRET}, clear=False
    ):
        bad = _solved_payload_b64(_TEST_SECRET)[:-4] + "XXXX"
        ok, code = verify_altcha_submission(bad)
        assert ok is False
        assert code is not None


@pytest.mark.asyncio
async def test_login_without_altcha_when_enabled(mock_app):
    mock_app.altcha_enabled = True
    mock_app.demo_mode = False
    mock_app.current_context.running = True
    mock_app.config.auth_enabled.set(True)
    password_hash = bcrypt.hashpw(b"secretpass", bcrypt.gensalt()).decode("utf-8")
    mock_app.config.auth_password_hash.set(password_hash)

    env = {
        "MESHCHAT_ALTCHA_ENABLED": "1",
        "MESHCHAT_ALTCHA_HMAC_KEY": _TEST_SECRET,
    }
    aio_app = build_test_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        with patch.dict(os.environ, env, clear=False):
            headers = await fetch_api_csrf_headers(client)
            response = await client.post(
                "/api/v1/auth/login",
                json={"password": "secretpass"},
                headers=headers,
            )
            assert response.status == 400
            body = await response.json()
            assert body.get("code") == ALTCHA_INVALID_CODE


@pytest.mark.asyncio
async def test_altcha_challenge_endpoint(mock_app):
    mock_app.altcha_enabled = True
    mock_app.current_context.running = True
    env = {
        "MESHCHAT_ALTCHA_ENABLED": "1",
        "MESHCHAT_ALTCHA_HMAC_KEY": _TEST_SECRET,
    }
    aio_app = build_test_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        with patch.dict(os.environ, env, clear=False):
            response = await client.get("/api/v1/auth/altcha/challenge")
            assert response.status == 200
            data = await response.json()
            assert "parameters" in data
            assert "signature" in data
            assert data["parameters"].get("algorithm") == "PBKDF2/SHA-256"
