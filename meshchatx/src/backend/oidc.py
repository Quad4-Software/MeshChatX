# SPDX-License-Identifier: 0BSD

"""OpenID Connect authorization-code login for the web UI.

Works with generic providers (Authentik, Keycloak, Pocket ID, and similar)
through discovery. Settings live in the per-identity config store and can be
overridden with MESHCHAT_OIDC_* environment variables, which is the intended
path for container deployments that inject client credentials via secrets.

The flow is deliberately narrow: authorization code + PKCE, ID token
signature validation against the provider JWKS, and strict iss/aud/exp/nonce
checks. Access tokens and refresh tokens are never requested or stored.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse

import aiohttp
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import (
    ec,
    ed25519,
    padding,
    rsa,
)
from cryptography.hazmat.primitives.asymmetric import (
    utils as asym_utils,
)

from meshchatx.src.backend.ip_allowlist import client_ip_allowed
from meshchatx.src.backend.privacy_mode import ensure_outbound_http_allowed
from meshchatx.src.env_utils import env_bool, env_str

logger = logging.getLogger(__name__)

OIDC_DISCOVERY_SUFFIX = "/.well-known/openid-configuration"
OIDC_DEFAULT_SCOPES = "openid profile email"
OIDC_STATE_MAX_AGE_SECONDS = 600
OIDC_FETCH_TIMEOUT_SECONDS = 10
OIDC_MAX_RESPONSE_BYTES = 512 * 1024
OIDC_MAX_ID_TOKEN_BYTES = 64 * 1024
OIDC_METADATA_CACHE_TTL = 300
OIDC_JWKS_CACHE_TTL = 300
OIDC_ALLOWED_ALGS = frozenset({"RS256", "ES256", "EdDSA"})
OIDC_LEEWAY_SECONDS = 60

_B64URL_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_",
)


class OidcError(Exception):
    """Base class for expected OIDC flow failures."""


class OidcConfigError(OidcError):
    """Issuer URL or provider metadata is malformed."""


class OidcFetchError(OidcError):
    """Provider HTTP call failed or returned unusable data."""


class OidcTokenError(OidcError):
    """Token endpoint rejected the code exchange."""


class OidcVerifyError(OidcError):
    """ID token signature or claim validation failed."""


OIDC_ENV_VARS = (
    "MESHCHAT_OIDC_ENABLED",
    "MESHCHAT_OIDC_ISSUER",
    "MESHCHAT_OIDC_CLIENT_ID",
    "MESHCHAT_OIDC_CLIENT_SECRET",
    "MESHCHAT_OIDC_DISPLAY_NAME",
    "MESHCHAT_OIDC_SCOPES",
)


@dataclass
class OidcSettings:
    enabled: bool
    issuer: str | None
    client_id: str | None
    client_secret: str | None
    display_name: str | None
    scopes: str
    env_managed: bool = False


def _config_value(config, name: str):
    if config is None:
        return None
    attr = getattr(config, name, None)
    if attr is None:
        return None
    return attr.get()


def load_oidc_settings(config) -> OidcSettings:
    """Effective OIDC settings. MESHCHAT_OIDC_* env vars override config."""
    issuer_raw = env_str("MESHCHAT_OIDC_ISSUER") or _config_value(
        config,
        "oidc_issuer_url",
    )
    issuer = None
    if issuer_raw:
        try:
            issuer = validate_issuer_url(issuer_raw)
        except OidcConfigError:
            logger.warning("Ignoring invalid OIDC issuer URL")
    client_id = env_str("MESHCHAT_OIDC_CLIENT_ID") or _config_value(
        config,
        "oidc_client_id",
    )
    client_secret = env_str("MESHCHAT_OIDC_CLIENT_SECRET") or _config_value(
        config,
        "oidc_client_secret",
    )
    display_name = env_str("MESHCHAT_OIDC_DISPLAY_NAME") or _config_value(
        config,
        "oidc_display_name",
    )
    scopes = (
        env_str("MESHCHAT_OIDC_SCOPES")
        or _config_value(config, "oidc_scopes")
        or OIDC_DEFAULT_SCOPES
    )

    enabled_env = env_str("MESHCHAT_OIDC_ENABLED")
    if enabled_env is not None:
        enabled = env_bool("MESHCHAT_OIDC_ENABLED")
    elif env_str("MESHCHAT_OIDC_ISSUER"):
        # An operator who exports an issuer via env clearly intends OIDC on.
        enabled = True
    else:
        enabled = bool(_config_value(config, "oidc_enabled"))

    return OidcSettings(
        enabled=enabled,
        issuer=issuer,
        client_id=client_id,
        client_secret=client_secret,
        display_name=display_name,
        scopes=scopes,
        env_managed=any(env_str(name) for name in OIDC_ENV_VARS),
    )


def oidc_ready(settings: OidcSettings) -> bool:
    return bool(settings.enabled and settings.issuer and settings.client_id)


def validate_issuer_url(raw: str | None) -> str:
    """Normalize an issuer (or pasted discovery URL) to its canonical form.

    Rejects non-http(s) schemes, userinfo, missing hosts, query, fragment,
    and embedded whitespace so the stored value is always a clean origin.
    Accepts a full discovery document URL and strips the well-known suffix.
    """
    if not raw or not isinstance(raw, str):
        raise OidcConfigError("OIDC issuer URL is required")
    text = raw.strip()
    if not text or len(text) > 2048:
        raise OidcConfigError("OIDC issuer URL is empty or too long")
    if any(c.isspace() or ord(c) < 0x20 for c in text):
        raise OidcConfigError("OIDC issuer URL contains invalid characters")
    parsed = urlparse(text)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise OidcConfigError("OIDC issuer URL must be http or https")
    if parsed.username or parsed.password or "@" in (parsed.netloc or ""):
        raise OidcConfigError("OIDC issuer URL must not contain credentials")
    host = parsed.hostname
    if not host:
        raise OidcConfigError("OIDC issuer URL is missing a host")
    if parsed.query or parsed.fragment:
        raise OidcConfigError("OIDC issuer URL must not contain query or fragment")
    try:
        port = parsed.port
    except ValueError as exc:
        raise OidcConfigError("OIDC issuer URL has an invalid port") from exc

    host = host.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    default_port = 443 if scheme == "https" else 80
    port_part = f":{port}" if port is not None and port != default_port else ""
    path = parsed.path.rstrip("/")
    issuer = f"{scheme}://{host}{port_part}{path}"
    if issuer.endswith(OIDC_DISCOVERY_SUFFIX):
        issuer = issuer[: -len(OIDC_DISCOVERY_SUFFIX)]
    return issuer


def discovery_url_for_issuer(issuer: str) -> str:
    return issuer + OIDC_DISCOVERY_SUFFIX


def _first_forwarded(value: str | None) -> str:
    if not value:
        return ""
    return value.split(",")[0].strip()


def _authority_has_port(authority: str) -> bool:
    try:
        return urlparse(f"//{authority}").port is not None
    except ValueError:
        return False


def public_request_base_url(
    request,
    trusted_proxy_cidrs: str | None = None,
) -> str:
    """Browser-visible scheme://authority for building the OIDC redirect URI.

    Mirrors the WebSocket origin logic: X-Forwarded-* values are trusted only
    when the direct peer matches the configured trusted proxy CIDRs, so an
    attacker cannot poison the redirect URI through injected headers.
    """
    scheme = request.scheme if request.scheme in ("http", "https") else "http"
    authority = request.host or ""
    remote = (request.remote or "").strip()
    if remote and trusted_proxy_cidrs:
        if client_ip_allowed(remote, trusted_proxy_cidrs):
            forwarded_host = _first_forwarded(
                request.headers.get("X-Forwarded-Host"),
            )
            forwarded_proto = _first_forwarded(
                request.headers.get("X-Forwarded-Proto"),
            ).lower()
            forwarded_port = _first_forwarded(
                request.headers.get("X-Forwarded-Port"),
            )
            if forwarded_proto in ("http", "https"):
                scheme = forwarded_proto
            if forwarded_host:
                authority = forwarded_host
                if not _authority_has_port(authority) and forwarded_port:
                    try:
                        port = int(forwarded_port)
                    except ValueError:
                        port = 0
                    default = 443 if scheme == "https" else 80
                    if 1 <= port <= 65535 and port != default:
                        authority = f"{authority}:{port}"
    return f"{scheme}://{authority}"


def build_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, S256 code_challenge)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _b64url_decode(text: str, *, field: str) -> bytes:
    if not text or len(text) > OIDC_MAX_ID_TOKEN_BYTES:
        raise OidcVerifyError(f"Invalid {field} encoding")
    if not set(text) <= _B64URL_ALPHABET:
        raise OidcVerifyError(f"Invalid {field} encoding")
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (ValueError, TypeError) as exc:
        raise OidcVerifyError(f"Invalid {field} encoding") from exc


def _b64url_int(text: str, *, field: str) -> int:
    raw = _b64url_decode(text, field=field)
    if not raw or len(raw) > 4096:
        raise OidcVerifyError(f"Invalid {field} value")
    return int.from_bytes(raw, "big")


def _validate_endpoint_url(url, *, field: str) -> str:
    if not isinstance(url, str) or not url:
        raise OidcConfigError(f"OIDC provider metadata is missing {field}")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise OidcConfigError(f"OIDC provider {field} must be http or https")
    if parsed.username or parsed.password or "@" in (parsed.netloc or ""):
        raise OidcConfigError(f"OIDC provider {field} must not contain credentials")
    if not parsed.hostname:
        raise OidcConfigError(f"OIDC provider {field} is missing a host")
    return url


async def _fetch_json(
    config,
    url: str,
    *,
    feature: str,
    error_cls: type[OidcError] = OidcFetchError,
    **kwargs,
) -> dict:
    ensure_outbound_http_allowed(config, feature=feature)
    timeout = aiohttp.ClientTimeout(total=OIDC_FETCH_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(url=url, **kwargs) as resp:
                body = await resp.content.read(OIDC_MAX_RESPONSE_BYTES + 1)
                if len(body) > OIDC_MAX_RESPONSE_BYTES:
                    raise error_cls(f"{feature} response too large")
                if resp.status != 200:
                    raise error_cls(
                        f"{feature} request failed with status {resp.status}",
                    )
    except (aiohttp.ClientError, TimeoutError) as exc:
        raise error_cls(f"{feature} request failed: {exc}") from exc
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise error_cls(f"{feature} returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise error_cls(f"{feature} returned an unexpected payload")
    return data


async def fetch_discovery(config, issuer: str) -> dict:
    data = await _fetch_json(
        config,
        discovery_url_for_issuer(issuer),
        feature="OIDC discovery",
        method="GET",
    )
    doc_issuer = data.get("issuer")
    if doc_issuer != issuer:
        raise OidcConfigError(
            "OIDC discovery issuer does not match the configured issuer",
        )
    return {
        "issuer": issuer,
        "authorization_endpoint": _validate_endpoint_url(
            data.get("authorization_endpoint"),
            field="authorization_endpoint",
        ),
        "token_endpoint": _validate_endpoint_url(
            data.get("token_endpoint"),
            field="token_endpoint",
        ),
        "jwks_uri": _validate_endpoint_url(
            data.get("jwks_uri"),
            field="jwks_uri",
        ),
    }


async def fetch_jwks(config, jwks_uri: str) -> dict:
    data = await _fetch_json(
        config,
        jwks_uri,
        feature="OIDC JWKS fetch",
        method="GET",
    )
    keys = data.get("keys")
    if not isinstance(keys, list) or not keys:
        raise OidcFetchError("OIDC JWKS document contains no keys")
    return data


async def exchange_code(
    config,
    token_endpoint: str,
    *,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str | None,
    code_verifier: str,
) -> dict:
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    auth = None
    if client_secret:
        auth = aiohttp.BasicAuth(client_id, client_secret)
    data = await _fetch_json(
        config,
        token_endpoint,
        feature="OIDC token exchange",
        error_cls=OidcTokenError,
        method="POST",
        data=form,
        auth=auth,
        headers={"Accept": "application/json"},
    )
    if not isinstance(data.get("id_token"), str):
        error = data.get("error")
        detail = f" ({error})" if isinstance(error, str) else ""
        raise OidcTokenError(f"OIDC token exchange returned no ID token{detail}")
    return data


_ALG_TO_KTY = {"RS256": "RSA", "ES256": "EC", "EdDSA": "OKP"}


def _select_jwk(jwks: dict, kid: str | None, alg: str) -> dict:
    expected_kty = _ALG_TO_KTY[alg]
    candidates = []
    for jwk in jwks.get("keys", []):
        if not isinstance(jwk, dict):
            continue
        if jwk.get("kty") != expected_kty:
            continue
        jwk_use = jwk.get("use")
        if jwk_use is not None and jwk_use != "sig":
            continue
        jwk_alg = jwk.get("alg")
        if jwk_alg is not None and jwk_alg != alg:
            continue
        candidates.append(jwk)
    if kid is not None:
        for jwk in candidates:
            if jwk.get("kid") == kid:
                return jwk
        raise OidcVerifyError("OIDC ID token references an unknown signing key")
    if len(candidates) != 1:
        raise OidcVerifyError(
            "OIDC ID token has no key id and the provider key is ambiguous",
        )
    return candidates[0]


def _jwk_to_public_key(jwk: dict):
    kty = jwk.get("kty")
    try:
        if kty == "RSA":
            numbers = rsa.RSAPublicNumbers(
                e=_b64url_int(jwk["e"], field="RSA exponent"),
                n=_b64url_int(jwk["n"], field="RSA modulus"),
            )
            return numbers.public_key()
        if kty == "EC":
            if jwk.get("crv") != "P-256":
                raise OidcVerifyError("Unsupported OIDC EC curve")
            numbers = ec.EllipticCurvePublicNumbers(
                x=_b64url_int(jwk["x"], field="EC x"),
                y=_b64url_int(jwk["y"], field="EC y"),
                curve=ec.SECP256R1(),
            )
            return numbers.public_key()
        if kty == "OKP":
            if jwk.get("crv") != "Ed25519":
                raise OidcVerifyError("Unsupported OIDC OKP curve")
            raw = _b64url_decode(jwk["x"], field="Ed25519 key")
            if len(raw) != 32:
                raise OidcVerifyError("Invalid OIDC Ed25519 key length")
            return ed25519.Ed25519PublicKey.from_public_bytes(raw)
    except KeyError as exc:
        raise OidcVerifyError(f"OIDC JWK is missing field {exc}") from exc
    except ValueError as exc:
        raise OidcVerifyError(f"OIDC JWK is invalid: {exc}") from exc
    raise OidcVerifyError(f"Unsupported OIDC key type {kty!r}")


def _verify_signature(key, alg: str, signature: bytes, data: bytes) -> None:
    try:
        if alg == "RS256":
            key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
        elif alg == "ES256":
            # JWS ES256 is raw R || S (64 bytes), not DER.
            if len(signature) != 64:
                raise InvalidSignature
            r = int.from_bytes(signature[:32], "big")
            s = int.from_bytes(signature[32:], "big")
            der = asym_utils.encode_dss_signature(r, s)
            key.verify(der, data, ec.ECDSA(hashes.SHA256()))
        else:
            key.verify(signature, data)
    except InvalidSignature as exc:
        raise OidcVerifyError("OIDC ID token signature is invalid") from exc


def verify_id_token(
    id_token: str,
    jwks: dict,
    *,
    issuer: str,
    client_id: str,
    nonce: str,
    now: float | None = None,
    leeway: int = OIDC_LEEWAY_SECONDS,
) -> dict:
    """Validate a provider ID token and return its claims.

    Enforces an explicit alg allowlist (no HS* or none), signature against
    the provider JWKS, exact iss match, client_id in aud, exp/iat/nbf windows
    with a small leeway, and the session nonce.
    """
    if (
        not isinstance(id_token, str)
        or len(id_token.encode()) > OIDC_MAX_ID_TOKEN_BYTES
    ):
        raise OidcVerifyError("OIDC ID token is missing or too large")
    parts = id_token.split(".")
    if len(parts) != 3:
        raise OidcVerifyError("OIDC ID token is malformed")

    try:
        header = json.loads(_b64url_decode(parts[0], field="token header"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise OidcVerifyError("OIDC ID token header is invalid") from exc
    if not isinstance(header, dict):
        raise OidcVerifyError("OIDC ID token header is invalid")
    alg = header.get("alg")
    if alg not in OIDC_ALLOWED_ALGS:
        raise OidcVerifyError("OIDC ID token uses a disallowed algorithm")
    kid = header.get("kid")
    if kid is not None and not isinstance(kid, str):
        raise OidcVerifyError("OIDC ID token key id is invalid")

    try:
        claims = json.loads(_b64url_decode(parts[1], field="token payload"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise OidcVerifyError("OIDC ID token payload is invalid") from exc
    if not isinstance(claims, dict):
        raise OidcVerifyError("OIDC ID token payload is invalid")

    signature = _b64url_decode(parts[2], field="token signature")
    jwk = _select_jwk(jwks, kid, alg)
    key = _jwk_to_public_key(jwk)
    _verify_signature(key, alg, signature, (parts[0] + "." + parts[1]).encode("ascii"))

    if claims.get("iss") != issuer:
        raise OidcVerifyError("OIDC ID token issuer mismatch")
    aud = claims.get("aud")
    if isinstance(aud, str):
        audiences = [aud]
    elif isinstance(aud, list):
        audiences = aud
    else:
        audiences = []
    if client_id not in audiences:
        raise OidcVerifyError("OIDC ID token audience mismatch")
    if len(audiences) > 1 and claims.get("azp") not in (None, client_id):
        raise OidcVerifyError("OIDC ID token authorized party mismatch")

    now = time.time() if now is None else now
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or now - leeway > exp:
        raise OidcVerifyError("OIDC ID token is expired or missing expiry")
    iat = claims.get("iat")
    if isinstance(iat, (int, float)) and iat - leeway > now:
        raise OidcVerifyError("OIDC ID token was issued in the future")
    nbf = claims.get("nbf")
    if isinstance(nbf, (int, float)) and now + leeway < nbf:
        raise OidcVerifyError("OIDC ID token is not yet valid")

    token_nonce = claims.get("nonce")
    if not isinstance(token_nonce, str) or not secrets.compare_digest(
        token_nonce,
        nonce,
    ):
        raise OidcVerifyError("OIDC ID token nonce mismatch")
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise OidcVerifyError("OIDC ID token is missing a subject")
    return claims


def _cache_get(cache: dict, key: str):
    entry = cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if expires_at <= time.time():
        cache.pop(key, None)
        return None
    return value


def _cache_put(cache: dict, key: str, value, ttl: int) -> None:
    cache[key] = (time.time() + ttl, value)


async def fetch_discovery_cached(app, config, issuer: str) -> dict:
    cache = getattr(app, "_oidc_metadata_cache", None)
    if cache is None:
        cache = {}
        app._oidc_metadata_cache = cache
    cached = _cache_get(cache, issuer)
    if cached is not None:
        return cached
    metadata = await fetch_discovery(config, issuer)
    _cache_put(cache, issuer, metadata, OIDC_METADATA_CACHE_TTL)
    return metadata


async def fetch_jwks_cached(
    app, config, jwks_uri: str, *, refresh: bool = False
) -> dict:
    cache = getattr(app, "_oidc_jwks_cache", None)
    if cache is None:
        cache = {}
        app._oidc_jwks_cache = cache
    if not refresh:
        cached = _cache_get(cache, jwks_uri)
        if cached is not None:
            return cached
    jwks = await fetch_jwks(config, jwks_uri)
    _cache_put(cache, jwks_uri, jwks, OIDC_JWKS_CACHE_TTL)
    return jwks


def authorization_url(metadata: dict, params: dict) -> str:
    separator = "&" if "?" in metadata["authorization_endpoint"] else "?"
    return metadata["authorization_endpoint"] + separator + urlencode(params)
