# SPDX-License-Identifier: 0BSD

"""Parse and validate NomadNet / RNGit map overlay source descriptors."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

import RNS

KIND_NOMADNET_FILE = "nomadnet_file"
KIND_RNGIT_FILES = "rngit_files"

_HASH_HEX_LEN = RNS.Reticulum.TRUNCATED_HASHLENGTH // 4
_HASH_RE = re.compile(rf"^[0-9a-fA-F]{{{_HASH_HEX_LEN}}}$")
_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_REF_RE = re.compile(r"^[A-Za-z0-9._/@+-]{1,256}$")
_COMMIT_LIKE_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


class OverlaySourceParseError(ValueError):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


@dataclass
class OverlaySourceSpec:
    kind: str
    destination_hash: str
    path_or_repo_path: str
    ref: str = "HEAD"
    group_name: str | None = None
    repository: str | None = None
    name: str | None = None
    paths: list[str] = field(default_factory=list)
    refresh_interval_seconds: int = 0

    def unique_key(self) -> tuple[str, str, str, str]:
        return (
            self.kind,
            self.destination_hash,
            self.path_or_repo_path,
            self.ref,
        )


def normalize_destination_hash_hex(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip().lower().replace(":", "")
    if not _HASH_RE.fullmatch(raw):
        return None
    try:
        bytes.fromhex(raw)
    except ValueError:
        return None
    return raw


def slug_segment(name: str) -> str | None:
    if not isinstance(name, str):
        return None
    s = name.strip()
    if not s or len(s) > 256 or not _SLUG_RE.fullmatch(s):
        return None
    return s


def normalize_ref(ref: str | None) -> str:
    if ref is None or str(ref).strip() == "":
        return "HEAD"
    s = str(ref).strip()
    if not _REF_RE.fullmatch(s):
        raise OverlaySourceParseError("invalid_ref")
    if ".." in s or s.startswith("-"):
        raise OverlaySourceParseError("invalid_ref")
    return s


def is_commit_like_ref(ref: str) -> bool:
    return bool(_COMMIT_LIKE_RE.fullmatch(ref))


def _safe_repo_relpath(path: str) -> str:
    if not isinstance(path, str):
        raise OverlaySourceParseError("invalid_path")
    p = path.strip().replace("\\", "/")
    if not p or p.startswith("/") or p.startswith("~"):
        raise OverlaySourceParseError("invalid_path")
    parts = [seg for seg in p.split("/") if seg and seg != "."]
    if not parts or any(seg == ".." for seg in parts):
        raise OverlaySourceParseError("path_traversal")
    joined = "/".join(parts)
    if len(joined) > 1024:
        raise OverlaySourceParseError("path_too_long")
    return joined


def _safe_nomadnet_file_path(path: str) -> str:
    if not isinstance(path, str):
        raise OverlaySourceParseError("invalid_path")
    p = path.strip().replace("\\", "/")
    if p.startswith("file/"):
        p = "/" + p
    if not p.startswith("/file/"):
        raise OverlaySourceParseError("not_file_path")
    rest = p[len("/file/") :]
    if not rest or rest.endswith("/"):
        raise OverlaySourceParseError("invalid_path")
    parts = [seg for seg in rest.split("/") if seg and seg != "."]
    if not parts or any(seg == ".." for seg in parts):
        raise OverlaySourceParseError("path_traversal")
    return "/file/" + "/".join(parts)


def _default_name_from_path(path: str) -> str:
    base = os.path.basename(path.rstrip("/"))
    return base or "overlay"


def parse_nomadnet_file_url(url: str) -> OverlaySourceSpec:
    if not isinstance(url, str) or not url.strip():
        raise OverlaySourceParseError("empty_url")
    raw = url.strip()
    for prefix in ("nomadnet://", "nomadnetwork://"):
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix) :]
            break
    if ":" in raw:
        hash_part, path_part = raw.split(":", 1)
    elif "/file/" in raw:
        idx = raw.lower().find("/file/")
        hash_part, path_part = raw[:idx], raw[idx:]
    else:
        raise OverlaySourceParseError("invalid_nomadnet_url")
    dest = normalize_destination_hash_hex(hash_part)
    if not dest:
        raise OverlaySourceParseError("invalid_destination_hash")
    file_path = _safe_nomadnet_file_path(path_part)
    return OverlaySourceSpec(
        kind=KIND_NOMADNET_FILE,
        destination_hash=dest,
        path_or_repo_path=file_path,
        ref="HEAD",
        name=_default_name_from_path(file_path),
        paths=[file_path],
    )


def parse_rngit_repo_url(url: str) -> tuple[str, str, str]:
    if not isinstance(url, str) or not url.strip():
        raise OverlaySourceParseError("empty_url")
    raw = url.strip()
    if raw.lower().startswith("rns://"):
        raw = raw[6:]
    parts = [p for p in raw.split("/") if p]
    if len(parts) < 3:
        raise OverlaySourceParseError("invalid_rngit_url")
    dest = normalize_destination_hash_hex(parts[0])
    if not dest:
        raise OverlaySourceParseError("invalid_destination_hash")
    group = slug_segment(parts[1])
    repo = slug_segment(parts[2])
    if not group or not repo:
        raise OverlaySourceParseError("invalid_repository")
    return dest, group, repo


def _clamp_refresh_interval(value: Any) -> int:
    try:
        refresh_i = int(value)
    except (TypeError, ValueError) as exc:
        raise OverlaySourceParseError("invalid_refresh_interval") from exc
    if refresh_i < 0:
        raise OverlaySourceParseError("invalid_refresh_interval")
    if 0 < refresh_i < 60:
        return 60
    if refresh_i > 86400:
        return 86400
    return refresh_i


def _looks_like_nomadnet(url: str) -> bool:
    u = url.strip().lower()
    return (
        u.startswith("nomadnet://")
        or u.startswith("nomadnetwork://")
        or ":/file/" in u
        or (len(u) > _HASH_HEX_LEN and "/file/" in u)
    )


def parse_create_payload(data: dict[str, Any]) -> list[OverlaySourceSpec]:
    """Parse POST /api/v1/map/overlays body into one or more source specs."""
    if not isinstance(data, dict):
        raise OverlaySourceParseError("invalid_body")

    kind = (data.get("kind") or "").strip().lower()
    url = str(data.get("url") or data.get("source") or "").strip()
    if not url:
        raise OverlaySourceParseError("empty_url")

    refresh_i = _clamp_refresh_interval(data.get("refresh_interval_seconds", 0))
    name_override = data.get("name")
    if name_override is not None:
        name_override = str(name_override).strip()[:200] or None

    use_nomadnet = kind in ("nomadnet", "nomadnet_file") or (
        kind in ("",)
        and _looks_like_nomadnet(url)
        and not url.lower().startswith("rns://")
    )
    use_rngit = kind in ("rngit", "rngit_files") or url.lower().startswith("rns://")

    if use_nomadnet and not use_rngit:
        spec = parse_nomadnet_file_url(url)
        if name_override:
            spec.name = name_override
        spec.refresh_interval_seconds = refresh_i
        return [spec]

    if use_rngit:
        dest, group, repo = parse_rngit_repo_url(url)
        ref = normalize_ref(data.get("ref"))
        paths_raw = data.get("paths") or data.get("files") or []
        if isinstance(paths_raw, str):
            paths_raw = [
                line.strip() for line in paths_raw.splitlines() if line.strip()
            ]
        if not isinstance(paths_raw, list) or not paths_raw:
            raise OverlaySourceParseError("missing_paths")
        if len(paths_raw) > 32:
            raise OverlaySourceParseError("too_many_paths")
        specs: list[OverlaySourceSpec] = []
        for raw_path in paths_raw:
            rel = _safe_repo_relpath(str(raw_path))
            lower = rel.lower()
            if not lower.endswith((".geojson", ".json", ".kml", ".kmz")):
                raise OverlaySourceParseError("unsupported_extension")
            nm = name_override or _default_name_from_path(rel)
            specs.append(
                OverlaySourceSpec(
                    kind=KIND_RNGIT_FILES,
                    destination_hash=dest,
                    path_or_repo_path=rel,
                    ref=ref,
                    group_name=group,
                    repository=repo,
                    name=nm,
                    paths=[rel],
                    refresh_interval_seconds=refresh_i,
                ),
            )
        return specs

    raise OverlaySourceParseError("unsupported_kind")


def guess_format_from_path(path: str) -> str | None:
    lower = path.lower()
    if lower.endswith(".kmz"):
        return "kmz"
    if lower.endswith(".kml"):
        return "kml"
    if lower.endswith(".geojson") or lower.endswith(".json"):
        return "geojson"
    return None
