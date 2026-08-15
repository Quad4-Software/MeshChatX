# SPDX-License-Identifier: 0BSD

"""Periodic and pressure-triggered memory cleanup for MeshChatX."""

from __future__ import annotations

import logging
import time
from typing import Any

from meshchatx.src.backend import (
    nomadnet_downloader,
    reticulum_pathfinding,
    rns_link_manager,
)

_log = logging.getLogger("meshchatx.memory_pressure")

HELD_ANNOUNCES_DROP_THRESHOLD = 512
ANNOUNCE_CACHE_CLEAN_INTERVAL_S = 30 * 60
ANNOUNCE_RATE_WINDOW_S = 3600.0
ANNOUNCE_RATE_HARD_CAP = 50_000
LXMF_INCOMING_RATE_WINDOW_S = 3600.0
LXMF_INCOMING_RATE_HARD_CAP = 20_000


def prune_time_windowed_floats(
    stamps: list[float],
    now: float | None = None,
    *,
    window_s: float,
    hard_cap: int,
) -> list[float]:
    """Keep timestamps inside window_s, then the newest hard_cap entries."""
    if not stamps:
        return stamps
    current = time.time() if now is None else float(now)
    cutoff = current - float(window_s)
    kept = [t for t in stamps if t >= cutoff]
    cap = max(0, int(hard_cap))
    if cap and len(kept) > cap:
        kept = kept[-cap:]
    return kept


def prune_announce_timestamps(
    stamps: list[float],
    now: float | None = None,
) -> list[float]:
    return prune_time_windowed_floats(
        stamps,
        now,
        window_s=ANNOUNCE_RATE_WINDOW_S,
        hard_cap=ANNOUNCE_RATE_HARD_CAP,
    )


def prune_lxmf_incoming_timestamps(
    stamps: list[float],
    now: float | None = None,
) -> list[float]:
    return prune_time_windowed_floats(
        stamps,
        now,
        window_s=LXMF_INCOMING_RATE_WINDOW_S,
        hard_cap=LXMF_INCOMING_RATE_HARD_CAP,
    )


def _app_flag(app: Any, name: str) -> bool:
    """Read a boolean flag without treating MagicMock defaults as True."""
    if app is None:
        return False
    try:
        return bool(object.__getattribute__(app, name))
    except AttributeError:
        return False


class MemoryPressureManager:
    """Coordinates link sweeps, path pruning, and SQLite disk offload."""

    def __init__(self, app: Any = None):
        self.app = app
        self._last_announce_cache_clean = 0.0
        self._sqlite_relaxed = False
        self.last_stats: dict[str, Any] = {
            "nomad_links_swept": 0,
            "rns_links_swept": 0,
            "paths_pruned_expired": 0,
            "paths_pruned_cap": 0,
            "announce_cache_cleaned": False,
            "held_queues_dropped": False,
            "sqlite_relaxed": False,
        }

    def run_periodic_cleanup(self) -> dict[str, Any]:
        """Called from announce_loop about every 5 minutes."""
        reticulum = getattr(self.app, "reticulum", None) if self.app else None

        before_nomad = nomadnet_downloader.cached_link_count()
        nomadnet_downloader.sweep_stale_links()
        after_nomad = nomadnet_downloader.cached_link_count()

        before_rns = rns_link_manager.cached_link_count()
        rns_link_manager.sweep_stale_links()
        after_rns = rns_link_manager.cached_link_count()

        expired_dropped = reticulum_pathfinding.prune_expired_path_table_entries(
            reticulum,
        )
        cap_dropped = reticulum_pathfinding.prune_path_table_to_soft_cap(reticulum)

        announce_cleaned = False
        now = time.time()
        if now - self._last_announce_cache_clean >= ANNOUNCE_CACHE_CLEAN_INTERVAL_S:
            announce_cleaned = reticulum_pathfinding.clean_rns_announce_cache()
            if announce_cleaned:
                self._last_announce_cache_clean = now

        held_dropped = self._maybe_drop_held_announce_queues()
        extra = self._prune_app_runtime_buffers()

        self.last_stats = {
            "nomad_links_swept": max(0, before_nomad - after_nomad),
            "rns_links_swept": max(0, before_rns - after_rns),
            "nomad_cached_links": after_nomad,
            "rns_cached_links": after_rns,
            "paths_pruned_expired": expired_dropped,
            "paths_pruned_cap": cap_dropped,
            "path_table_size": reticulum_pathfinding.path_table_size(),
            "announce_cache_cleaned": announce_cleaned,
            "held_queues_dropped": held_dropped,
            "sqlite_relaxed": self._sqlite_relaxed,
            **extra,
        }
        if (
            expired_dropped
            or cap_dropped
            or announce_cleaned
            or held_dropped
            or before_nomad != after_nomad
            or before_rns != after_rns
        ):
            _log.info("Memory cleanup: %s", self.last_stats)
        return self.last_stats

    def on_memory_low(self, available_mb: float) -> dict[str, Any]:
        """Reactive cleanup when HealthMonitor reports low available RAM."""
        stats = self.run_periodic_cleanup()
        db = getattr(self.app, "database", None) if self.app else None
        if db is not None and hasattr(db, "apply_memory_pressure_pragmas"):
            try:
                fs_sandbox_active = (
                    _app_flag(self.app, "fs_sandbox_active")
                    or _app_flag(
                        self.app,
                        "landlock_active",
                    )
                    or _app_flag(self.app, "appcontainer_active")
                )
                db.apply_memory_pressure_pragmas(
                    True,
                    fs_sandbox_active=fs_sandbox_active,
                )
                self._sqlite_relaxed = True
                stats["sqlite_relaxed"] = True
                stats["sqlite_file_temp"] = not fs_sandbox_active
            except Exception as exc:
                _log.debug("SQLite pressure pragmas failed: %s", exc)
        _log.warning(
            "Memory pressure cleanup (available=%.0f MB): %s",
            available_mb,
            stats,
        )
        return stats

    def on_memory_recovered(self) -> None:
        if not self._sqlite_relaxed:
            return
        db = getattr(self.app, "database", None) if self.app else None
        if db is not None and hasattr(db, "apply_memory_pressure_pragmas"):
            try:
                db.apply_memory_pressure_pragmas(False)
                self._sqlite_relaxed = False
                self.last_stats["sqlite_relaxed"] = False
            except Exception as exc:
                _log.debug("SQLite restore pragmas failed: %s", exc)

    def _maybe_drop_held_announce_queues(self) -> bool:
        if self.app is None:
            return False
        handler = getattr(self.app, "rnpath_handler", None)
        if handler is None or not hasattr(handler, "drop_announce_queues"):
            return False
        held = self._count_held_announces()
        if held < HELD_ANNOUNCES_DROP_THRESHOLD:
            return False
        try:
            handler.drop_announce_queues()
            _log.info("Dropped announce queues (held_announces=%s)", held)
            return True
        except Exception as exc:
            _log.debug("drop_announce_queues failed: %s", exc)
            return False

    def _prune_app_runtime_buffers(self) -> dict[str, int]:
        extra = {
            "announce_timestamps": 0,
            "lxmf_incoming_timestamps": 0,
            "auto_resend_locks_dropped": 0,
            "rncp_transfers_pruned": 0,
            "overlay_jobs_pruned": 0,
            "map_exports_pruned": 0,
        }
        app = self.app
        if app is None:
            return extra
        stamps = getattr(app, "announce_timestamps", None)
        if isinstance(stamps, list):
            pruned = prune_announce_timestamps(stamps)
            extra["announce_timestamps"] = max(0, len(stamps) - len(pruned))
            app.announce_timestamps = pruned
        incoming = getattr(app, "_lxmf_incoming_timestamps", None)
        if isinstance(incoming, list):
            pruned_in = prune_lxmf_incoming_timestamps(incoming)
            extra["lxmf_incoming_timestamps"] = max(0, len(incoming) - len(pruned_in))
            app._lxmf_incoming_timestamps = pruned_in
        try:
            coord = getattr(app, "_auto_resend_coordinator", None)
            dropped = coord.evict_unlocked_locks()
            extra["auto_resend_locks_dropped"] = int(dropped or 0)
        except Exception:
            pass
        ctx = getattr(app, "current_context", None)
        try:
            extra["rncp_transfers_pruned"] = int(
                ctx.rncp_handler.prune_terminal_transfers() or 0,
            )
        except Exception:
            pass
        try:
            extra["overlay_jobs_pruned"] = int(
                ctx.map_overlay_manager.prune_finished_jobs() or 0,
            )
        except Exception:
            pass
        try:
            extra["map_exports_pruned"] = int(
                ctx.map_manager.prune_export_records() or 0
            )
        except Exception:
            pass
        return extra

    def _count_held_announces(self) -> int:
        total = 0
        try:
            held = getattr(
                __import__("RNS").Transport,
                "held_announces",
                None,
            )
            if isinstance(held, dict):
                total += len(held)
        except Exception:
            pass
        try:
            import RNS

            interfaces = getattr(RNS.Transport, "interfaces", None) or []
            for iface in interfaces:
                iface_held = getattr(iface, "held_announces", None)
                if isinstance(iface_held, dict) or isinstance(
                    iface_held, (list, set, tuple)
                ):
                    total += len(iface_held)
        except Exception:
            pass
        return total


def cache_stats() -> dict[str, int]:
    return {
        "nomad_cached_links": nomadnet_downloader.cached_link_count(),
        "rns_cached_links": rns_link_manager.cached_link_count(),
        "path_table_size": reticulum_pathfinding.path_table_size(),
    }
