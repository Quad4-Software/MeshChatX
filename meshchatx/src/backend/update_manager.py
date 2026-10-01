# SPDX-License-Identifier: 0BSD
"""Signed update manifest checking, download verification and staging.

Update flow:

  1. The release pipeline signs update.json into update.rsm (rnid-format
     RSG envelope) and uploads it to "<base>/<track>/latest.rsm" plus the
     per-tag directory on the CDN.
  2. UpdateManager.check fetches latest.rsm, verifies the embedded
     signature against a pinned release-identity hash, compares versions and
     returns the artifacts matching this platform/arch.
  3. UpdateManager.download streams a chosen artifact to a temp file
     and enforces sha256 + size from the signed manifest before staging.
  4. UpdateManager.verify_local_file does the same check for a file
     the user downloaded by hand ("manual update").
  5. UpdateManager.stage writes the payload into
     "<storage>/updates/pending/" with a pending.json marker. The platform
     front-end (Electron swap, package manager, APK intent) applies it.

The pinned signer is the trust anchor: TLS and the CDN only carry the bits.
A hostile or compromised CDN can withhold updates but cannot forge a
manifest without the release private key.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from packaging.version import InvalidVersion, Version

from meshchatx.src.env_utils import env_bool, env_str

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://cdn.quad4.io"
DEFAULT_SIGNER_HASH = "e46112d44649266d71fe2193e00a4710"
MANIFEST_NAME = "latest.rsm"
MANIFEST_MAX_BYTES = 256 * 1024
# Upper bound on a single artifact download. AppImage/whl are well under this.
ARTIFACT_MAX_BYTES = 2 * 1024 * 1024 * 1024
USER_AGENT = "MeshChatX-Updater/1"
PENDING_DIRNAME = "updates"
PENDING_MARKER = "pending.json"

_CHANNEL_TRACKS = {
    "stable": "release",
    "beta": "beta",
    "testing": "testing",
}

_KNOWN_PLATFORMS = ("linux", "windows", "macos", "android", "python")


class UpdateError(Exception):
    """Base error for update operations."""


class UpdateUnavailable(UpdateError):
    """No update channel, manifest missing, or nothing applicable."""


class UpdateVerifyError(UpdateError):
    """Signature, signer, or checksum verification failed."""


def _pinned_signer_hash() -> bytes:
    raw = (env_str("MESHCHATX_UPDATE_SIGNER") or "").strip()
    if raw:
        return bytes.fromhex(raw)
    return bytes.fromhex(DEFAULT_SIGNER_HASH)


def _base_url() -> str:
    raw = (env_str("MESHCHATX_UPDATE_BASE_URL") or DEFAULT_BASE_URL).strip()
    return raw.rstrip("/")


def updates_disabled() -> bool:
    return env_bool("MESHCHATX_UPDATE_DISABLED")


def normalize_arch(machine: str | None = None) -> str:
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
    """Return the manifest platform token for this install."""
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


def _version_newer(candidate: str, current: str) -> bool:
    try:
        return Version(candidate) > Version(current)
    except InvalidVersion:
        return False


def _version_allowed(candidate: str, minimum: str) -> bool:
    try:
        return Version(candidate) >= Version(minimum)
    except InvalidVersion:
        return False


def _safe_artifact_relpath(rel: str) -> str | None:
    """Reject manifest artifact paths that escape the tag directory."""
    if not rel or rel.startswith(("/", "\\")) or "://" in rel:
        return None
    parts = Path(rel).parts
    if any(p in ("", ".", "..") for p in parts):
        return None
    return rel


class UpdateManager:
    """Fetch, verify and stage signed updates for this install."""

    def __init__(
        self,
        storage_dir: str,
        *,
        current_version: str,
        channel: str,
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.current_version = current_version
        self.channel = channel
        self._manifest: dict | None = None
        self._manifest_fetched_at = 0.0

    # -- config -----------------------------------------------------------

    @property
    def track(self) -> str | None:
        return _CHANNEL_TRACKS.get(self.channel)

    @property
    def enabled(self) -> bool:
        return not updates_disabled() and self.track is not None

    @property
    def pending_dir(self) -> Path:
        return self.storage_dir / PENDING_DIRNAME / "pending"

    @property
    def pending_marker_path(self) -> Path:
        return self.storage_dir / PENDING_DIRNAME / PENDING_MARKER

    # -- manifest ---------------------------------------------------------

    def manifest_url(self) -> str:
        return f"{_base_url()}/{self.track}/{MANIFEST_NAME}"

    def _fetch_bytes(self, url: str, max_bytes: int, timeout: int = 20) -> bytes:
        if not url.startswith("https://"):
            raise UpdateError(f"update fetch requires https: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310 - https enforced above
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - https enforced above
                data = resp.read(max_bytes + 1)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise UpdateUnavailable(
                    "no update manifest published for this channel"
                ) from e
            raise UpdateError(f"manifest fetch failed: HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise UpdateUnavailable(f"update endpoint unreachable: {e.reason}") from e
        if len(data) > max_bytes:
            raise UpdateError("manifest exceeds size cap")
        return data

    async def fetch_manifest(self, *, force: bool = False) -> dict:
        import asyncio

        if (
            not force
            and self._manifest is not None
            and time.monotonic() - self._manifest_fetched_at < 300
        ):
            return self._manifest
        raw = await asyncio.to_thread(
            self._fetch_bytes, self.manifest_url(), MANIFEST_MAX_BYTES
        )
        manifest = await asyncio.to_thread(_verify_rsm, raw, _pinned_signer_hash())
        if manifest.get("track") != self.track:
            raise UpdateError("manifest track does not match this channel")
        tag = manifest.get("tag") or ""
        if not tag or "/" in tag or "\\" in tag or ".." in tag:
            raise UpdateError("manifest tag is not a safe path segment")
        self._manifest = manifest
        self._manifest_fetched_at = time.monotonic()
        return manifest

    # -- status / matching -------------------------------------------------

    def matching_artifacts(self, manifest: dict) -> list[dict]:
        plat = host_platform()
        arch = normalize_arch()
        out = []
        for art in manifest.get("artifacts") or []:
            if not isinstance(art, dict):
                continue
            aplat = art.get("platform")
            if aplat not in _KNOWN_PLATFORMS:
                continue
            if aplat != plat and not (aplat == "python" and plat != "android"):
                continue
            aarch = art.get("arch") or "any"
            if aarch != "any" and aarch != arch:
                continue
            if _safe_artifact_relpath(art.get("file") or "") is None:
                continue
            if not isinstance(art.get("sha256"), str) or len(art["sha256"]) != 64:
                continue
            if not isinstance(art.get("size"), int) or art["size"] <= 0:
                continue
            if art["size"] > ARTIFACT_MAX_BYTES:
                continue
            out.append(art)
        return out

    async def check(self) -> dict:
        result = {
            "enabled": self.enabled,
            "current_version": self.current_version,
            "channel": self.channel,
            "track": self.track,
            "platform": host_platform(),
            "arch": normalize_arch(),
            "update_available": False,
            "pending": self.pending(),
        }
        if not self.enabled:
            return result
        try:
            manifest = await self.fetch_manifest()
        except UpdateError as e:
            result["error"] = str(e)
            return result

        latest = manifest.get("version") or ""
        minimum = manifest.get("minimum_version") or "0.0.0"
        result["manifest"] = {
            "version": latest,
            "tag": manifest.get("tag"),
            "released_at": manifest.get("released_at"),
            "minimum_version": minimum,
        }
        if not _version_allowed(self.current_version, minimum):
            # This install is older than the manifest's minimum_version
            # floor and must update through an intermediate release first.
            result["error"] = (
                f"update {latest} requires version {minimum} or newer installed first"
            )
            return result
        if not _version_newer(latest, self.current_version):
            return result
        arts = self.matching_artifacts(manifest)
        result["update_available"] = bool(arts)
        result["artifacts"] = [
            {k: a[k] for k in ("file", "size", "kind", "platform", "arch")}
            for a in arts
        ]
        return result

    # -- download / verify -------------------------------------------------

    def artifact_url(self, manifest: dict, entry: dict) -> str:
        rel = _safe_artifact_relpath(entry["file"])
        if rel is None:
            raise UpdateError("unsafe artifact path in manifest")
        return f"{_base_url()}/{self.track}/{manifest['tag']}/{rel}"

    def _verify_file(self, path: Path, entry: dict) -> None:
        size = path.stat().st_size
        if size != entry["size"]:
            raise UpdateVerifyError(
                f"size mismatch: got {size}, expected {entry['size']}"
            )
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != entry["sha256"]:
            raise UpdateVerifyError("sha256 mismatch for downloaded artifact")

    async def download(self, manifest: dict, entry: dict) -> Path:
        import asyncio

        url = self.artifact_url(manifest, entry)
        if not url.startswith("https://"):
            raise UpdateError("update download requires https")

        def _dl() -> Path:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310 - https enforced above
            fd, tmp = tempfile.mkstemp(prefix="meshchatx-update-", suffix=".part")
            tmp_path = Path(tmp)
            try:
                with os.fdopen(fd, "wb") as out:
                    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - https enforced above
                        remaining = ARTIFACT_MAX_BYTES + 1
                        while True:
                            chunk = resp.read(min(1024 * 1024, remaining))
                            if not chunk:
                                break
                            out.write(chunk)
                            remaining -= len(chunk)
                            if remaining <= 0:
                                raise UpdateError("artifact exceeds size cap")
                self._verify_file(tmp_path, entry)
                return tmp_path
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise

        return await asyncio.to_thread(_dl)

    async def verify_local_file(self, path: str) -> dict:
        """Verify a user-supplied update file against the signed manifest.

        Returns {ok, entry, staged} where entry is the manifest artifact that
        matched. Raises UpdateError subclasses on failure.
        """
        import asyncio

        p = Path(path)
        if not p.is_file():
            raise UpdateError(f"no such file: {path}")
        manifest = await self.fetch_manifest()
        latest = manifest.get("version") or ""
        minimum = manifest.get("minimum_version") or "0.0.0"
        if not _version_allowed(self.current_version, minimum):
            raise UpdateError(
                f"update {latest} requires version {minimum} or newer installed first"
            )
        if not _version_newer(latest, self.current_version):
            raise UpdateUnavailable("manifest is not newer than this install")

        plat = host_platform()
        arch = normalize_arch()
        sha = await asyncio.to_thread(_sha256_file, p)
        size = p.stat().st_size
        for art in manifest.get("artifacts") or []:
            if (
                isinstance(art, dict)
                and art.get("sha256") == sha
                and art.get("size") == size
                and art.get("platform") == plat
                and (art.get("arch") in (None, "any", arch))
            ):
                return {"ok": True, "entry": art, "manifest": manifest}
        raise UpdateVerifyError(
            "file does not match any artifact in the signed manifest"
        )

    # -- staging ------------------------------------------------------------

    def stage(self, source: Path, entry: dict, manifest: dict) -> dict:
        """Move a verified artifact into updates/pending/ and write the marker."""
        self._verify_file(source, entry)
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        dest = self.pending_dir / Path(entry["file"]).name
        shutil.move(str(source), dest)
        marker = {
            "file": dest.name,
            "path": str(dest),
            "sha256": entry["sha256"],
            "size": entry["size"],
            "kind": entry["kind"],
            "platform": entry["platform"],
            "arch": entry["arch"],
            "version": manifest.get("version"),
            "tag": manifest.get("tag"),
            "staged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        tmp = self.pending_marker_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(marker, indent=2), encoding="utf-8")
        os.replace(tmp, self.pending_marker_path)
        return marker

    def pending(self) -> dict | None:
        try:
            return json.loads(self.pending_marker_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def pending_payload_path(self) -> Path | None:
        """Return the staged payload path if marker + file agree on sha256."""
        marker = self.pending()
        if not marker:
            return None
        dest = self.pending_dir / marker.get("file", "")
        if not dest.is_file():
            return None
        try:
            if _sha256_file(dest) != marker["sha256"]:
                return None
        except Exception:
            return None
        return dest

    def clear_pending(self) -> None:
        marker = self.pending()
        if marker:
            dest = self.pending_dir / marker.get("file", "")
            dest.unlink(missing_ok=True)
            self.pending_marker_path.unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_rsm(rsm: bytes, signer_hash: bytes) -> dict:
    from meshchatx.src.update_rsm import verify_rsm

    try:
        return verify_rsm(rsm, required_signer_hash=signer_hash)
    except ValueError as e:
        raise UpdateVerifyError(str(e)) from e
    except Exception as e:
        raise UpdateVerifyError(f"manifest verification failed: {e}") from e
