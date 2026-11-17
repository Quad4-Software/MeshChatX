# SPDX-License-Identifier: 0BSD
"""Shared types, constants and validation for the update system.

Trust model: every transport and mirror is untrusted. The signed manifest
(RSG envelope verified against a pinned or user-configured signer hash set)
is the only trust anchor. This module holds manifest schema checks,
settings accessors, mirror and signer validation, and the low-bandwidth
guard.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import platform
import random
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from packaging.version import InvalidVersion, Version

from meshchatx.src.env_utils import env_bool, env_str

DEFAULT_SIGNER_HASH = "e46112d44649266d71fe2193e00a4710"
MANIFEST_MAX_BYTES = 256 * 1024
BLOCKMAP_MAX_BYTES = 16 * 1024 * 1024
BLOCKMAP_MAX_DECOMPRESSED = 32 * 1024 * 1024
ARTIFACT_MAX_BYTES = 2 * 1024 * 1024 * 1024
USER_AGENT = "MeshChatX-Updater"
PENDING_DIRNAME = "updates"
PENDING_MARKER = "pending.json"
STATE_FILENAME = "state.json"
MANIFEST_STORE_DIRNAME = "manifests"
SEED_DIRNAME = "seeds"

CHANNELS = ("stable", "beta", "testing")
TRANSPORTS = ("auto", "clearnet", "rns")
APPLY_POLICIES = ("manual", "on_restart")
RNS_UPDATE_ASPECT = "meshchatx.update"
RNS_UPDATE_APP = "meshchatx"
RNS_UPDATE_SUBASPECT = "update"
DEFAULT_CHECK_INTERVAL_HOURS = 24.0
MIN_CHECK_INTERVAL_HOURS = 6.0
MAX_CHECK_INTERVAL_HOURS = 24 * 30
DEFAULT_SLOW_LINK_KBPS = 1000.0
DEFAULT_RNS_RATE_KBPS = 256.0
DEFAULT_MAX_DOWNLOAD_MB = 2048
MAX_MIRRORS = 8
MAX_SIGNER_HASHES = 8
MAX_RNS_SEEDS = 16
RNS_RANGE_MAX_BYTES = 1024 * 1024
HTTP_MAX_REDIRECTS = 3
RNS_MAX_RANGE_RETRIES = 2
BLOCK_SIZE = 512 * 1024
MAX_BLOCK_SIZE = 8 * 1024 * 1024
MIN_BLOCK_SIZE = 64 * 1024
MAX_CONCURRENT_RANGE_FETCHES = 4
FULL_DOWNLOAD_MISS_RATIO = 0.9

_KNOWN_PLATFORMS = ("linux", "windows", "macos", "android", "python")
_KNOWN_KINDS = (
    "appimage",
    "deb",
    "rpm",
    "flatpak",
    "apk",
    "dmg",
    "exe",
    "msi",
    "wheel",
    "pyz",
    "tarball",
    "other",
)
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_HEX32 = re.compile(r"^[0-9a-fA-F]{32}$")
_SIGNER_RE = re.compile(r"^(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{64})$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+~-]{0,199}$")


class UpdateError(Exception):
    """Base error for update operations."""


class UpdateUnavailable(UpdateError):
    """Updates disabled, no manifest, or nothing applicable."""


class UpdateVerifyError(UpdateError):
    """Signature, signer, checksum or manifest validation failure."""


def updates_disabled() -> bool:
    return env_bool("MESHCHATX_UPDATE_DISABLED")


def pinned_signer_hashes(extra=None) -> list[bytes]:
    """Signer hashes accepted for manifest verification.

    A pin is the release identity hash: 32 hex chars (the RNS
    identity.hash, i.e. truncated pubkey hash) or 64 hex chars (the full
    sha256 of the public key). MESHCHATX_UPDATE_SIGNER env pins a single
    signer. The user setting update_signer_hashes, when non-empty,
    replaces the default release signer so a user can pin their own
    release identity.
    """
    env_raw = (env_str("MESHCHATX_UPDATE_SIGNER") or "").strip()
    if env_raw:
        try:
            return [bytes.fromhex(env_raw)]
        except ValueError:
            return [bytes.fromhex(DEFAULT_SIGNER_HASH)]
    if extra:
        out = []
        for h in extra:
            try:
                out.append(bytes.fromhex(h))
            except (ValueError, TypeError):
                continue
        if out:
            return out
    return [bytes.fromhex(DEFAULT_SIGNER_HASH)]


def normalize_arch(machine=None) -> str:
    m = (machine or platform.machine() or "").lower()
    if m in ("x86_64", "amd64", "x64"):
        return "x86_64"
    if m in ("aarch64", "arm64"):
        return "aarch64"
    if m.startswith("armv7") or m == "armhf":
        return "armv7"
    if m in ("i386", "i686", "x86"):
        return "x86"
    return m or "any"


def host_platform() -> str:
    try:
        from meshchatx.android_push_bridge import _is_chaquopy_android

        if _is_chaquopy_android():
            return "android"
    except Exception:
        pass
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def version_newer(candidate: str, current: str) -> bool:
    try:
        return Version(candidate) > Version(current)
    except InvalidVersion:
        return False


def version_allowed(candidate: str, minimum: str) -> bool:
    try:
        return Version(candidate) >= Version(minimum)
    except InvalidVersion:
        return False


def valid_version(value) -> bool:
    try:
        Version(str(value))
        return True
    except InvalidVersion:
        return False


def safe_artifact_name(name) -> str | None:
    """Artifact names are bare file names: no separators, no dot segments."""
    if not isinstance(name, str):
        return None
    if not _NAME_RE.match(name):
        return None
    if name in (".", "..") or "/" in name or "\\" in name or "\x00" in name:
        return None
    return name


def is_loopback_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback
    except ValueError:
        return host in ("localhost", "localhost.localdomain")


def validate_https_url(url) -> str | None:
    """Return the URL unchanged when acceptable, else None.

    https only, no userinfo. Plain http is allowed only for loopback hosts
    so tests can use a local http.server.
    """
    if not isinstance(url, str) or not url or len(url) > 2048:
        return None
    try:
        p = urlparse(url)
    except Exception:
        return None
    if p.username or p.password:
        return None
    if p.scheme == "https" and p.hostname:
        return url
    if p.scheme == "http" and p.hostname and is_loopback_host(p.hostname):
        return url
    return None


def default_mirrors() -> list[dict]:
    """Ordered default mirror list: GitHub Releases, Forgejo, CDN."""
    return [
        {
            "name": "github",
            "kind": "github",
            "base": "https://github.com/Quad4-Software/MeshChatX",
        },
        {
            "name": "forgejo",
            "kind": "forgejo",
            "base": "https://git.quad4.io/reticulum/MeshChatX",
        },
        {"name": "cdn", "kind": "static", "base": "https://cdn.quad4.io"},
    ]


def mirror_asset_name(channel: str) -> str:
    return f"update-manifest-{channel}.rsm"


def parse_json_list(raw, fallback):
    if not raw:
        return list(fallback)
    try:
        val = json.loads(raw)
    except Exception:
        return list(fallback)
    return val if isinstance(val, list) else list(fallback)


def dumps_json_list(items) -> str:
    return json.dumps(list(items))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# -- settings -----------------------------------------------------------------


@dataclass
class UpdateSettings:
    enabled: bool = False
    auto_check: bool = False
    check_interval_hours: float = DEFAULT_CHECK_INTERVAL_HOURS
    auto_download: bool = False
    apply_policy: str = "manual"
    channel: str = ""
    transport: str = "auto"
    custom_mirrors: list = field(default_factory=list)
    signer_hashes: list = field(default_factory=list)
    peer_relay: bool = False
    max_download_mb: int = DEFAULT_MAX_DOWNLOAD_MB
    rns_rate_kbps: float = DEFAULT_RNS_RATE_KBPS
    slow_link_kbps: float = DEFAULT_SLOW_LINK_KBPS
    rns_seeds: list = field(default_factory=list)

    @classmethod
    def from_config(cls, config) -> UpdateSettings:
        if config is None:
            return cls()

        def b(key, default=False):
            try:
                v = config.get(key, default)
            except Exception:
                return default
            if isinstance(v, str):
                return v.lower() in ("1", "true", "yes", "on")
            return bool(v)

        def f(key, default):
            try:
                return float(config.get(key, default))
            except Exception:
                return default

        def i(key, default):
            try:
                return int(float(config.get(key, default)))
            except Exception:
                return default

        def s(key, default=""):
            try:
                v = config.get(key, default)
            except Exception:
                return default
            return v if isinstance(v, str) else (default or "")

        mirrors_raw = parse_json_list(s("update_custom_mirrors"), [])
        mirrors = []
        for m in mirrors_raw:
            if isinstance(m, str):
                ok = validate_https_url(m)
                if ok:
                    mirrors.append(
                        {"name": "custom", "kind": "static", "base": ok.rstrip("/")}
                    )
        signers = [
            h
            for h in parse_json_list(s("update_signer_hashes"), [])
            if isinstance(h, str) and _SIGNER_RE.match(h)
        ]
        seeds = [
            h
            for h in parse_json_list(s("update_rns_seeds"), [])
            if isinstance(h, str) and _HEX32.match(h)
        ]
        channel = s("update_channel", "")
        transport = s("update_transport", "auto")
        policy = s("update_apply_policy", "manual")
        return cls(
            enabled=b("updates_enabled", False),
            auto_check=b("update_auto_check", False),
            check_interval_hours=max(
                MIN_CHECK_INTERVAL_HOURS,
                min(
                    MAX_CHECK_INTERVAL_HOURS,
                    f("update_check_interval_hours", DEFAULT_CHECK_INTERVAL_HOURS),
                ),
            ),
            auto_download=b("update_auto_download", False),
            apply_policy=policy if policy in APPLY_POLICIES else "manual",
            channel=channel if channel in CHANNELS else "",
            transport=transport if transport in TRANSPORTS else "auto",
            custom_mirrors=mirrors[:MAX_MIRRORS],
            signer_hashes=signers[:MAX_SIGNER_HASHES],
            peer_relay=b("update_peer_relay", False),
            max_download_mb=max(
                1, min(8192, i("update_max_download_mb", DEFAULT_MAX_DOWNLOAD_MB))
            ),
            rns_rate_kbps=max(
                8.0, min(10240.0, f("update_rns_rate_kbps", DEFAULT_RNS_RATE_KBPS))
            ),
            slow_link_kbps=max(
                1.0, min(100000.0, f("update_slow_link_kbps", DEFAULT_SLOW_LINK_KBPS))
            ),
            rns_seeds=seeds[:MAX_RNS_SEEDS],
        )

    def as_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "auto_check": self.auto_check,
            "check_interval_hours": self.check_interval_hours,
            "auto_download": self.auto_download,
            "apply_policy": self.apply_policy,
            "channel": self.channel,
            "transport": self.transport,
            "custom_mirrors": [m["base"] for m in self.custom_mirrors],
            "signer_hashes": list(self.signer_hashes),
            "peer_relay": self.peer_relay,
            "max_download_mb": self.max_download_mb,
            "rns_rate_kbps": self.rns_rate_kbps,
            "slow_link_kbps": self.slow_link_kbps,
            "rns_seeds": list(self.rns_seeds),
        }

    def validate_patch(self, patch: dict) -> dict:
        """Validate a settings patch; returns clean key->value dict."""
        out = {}
        if "enabled" in patch:
            if not isinstance(patch["enabled"], bool):
                raise UpdateError("enabled must be a boolean")
            out["updates_enabled"] = patch["enabled"]
        if "auto_check" in patch:
            if not isinstance(patch["auto_check"], bool):
                raise UpdateError("auto_check must be a boolean")
            out["update_auto_check"] = patch["auto_check"]
        if "auto_download" in patch:
            if not isinstance(patch["auto_download"], bool):
                raise UpdateError("auto_download must be a boolean")
            out["update_auto_download"] = patch["auto_download"]
        if "peer_relay" in patch:
            if not isinstance(patch["peer_relay"], bool):
                raise UpdateError("peer_relay must be a boolean")
            out["update_peer_relay"] = patch["peer_relay"]
        if "check_interval_hours" in patch:
            try:
                v = float(patch["check_interval_hours"])
            except (TypeError, ValueError):
                raise UpdateError("check_interval_hours must be a number") from None
            if not (MIN_CHECK_INTERVAL_HOURS <= v <= MAX_CHECK_INTERVAL_HOURS):
                raise UpdateError(
                    "check_interval_hours must be between "
                    f"{MIN_CHECK_INTERVAL_HOURS} and {MAX_CHECK_INTERVAL_HOURS}"
                )
            out["update_check_interval_hours"] = v
        if "apply_policy" in patch:
            if patch["apply_policy"] not in APPLY_POLICIES:
                raise UpdateError("apply_policy must be manual or on_restart")
            out["update_apply_policy"] = patch["apply_policy"]
        if "channel" in patch:
            if patch["channel"] not in CHANNELS:
                raise UpdateError("channel must be stable, beta or testing")
            out["update_channel"] = patch["channel"]
        if "transport" in patch:
            if patch["transport"] not in TRANSPORTS:
                raise UpdateError("transport must be auto, clearnet or rns")
            out["update_transport"] = patch["transport"]
        if "custom_mirrors" in patch:
            raw = patch["custom_mirrors"]
            if not isinstance(raw, list) or len(raw) > MAX_MIRRORS:
                raise UpdateError("custom_mirrors must be a list of at most 8 URLs")
            cleaned = []
            for m in raw:
                ok = validate_https_url(m)
                if not ok:
                    raise UpdateError(
                        f"invalid mirror URL: {m!r} (https required, no credentials)"
                    )
                base = ok.rstrip("/")
                if base not in cleaned:
                    cleaned.append(base)
            out["update_custom_mirrors"] = dumps_json_list(cleaned)
        if "signer_hashes" in patch:
            raw = patch["signer_hashes"]
            if not isinstance(raw, list) or len(raw) > MAX_SIGNER_HASHES:
                raise UpdateError("signer_hashes must be a list of at most 8 hashes")
            cleaned = []
            for h in raw:
                if not isinstance(h, str) or not _SIGNER_RE.match(h):
                    raise UpdateError("signer hash must be 32 or 64 hex characters")
                hh = h.lower()
                if hh not in cleaned:
                    cleaned.append(hh)
            out["update_signer_hashes"] = dumps_json_list(cleaned)
        if "max_download_mb" in patch:
            try:
                v = int(patch["max_download_mb"])
            except (TypeError, ValueError):
                raise UpdateError("max_download_mb must be an integer") from None
            if not (1 <= v <= 8192):
                raise UpdateError("max_download_mb must be between 1 and 8192")
            out["update_max_download_mb"] = v
        if "rns_rate_kbps" in patch:
            try:
                v = float(patch["rns_rate_kbps"])
            except (TypeError, ValueError):
                raise UpdateError("rns_rate_kbps must be a number") from None
            if not (8.0 <= v <= 10240.0):
                raise UpdateError("rns_rate_kbps must be between 8 and 10240")
            out["update_rns_rate_kbps"] = v
        if "slow_link_kbps" in patch:
            try:
                v = float(patch["slow_link_kbps"])
            except (TypeError, ValueError):
                raise UpdateError("slow_link_kbps must be a number") from None
            if not (1.0 <= v <= 100000.0):
                raise UpdateError("slow_link_kbps must be between 1 and 100000")
            out["update_slow_link_kbps"] = v
        if "rns_seeds" in patch:
            raw = patch["rns_seeds"]
            if not isinstance(raw, list) or len(raw) > MAX_RNS_SEEDS:
                raise UpdateError("rns_seeds must be a list of at most 16 hashes")
            cleaned = []
            for h in raw:
                if not isinstance(h, str) or not _HEX32.match(h):
                    raise UpdateError(
                        "rns seed must be a 32-character hex destination hash"
                    )
                hh = h.lower()
                if hh not in cleaned:
                    cleaned.append(hh)
            out["update_rns_seeds"] = dumps_json_list(cleaned)
        return out


# -- manifest validation ------------------------------------------------------


def validate_manifest(
    manifest: dict, *, channel: str, current_version: str, enforce_newer: bool = True
) -> list[dict]:
    """Validate a verified manifest dict.

    Returns artifacts matching this host, or raises
    UpdateVerifyError/UpdateUnavailable.
    """
    if not isinstance(manifest, dict):
        raise UpdateVerifyError("manifest is not an object")
    if manifest.get("schema") != 2:
        raise UpdateVerifyError("unrecognized manifest schema")
    if manifest.get("app") != "reticulum-meshchatx":
        raise UpdateVerifyError("manifest is not for this application")
    mchannel = manifest.get("channel")
    if mchannel not in CHANNELS:
        raise UpdateVerifyError("manifest channel invalid")
    if channel and mchannel != channel:
        raise UpdateVerifyError("manifest channel does not match this install")
    version = manifest.get("version")
    if not valid_version(version):
        raise UpdateVerifyError("manifest version invalid")
    issued = manifest.get("issued_at")
    valid_until = manifest.get("valid_until")
    if not isinstance(issued, (int, float)) or not isinstance(
        valid_until, (int, float)
    ):
        raise UpdateVerifyError("manifest timestamps invalid")
    now = time.time()
    if issued > now + 3600:
        raise UpdateVerifyError("manifest issued_at is in the future")
    if valid_until <= now:
        raise UpdateVerifyError("manifest has expired")
    if valid_until <= issued:
        raise UpdateVerifyError("manifest validity window invalid")
    min_sup = manifest.get("min_supported_version") or "0.0.0"
    if not valid_version(min_sup):
        raise UpdateVerifyError("manifest min_supported_version invalid")
    if not version_allowed(str(current_version), str(min_sup)):
        raise UpdateUnavailable(
            f"update {version} requires version {min_sup} or newer installed first"
        )
    if enforce_newer and not version_newer(str(version), str(current_version)):
        return []
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise UpdateVerifyError("manifest artifacts invalid")
    plat = host_platform()
    arch = normalize_arch()
    matched = []
    for art in artifacts:
        if not isinstance(art, dict):
            continue
        name = safe_artifact_name(art.get("name"))
        size = art.get("size")
        sha = art.get("sha256")
        aplat = art.get("platform")
        aarch = art.get("arch") or "any"
        if name is None or not isinstance(size, int) or size <= 0:
            continue
        if size > ARTIFACT_MAX_BYTES:
            continue
        if not isinstance(sha, str) or not _HEX64.match(sha):
            continue
        if aplat not in _KNOWN_PLATFORMS:
            continue
        if aplat != plat and not (aplat == "python" and plat != "android"):
            continue
        if aarch != "any" and aarch != arch:
            continue
        kind = art.get("kind") or "other"
        if kind not in _KNOWN_KINDS:
            kind = "other"
        matched.append(
            {
                "name": name,
                "size": size,
                "sha256": sha.lower(),
                "kind": kind,
                "platform": aplat,
                "arch": aarch,
                "blockmap_sha256": (art.get("blockmap_sha256") or "").lower() or None,
                "block_size": art.get("block_size")
                if isinstance(art.get("block_size"), int)
                else None,
                "block_count": art.get("block_count")
                if isinstance(art.get("block_count"), int)
                else None,
            }
        )
    return matched


def manifest_fingerprint(manifest_rsm: bytes) -> str:
    return sha256_hex(manifest_rsm)


# -- low bandwidth guard -------------------------------------------------------


def online_interface_bitrates(interfaces=None) -> list[float]:
    """Bitrates (bit/s) of online RNS interfaces. Injectable for tests."""
    if interfaces is None:
        try:
            import RNS

            interfaces = list(getattr(RNS.Transport, "interfaces", []) or [])
        except Exception:
            return []
    out = []
    for iface in interfaces:
        try:
            if not getattr(iface, "online", True):
                continue
            br = getattr(iface, "bitrate", None)
            if br:
                out.append(float(br))
        except Exception:
            continue
    return out


def slow_rns_link(
    threshold_kbps: float = DEFAULT_SLOW_LINK_KBPS, interfaces=None
) -> bool:
    """True when the slowest online RNS interface is under the threshold.

    Heuristic: RNS interfaces report bitrate in bit/s. LoRa, packet radio and
    serial links fall under ~1 Mbit/s. If no interface reports a bitrate the
    link quality is unknown and we do not block.
    """
    rates = online_interface_bitrates(interfaces)
    if not rates:
        return False
    return min(rates) < threshold_kbps * 1000.0


def auto_download_allowed(
    settings: UpdateSettings, config=None, interfaces=None
) -> tuple[bool, str]:
    """Whether an automatic download may run now. Manual is always allowed.

    Automatic downloads are skipped on slow RNS links unless a clearnet
    transport is usable.
    """
    if not settings.auto_download:
        return False, "auto_download disabled"
    if settings.transport == "clearnet":
        return True, "clearnet transport"
    if settings.transport == "rns":
        if slow_rns_link(settings.slow_link_kbps, interfaces):
            return False, "slow RNS link"
        return True, "rns transport"
    # auto: clearnet is fine on any host link; rns-only path needs the guard
    if config is not None:
        try:
            from meshchatx.src.backend.privacy_mode import (
                ensure_outbound_http_allowed,
            )

            ensure_outbound_http_allowed(config, feature="update download")
            return True, "clearnet available"
        except Exception:
            pass
    if slow_rns_link(settings.slow_link_kbps, interfaces):
        return False, "slow RNS link and no clearnet"
    return True, "auto transport"


def jittered_interval_hours(hours: float, rng=None) -> float:
    """Interval with +-10% jitter so installs do not sync."""
    r = rng or random
    return hours * r.uniform(0.9, 1.1)


def app_version() -> str:
    try:
        from meshchatx.src.version import __version__

        return __version__
    except Exception:
        return "0.0.0"


def artifact_cap_bytes(settings: UpdateSettings) -> int:
    return settings.max_download_mb * 1024 * 1024


def pending_dir(storage_dir) -> Path:
    return Path(storage_dir) / PENDING_DIRNAME / "pending"


def pending_marker_path(storage_dir) -> Path:
    return Path(storage_dir) / PENDING_DIRNAME / PENDING_MARKER


def state_path(storage_dir) -> Path:
    return Path(storage_dir) / PENDING_DIRNAME / STATE_FILENAME


def manifest_store_dir(storage_dir) -> Path:
    return Path(storage_dir) / PENDING_DIRNAME / MANIFEST_STORE_DIRNAME


def seed_dir(storage_dir) -> Path:
    return Path(storage_dir) / PENDING_DIRNAME / SEED_DIRNAME


def updates_root(storage_dir) -> Path:
    return Path(storage_dir) / PENDING_DIRNAME


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write to temp file, fsync, rename. Used for all staged state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, obj) -> None:
    atomic_write_bytes(path, json.dumps(obj, indent=2, sort_keys=True).encode("utf-8"))


def read_json_file(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def current_artifact_path() -> str | None:
    """Best-effort path of the currently installed AppImage, if any."""
    appimage = os.environ.get("APPIMAGE")
    if appimage and os.path.isfile(appimage):
        return appimage
    return None


def disclosure_for(settings: UpdateSettings, channel: str) -> dict:
    """What the UI must show before the user enables updates."""
    if settings.custom_mirrors:
        mirrors = [
            {"name": "custom", "url": m["base"]} for m in settings.custom_mirrors
        ]
    else:
        mirrors = [{"name": m["name"], "url": m["base"]} for m in default_mirrors()]
    signers = pinned_signer_hashes(settings.signer_hashes)
    return {
        "mirrors": mirrors,
        "rns_destination": RNS_UPDATE_ASPECT,
        "signer_hashes": [h.hex() for h in signers],
        "channel": channel or settings.channel or "stable",
        "note": (
            "Updates are only installed after the signed manifest and "
            "artifact checksums verify. Mirrors and peers are untrusted "
            "transports."
        ),
    }


def channel_track(channel: str) -> str:
    return {"stable": "release", "beta": "beta", "testing": "testing"}.get(
        channel, channel
    )


def build_channel(build_meta: dict | None) -> str:
    """Resolve the update channel: stable/beta/testing from build metadata."""
    meta = build_meta or {}
    bc = str(meta.get("build_channel") or "").lower()
    if bc in CHANNELS:
        return bc
    if bc in ("nightly", "testing"):
        return "testing"
    if bc == "beta":
        return "beta"
    return "stable"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def env_mirrors_override():
    raw = (env_str("MESHCHATX_UPDATE_MIRRORS") or "").strip()
    if not raw:
        return None
    out = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        ok = validate_https_url(part)
        if ok:
            out.append({"name": "env", "kind": "static", "base": ok.rstrip("/")})
    return out or None


def env_rns_seeds() -> list:
    raw = (env_str("MESHCHATX_UPDATE_RNS_SEEDS") or "").strip()
    if not raw:
        return []
    out = []
    for part in raw.split(","):
        part = part.strip().lower()
        if _HEX32.match(part):
            out.append(part)
    return out[:MAX_RNS_SEEDS]
