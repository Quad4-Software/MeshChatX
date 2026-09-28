# SPDX-License-Identifier: 0BSD

"""OIDC single sign-on tests: config, token verification, and full flow."""

import base64
import hashlib
import json
import secrets
import time
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import (
    ec,
    ed25519,
    padding,
    rsa,
)
from cryptography.hazmat.primitives.asymmetric import (
    utils as asym_utils,
)

from meshchatx.src.backend import oidc
from meshchatx.src.backend.oidc import (
    OidcConfigError,
    OidcVerifyError,
    load_oidc_settings,
    public_request_base_url,
    validate_issuer_url,
    verify_id_token,
)
from meshchatx.src.backend.websocket_config_guard import (
    sanitize_websocket_config_update,
)
from tests.backend.conftest import extend_meshchat_middlewares, fetch_api_csrf_headers

ISSUER = "http://127.0.0.1:9999"
CLIENT_ID = "meshchatx-test"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64_int(value: int) -> str:
    return _b64(value.to_bytes((value.bit_length() + 7) // 8 or 1, "big"))


def _make_rsa():
    key = rsa.generate_private_key(65537, 2048)
    pub = key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "rsa1",
        "alg": "RS256",
        "use": "sig",
        "n": _b64_int(pub.n),
        "e": _b64_int(pub.e),
    }
    return key, jwk


def _make_ec():
    key = ec.generate_private_key(ec.SECP256R1())
    pub = key.public_key().public_numbers()
    jwk = {
        "kty": "EC",
        "kid": "ec1",
        "alg": "ES256",
        "use": "sig",
        "crv": "P-256",
        "x": _b64_int(pub.x),
        "y": _b64_int(pub.y),
    }
    return key, jwk


def _make_ed():
    key = ed25519.Ed25519PrivateKey.generate()
    raw = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    jwk = {
        "kty": "OKP",
        "kid": "ed1",
        "alg": "EdDSA",
        "use": "sig",
        "crv": "Ed25519",
        "x": _b64(raw),
    }
    return key, jwk


def _sign_jwt(header: dict, claims: dict, key, alg: str) -> str:
    head = _b64(json.dumps(header).encode())
    payload = _b64(json.dumps(claims).encode())
    data = f"{head}.{payload}".encode("ascii")
    if alg == "RS256":
        sig = key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    elif alg == "ES256":
        # Emit the raw R || S form real providers use for JWS ES256.
        der = key.sign(data, ec.ECDSA(hashes.SHA256()))
        r, s = asym_utils.decode_dss_signature(der)
        sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    elif alg == "EdDSA":
        sig = key.sign(data)
    else:
        sig = b""
    return f"{head}.{payload}.{_b64(sig)}"


def _claims(**overrides):
    claims = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "user-123",
        "exp": time.time() + 600,
        "iat": time.time() - 10,
        "nonce": "test-nonce",
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def rsa_pair():
    return _make_rsa()


@pytest.fixture
def ec_pair():
    return _make_ec()


@pytest.fixture
def ed_pair():
    return _make_ed()


# issuer URL validation


def test_issuer_url_accepts_https():
    assert validate_issuer_url("https://idp.example.com") == "https://idp.example.com"


def test_issuer_url_strips_trailing_slash():
    assert validate_issuer_url("https://idp.example.com/") == "https://idp.example.com"


def test_issuer_url_accepts_path():
    assert (
        validate_issuer_url("https://idp.example.com/application/o/meshchatx/")
        == "https://idp.example.com/application/o/meshchatx"
    )


def test_issuer_url_strips_discovery_suffix():
    assert (
        validate_issuer_url("https://idp.example.com/.well-known/openid-configuration")
        == "https://idp.example.com"
    )


def test_issuer_url_keeps_nondefault_port():
    assert validate_issuer_url("http://localhost:9000") == "http://localhost:9000"


def test_issuer_url_strips_default_port():
    assert (
        validate_issuer_url("https://idp.example.com:443") == "https://idp.example.com"
    )
    assert validate_issuer_url("http://idp.example.com:80") == "http://idp.example.com"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        None,
        "notaurl",
        "ftp://idp.example.com",
        "javascript:alert(1)",
        "data:text/html,x",
        "https://user:pass@idp.example.com",
        "https://user@idp.example.com",
        "https://idp.example.com?x=1",
        "https://idp.example.com#frag",
        "https://idp.example.com:bad",
        "https://",
        "https://idp.example.com/x y",
        " https://idp.example.com\n/path",
    ],
)
def test_issuer_url_rejects_malformed(raw):
    with pytest.raises(OidcConfigError):
        validate_issuer_url(raw)


def test_issuer_url_ipv6():
    assert validate_issuer_url("http://[::1]:8080/app") == "http://[::1]:8080/app"


# settings loading


def test_settings_defaults(mock_app):
    settings = load_oidc_settings(mock_app.config)
    assert settings.enabled is False
    assert settings.issuer is None
    assert settings.env_managed is False


def test_settings_from_config(mock_app):
    mock_app.config.oidc_enabled.set(True)
    mock_app.config.oidc_issuer_url.set("https://idp.example.com")
    mock_app.config.oidc_client_id.set("cid")
    mock_app.config.oidc_client_secret.set("s3cret")
    settings = load_oidc_settings(mock_app.config)
    assert settings.enabled is True
    assert settings.issuer == "https://idp.example.com"
    assert settings.client_id == "cid"
    assert settings.client_secret == "s3cret"


def test_settings_env_overrides_config(mock_app, monkeypatch):
    mock_app.config.oidc_enabled.set(False)
    mock_app.config.oidc_issuer_url.set("https://config.example.com")
    mock_app.config.oidc_client_id.set("config-cid")
    monkeypatch.setenv("MESHCHAT_OIDC_ISSUER", "https://env.example.com")
    monkeypatch.setenv("MESHCHAT_OIDC_CLIENT_ID", "env-cid")
    settings = load_oidc_settings(mock_app.config)
    assert settings.enabled is True
    assert settings.issuer == "https://env.example.com"
    assert settings.client_id == "env-cid"
    assert settings.env_managed is True


def test_settings_env_enabled_false_beats_env_issuer(mock_app, monkeypatch):
    monkeypatch.setenv("MESHCHAT_OIDC_ISSUER", "https://env.example.com")
    monkeypatch.setenv("MESHCHAT_OIDC_ENABLED", "false")
    settings = load_oidc_settings(mock_app.config)
    assert settings.enabled is False


def test_settings_invalid_env_issuer_dropped(mock_app, monkeypatch):
    monkeypatch.setenv("MESHCHAT_OIDC_ISSUER", "javascript:alert(1)")
    monkeypatch.setenv("MESHCHAT_OIDC_CLIENT_ID", "cid")
    settings = load_oidc_settings(mock_app.config)
    assert settings.issuer is None
    assert not oidc.oidc_ready(settings)


def test_oidc_ready_requires_issuer_and_client_id(mock_app):
    mock_app.config.oidc_enabled.set(True)
    assert not mock_app._oidc_ready()
    mock_app.config.oidc_issuer_url.set("https://idp.example.com")
    assert not mock_app._oidc_ready()
    mock_app.config.oidc_client_id.set("cid")
    assert mock_app._oidc_ready()


def test_oidc_ready_implies_auth_enabled(mock_app):
    mock_app.config.oidc_enabled.set(True)
    mock_app.config.oidc_issuer_url.set("https://idp.example.com")
    mock_app.config.oidc_client_id.set("cid")
    assert mock_app.config.auth_enabled.get() is False
    assert mock_app.auth_enabled is True


# public base URL for the redirect URI


def _fake_request(
    *,
    scheme="http",
    host="meshchatx.local:8000",
    remote="10.0.0.5",
    headers=None,
):
    request = MagicMock()
    request.scheme = scheme
    request.host = host
    request.remote = remote
    request.headers = headers or {}
    return request


def test_base_url_direct():
    request = _fake_request()
    assert public_request_base_url(request) == "http://meshchatx.local:8000"


def test_base_url_https():
    request = _fake_request(scheme="https", host="meshchatx.local")
    assert public_request_base_url(request) == "https://meshchatx.local"


def test_base_url_trusted_proxy_headers():
    request = _fake_request(
        headers={
            "X-Forwarded-Host": "chat.example.com",
            "X-Forwarded-Proto": "https",
        },
    )
    assert public_request_base_url(request, "10.0.0.0/8") == "https://chat.example.com"


def test_base_url_trusted_proxy_nondefault_port():
    request = _fake_request(
        headers={
            "X-Forwarded-Host": "chat.example.com",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Port": "8443",
        },
    )
    assert (
        public_request_base_url(request, "10.0.0.0/8")
        == "https://chat.example.com:8443"
    )


def test_base_url_untrusted_forwarded_ignored():
    request = _fake_request(
        remote="192.0.2.9",
        headers={
            "X-Forwarded-Host": "evil.example.com",
            "X-Forwarded-Proto": "https",
        },
    )
    assert (
        public_request_base_url(request, "10.0.0.0/8") == "http://meshchatx.local:8000"
    )


def test_base_url_no_trusted_proxies_ignores_forwarded():
    request = _fake_request(
        headers={
            "X-Forwarded-Host": "evil.example.com",
            "X-Forwarded-Proto": "https",
        },
    )
    assert public_request_base_url(request, None) == "http://meshchatx.local:8000"


def test_base_url_first_forwarded_value_only():
    request = _fake_request(
        headers={
            "X-Forwarded-Host": "chat.example.com, evil.example.com",
            "X-Forwarded-Proto": "https, http",
        },
    )
    assert public_request_base_url(request, "10.0.0.0/8") == "https://chat.example.com"


def test_base_url_invalid_forwarded_port_ignored():
    request = _fake_request(
        headers={
            "X-Forwarded-Host": "chat.example.com",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Port": "99999",
        },
    )
    assert public_request_base_url(request, "10.0.0.0/8") == "https://chat.example.com"


# PKCE


def test_pkce_pair():
    verifier, challenge = oidc.build_pkce_pair()
    assert 43 <= len(verifier) <= 128
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    assert challenge == _b64(digest)


# ID token verification


def test_verify_rs256(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt({"alg": "RS256", "kid": "rsa1"}, _claims(), key, "RS256")
    claims = verify_id_token(
        token,
        {"keys": [jwk]},
        issuer=ISSUER,
        client_id=CLIENT_ID,
        nonce="test-nonce",
    )
    assert claims["sub"] == "user-123"


def test_verify_es256(ec_pair):
    key, jwk = ec_pair
    token = _sign_jwt({"alg": "ES256", "kid": "ec1"}, _claims(), key, "ES256")
    claims = verify_id_token(
        token,
        {"keys": [jwk]},
        issuer=ISSUER,
        client_id=CLIENT_ID,
        nonce="test-nonce",
    )
    assert claims["sub"] == "user-123"


def test_verify_eddsa(ed_pair):
    key, jwk = ed_pair
    token = _sign_jwt({"alg": "EdDSA", "kid": "ed1"}, _claims(), key, "EdDSA")
    claims = verify_id_token(
        token,
        {"keys": [jwk]},
        issuer=ISSUER,
        client_id=CLIENT_ID,
        nonce="test-nonce",
    )
    assert claims["sub"] == "user-123"


def test_verify_rejects_alg_none(rsa_pair):
    _, jwk = rsa_pair
    token = _sign_jwt({"alg": "none"}, _claims(), None, "none")
    with pytest.raises(OidcVerifyError):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_hs256(rsa_pair):
    _, jwk = rsa_pair
    token = _sign_jwt({"alg": "HS256"}, _claims(), None, "none")
    with pytest.raises(OidcVerifyError):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_bad_signature(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt({"alg": "RS256", "kid": "rsa1"}, _claims(), key, "RS256")
    parts = token.split(".")
    forged = f"{parts[0]}.{parts[1]}.{_b64(b'x' * 256)}"
    with pytest.raises(OidcVerifyError, match="signature"):
        verify_id_token(
            forged,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_tampered_claims(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt({"alg": "RS256", "kid": "rsa1"}, _claims(), key, "RS256")
    parts = token.split(".")
    evil_payload = _b64(json.dumps(_claims(sub="attacker")).encode())
    forged = f"{parts[0]}.{evil_payload}.{parts[2]}"
    with pytest.raises(OidcVerifyError, match="signature"):
        verify_id_token(
            forged,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_wrong_issuer(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt(
        {"alg": "RS256", "kid": "rsa1"},
        _claims(iss="https://evil.example.com"),
        key,
        "RS256",
    )
    with pytest.raises(OidcVerifyError, match="issuer"):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_wrong_audience(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt(
        {"alg": "RS256", "kid": "rsa1"},
        _claims(aud="other-client"),
        key,
        "RS256",
    )
    with pytest.raises(OidcVerifyError, match="audience"):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_accepts_audience_list(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt(
        {"alg": "RS256", "kid": "rsa1"},
        _claims(aud=["other", CLIENT_ID], azp=CLIENT_ID),
        key,
        "RS256",
    )
    claims = verify_id_token(
        token,
        {"keys": [jwk]},
        issuer=ISSUER,
        client_id=CLIENT_ID,
        nonce="test-nonce",
    )
    assert claims["sub"] == "user-123"


def test_verify_rejects_wrong_azp(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt(
        {"alg": "RS256", "kid": "rsa1"},
        _claims(aud=["other", CLIENT_ID], azp="attacker"),
        key,
        "RS256",
    )
    with pytest.raises(OidcVerifyError, match="authorized party"):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_expired(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt(
        {"alg": "RS256", "kid": "rsa1"},
        _claims(exp=time.time() - 3600),
        key,
        "RS256",
    )
    with pytest.raises(OidcVerifyError, match="expired"):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_missing_exp(rsa_pair):
    key, jwk = rsa_pair
    claims = _claims()
    del claims["exp"]
    token = _sign_jwt({"alg": "RS256", "kid": "rsa1"}, claims, key, "RS256")
    with pytest.raises(OidcVerifyError):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_future_iat(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt(
        {"alg": "RS256", "kid": "rsa1"},
        _claims(iat=time.time() + 3600),
        key,
        "RS256",
    )
    with pytest.raises(OidcVerifyError, match="future"):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_nonce_mismatch(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt(
        {"alg": "RS256", "kid": "rsa1"},
        _claims(nonce="other-nonce"),
        key,
        "RS256",
    )
    with pytest.raises(OidcVerifyError, match="nonce"):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_unknown_kid(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt({"alg": "RS256", "kid": "nope"}, _claims(), key, "RS256")
    with pytest.raises(OidcVerifyError, match="unknown signing key"):
        verify_id_token(
            token,
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_malformed_token(rsa_pair):
    _, jwk = rsa_pair
    with pytest.raises(OidcVerifyError):
        verify_id_token(
            "not-a-jwt",
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )
    with pytest.raises(OidcVerifyError):
        verify_id_token(
            "!!!.!!!.!!!",
            {"keys": [jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


def test_verify_rejects_no_kid_ambiguous(rsa_pair, ec_pair):
    rsa_key, rsa_jwk = rsa_pair
    _, ec_jwk = ec_pair
    rsa_jwk_no_kid = dict(rsa_jwk)
    del rsa_jwk_no_kid["kid"]
    token = _sign_jwt({"alg": "RS256"}, _claims(), rsa_key, "RS256")
    claims = verify_id_token(
        token,
        {"keys": [rsa_jwk_no_kid, ec_jwk]},
        issuer=ISSUER,
        client_id=CLIENT_ID,
        nonce="test-nonce",
    )
    assert claims["sub"] == "user-123"


def test_verify_skips_encryption_use_keys(rsa_pair):
    key, jwk = rsa_pair
    enc_jwk = dict(jwk, use="enc")
    token = _sign_jwt({"alg": "RS256", "kid": "rsa1"}, _claims(), key, "RS256")
    with pytest.raises(OidcVerifyError):
        verify_id_token(
            token,
            {"keys": [enc_jwk]},
            issuer=ISSUER,
            client_id=CLIENT_ID,
            nonce="test-nonce",
        )


# WS denylist


def test_ws_config_set_strips_oidc_keys():
    sanitized = sanitize_websocket_config_update(
        {
            "oidc_enabled": True,
            "oidc_issuer_url": "https://evil.example.com",
            "oidc_client_id": "x",
            "oidc_client_secret": "s",
            "oidc_display_name": "x",
            "oidc_scopes": "openid",
            "theme": "dark",
        },
    )
    assert sanitized == {"theme": "dark"}


# full flow with a mock provider


class MockIdP:
    """In-process OIDC provider serving discovery, JWKS, authorize, token."""

    def __init__(self):
        self.rsa_key, self.rsa_jwk = _make_rsa()
        self.ec_key, self.ec_jwk = _make_ec()
        self.ed_key, self.ed_jwk = _make_ed()
        self.issuer = None
        self.authorize_request = None
        self.token_request = None
        self.claims_overrides = {}
        self.token_status = 200
        self.token_error = None
        self.bad_signature = False
        self.omit_id_token = False
        self.bad_doc = None
        self.app = web.Application()
        self.app.router.add_get(
            "/.well-known/openid-configuration",
            self.discovery,
        )
        self.app.router.add_get(
            "/bad/.well-known/openid-configuration",
            self.bad_discovery,
        )
        self.app.router.add_get("/authorize", self.authorize)
        self.app.router.add_get("/jwks", self.jwks)
        self.app.router.add_post("/token", self.token)

    async def discovery(self, request):
        return web.json_response(
            {
                "issuer": self.issuer,
                "authorization_endpoint": f"{self.issuer}/authorize",
                "token_endpoint": f"{self.issuer}/token",
                "jwks_uri": f"{self.issuer}/jwks",
                "id_token_signing_alg_values_supported": ["RS256", "ES256"],
            },
        )

    async def bad_discovery(self, request):
        doc = self.bad_doc or {}
        return web.json_response(doc)

    async def authorize(self, request):
        self.authorize_request = dict(request.query)
        redirect_uri = request.query.get("redirect_uri", "")
        state = request.query.get("state", "")
        raise web.HTTPFound(f"{redirect_uri}?code=test-auth-code&state={state}")

    async def jwks(self, request):
        return web.json_response(
            {"keys": [self.rsa_jwk, self.ec_jwk, self.ed_jwk]},
        )

    async def token(self, request):
        if self.token_status != 200:
            return web.json_response(
                {"error": self.token_error or "server_error"},
                status=self.token_status,
            )
        data = await request.post()
        self.token_request = dict(data)
        if data.get("grant_type") != "authorization_code":
            return web.json_response({"error": "unsupported_grant_type"}, status=400)
        if data.get("code") != "test-auth-code":
            return web.json_response({"error": "invalid_grant"}, status=400)
        expected_challenge = self.authorize_request.get("code_challenge", "")
        verifier = data.get("code_verifier", "")
        actual = _b64(hashlib.sha256(verifier.encode()).digest())
        if actual != expected_challenge:
            return web.json_response({"error": "invalid_grant"}, status=400)

        key, alg = (
            (self.ec_key, "ES256") if self.bad_signature else (self.rsa_key, "RS256")
        )
        claims = _claims(
            iss=self.issuer,
            nonce=self.authorize_request.get("nonce", ""),
            **self.claims_overrides,
        )
        token = _sign_jwt(
            {"alg": alg, "kid": "ec1" if alg == "ES256" else "rsa1"}, claims, key, alg
        )
        if self.bad_signature:
            parts = token.split(".")
            token = f"{parts[0]}.{parts[1]}.{_b64(b'bad' * 64)}"
        body = {"access_token": "x", "token_type": "Bearer"}
        if not self.omit_id_token:
            body["id_token"] = token
        return web.json_response(body)


@pytest.fixture
async def idp():
    mock = MockIdP()
    server = TestServer(mock.app)
    await server.start_server()
    mock.issuer = str(server.make_url("")).rstrip("/")
    yield mock
    await server.close()


def _make_aio_app(mock_app):
    mock_app.session_secret_key = secrets.token_urlsafe(32)
    mock_app.listen_host = "127.0.0.1"
    mock_app.listen_port = 8000
    mock_app.use_https = False
    mock_app.landlock_active = False
    routes = web.RouteTableDef()
    middlewares = mock_app._define_routes(routes)
    aio_app = web.Application()
    setup_session(aio_app, mock_app._encrypted_cookie_storage(False))
    extend_meshchat_middlewares(aio_app, middlewares)
    aio_app.add_routes(routes)
    return aio_app


def _enable_oidc(mock_app, issuer):
    mock_app.config.oidc_enabled.set(True)
    mock_app.config.oidc_issuer_url.set(issuer)
    mock_app.config.oidc_client_id.set(CLIENT_ID)


async def _start_login(client):
    return await client.get("/api/v1/auth/oidc/login", allow_redirects=False)


async def _run_flow_to_callback(client, idp):
    """Drive login + provider authorize. Return the callback path."""
    resp = await _start_login(client)
    assert resp.status == 302
    authorize_url = resp.headers["Location"]
    async with TestClient(TestServer(idp.app)) as idp_client:
        auth_resp = await idp_client.get(
            authorize_url[len(idp.issuer) :],
            allow_redirects=False,
        )
    assert auth_resp.status == 302
    callback_url = auth_resp.headers["Location"]
    return "/" + callback_url.split("/", 3)[3]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_login_404_when_disabled(mock_app):
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        assert resp.status == 404
        resp = await client.get("/api/v1/auth/oidc/callback", allow_redirects=False)
        assert resp.status == 404


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_login_redirects_to_provider(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        assert resp.status == 302
        location = resp.headers["Location"]
        assert location.startswith(f"{idp.issuer}/authorize?")
        assert "response_type=code" in location
        assert f"client_id={CLIENT_ID}" in location
        assert "code_challenge=" in location
        assert "code_challenge_method=S256" in location
        assert "state=" in location
        assert "nonce=" in location
        assert "redirect_uri=" in location
        assert "openid" in location


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_full_flow_authenticates_session(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        # OIDC being ready enforces auth even though auth_enabled config is off
        protected = await client.get("/api/v1/server/security")
        assert protected.status == 401

        resp = await _start_login(client)
        assert resp.status == 302
        # Follow the provider authorize redirect manually
        authorize_url = resp.headers["Location"]
        async with TestClient(TestServer(idp.app)) as idp_client:
            auth_resp = await idp_client.get(
                authorize_url[len(idp.issuer) :],
                allow_redirects=False,
            )
        assert auth_resp.status == 302
        callback_url = auth_resp.headers["Location"]
        callback_path = "/" + callback_url.split("/", 3)[3]

        resp = await client.get(callback_path, allow_redirects=False)
        assert resp.status == 302
        assert resp.headers["Location"] == "/"

        status = await client.get("/api/v1/auth/status")
        data = await status.json()
        assert data["authenticated"] is True

        # authenticated session reaches a protected endpoint
        protected = await client.get("/api/v1/server/security")
        assert protected.status == 200


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_callback_rejects_bad_state(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        assert resp.status == 302
        resp = await client.get(
            "/api/v1/auth/oidc/callback?code=test-auth-code&state=forged",
            allow_redirects=False,
        )
        assert resp.status == 302
        assert "oidc_error=invalid_state" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_callback_rejects_missing_session(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.get(
            "/api/v1/auth/oidc/callback?code=test-auth-code&state=abc",
            allow_redirects=False,
        )
        assert resp.status == 302
        assert "oidc_error=invalid_state" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_callback_expired_state(mock_app, idp, monkeypatch):
    _enable_oidc(mock_app, idp.issuer)
    monkeypatch.setattr(oidc, "OIDC_STATE_MAX_AGE_SECONDS", -1)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        assert resp.status == 302
        resp = await client.get(
            "/api/v1/auth/oidc/callback?code=test-auth-code&state=x",
            allow_redirects=False,
        )
        assert "oidc_error=invalid_state" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_callback_provider_error_slug(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.get(
            "/api/v1/auth/oidc/callback?error=access_denied",
            allow_redirects=False,
        )
        assert "oidc_error=access_denied" in resp.headers["Location"]
        resp = await client.get(
            "/api/v1/auth/oidc/callback?error=<script>alert(1)</script>",
            allow_redirects=False,
        )
        assert "oidc_error=failed" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_callback_token_exchange_failure(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    idp.token_status = 400
    idp.token_error = "invalid_grant"
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        authorize_url = resp.headers["Location"]
        async with TestClient(TestServer(idp.app)) as idp_client:
            auth_resp = await idp_client.get(
                authorize_url[len(idp.issuer) :],
                allow_redirects=False,
            )
        callback_path = "/" + auth_resp.headers["Location"].split("/", 3)[3]
        resp = await client.get(callback_path, allow_redirects=False)
        assert "oidc_error=exchange_failed" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_callback_bad_signature_rejected(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    idp.bad_signature = True
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        authorize_url = resp.headers["Location"]
        async with TestClient(TestServer(idp.app)) as idp_client:
            auth_resp = await idp_client.get(
                authorize_url[len(idp.issuer) :],
                allow_redirects=False,
            )
        callback_path = "/" + auth_resp.headers["Location"].split("/", 3)[3]
        resp = await client.get(callback_path, allow_redirects=False)
        assert "oidc_error=verify_failed" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_privacy_mode_blocks(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    mock_app.config.privacy_mode_enabled.set(True)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        assert resp.status == 302
        assert "oidc_error=blocked" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_login_discovery_failure(mock_app):
    _enable_oidc(mock_app, "http://127.0.0.1:1")  # nothing listening
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        assert resp.status == 302
        assert "oidc_error=unreachable" in resp.headers["Location"]


def _stub_config_dict_identities(mock_app):
    """Give get_config_dict real values for mocked identity internals."""
    ctx = mock_app.current_context
    ctx.identity.get_public_key = MagicMock(return_value=b"k" * 32)
    ctx.local_lxmf_destination = MagicMock(hexhash="aa" * 16)
    ctx.telephone_manager.telephone = None
    ctx.message_router.propagation_destination = MagicMock(hexhash="bb" * 16)
    mock_app.reticulum = MagicMock()
    mock_app.reticulum.transport_enabled.return_value = False


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_config_patch_and_no_secret_leak(mock_app):
    _stub_config_dict_identities(mock_app)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        resp = await client.patch(
            "/api/v1/config",
            json={
                "oidc_enabled": True,
                "oidc_issuer_url": "https://idp.example.com/app/",
                "oidc_client_id": "cid-1",
                "oidc_client_secret": "s3cret",
                "oidc_display_name": "Authentik",
            },
            headers=headers,
        )
        assert resp.status == 200
        data = await resp.json()
        config = data["config"]
        assert config["oidc_enabled"] is True
        assert config["oidc_issuer_url"] == "https://idp.example.com/app"
        assert config["oidc_client_id"] == "cid-1"
        assert config["oidc_client_secret_set"] is True
        assert config["oidc_display_name"] == "Authentik"
        assert "s3cret" not in json.dumps(config)
        assert mock_app._oidc_ready() is True


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_config_patch_rejects_bad_issuer(mock_app):
    _stub_config_dict_identities(mock_app)
    mock_app.config.oidc_issuer_url.set("https://good.example.com")
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)
        resp = await client.patch(
            "/api/v1/config",
            json={"oidc_issuer_url": "javascript:alert(1)"},
            headers=headers,
        )
        assert resp.status == 400
        assert mock_app.config.oidc_issuer_url.get() == "https://good.example.com"


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_auth_status_reports(mock_app):
    _enable_oidc(mock_app, "https://idp.example.com")
    mock_app.config.oidc_display_name.set("Authentik")
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await client.get("/api/v1/auth/status")
        data = await resp.json()
        assert data["auth_enabled"] is True
        assert data["oidc_enabled"] is True
        assert data["oidc_display_name"] == "Authentik"


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_login_not_ready_without_client_id(mock_app, idp):
    mock_app.config.oidc_enabled.set(True)
    mock_app.config.oidc_issuer_url.set(idp.issuer)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        assert resp.status == 404


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_callback_state_replay(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        callback_path = await _run_flow_to_callback(client, idp)
        resp = await client.get(callback_path, allow_redirects=False)
        assert resp.status == 302
        assert resp.headers["Location"] == "/"
        # The session was rotated. The same code+state must not work twice.
        resp = await client.get(callback_path, allow_redirects=False)
        assert "oidc_error=invalid_state" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_callback_cross_session_state(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    aio_app = _make_aio_app(mock_app)
    server = TestServer(aio_app)
    async with TestClient(server) as client_a, TestClient(server) as client_b:
        resp = await _start_login(client_a)
        assert resp.status == 302
        authorize_url = resp.headers["Location"]
        async with TestClient(TestServer(idp.app)) as idp_client:
            auth_resp = await idp_client.get(
                authorize_url[len(idp.issuer) :],
                allow_redirects=False,
            )
        callback_path = "/" + auth_resp.headers["Location"].split("/", 3)[3]
        # A different browser session holds no oidc_state.
        resp = await client_b.get(callback_path, allow_redirects=False)
        assert "oidc_error=invalid_state" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_callback_missing_id_token(mock_app, idp):
    _enable_oidc(mock_app, idp.issuer)
    idp.omit_id_token = True
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        callback_path = await _run_flow_to_callback(client, idp)
        resp = await client.get(callback_path, allow_redirects=False)
        assert "oidc_error=exchange_failed" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_login_rejects_userinfo_endpoint(mock_app, idp):
    bad_issuer = f"{idp.issuer}/bad"
    _enable_oidc(mock_app, bad_issuer)
    idp.bad_doc = {
        "issuer": bad_issuer,
        "authorization_endpoint": f"{bad_issuer}/authorize",
        # Userinfo smuggles a different host past prefix checks.
        "token_endpoint": f"https://evil.example.com@{idp.issuer[7:]}/token",
        "jwks_uri": f"{bad_issuer}/jwks",
    }
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        assert resp.status == 302
        assert "oidc_error=unreachable" in resp.headers["Location"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_oidc_login_rejects_discovery_issuer_mismatch(mock_app, idp):
    bad_issuer = f"{idp.issuer}/bad"
    _enable_oidc(mock_app, bad_issuer)
    idp.bad_doc = {
        # Doc claims a different issuer than the configured one.
        "issuer": idp.issuer,
        "authorization_endpoint": f"{idp.issuer}/authorize",
        "token_endpoint": f"{idp.issuer}/token",
        "jwks_uri": f"{idp.issuer}/jwks",
    }
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        resp = await _start_login(client)
        assert resp.status == 302
        assert "oidc_error=unreachable" in resp.headers["Location"]


def test_verify_rejects_iss_trailing_slash(rsa_pair):
    key, jwk = rsa_pair
    token = _sign_jwt(
        {"alg": "RS256", "kid": "rsa1"},
        _claims(iss="https://idp.example.com/", nonce="n"),
        key,
        "RS256",
    )
    with pytest.raises(oidc.OidcVerifyError):
        oidc.verify_id_token(
            token,
            {"keys": [jwk]},
            issuer="https://idp.example.com",
            client_id=CLIENT_ID,
            nonce="n",
        )


@pytest.mark.asyncio
async def test_update_config_invalid_issuer_leaves_no_partial_mutation(mock_app):
    """A rejected oidc_issuer_url must not persist earlier keys in the PATCH."""
    mock_app.config.display_name.set("before")
    mock_app.config.oidc_enabled.set(False)
    with pytest.raises(ValueError):
        await mock_app.update_config(
            {
                "display_name": "after",
                "oidc_enabled": True,
                "oidc_issuer_url": "ht!tp://not a url",
            }
        )
    assert mock_app.config.display_name.get() == "before"
    assert mock_app.config.oidc_enabled.get() is False
    assert mock_app.config.oidc_issuer_url.get() is None


@pytest.mark.asyncio
async def test_update_config_valid_issuer_persists(mock_app):
    await mock_app.update_config(
        {
            "oidc_enabled": True,
            "oidc_issuer_url": "https://idp.example.com/",
        }
    )
    assert mock_app.config.oidc_enabled.get() is True
    assert mock_app.config.oidc_issuer_url.get() == "https://idp.example.com"
