# SPDX-License-Identifier: 0BSD

"""Publish and fetch map packs over aspect map-data-v1."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import stat
import threading
import uuid
from contextlib import suppress
from typing import Any

import RNS

from meshchatx.src.backend.map_geo_sanitizer import sanitize_geo_bytes
from meshchatx.src.backend.map_geo_validator import (
    GeoValidationError,
    validate_geo_bytes,
)
from meshchatx.src.backend.map_overlay_manager import (
    atomic_write_bytes,
    clamp_overlay_config_value,
    read_regular_file_bytes,
)
from meshchatx.src.backend.map_overlay_sources import (
    ALLOWED_OVERLAY_FORMATS,
    KIND_MAP_DATA,
)
from meshchatx.src.backend.path_utils import path_response_window
from meshchatx.src.path_utils import is_path_within_dir

_log = logging.getLogger("meshchatx.map_data")

MAP_ASPECT = "map-data-v1"
CATALOG_PATH = "/catalog"
MAP_PATH_PREFIX = "/map/"
MAP_ID_RE = re.compile(r"^[0-9a-f]{16}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DISPLAY_NAME_MAX = 32
DEFAULT_MAX_BYTES = 512 * 1024
MIN_ANNOUNCE_INTERVAL = 10
DEFAULT_ANNOUNCE_INTERVAL = 900
MAX_ANNOUNCE_INTERVAL = 86400
MAX_PUBLISHED_MAPS = 64
MAX_CATALOG_BYTES = 256 * 1024
MAX_COERCE_DEPTH = 2


class MapDataError(ValueError):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


def coerce_map_request_body(payload, *, _depth: int = 0) -> bytes:
    """Turn an RNS request receipt payload into raw bytes.

    Catalog handlers return bytes. A list of [bytes, metadata] is the file
    response shape, but RNS only treats index 0 as a file when it is a
    BufferedReader. Bytes in a list must be unwrapped here.
    """
    if _depth > MAX_COERCE_DEPTH:
        raise MapDataError("invalid_response")
    if payload is None:
        raise MapDataError("empty_response")
    if isinstance(payload, (bytes, bytearray, memoryview)):
        return bytes(payload)
    if isinstance(payload, str):
        return payload.encode("utf-8")
    reader = getattr(payload, "read", None)
    if callable(reader):
        return coerce_map_request_body(reader(), _depth=_depth + 1)
    if isinstance(payload, (list, tuple)) and payload:
        return coerce_map_request_body(payload[0], _depth=_depth + 1)
    raise MapDataError("invalid_response")


def parse_map_data_app_data(app_data) -> dict[str, Any]:
    if not app_data:
        return {"v": 1, "n": "", "c": 0}
    raw = app_data
    if isinstance(raw, str):
        raw = raw.encode("utf-8", errors="replace")
    try:
        obj = json.loads(bytes(raw).decode("utf-8"))
        if isinstance(obj, dict):
            name = str(obj.get("n") or "")[:DISPLAY_NAME_MAX]
            try:
                count = int(obj.get("c") or 0)
            except (TypeError, ValueError):
                count = 0
            return {"v": 1, "n": name, "c": max(0, count)}
    except Exception:
        pass
    name = bytes(raw).decode("utf-8", errors="replace")[:DISPLAY_NAME_MAX]
    return {"v": 1, "n": name, "c": 0}


def clamp_announce_interval(
    value: Any,
    default: int = DEFAULT_ANNOUNCE_INTERVAL,
) -> int:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return int(default)
    if seconds <= 0:
        return 0
    return max(MIN_ANNOUNCE_INTERVAL, min(MAX_ANNOUNCE_INTERVAL, seconds))


class MapDataManager:
    def __init__(
        self,
        config,
        database,
        storage_dir: str,
        identity,
        *,
        reticulum=None,
        link_manager_getter=None,
        overlay_manager_getter=None,
    ):
        self.config = config
        self.database = database
        self.storage_dir = storage_dir
        self.identity = identity
        self.reticulum = reticulum
        self._link_manager_getter = link_manager_getter
        self._overlay_manager_getter = overlay_manager_getter
        self._lock = threading.RLock()
        self._destination: RNS.Destination | None = None
        self._announce_timer = None
        self._registered_map_paths: set[str] = set()
        self._running = False

    def identity_hash(self) -> str:
        return self.identity.hash.hex()

    def data_root(self) -> str:
        path = os.path.join(self.storage_dir, "map_data")
        os.makedirs(path, exist_ok=True)
        return path

    def _cfg_max_bytes(self) -> int:
        overlay_max = clamp_overlay_config_value(
            "map_overlay_max_bytes",
            int(self.config.map_overlay_max_bytes.get() or (8 * 1024 * 1024)),
        )
        raw = getattr(self.config, "map_data_max_bytes", None)
        if raw is None:
            wanted = DEFAULT_MAX_BYTES
        else:
            try:
                wanted = int(raw.get())
            except (TypeError, ValueError):
                wanted = DEFAULT_MAX_BYTES
            if wanted <= 0:
                wanted = DEFAULT_MAX_BYTES
        return max(64 * 1024, min(overlay_max, wanted))

    def _cfg_timeout(self, key: str, default: int) -> int:
        raw = getattr(self.config, key, None)
        try:
            value = default if raw is None else int(raw.get() or default)
        except (TypeError, ValueError):
            value = default
        return clamp_overlay_config_value(key, value)

    def _resolve_published_file(self, map_id: str, rel: str | None) -> str | None:
        if not MAP_ID_RE.fullmatch(map_id or ""):
            return None
        base = os.path.basename(str(rel or "").replace("\\", "/"))
        if not base or "\x00" in base:
            return None
        name, ext = os.path.splitext(base)
        fmt = ext.lstrip(".").lower()
        if name != map_id or fmt not in ALLOWED_OVERLAY_FORMATS:
            return None
        root = self.data_root()
        abs_path = os.path.join(root, base)
        try:
            st = os.lstat(abs_path)
        except OSError:
            return None
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            return None
        if not is_path_within_dir(abs_path, root):
            return None
        return os.path.realpath(abs_path)

    def _display_name(self) -> str:
        raw = getattr(self.config, "map_data_display_name", None)
        name = ""
        if raw is not None:
            name = str(raw.get() or "").strip()
        if not name:
            name = "Maps"
        return name[:DISPLAY_NAME_MAX]

    def _announce_enabled(self) -> bool:
        raw = getattr(self.config, "map_data_announce_enabled", None)
        if raw is None:
            return False
        return bool(raw.get())

    def _published_count(self) -> int:
        return int(
            self.database.map_published.count_for_identity(self.identity_hash()) or 0,
        )

    def _should_announce(self) -> bool:
        return self._announce_enabled() and self._published_count() > 0

    def _is_local_hash(self, dest: bytes) -> bool:
        current = self._destination
        return current is not None and current.hash == dest

    def _announce_interval(self) -> int:
        raw = getattr(self.config, "map_data_announce_interval", None)
        value = DEFAULT_ANNOUNCE_INTERVAL if raw is None else raw.get()
        return clamp_announce_interval(value)

    def status(self) -> dict[str, Any]:
        dest = self._destination
        return {
            "aspect": MAP_ASPECT,
            "running": self._running and dest is not None,
            "destination_hash": dest.hash.hex() if dest is not None else None,
            "display_name": self._display_name(),
            "announce_enabled": self._announce_enabled(),
            "announce_interval": self._announce_interval(),
            "max_bytes": self._cfg_max_bytes(),
            "published_count": self._published_count(),
        }

    def start(self) -> dict[str, Any]:
        with self._lock:
            self._running = True
            if self._published_count() > 0:
                self._ensure_destination_locked()
                if self._should_announce():
                    self._announce_locked()
            self._sync_announce_timer()
            return self.status()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._teardown_destination_locked()

    def _ensure_destination_locked(self) -> None:
        if self._destination is not None:
            self._register_all_handlers()
            return
        app_name, aspects = RNS.Destination.app_and_aspects_from_name(MAP_ASPECT)
        destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            app_name,
            *aspects,
        )
        destination.set_link_established_callback(self._on_link)
        self._destination = destination
        self._register_all_handlers()

    def _teardown_destination_locked(self) -> None:
        self._cancel_announce_timer()
        dest = self._destination
        self._destination = None
        if dest is None:
            return
        for path in list(self._registered_map_paths):
            with suppress(Exception):
                dest.deregister_request_handler(path)
        self._registered_map_paths.clear()
        with suppress(Exception):
            dest.deregister_request_handler(CATALOG_PATH)
        with suppress(Exception):
            RNS.Transport.deregister_destination(dest)

    def _on_link(self, _link) -> None:
        return

    def _register_all_handlers(self) -> None:
        dest = self._destination
        if dest is None:
            return
        dest.register_request_handler(
            CATALOG_PATH,
            response_generator=self._catalog_responder,
            allow=RNS.Destination.ALLOW_ALL,
        )
        for row in self.database.map_published.list_for_identity(self.identity_hash()):
            self._register_map_handler(str(row["map_id"]))

    def _register_map_handler(self, map_id: str) -> None:
        dest = self._destination
        if dest is None or not MAP_ID_RE.fullmatch(map_id):
            return
        path = MAP_PATH_PREFIX + map_id
        if path in self._registered_map_paths:
            return
        dest.register_request_handler(
            path,
            response_generator=self._make_map_responder(map_id),
            allow=RNS.Destination.ALLOW_ALL,
        )
        self._registered_map_paths.add(path)

    def _deregister_map_handler(self, map_id: str) -> None:
        dest = self._destination
        path = MAP_PATH_PREFIX + map_id
        if dest is None or path not in self._registered_map_paths:
            return
        with suppress(Exception):
            dest.deregister_request_handler(path)
        self._registered_map_paths.discard(path)

    def _catalog_payload(self) -> dict[str, Any]:
        maps = []
        for row in self.database.map_published.list_for_identity(self.identity_hash()):
            maps.append(
                {
                    "id": row["map_id"],
                    "name": row["name"],
                    "format": row["format"],
                    "size": int(row["size"] or 0),
                    "sha256": row["sha256"],
                    "bbox": _parse_bbox(row["bbox"]),
                    "feature_count": int(row["feature_count"] or 0),
                    "updated_at": row["updated_at"],
                },
            )
        return {"maps": maps}

    def _catalog_responder(
        self,
        path,
        data,
        request_id,
        link_id,
        remote_identity,
        requested_at,
    ):
        body = json.dumps(self._catalog_payload(), separators=(",", ":")).encode(
            "utf-8",
        )
        return body

    def _make_map_responder(self, map_id: str):
        def responder(path, data, request_id, link_id, remote_identity, requested_at):
            row = self.database.map_published.get_by_map_id(
                self.identity_hash(),
                map_id,
            )
            if not row:
                return None
            abs_path = self._resolve_published_file(map_id, row["path"])
            if not abs_path:
                return None
            max_bytes = self._cfg_max_bytes()
            try:
                body = read_regular_file_bytes(abs_path, max_bytes=max_bytes)
            except OSError:
                return None
            expected = str(row["sha256"] or "").lower()
            if expected and hashlib.sha256(body).hexdigest() != expected:
                return None
            name = (row["name"] or map_id) + "." + (row["format"] or "bin")
            return [body, {"name": name.encode("utf-8")}]

        return responder

    def list_published(self) -> list[dict[str, Any]]:
        rows = self.database.map_published.list_for_identity(self.identity_hash())
        out = []
        for row in rows:
            item = (
                dict(row)
                if not hasattr(row, "keys")
                else {k: row[k] for k in row.keys()}
            )
            item["bbox"] = _parse_bbox(item.get("bbox"))
            out.append(item)
        return out

    def publish_bytes(
        self,
        payload: bytes,
        *,
        name: str,
        hinted_format: str | None = None,
    ) -> dict[str, Any]:
        max_bytes = self._cfg_max_bytes()
        if len(payload) > max_bytes:
            raise MapDataError("file_too_large")
        if self._published_count() >= MAX_PUBLISHED_MAPS:
            raise MapDataError("max_published_exceeded")
        sanitized = sanitize_geo_bytes(payload, hinted_format=hinted_format)
        limits = {
            "max_bytes": max_bytes,
            "max_features": int(self.config.map_overlay_max_features.get() or 50_000),
            "max_kmz": int(
                self.config.map_overlay_max_kmz_uncompressed_bytes.get()
                or (16 * 1024 * 1024),
            ),
        }
        validated = validate_geo_bytes(
            sanitized.data,
            hinted_format=sanitized.format,
            max_bytes=limits["max_bytes"],
            max_features=limits["max_features"],
            max_kmz_uncompressed_bytes=limits["max_kmz"],
        )
        map_id = uuid.uuid4().hex[:16]
        ext = validated.format
        rel = f"{map_id}.{ext}"
        abs_path = os.path.join(self.data_root(), rel)
        atomic_write_bytes(abs_path, sanitized.data)
        digest = hashlib.sha256(sanitized.data).hexdigest()
        display = str(name or "map").strip()[:200] or "map"
        self.database.map_published.insert(
            self.identity_hash(),
            map_id=map_id,
            name=display,
            format=validated.format,
            size=len(sanitized.data),
            sha256=digest,
            bbox=None,
            feature_count=validated.feature_count,
            path=rel,
        )
        with self._lock:
            if self._running:
                self._ensure_destination_locked()
                self._register_map_handler(map_id)
                if self._should_announce():
                    self._announce_locked()
        return {
            "map": self._row_or_raise(map_id),
            "stripped": sanitized.stripped,
        }

    def unpublish(self, map_id: str) -> bool:
        if not MAP_ID_RE.fullmatch(map_id or ""):
            raise MapDataError("invalid_map_id")
        row = self.database.map_published.get_by_map_id(self.identity_hash(), map_id)
        if not row:
            return False
        rel = os.path.basename(row["path"] or "")
        abs_path = self._resolve_published_file(map_id, rel)
        if abs_path:
            with suppress(Exception):
                os.remove(abs_path)
        self.database.map_published.delete(self.identity_hash(), map_id)
        with self._lock:
            self._deregister_map_handler(map_id)
            if self._published_count() <= 0:
                self._teardown_destination_locked()
            elif self._should_announce():
                self._announce_locked()
        return True

    def _row_or_raise(self, map_id: str) -> dict[str, Any]:
        row = self.database.map_published.get_by_map_id(self.identity_hash(), map_id)
        if not row:
            raise MapDataError("not_found")
        item = {k: row[k] for k in row.keys()}
        item["bbox"] = _parse_bbox(item.get("bbox"))
        return item

    def announce(self) -> dict[str, Any]:
        with self._lock:
            if not self._running:
                raise MapDataError("not_running")
            if self._published_count() <= 0:
                raise MapDataError("nothing_published")
            self._ensure_destination_locked()
            self._announce_locked()
            return self.status()

    def _announce_locked(self) -> None:
        dest = self._destination
        if dest is None:
            raise MapDataError("not_running")
        count = self._published_count()
        app_data = json.dumps(
            {"v": 1, "n": self._display_name(), "c": count},
            separators=(",", ":"),
        ).encode("utf-8")
        dest.announce(app_data=app_data)

    def update_settings(
        self,
        *,
        display_name: str | None = None,
        announce_enabled: bool | None = None,
        announce_interval: int | None = None,
    ) -> dict[str, Any]:
        if display_name is not None:
            self.config.map_data_display_name.set(
                str(display_name).strip()[:DISPLAY_NAME_MAX],
            )
        if announce_enabled is not None:
            self.config.map_data_announce_enabled.set(bool(announce_enabled))
        if announce_interval is not None:
            self.config.map_data_announce_interval.set(
                clamp_announce_interval(announce_interval),
            )
        with self._lock:
            self._sync_announce_timer()
            if self._should_announce():
                self._ensure_destination_locked()
                self._announce_locked()
        return self.status()

    def _cancel_announce_timer(self) -> None:
        timer = self._announce_timer
        self._announce_timer = None
        if timer is not None:
            with suppress(Exception):
                timer.cancel()

    def _sync_announce_timer(self) -> None:
        self._cancel_announce_timer()
        if not self._running or not self._should_announce():
            return
        interval = self._announce_interval()
        if interval <= 0:
            return
        timer = threading.Timer(interval, self._announce_timer_fire)
        timer.daemon = True
        self._announce_timer = timer
        timer.start()

    def _announce_timer_fire(self) -> None:
        try:
            with self._lock:
                if self._running and self._should_announce():
                    self._announce_locked()
        except Exception:
            _log.exception("map-data-v1 periodic announce failed")
        with self._lock:
            self._sync_announce_timer()

    def list_heard(
        self,
        *,
        query: str | None = None,
        limit: int = 250,
    ) -> list[dict[str, Any]]:
        from meshchatx.src.backend.announce_manager import AnnounceManager

        mgr = AnnounceManager(self.database, self.config)
        rows = mgr.get_filtered_announces(aspect=MAP_ASPECT, query=query, limit=limit)
        out = []
        q = (query or "").strip().lower()
        for row in rows:
            item = (
                dict(row)
                if not hasattr(row, "keys")
                else {k: row[k] for k in row.keys()}
            )
            parsed = {"v": 1, "n": "", "c": 0}
            app_data = item.get("app_data")
            if app_data:
                try:
                    import base64

                    raw = base64.b64decode(app_data)
                    parsed = parse_map_data_app_data(raw)
                except Exception:
                    parsed = parse_map_data_app_data(app_data)
            item["map_name"] = parsed.get("n") or ""
            item["map_count"] = parsed.get("c") or 0
            if q:
                blob = (
                    f"{item.get('destination_hash') or ''} {item['map_name']}".lower()
                )
                if q not in blob:
                    continue
            out.append(item)
        return out

    def _parse_catalog_body(self, body: bytes, dest_hex: str) -> dict[str, Any]:
        if not isinstance(body, (bytes, bytearray)) or len(body) > MAX_CATALOG_BYTES:
            raise MapDataError("invalid_catalog")
        try:
            obj = json.loads(bytes(body).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MapDataError("invalid_catalog") from exc
        if not isinstance(obj, dict) or not isinstance(obj.get("maps"), list):
            raise MapDataError("invalid_catalog")
        maps = []
        for entry in obj["maps"][:MAX_PUBLISHED_MAPS]:
            if not isinstance(entry, dict):
                continue
            map_id = str(entry.get("id") or "")
            if not MAP_ID_RE.fullmatch(map_id):
                continue
            fmt = str(entry.get("format") or "").strip().lower()[:16]
            if fmt == "json":
                fmt = "geojson"
            if fmt and fmt not in ALLOWED_OVERLAY_FORMATS:
                continue
            sha = str(entry.get("sha256") or "").strip().lower()
            if sha and not _SHA256_RE.fullmatch(sha):
                sha = ""
            try:
                size = int(entry.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            if size < 0 or size > self._cfg_max_bytes():
                size = 0
            try:
                feature_count = int(entry.get("feature_count") or 0)
            except (TypeError, ValueError):
                feature_count = 0
            maps.append(
                {
                    "id": map_id,
                    "name": str(entry.get("name") or map_id)[:200],
                    "format": fmt,
                    "size": size,
                    "sha256": sha,
                    "bbox": entry.get("bbox"),
                    "feature_count": max(0, feature_count),
                    "updated_at": str(entry.get("updated_at") or "")[:64],
                },
            )
        return {"destination_hash": dest_hex, "maps": maps}

    def _read_local_map_bytes(self, map_id: str) -> bytes:
        row = self.database.map_published.get_by_map_id(self.identity_hash(), map_id)
        if not row:
            raise MapDataError("not_found")
        abs_path = self._resolve_published_file(map_id, row["path"])
        if not abs_path:
            raise MapDataError("not_found")
        max_bytes = self._cfg_max_bytes()
        try:
            body = read_regular_file_bytes(abs_path, max_bytes=max_bytes)
        except OSError as exc:
            raise MapDataError("not_found") from exc
        expected = str(row["sha256"] or "").lower()
        if expected and hashlib.sha256(body).hexdigest() != expected:
            raise MapDataError("sha256_mismatch")
        return body

    async def fetch_catalog(self, destination_hash: str) -> dict[str, Any]:
        dest = _require_dest_hash(destination_hash)
        if self._is_local_hash(dest):
            body = json.dumps(self._catalog_payload(), separators=(",", ":")).encode(
                "utf-8",
            )
            return self._parse_catalog_body(body, dest.hex())
        body = await self._link_request(dest, CATALOG_PATH)
        return self._parse_catalog_body(body, dest.hex())

    async def fetch_map_bytes(
        self,
        destination_hash: str,
        map_id: str,
        *,
        expected_sha256: str | None = None,
        hinted_format: str | None = None,
    ) -> bytes:
        if not MAP_ID_RE.fullmatch(map_id or ""):
            raise MapDataError("invalid_map_id")
        dest = _require_dest_hash(destination_hash)
        if self._is_local_hash(dest):
            body = self._read_local_map_bytes(map_id)
        else:
            body = await self._link_request(dest, MAP_PATH_PREFIX + map_id)
        max_bytes = self._cfg_max_bytes()
        if len(body) > max_bytes:
            raise MapDataError("file_too_large")
        want = str(expected_sha256 or "").strip().lower()
        if want:
            if not _SHA256_RE.fullmatch(want):
                raise MapDataError("sha256_mismatch")
            if hashlib.sha256(body).hexdigest() != want:
                raise MapDataError("sha256_mismatch")
        try:
            sanitized = sanitize_geo_bytes(body, hinted_format=hinted_format)
            validate_geo_bytes(
                sanitized.data,
                hinted_format=sanitized.format,
                max_bytes=max_bytes,
                max_features=int(self.config.map_overlay_max_features.get() or 50_000),
                max_kmz_uncompressed_bytes=int(
                    self.config.map_overlay_max_kmz_uncompressed_bytes.get()
                    or (16 * 1024 * 1024),
                ),
            )
        except GeoValidationError as exc:
            raise MapDataError(exc.code) from exc
        return sanitized.data

    async def add_as_overlay(
        self,
        destination_hash: str,
        map_id: str,
    ) -> dict[str, Any]:
        getter = self._overlay_manager_getter
        overlay_manager = getter() if getter else None
        if overlay_manager is None:
            raise MapDataError("overlay_unavailable")
        dest = _require_dest_hash(destination_hash)
        catalog = await self.fetch_catalog(destination_hash)
        name = map_id
        hinted = None
        expected_sha = None
        for entry in catalog.get("maps") or []:
            if entry.get("id") == map_id:
                name = entry.get("name") or map_id
                hinted = entry.get("format") or None
                expected_sha = entry.get("sha256") or None
                break
        else:
            raise MapDataError("not_found")
        payload = await self.fetch_map_bytes(
            destination_hash,
            map_id,
            expected_sha256=expected_sha,
            hinted_format=hinted,
        )
        return await overlay_manager.ingest_local_overlay(
            self.identity_hash(),
            kind=KIND_MAP_DATA,
            destination_hash=dest.hex(),
            path_or_repo_path=map_id,
            name=name,
            payload=payload,
            hinted_format=hinted,
        )

    async def _link_request(self, destination_hash: bytes, path: str) -> bytes:
        getter = self._link_manager_getter
        link_manager = getter() if getter else None
        if link_manager is None:
            raise MapDataError("link_unavailable")
        path_timeout = self._cfg_timeout("map_overlay_path_timeout_seconds", 30)
        try:
            path_timeout = max(
                float(path_timeout),
                path_response_window(destination_hash, self.reticulum),
            )
        except Exception:
            path_timeout = float(path_timeout)
        transfer_timeout = self._cfg_timeout(
            "map_overlay_transfer_timeout_seconds",
            120,
        )
        job_timeout = self._cfg_timeout("map_overlay_job_timeout_seconds", 300)
        link, _identified, failure = await link_manager.open_link(
            destination_hash,
            MAP_ASPECT,
            path_lookup_timeout=float(path_timeout),
        )
        if link is None:
            code = (
                "missing_path" if failure and "path" in str(failure) else "link_failed"
            )
            raise MapDataError(code, failure)

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        def on_response(receipt):
            try:
                body = coerce_map_request_body(getattr(receipt, "response", None))
            except MapDataError as exc:
                loop.call_soon_threadsafe(_fail_future, future, exc)
                return
            except Exception:
                loop.call_soon_threadsafe(
                    _fail_future,
                    future,
                    MapDataError("invalid_response"),
                )
                return
            loop.call_soon_threadsafe(_resolve_future, future, body)

        def on_failed(_receipt=None):
            loop.call_soon_threadsafe(
                _fail_future,
                future,
                MapDataError("request_failed"),
            )

        try:
            link_manager.request(
                destination_hash,
                MAP_ASPECT,
                path,
                None,
                on_response,
                on_failed,
                lambda _r: None,
                timeout=float(transfer_timeout),
            )
        except RuntimeError as exc:
            raise MapDataError("no_active_link") from exc
        try:
            return await asyncio.wait_for(future, timeout=float(job_timeout))
        except TimeoutError as exc:
            raise MapDataError("job_timeout") from exc


def _resolve_future(future: asyncio.Future, value) -> None:
    if not future.done():
        future.set_result(value)


def _fail_future(future: asyncio.Future, exc: BaseException) -> None:
    if not future.done():
        future.set_exception(exc)


def _require_dest_hash(value: str) -> bytes:
    raw = str(value or "").strip().lower().replace(":", "")
    if len(raw) != 32:
        raise MapDataError("invalid_destination_hash")
    try:
        return bytes.fromhex(raw)
    except ValueError as exc:
        raise MapDataError("invalid_destination_hash") from exc


def _parse_bbox(value):
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    try:
        obj = json.loads(value)
        if isinstance(obj, list):
            return obj
    except Exception:
        return None
