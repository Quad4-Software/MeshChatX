# SPDX-License-Identifier: 0BSD

"""Manage remote map overlay sources: fetch, cache, refresh, export."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import random
import re
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from meshchatx.src.backend.map_geo_validator import (
    GeoValidationError,
    validate_geo_bytes,
)
from meshchatx.src.backend.map_geo_sanitizer import sanitize_geo_bytes
from meshchatx.src.backend.map_overlay_export import (
    CONTENT_TYPES,
    EXTENSIONS,
    OverlayExportError,
    convert_overlay_bytes,
    from_geojson,
    merge_geojson_bytes,
    to_geojson,
)
from meshchatx.src.backend.map_overlay_sources import (
    KIND_NOMADNET_FILE,
    KIND_RNGIT_FILES,
    OverlaySourceParseError,
    OverlaySourceSpec,
    guess_format_from_path,
    parse_create_payload,
)
from meshchatx.src.backend.nomadnet_downloader import NomadnetFileDownloader
from meshchatx.src.backend.rngit_sparse_fetcher import (
    RngitFetchError,
    RngitSparseFetcher,
)
from meshchatx.src.path_utils import is_path_within_dir

_log = logging.getLogger("meshchatx.map_overlays")

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

CONFIG_CLAMPS = {
    "map_overlay_max_bytes": (64 * 1024, 64 * 1024 * 1024),
    "map_overlay_max_features": (100, 500_000),
    "map_overlay_max_kmz_uncompressed_bytes": (256 * 1024, 128 * 1024 * 1024),
    "map_overlay_max_sources": (1, 256),
    "map_overlay_max_concurrent_jobs": (1, 8),
    "map_overlay_path_timeout_seconds": (5, 300),
    "map_overlay_transfer_timeout_seconds": (15, 600),
    "map_overlay_job_timeout_seconds": (30, 1800),
    "map_overlay_max_retries": (0, 10),
    "map_overlay_retry_delay_seconds": (1, 120),
}


def clamp_overlay_config_value(key: str, value: int) -> int:
    lo, hi = CONFIG_CLAMPS[key]
    return max(lo, min(hi, int(value)))


def atomic_write_bytes(path: str, data: bytes) -> None:
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _safe_filename(name: str, ext: str) -> str:
    base = _SAFE_NAME_RE.sub("_", (name or "overlay").strip())[:80] or "overlay"
    if not ext.startswith("."):
        ext = "." + ext
    return base + ext


def _row_to_dict(row) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    return dict(row)


class MapOverlayManager:
    def __init__(
        self,
        config,
        database,
        storage_dir: str,
        *,
        reticulum_config_dir: str | None = None,
        identity=None,
        reticulum=None,
        file_downloader_factory=None,
        rngit_fetcher_factory=None,
    ):
        self.config = config
        self.database = database
        self.storage_dir = storage_dir
        self.reticulum_config_dir = reticulum_config_dir
        self.identity = identity
        self.reticulum = reticulum
        self._file_downloader_factory = (
            file_downloader_factory or self._default_file_downloader_factory
        )
        self._rngit_fetcher_factory = (
            rngit_fetcher_factory or self._default_rngit_fetcher_factory
        )

        self._jobs: dict[str, dict[str, Any]] = {}
        self._source_locks: dict[int, asyncio.Lock] = {}
        self._active_fetchers: dict[str, Any] = {}
        self._job_semaphore: asyncio.Semaphore | None = None
        self._scheduler_task: asyncio.Task | None = None
        self._stopped = False

    def overlay_root(self) -> str:
        path = os.path.join(self.storage_dir, "map_overlays")
        os.makedirs(path, exist_ok=True)
        return path

    def work_root(self) -> str:
        path = os.path.join(self.overlay_root(), ".work")
        os.makedirs(path, exist_ok=True)
        return path

    def cache_path_for(
        self,
        identity_hash: str,
        overlay_id: int,
        fmt: str,
    ) -> tuple[str, str]:
        rel = os.path.join(identity_hash, f"{overlay_id}.{fmt}")
        return os.path.join(self.overlay_root(), rel), rel

    def _cache_abs_under_root(self, rel: str) -> str | None:
        if not isinstance(rel, str) or not rel or "\x00" in rel:
            return None
        root = self.overlay_root()
        abs_path = os.path.join(root, rel)
        if not is_path_within_dir(abs_path, root):
            return None
        return os.path.realpath(abs_path)

    def _cfg_int(self, key: str) -> int:
        conf = getattr(self.config, key)
        raw = conf.get()
        return clamp_overlay_config_value(key, int(raw))

    def limits(self) -> dict[str, int]:
        return {k: self._cfg_int(k) for k in CONFIG_CLAMPS}

    def _source_lock(self, overlay_id: int) -> asyncio.Lock:
        lock = self._source_locks.get(overlay_id)
        if lock is None:
            lock = asyncio.Lock()
            self._source_locks[overlay_id] = lock
        return lock

    def _default_file_downloader_factory(self, **kwargs):
        return NomadnetFileDownloader(**kwargs)

    def _default_rngit_fetcher_factory(self, **kwargs):
        return RngitSparseFetcher(**kwargs)

    def start_scheduler(self) -> None:
        if self._scheduler_task is not None:
            return
        self._stopped = False
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._scheduler_task = loop.create_task(self._autorefresh_loop())

    def stop_scheduler(self) -> None:
        self._stopped = True
        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            self._scheduler_task = None
        for fetcher in list(self._active_fetchers.values()):
            try:
                fetcher.cancel()
            except Exception:
                pass

    async def _autorefresh_loop(self) -> None:
        while not self._stopped:
            try:
                await self._tick_autorefresh()
            except asyncio.CancelledError:
                raise
            except Exception:
                _log.exception("map overlay autorefresh tick failed")
            await asyncio.sleep(15)

    async def _tick_autorefresh(self) -> None:
        now = datetime.now(UTC).isoformat()
        rows = self.database.map_overlays.list_due_autorefresh(now)
        for row in rows:
            overlay_id = int(row["id"])
            identity_hash = row["identity_hash"]
            if self._source_lock(overlay_id).locked():
                continue
            try:
                await self.refresh_overlay(
                    identity_hash,
                    overlay_id,
                    reason="autorefresh",
                )
            except Exception:
                _log.exception("autorefresh failed for overlay %s", overlay_id)

    def list_overlays(self, identity_hash: str) -> list[dict[str, Any]]:
        rows = self.database.map_overlays.list_for_identity(identity_hash)
        return [_row_to_dict(r) for r in rows]

    def get_overlay(self, identity_hash: str, overlay_id: int) -> dict[str, Any] | None:
        row = self.database.map_overlays.get_by_id(overlay_id)
        if not row or row["identity_hash"] != identity_hash:
            return None
        return _row_to_dict(row)

    def get_job(
        self, job_id: str, identity_hash: str | None = None
    ) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if identity_hash is not None and job.get("identity_hash") != identity_hash:
            return None
        return job

    async def create_overlays(
        self,
        identity_hash: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        specs = parse_create_payload(payload)
        max_sources = self._cfg_int("map_overlay_max_sources")
        current = self.database.map_overlays.count_for_identity(identity_hash)
        if current + len(specs) > max_sources:
            raise OverlaySourceParseError("max_sources_exceeded")

        created_ids: list[int] = []
        for spec in specs:
            existing = self.database.map_overlays.get_by_unique(
                identity_hash,
                spec.kind,
                spec.destination_hash,
                spec.path_or_repo_path,
                spec.ref,
            )
            if existing:
                created_ids.append(int(existing["id"]))
                continue
            oid = self.database.map_overlays.insert(
                identity_hash,
                kind=spec.kind,
                destination_hash=spec.destination_hash,
                path_or_repo_path=spec.path_or_repo_path,
                ref=spec.ref,
                name=spec.name or "overlay",
                group_name=spec.group_name,
                repository=spec.repository,
                refresh_interval_seconds=spec.refresh_interval_seconds,
                status="pending",
            )
            created_ids.append(oid)

        job_id = await self._start_job_for_ids(identity_hash, created_ids, specs)
        overlays = [self.get_overlay(identity_hash, i) for i in created_ids]
        return {"job_id": job_id, "overlays": overlays}

    async def ingest_local_overlay(
        self,
        identity_hash: str,
        *,
        kind: str,
        destination_hash: str,
        path_or_repo_path: str,
        name: str,
        payload: bytes,
        hinted_format: str | None = None,
        ref: str = "HEAD",
    ) -> dict[str, Any]:
        max_sources = self._cfg_int("map_overlay_max_sources")
        existing = self.database.map_overlays.get_by_unique(
            identity_hash,
            kind,
            destination_hash,
            path_or_repo_path,
            ref,
        )
        if existing:
            oid = int(existing["id"])
        else:
            current = self.database.map_overlays.count_for_identity(identity_hash)
            if current + 1 > max_sources:
                raise OverlaySourceParseError("max_sources_exceeded")
            oid = self.database.map_overlays.insert(
                identity_hash,
                kind=kind,
                destination_hash=destination_hash,
                path_or_repo_path=path_or_repo_path,
                ref=ref,
                name=name or "overlay",
                status="pending",
            )
        row = self.database.map_overlays.get_by_id(oid)
        gen = int(row["generation"] or 0) + 1 if row else 1
        self.database.map_overlays.update_fields(
            oid,
            status="fetching",
            last_error=None,
            generation=gen,
        )
        job_id = "local-" + uuid.uuid4().hex[:12]
        self._jobs[job_id] = {
            "job_id": job_id,
            "identity_hash": identity_hash,
            "overlay_ids": [oid],
            "status": "running",
            "phase": "validating",
            "progress": 0.0,
            "error": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
        try:
            await self._commit_bytes(
                job_id,
                identity_hash,
                oid,
                gen,
                payload,
                hinted_format=hinted_format,
                resolved_ref=ref,
                refresh_interval=0,
            )
            self._jobs[job_id]["status"] = "success"
            self._jobs[job_id]["phase"] = "done"
            self._jobs[job_id]["progress"] = 1.0
        except Exception as exc:
            code = getattr(exc, "code", str(exc))
            self._jobs[job_id]["status"] = "error"
            self._jobs[job_id]["error"] = code
            self._mark_error(oid, code)
            raise
        return {
            "job_id": job_id,
            "overlay": self.get_overlay(identity_hash, oid),
        }

    async def refresh_overlay(
        self,
        identity_hash: str,
        overlay_id: int,
        *,
        reason: str = "manual",
    ) -> dict[str, Any]:
        row = self.get_overlay(identity_hash, overlay_id)
        if not row:
            raise OverlaySourceParseError("not_found")
        spec = OverlaySourceSpec(
            kind=row["kind"],
            destination_hash=row["destination_hash"],
            path_or_repo_path=row["path_or_repo_path"],
            ref=row.get("ref") or "HEAD",
            group_name=row.get("group_name"),
            repository=row.get("repository"),
            name=row.get("name"),
            paths=[row["path_or_repo_path"]],
            refresh_interval_seconds=int(row.get("refresh_interval_seconds") or 0),
        )
        job_id = await self._start_job_for_ids(identity_hash, [overlay_id], [spec])
        return {
            "job_id": job_id,
            "overlay": self.get_overlay(identity_hash, overlay_id),
            "reason": reason,
        }

    async def _start_job_for_ids(
        self,
        identity_hash: str,
        overlay_ids: list[int],
        specs: list[OverlaySourceSpec],
    ) -> str:
        job_id = uuid.uuid4().hex
        generations: dict[int, int] = {}
        for oid in overlay_ids:
            row = self.database.map_overlays.get_by_id(oid)
            gen = int(row["generation"] or 0) + 1 if row else 1
            generations[oid] = gen
            self.database.map_overlays.update_fields(
                oid,
                status="fetching",
                last_error=None,
                job_id=job_id,
                generation=gen,
            )

        self._jobs[job_id] = {
            "job_id": job_id,
            "identity_hash": identity_hash,
            "overlay_ids": list(overlay_ids),
            "status": "running",
            "phase": "queued",
            "progress": 0.0,
            "error": None,
            "created_at": datetime.now(UTC).isoformat(),
        }

        async def runner():
            try:
                await self._run_job(
                    job_id,
                    identity_hash,
                    overlay_ids,
                    specs,
                    generations,
                )
            except Exception as exc:
                _log.exception("overlay job %s failed", job_id)
                self._jobs[job_id]["status"] = "error"
                self._jobs[job_id]["error"] = str(exc)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(runner())
        except RuntimeError:
            await runner()
        return job_id

    async def _run_job(
        self,
        job_id: str,
        identity_hash: str,
        overlay_ids: list[int],
        specs: list[OverlaySourceSpec],
        generations: dict[int, int],
    ) -> None:
        max_conc = self._cfg_int("map_overlay_max_concurrent_jobs")
        if self._job_semaphore is None:
            self._job_semaphore = asyncio.Semaphore(max_conc)
        # Resize not supported mid-flight. Create a new semaphore if limit changed and idle.
        async with self._job_semaphore:
            job = self._jobs[job_id]
            try:
                kind = specs[0].kind if specs else None
                if kind == KIND_NOMADNET_FILE:
                    await self._fetch_nomadnet_job(
                        job_id,
                        identity_hash,
                        overlay_ids[0],
                        specs[0],
                        generations[overlay_ids[0]],
                    )
                elif kind == KIND_RNGIT_FILES:
                    await self._fetch_rngit_job(
                        job_id,
                        identity_hash,
                        overlay_ids,
                        specs,
                        generations,
                    )
                else:
                    raise OverlaySourceParseError("unsupported_kind")
                job["status"] = "success"
                job["phase"] = "done"
                job["progress"] = 1.0
            except asyncio.CancelledError:
                job["status"] = "cancelled"
                job["error"] = "cancelled"
                raise
            except (
                OverlaySourceParseError,
                GeoValidationError,
                RngitFetchError,
            ) as exc:
                code = getattr(exc, "code", str(exc))
                job["status"] = "error"
                job["error"] = code
                for oid in overlay_ids:
                    if not self._generation_current(oid, generations[oid]):
                        continue
                    self._mark_error(oid, code)
            except Exception as exc:
                job["status"] = "error"
                job["error"] = str(exc)
                for oid in overlay_ids:
                    if not self._generation_current(oid, generations[oid]):
                        continue
                    self._mark_error(oid, "fetch_failed")

    def _generation_current(self, overlay_id: int, generation: int) -> bool:
        row = self.database.map_overlays.get_by_id(overlay_id)
        return bool(row) and int(row["generation"] or 0) == generation

    def _mark_error(self, overlay_id: int, code: str) -> None:
        row = self.database.map_overlays.get_by_id(overlay_id)
        interval = int(row["refresh_interval_seconds"] or 0) if row else 0
        next_at = None
        if interval > 0:
            # backoff after failure: at least interval
            next_at = (datetime.now(UTC) + timedelta(seconds=interval)).isoformat()
        self.database.map_overlays.update_fields(
            overlay_id,
            status="error",
            last_error=code,
            next_refresh_at=next_at,
        )

    def _set_phase(
        self,
        job_id: str,
        phase: str,
        progress: float | None = None,
    ) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job["phase"] = phase
        if progress is not None:
            job["progress"] = progress

    async def _fetch_nomadnet_job(
        self,
        job_id: str,
        identity_hash: str,
        overlay_id: int,
        spec: OverlaySourceSpec,
        generation: int,
    ) -> None:
        async with self._source_lock(overlay_id):
            await self._fetch_with_retries(
                job_id,
                lambda: self._download_nomadnet_once(
                    job_id,
                    identity_hash,
                    overlay_id,
                    spec,
                    generation,
                ),
            )

    async def _fetch_rngit_job(
        self,
        job_id: str,
        identity_hash: str,
        overlay_ids: list[int],
        specs: list[OverlaySourceSpec],
        generations: dict[int, int],
    ) -> None:
        # Lock all sources in id order to avoid deadlocks
        locks = [self._source_lock(oid) for oid in sorted(overlay_ids)]
        for lock in locks:
            await lock.acquire()
        try:
            await self._fetch_with_retries(
                job_id,
                lambda: self._download_rngit_once(
                    job_id,
                    identity_hash,
                    overlay_ids,
                    specs,
                    generations,
                ),
            )
        finally:
            for lock in reversed(locks):
                lock.release()

    async def _fetch_with_retries(self, job_id: str, attempt_fn) -> None:
        max_retries = self._cfg_int("map_overlay_max_retries")
        base_delay = self._cfg_int("map_overlay_retry_delay_seconds")
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                await attempt_fn()
                return
            except (GeoValidationError, OverlaySourceParseError) as exc:
                # Do not retry validation / parse errors
                raise exc
            except RngitFetchError as exc:
                if exc.code in (
                    "cancelled",
                    "rngit_tools_unavailable",
                    "path_missing",
                    "path_traversal",
                ):
                    raise
                last_exc = exc
            except Exception as exc:
                last_exc = exc
            if attempt >= max_retries:
                break
            delay = min(120.0, base_delay * (2**attempt))
            delay *= 0.5 + random.random()
            self._set_phase(job_id, "retry_wait", progress=0.0)
            await asyncio.sleep(delay)
        if last_exc:
            raise last_exc
        raise RuntimeError("fetch_failed")

    async def _download_nomadnet_once(
        self,
        job_id: str,
        identity_hash: str,
        overlay_id: int,
        spec: OverlaySourceSpec,
        generation: int,
    ) -> None:
        path_timeout = self._cfg_int("map_overlay_path_timeout_seconds")
        transfer_timeout = self._cfg_int("map_overlay_transfer_timeout_seconds")
        job_timeout = self._cfg_int("map_overlay_job_timeout_seconds")

        loop = asyncio.get_running_loop()
        done = asyncio.Event()
        result: dict[str, Any] = {}

        def on_success(file_name: str, payload: bytes):
            result["ok"] = True
            result["name"] = file_name
            result["payload"] = payload
            loop.call_soon_threadsafe(done.set)

        def on_failure(reason: str):
            result["ok"] = False
            result["error"] = reason
            loop.call_soon_threadsafe(done.set)

        def on_progress(p: float):
            self._set_phase(job_id, "transferring", progress=float(p or 0))

        def on_phase(phase: str):
            self._set_phase(job_id, phase)

        downloader = self._file_downloader_factory(
            destination_hash=bytes.fromhex(spec.destination_hash),
            page_path=spec.path_or_repo_path,
            on_file_download_success=on_success,
            on_file_download_failure=on_failure,
            on_progress_update=on_progress,
            timeout=transfer_timeout,
            on_phase=on_phase,
            reticulum=self.reticulum,
        )
        self._active_fetchers[job_id] = downloader
        try:
            await asyncio.wait_for(
                downloader.download(
                    path_lookup_timeout=path_timeout,
                    link_establishment_timeout=path_timeout,
                ),
                timeout=job_timeout,
            )
            await asyncio.wait_for(done.wait(), timeout=job_timeout)
        except TimeoutError as exc:
            downloader.cancel()
            raise RngitFetchError("job_timeout") from exc
        finally:
            self._active_fetchers.pop(job_id, None)

        if not result.get("ok"):
            raise RngitFetchError(str(result.get("error") or "request_failed"))

        payload = result["payload"]
        if not isinstance(payload, (bytes, bytearray)):
            raise GeoValidationError("invalid_response_body")
        await self._commit_bytes(
            job_id,
            identity_hash,
            overlay_id,
            generation,
            bytes(payload),
            hinted_format=guess_format_from_path(spec.path_or_repo_path),
            resolved_ref=None,
            refresh_interval=spec.refresh_interval_seconds,
        )

    async def _download_rngit_once(
        self,
        job_id: str,
        identity_hash: str,
        overlay_ids: list[int],
        specs: list[OverlaySourceSpec],
        generations: dict[int, int],
    ) -> None:
        job_timeout = self._cfg_int("map_overlay_job_timeout_seconds")
        first = specs[0]
        paths = [s.path_or_repo_path for s in specs]
        fetcher = self._rngit_fetcher_factory(
            work_root=self.work_root(),
            reticulum_config_dir=self.reticulum_config_dir,
        )
        self._active_fetchers[job_id] = fetcher

        def on_phase(phase: str):
            self._set_phase(job_id, phase)

        try:
            result = await asyncio.wait_for(
                fetcher.fetch(
                    destination_hash=first.destination_hash,
                    group=first.group_name or "",
                    repository=first.repository or "",
                    paths=paths,
                    ref=first.ref,
                    job_id=job_id,
                    timeout_seconds=job_timeout,
                    on_phase=on_phase,
                ),
                timeout=job_timeout + 5,
            )
        finally:
            self._active_fetchers.pop(job_id, None)

        for oid, spec in zip(overlay_ids, specs, strict=True):
            if not self._generation_current(oid, generations[oid]):
                continue
            payload = result.files.get(spec.path_or_repo_path)
            if payload is None:
                self._mark_error(oid, "path_missing")
                continue
            await self._commit_bytes(
                job_id,
                identity_hash,
                oid,
                generations[oid],
                payload,
                hinted_format=guess_format_from_path(spec.path_or_repo_path),
                resolved_ref=result.resolved_ref,
                refresh_interval=spec.refresh_interval_seconds,
            )

    async def _commit_bytes(
        self,
        job_id: str,
        identity_hash: str,
        overlay_id: int,
        generation: int,
        payload: bytes,
        *,
        hinted_format: str | None,
        resolved_ref: str | None,
        refresh_interval: int,
    ) -> None:
        if not self._generation_current(overlay_id, generation):
            return
        limits = self.limits()
        self._set_phase(job_id, "validating")
        sanitized = sanitize_geo_bytes(payload, hinted_format=hinted_format)
        payload = sanitized.data
        hinted_format = sanitized.format
        validated = validate_geo_bytes(
            payload,
            hinted_format=hinted_format,
            max_bytes=limits["map_overlay_max_bytes"],
            max_features=limits["map_overlay_max_features"],
            max_kmz_uncompressed_bytes=limits["map_overlay_max_kmz_uncompressed_bytes"],
        )
        digest = hashlib.sha256(payload).hexdigest()
        row = self.database.map_overlays.get_by_id(overlay_id)
        if row and row.get("content_sha256") == digest and row.get("cache_relpath"):
            abs_existing = self._cache_abs_under_root(row["cache_relpath"])
            if abs_existing and os.path.isfile(abs_existing):
                now = datetime.now(UTC)
                next_at = None
                if refresh_interval > 0:
                    next_at = (now + timedelta(seconds=refresh_interval)).isoformat()
                self.database.map_overlays.update_fields(
                    overlay_id,
                    status="ready",
                    last_error=None,
                    last_fetched_at=now.isoformat(),
                    next_refresh_at=next_at,
                    resolved_ref=resolved_ref or row.get("resolved_ref"),
                    format=validated.format,
                    byte_size=validated.byte_size,
                )
                return

        abs_path, rel = self.cache_path_for(identity_hash, overlay_id, validated.format)
        atomic_write_bytes(abs_path, payload)
        now = datetime.now(UTC)
        next_at = None
        if refresh_interval > 0:
            next_at = (now + timedelta(seconds=refresh_interval)).isoformat()
        if not self._generation_current(overlay_id, generation):
            return
        self.database.map_overlays.update_fields(
            overlay_id,
            status="ready",
            last_error=None,
            last_fetched_at=now.isoformat(),
            next_refresh_at=next_at,
            content_sha256=digest,
            resolved_ref=resolved_ref,
            format=validated.format,
            byte_size=validated.byte_size,
            cache_relpath=rel,
        )

    def cancel_job(self, job_id: str, identity_hash: str | None = None) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.get("status") not in ("running",):
            return False
        if identity_hash is not None and job.get("identity_hash") != identity_hash:
            return False
        fetcher = self._active_fetchers.get(job_id)
        if fetcher is not None:
            try:
                fetcher.cancel()
            except Exception:
                pass
        job["status"] = "cancelled"
        job["error"] = "cancelled"
        for oid in job.get("overlay_ids") or []:
            row = self.database.map_overlays.get_by_id(oid)
            if row and row.get("job_id") == job_id and row.get("status") == "fetching":
                self.database.map_overlays.update_fields(
                    oid,
                    status="error",
                    last_error="cancelled",
                )
        return True

    def patch_overlay(
        self,
        identity_hash: str,
        overlay_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        row = self.get_overlay(identity_hash, overlay_id)
        if not row:
            raise OverlaySourceParseError("not_found")
        fields: dict[str, Any] = {}
        if "name" in data and data["name"] is not None:
            fields["name"] = str(data["name"]).strip()[:200] or row["name"]
        if "enabled" in data:
            fields["enabled"] = 1 if data["enabled"] else 0
        if "visible" in data:
            fields["visible"] = 1 if data["visible"] else 0
        if "refresh_interval_seconds" in data:
            try:
                ri = int(data["refresh_interval_seconds"])
            except (TypeError, ValueError) as exc:
                raise OverlaySourceParseError("invalid_refresh_interval") from exc
            if ri < 0:
                raise OverlaySourceParseError("invalid_refresh_interval")
            if 0 < ri < 60:
                ri = 60
            ri = min(ri, 86400)
            fields["refresh_interval_seconds"] = ri
            if ri > 0:
                base = row.get("last_fetched_at")
                if base:
                    fields["next_refresh_at"] = (
                        datetime.fromisoformat(str(base).replace("Z", "+00:00"))
                        + timedelta(seconds=ri)
                    ).isoformat()
                else:
                    fields["next_refresh_at"] = datetime.now(UTC).isoformat()
            else:
                fields["next_refresh_at"] = None
        if "ref" in data and row["kind"] == KIND_RNGIT_FILES:
            from meshchatx.src.backend.map_overlay_sources import normalize_ref

            fields["ref"] = normalize_ref(data["ref"])
        if fields:
            self.database.map_overlays.update_fields(overlay_id, **fields)
        return self.get_overlay(identity_hash, overlay_id) or {}

    def delete_overlay(self, identity_hash: str, overlay_id: int) -> bool:
        row = self.get_overlay(identity_hash, overlay_id)
        if not row:
            return False
        rel = row.get("cache_relpath")
        if rel:
            abs_path = self._cache_abs_under_root(rel)
            try:
                if abs_path and os.path.isfile(abs_path):
                    os.remove(abs_path)
            except OSError:
                pass
        return self.database.map_overlays.delete_for_identity(identity_hash, overlay_id)

    def read_cache_bytes(
        self,
        identity_hash: str,
        overlay_id: int,
    ) -> tuple[bytes, str] | None:
        row = self.get_overlay(identity_hash, overlay_id)
        if not row or not row.get("cache_relpath") or not row.get("format"):
            return None
        abs_path = self._cache_abs_under_root(row["cache_relpath"])
        if not abs_path or not os.path.isfile(abs_path):
            return None
        with open(abs_path, "rb") as f:
            data = f.read()
        return data, row["format"]

    def export_overlay(
        self,
        identity_hash: str,
        overlay_id: int,
        target_format: str,
    ) -> tuple[bytes, str, str]:
        cached = self.read_cache_bytes(identity_hash, overlay_id)
        if not cached:
            raise OverlayExportError("cache_missing")
        data, src_fmt = cached
        limits = self.limits()
        out = convert_overlay_bytes(
            data,
            source_format=src_fmt,
            target_format=target_format,
            max_bytes=limits["map_overlay_max_bytes"],
            max_features=limits["map_overlay_max_features"],
            max_kmz_uncompressed_bytes=limits["map_overlay_max_kmz_uncompressed_bytes"],
        )
        row = self.get_overlay(identity_hash, overlay_id)
        filename = _safe_filename(
            (row.get("name") or "overlay") if row else "overlay",
            EXTENSIONS[target_format],
        )
        return out, CONTENT_TYPES[target_format], filename

    def export_many(
        self,
        identity_hash: str,
        overlay_ids: list[int],
        target_format: str,
    ) -> tuple[bytes, str, str]:
        if not overlay_ids:
            raise OverlayExportError("missing_ids")
        if len(overlay_ids) == 1:
            return self.export_overlay(identity_hash, overlay_ids[0], target_format)
        geo_chunks: list[bytes] = []
        limits = self.limits()
        for oid in overlay_ids:
            cached = self.read_cache_bytes(identity_hash, oid)
            if not cached:
                raise OverlayExportError("cache_missing")
            data, src_fmt = cached
            geo_chunks.append(to_geojson(data, src_fmt))
        merged = merge_geojson_bytes(geo_chunks)
        out = from_geojson(merged, target_format)
        max_bytes = limits["map_overlay_max_bytes"] * max(1, len(overlay_ids))
        max_features = limits["map_overlay_max_features"] * max(1, len(overlay_ids))
        max_uncomp = limits["map_overlay_max_kmz_uncompressed_bytes"] * max(
            1,
            len(overlay_ids),
        )
        if len(out) > max_bytes:
            raise OverlayExportError("file_too_large")
        validate_geo_bytes(
            out,
            hinted_format=target_format,
            max_bytes=max_bytes,
            max_features=max_features,
            max_kmz_uncompressed_bytes=max_uncomp,
        )
        filename = _safe_filename("overlays", EXTENSIONS[target_format])
        return out, CONTENT_TYPES[target_format], filename

    def cleanup(self) -> None:
        self.stop_scheduler()
        for job_id in list(self._jobs.keys()):
            job = self._jobs.get(job_id)
            if job and job.get("status") == "running":
                self.cancel_job(job_id)
        self._jobs.clear()
        self._active_fetchers.clear()
        work = os.path.join(self.overlay_root(), ".work")
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
