"""Tests for login/setup rate limiting, lockout, and HTTP smoke paths."""

from __future__ import annotations

import json
import secrets
import time
from types import SimpleNamespace
from unittest.mock import patch

import bcrypt
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import _request_client_ip
from meshchatx.src.backend.database.access_attempts import (
    LOGIN_PATH,
    MAX_FAILED_BEFORE_LOCKOUT,
    MAX_TRUSTED_LOGIN_PER_WINDOW,
    MAX_UNTRUSTED_LOGIN_PER_WINDOW,
    WINDOW_LOCKOUT_S,
    WINDOW_RATE_TRUSTED_S,
    WINDOW_RATE_UNTRUSTED_S,
    user_agent_hash,
)


def _make_req(
    ip: str, ua: str, method: str = "POST", xff: str | None = None,
) -> SimpleNamespace:
    h = {"User-Agent": ua}
    if xff is not None:
        h["X-Forwarded-For"] = xff
    return SimpleNamespace(headers=h, remote=ip, method=method)


def _id_hex(mock_app) -> str:
    return mock_app.identity.hash.hex()


def test_request_client_ip_prefers_x_forwarded_for():
    r = _make_req("10.0.0.1", "ua", xff="203.0.113.5, 10.0.0.2")
    assert _request_client_ip(r) == "203.0.113.5"


def test_request_client_ip_falls_back_to_remote():
    r = _make_req("198.51.100.2", "ua")
    assert _request_client_ip(r) == "198.51.100.2"


def test_enforce_returns_none_when_no_database(mock_app):
    db = mock_app.database
    try:
        mock_app.database = None
        r = _make_req("127.0.0.1", "Mozilla/5.0")
        assert mock_app._enforce_login_access(r, LOGIN_PATH) is None
    finally:
        mock_app.database = db


def test_untrusted_rate_limit_after_max_per_window(mock_app):
    dao = mock_app.database.access_attempts
    ih = _id_hex(mock_app)
    ip = "192.0.2.10"
    ua = "RateTest/1"
    now = time.time()
    ts = now - (WINDOW_RATE_UNTRUSTED_S / 2)
    for _ in range(MAX_UNTRUSTED_LOGIN_PER_WINDOW):
        dao.provider.execute(
            """
            INSERT INTO access_attempts (
                created_at, identity_hash, client_ip, user_agent, user_agent_hash,
                path, method, outcome, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                ih,
                ip,
                ua,
                user_agent_hash(ua),
                LOGIN_PATH,
                "POST",
                "success",
                None,
            ),
        )
    r = _make_req(ip, ua)
    resp = mock_app._enforce_login_access(r, LOGIN_PATH)
    assert resp is not None
    assert resp.status == 429


def test_lockout_when_enough_untrusted_failures(mock_app):
    dao = mock_app.database.access_attempts
    ih = _id_hex(mock_app)
    ip = "192.0.2.20"
    ua = "Attacker/1"
    now = time.time()
    ts = now - (WINDOW_LOCKOUT_S / 2)
    for _ in range(MAX_FAILED_BEFORE_LOCKOUT):
        dao.provider.execute(
            """
            INSERT INTO access_attempts (
                created_at, identity_hash, client_ip, user_agent, user_agent_hash,
                path, method, outcome, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                ih,
                ip,
                ua,
                user_agent_hash(ua),
                LOGIN_PATH,
                "POST",
                "failed_password",
                None,
            ),
        )
    r = _make_req(ip, ua)
    resp = mock_app._enforce_login_access(r, LOGIN_PATH)
    assert resp is not None
    assert resp.status == 429
    body = json.loads(resp.body.decode())
    err = body.get("error", "")
    assert "failed" in err.lower() or "later" in err.lower()


def test_trusted_client_not_locked_out_by_own_failed_rows(mock_app):
    dao = mock_app.database.access_attempts
    ih = _id_hex(mock_app)
    ip = "192.0.2.30"
    ua = "GoodUser/1"
    h = user_agent_hash(ua)
    dao.upsert_trusted(ih, ip, h)
    ts = time.time() - (WINDOW_LOCKOUT_S / 2)
    for _ in range(10):
        dao.provider.execute(
            """
            INSERT INTO access_attempts (
                created_at, identity_hash, client_ip, user_agent, user_agent_hash,
                path, method, outcome, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                ih,
                ip,
                ua,
                h,
                LOGIN_PATH,
                "POST",
                "failed_password",
                None,
            ),
        )
    r = _make_req(ip, ua)
    assert mock_app._enforce_login_access(r, LOGIN_PATH) is None


def test_trusted_rate_limit_after_max_trusted_window(mock_app):
    dao = mock_app.database.access_attempts
    ih = _id_hex(mock_app)
    ip = "192.0.2.40"
    ua = "HeavyTrusted/1"
    h = user_agent_hash(ua)
    dao.upsert_trusted(ih, ip, h)
    now = time.time()
    ts = now - (WINDOW_RATE_TRUSTED_S / 2)
    for _ in range(MAX_TRUSTED_LOGIN_PER_WINDOW):
        dao.provider.execute(
            """
            INSERT INTO access_attempts (
                created_at, identity_hash, client_ip, user_agent, user_agent_hash,
                path, method, outcome, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                ih,
                ip,
                ua,
                h,
                LOGIN_PATH,
                "POST",
                "success",
                None,
            ),
        )
    r = _make_req(ip, ua)
    resp = mock_app._enforce_login_access(r, LOGIN_PATH)
    assert resp is not None
    assert resp.status == 429


@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    n=st.integers(min_value=0, max_value=MAX_UNTRUSTED_LOGIN_PER_WINDOW + 3),
)
def test_enforce_untrusted_monotone_hypothesis(mock_app, n):
    dao = mock_app.database.access_attempts
    ih = _id_hex(mock_app)
    ip = "198.18.0.1"
    ua = "Hyp/1"
    dao.provider.execute("DELETE FROM access_attempts", ())
    for _ in range(n):
        dao.insert(ih, ip, ua, LOGIN_PATH, "POST", "success", None)
    r = _make_req(ip, ua)
    out = mock_app._enforce_login_access(r, LOGIN_PATH)
    if n >= MAX_UNTRUSTED_LOGIN_PER_WINDOW:
        assert out is not None
        assert out.status == 429
    else:
        assert out is None


def _make_aio_app(mock_app, use_https: bool):
    mock_app.session_secret_key = secrets.token_urlsafe(32)
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw = mock_app._define_routes(routes)
    aio_app = web.Application()
    setup_session(aio_app, mock_app._encrypted_cookie_storage(use_https))
    aio_app.middlewares.extend([auth_mw, mime_mw, sec_mw])
    aio_app.add_routes(routes)
    return aio_app


@pytest.mark.asyncio
async def test_login_records_access_attempt_and_debug_list(mock_app):
    mock_app.config.auth_enabled.set(True)
    pw = b"smoke-access-attempt-pw-ok"
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        bad = await client.post("/api/v1/auth/login", json={"password": "wrong"})
        assert bad.status == 401
        good = await client.post(
            "/api/v1/auth/login",
            json={"password": pw.decode("utf-8")},
        )
        assert good.status == 200

    dao = mock_app.database.access_attempts
    rows = dao.list_attempts(limit=20, outcome="failed_password")
    assert any(r["outcome"] == "failed_password" for r in rows)
    rows_ok = dao.list_attempts(limit=20, outcome="success")
    assert any(r["outcome"] == "success" for r in rows_ok)
    total = dao.count_attempts()
    assert total >= 2


@pytest.mark.asyncio
async def test_lockout_login_returns_429_smoke(mock_app):
    mock_app.config.auth_enabled.set(True)
    pw = b"lockout-smoke-pw"
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8"),
    )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        ip = "192.0.2.88"
        with patch(
            "meshchatx.meshchat._request_client_ip",
            return_value=ip,
        ):
            for _ in range(MAX_FAILED_BEFORE_LOCKOUT):
                r = await client.post(
                    "/api/v1/auth/login",
                    json={"password": "nope"},
                    headers={"User-Agent": "SmokeLock/1"},
                )
                assert r.status == 401
            r429 = await client.post(
                "/api/v1/auth/login",
                json={"password": "nope"},
                headers={"User-Agent": "SmokeLock/1"},
            )
            assert r429.status == 429


@pytest.mark.asyncio
async def test_rate_limited_login_returns_429_smoke(mock_app):
    mock_app.config.auth_enabled.set(True)
    pw = b"rl-smoke-pw"
    mock_app.config.auth_password_hash.set(
        bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8"),
    )
    dao = mock_app.database.access_attempts
    ih = _id_hex(mock_app)
    ip = "192.0.2.99"
    ua = "SmokeRL/1"
    now = time.time()
    ts = now - (WINDOW_RATE_UNTRUSTED_S / 2)
    for _ in range(MAX_UNTRUSTED_LOGIN_PER_WINDOW):
        dao.provider.execute(
            """
            INSERT INTO access_attempts (
                created_at, identity_hash, client_ip, user_agent, user_agent_hash,
                path, method, outcome, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                ih,
                ip,
                ua,
                user_agent_hash(ua),
                LOGIN_PATH,
                "POST",
                "success",
                None,
            ),
        )
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        with patch(
            "meshchatx.meshchat._request_client_ip",
            return_value=ip,
        ):
            r429 = await client.post(
                "/api/v1/auth/login",
                json={"password": "nope"},
                headers={"User-Agent": ua},
            )
            assert r429.status == 429


@pytest.mark.asyncio
async def test_debug_access_attempts_endpoint_returns_shape(mock_app):
    mock_app.config.auth_enabled.set(False)
    aio_app = _make_aio_app(mock_app, use_https=False)

    async with TestClient(TestServer(aio_app)) as client:
        r = await client.get("/api/v1/debug/access-attempts?limit=5&offset=0")
        assert r.status == 200
        data = await r.json()
        assert "attempts" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["attempts"], list)
