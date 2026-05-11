import gc
import sys
import tracemalloc
from typing import Any, Optional


def _obj_size(obj: Any) -> int:
    try:
        return sys.getsizeof(obj)
    except Exception:
        return 0


def _safe_type_name(obj: Any) -> str:
    try:
        return type(obj).__qualname__
    except Exception:
        return "<unknown>"


def _safe_module(obj: Any) -> str:
    try:
        return type(obj).__module__
    except Exception:
        return ""


def _is_reticulum_obj(obj: Any) -> bool:
    mod = _safe_module(obj)
    return "RNS" in mod or "LXMF" in mod or "LXST" in mod or "meshchatx" in mod


def _is_closure(obj: Any) -> bool:
    return type(obj).__name__ in ("function", "cell", "code", "FrameType", "MethodType")


def _classify(obj: Any) -> str:
    t = type(obj)
    if t in (str, bytes, bytearray, int, float, bool, type(None)):
        return "builtin"
    if isinstance(obj, (list, tuple, set, frozenset)):
        return "container"
    if isinstance(obj, dict):
        return "dict"
    mod = _safe_module(obj)
    if "RNS" in mod:
        return "RNS"
    if "LXMF" in mod:
        return "LXMF"
    if "LXST" in mod:
        return "LXST"
    if "meshchatx" in mod:
        return "meshchatx"
    if mod.startswith(("asyncio", "concurrent", "threading")):
        return "async"
    return "other"


class _ObjectTypeTracker:
    """Tracks per-type object counts across snapshots to detect accumulation."""

    def __init__(self) -> None:
        self._history: list[dict[str, int]] = []
        self._last_full: dict[str, int] = {}

    def record(self) -> None:
        counts: dict[str, int] = {}
        try:
            for obj in gc.get_objects():
                try:
                    name = _safe_type_name(obj)
                    counts[name] = counts.get(name, 0) + 1
                except Exception:
                    continue
        except Exception:
            pass
        self._history.append(counts)
        self._last_full = counts

    @property
    def growth_since_first(self) -> list[tuple[str, int]]:
        if len(self._history) < 2:
            return []
        first = self._history[0]
        last = self._history[-1]
        result: list[tuple[str, int]] = []
        for tname, count in last.items():
            diff = count - first.get(tname, 0)
            if diff > 0:
                result.append((tname, diff))
        result.sort(key=lambda x: -x[1])
        return result

    @property
    def accumulating_types(self) -> list[tuple[str, int]]:
        if len(self._history) < 3:
            return []
        result: list[tuple[str, int]] = []
        for tname in self._history[-1]:
            counts = [h.get(tname, 0) for h in self._history]
            if (
                all(counts[i] <= counts[i + 1] for i in range(len(counts) - 1))
                and counts[-1] - counts[0] > 0
            ):
                result.append((tname, counts[-1] - counts[0]))
        result.sort(key=lambda x: -x[1])
        return result


class MemoryDiagnostics:
    """tracemalloc-based memory diagnostics for identifying leaks.

    Python 3.14+ uses an incremental GC that spreads collection work across
    allocations instead of doing one big sweep.  Cyclic garbage can therefore
    linger longer between full collections.  This class helps detect
    accumulating objects by:

    * Taking periodic ``tracemalloc`` snapshots and diffing against a baseline.
    * Tracking GC generation sizes (gen0/gen1/gen2 object counts).
    * Profiling ``gc.get_objects()`` by type to spot monotonic growth.
    * Finding the top-N allocation sites (filename + line number) that
      contribute the most to memory growth.

    Usage::

        from meshchatx.src.backend.diagnostics import MemoryDiagnostics
        diag = MemoryDiagnostics()
        diag.start()
        # ... let app run for a while ...
        report = diag.report()
        diag.stop()

    All methods are safe to call when tracing is inactive (they return
    empty/default values).
    """

    def __init__(self, nframes: int = 25) -> None:
        self._nframes = nframes
        self._enabled = False
        self._baseline: Optional[tracemalloc.Snapshot] = None
        self._snapshots: list[tracemalloc.Snapshot] = []
        self._gc_stats: list[dict[str, Any]] = []
        self._type_tracker = _ObjectTypeTracker()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._enabled:
            return
        if not tracemalloc.is_tracing():
            tracemalloc.start(self._nframes)
        self._enabled = True
        self._baseline = tracemalloc.take_snapshot()
        self._snapshots = [self._baseline]
        self._record_gc_stats()
        self._type_tracker.record()
        print(
            f"[mem_diag] Started tracing (nframes={self._nframes}, "
            f"gc.freeze={getattr(gc, 'freeze_count', 0)})",
        )

    def stop(self) -> None:
        if not self._enabled:
            return
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        self._enabled = False
        print("[mem_diag] Stopped tracing")

    def reset(self) -> None:
        self.stop()
        self._baseline = None
        self._snapshots.clear()
        self._gc_stats.clear()

    @property
    def enabled(self) -> bool:
        return self._enabled and tracemalloc.is_tracing()

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def snapshot(self) -> Optional[tracemalloc.Snapshot]:
        if not self.enabled:
            return None
        snap = tracemalloc.take_snapshot()
        self._snapshots.append(snap)
        self._record_gc_stats()
        self._type_tracker.record()
        return snap

    def diff_snapshots(
        self,
        new_idx: int = -1,
        old_idx: int = 0,
        key_type: str = "lineno",
        top_n: int = 40,
    ) -> list[dict[str, Any]]:
        if not self._snapshots or len(self._snapshots) < 2:
            return []
        if old_idx < 0:
            old_idx = len(self._snapshots) + old_idx
        if new_idx < 0:
            new_idx = len(self._snapshots) + new_idx
        if old_idx < 0 or old_idx >= len(self._snapshots):
            return []
        if new_idx < 0 or new_idx >= len(self._snapshots):
            return []
        diff = self._snapshots[new_idx].compare_to(self._snapshots[old_idx], key_type)
        result: list[dict[str, Any]] = []
        for stat in diff[:top_n]:
            frame = stat.traceback[0]
            result.append(
                {
                    "size": stat.size,
                    "size_mib": round(stat.size / (1024 * 1024), 3),
                    "count": stat.count,
                    "file": frame.filename,
                    "line": frame.lineno,
                },
            )
        return result

    def top_allocation_sites(self, top_n: int = 40) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        snap = tracemalloc.take_snapshot()
        stats = snap.statistics("lineno", True)
        result: list[dict[str, Any]] = []
        for stat in stats[:top_n]:
            frame = stat.traceback[0]
            result.append(
                {
                    "size": stat.size,
                    "size_mib": round(stat.size / (1024 * 1024), 3),
                    "count": stat.count,
                    "file": frame.filename,
                    "line": frame.lineno,
                },
            )
        return result

    # ------------------------------------------------------------------
    # GC generation tracking (critical for incremental GC diagnostics)
    # ------------------------------------------------------------------

    def _record_gc_stats(self) -> None:
        g0 = g1 = g2 = -1
        try:
            g0 = len(gc.get_objects(0))
            g1 = len(gc.get_objects(1))
            g2 = len(gc.get_objects(2))
        except TypeError:
            g0 = g1 = g2 = -1
        except Exception:
            pass
        self._gc_stats.append(
            {
                "gen0": g0,
                "gen1": g1,
                "gen2": g2,
                "total": sum(x for x in (g0, g1, g2) if x >= 0),
                "thresholds": list(gc.get_threshold()),
                "count": gc.get_count(),
                "frozen": getattr(gc, "freeze_count", 0),
            },
        )

    def gc_stats(self) -> dict[str, Any]:
        if not self._gc_stats:
            return {"available": False}
        first = self._gc_stats[0]
        last = self._gc_stats[-1]
        return {
            "available": True,
            "snapshots_taken": len(self._snapshots),
            "records": len(self._gc_stats),
            "first": first,
            "last": last,
            "deltas": {
                k: last.get(k, 0) - first.get(k, 0)
                for k in ("gen0", "gen1", "gen2", "total")
                if k in first and k in last
            },
            "history": self._gc_stats,
        }

    # ------------------------------------------------------------------
    # Heap analysis (gc.get_objects based)
    # ------------------------------------------------------------------

    def heap_by_type(self, top_n: int = 40) -> list[dict[str, Any]]:
        """Count live objects grouped by their type name."""
        counts: dict[str, int] = {}
        sizes: dict[str, int] = {}
        try:
            for obj in gc.get_objects():
                try:
                    tname = _safe_type_name(obj)
                    counts[tname] = counts.get(tname, 0) + 1
                    sizes[tname] = sizes.get(tname, 0) + _obj_size(obj)
                except Exception:
                    continue
        except Exception:
            return []
        sorted_types = sorted(counts.items(), key=lambda x: -x[1])
        return [
            {
                "type": tname,
                "count": cnt,
                "size_bytes": sizes.get(tname, 0),
                "size_mib": round(sizes.get(tname, 0) / (1024 * 1024), 3),
            }
            for tname, cnt in sorted_types[:top_n]
        ]

    def heap_by_category(self, top_n: int = 40) -> list[dict[str, Any]]:
        """Count live objects grouped by category (RNS, LXMF, meshchatx, etc)."""
        counts: dict[str, int] = {}
        sizes: dict[str, int] = {}
        try:
            for obj in gc.get_objects():
                try:
                    cat = _classify(obj)
                    counts[cat] = counts.get(cat, 0) + 1
                    sizes[cat] = sizes.get(cat, 0) + _obj_size(obj)
                except Exception:
                    continue
        except Exception:
            return []
        sorted_cats = sorted(counts.items(), key=lambda x: -x[1])
        return [
            {
                "category": cat,
                "count": cnt,
                "size_bytes": sizes.get(cat, 0),
                "size_mib": round(sizes.get(cat, 0) / (1024 * 1024), 3),
            }
            for cat, cnt in sorted_cats[:top_n]
        ]

    def accumulating_types(self, top_n: int = 20) -> list[tuple[str, int]]:
        return self._type_tracker.accumulating_types[:top_n]

    def type_growth_since_start(self, top_n: int = 20) -> list[tuple[str, int]]:
        return self._type_tracker.growth_since_first[:top_n]

    # ------------------------------------------------------------------
    # Reference cycle detection helpers
    # ------------------------------------------------------------------

    def find_referrers(
        self, type_name: str, max_results: int = 20
    ) -> list[dict[str, Any]]:
        """Find referrers of objects of a given type — useful to trace who holds references."""
        matches: list[Any] = []
        try:
            for obj in gc.get_objects():
                try:
                    if _safe_type_name(obj) == type_name:
                        matches.append(obj)
                        if len(matches) >= max_results:
                            break
                except Exception:
                    continue
        except Exception:
            return []
        result: list[dict[str, Any]] = []
        for obj in matches:
            refs: list[str] = []
            try:
                for ref in gc.get_referrers(obj):
                    try:
                        refs.append(f"{_safe_type_name(ref)} at {id(ref):#x}")
                    except Exception:
                        refs.append("<error>")
                    if len(refs) >= 10:
                        break
            except Exception:
                refs = ["<error>"]
            result.append(
                {
                    "type": _safe_type_name(obj),
                    "id": id(obj),
                    "size": _obj_size(obj),
                    "referrers": refs,
                },
            )
        return result

    def find_cyclic_garbage(self) -> list[dict[str, Any]]:
        """Run gc.collect() and return info about what was collected."""
        unreachable_before = gc.get_count()
        cols: list[int] = []
        for gen in range(3):
            try:
                n = gc.collect(gen)
                cols.append(n)
            except Exception:
                cols.append(-1)
        unreachable_after = gc.get_count()
        return [
            {
                "generation": i,
                "collected": n,
            }
            for i, n in enumerate(cols)
        ] + [
            {
                "unreachable_before": list(unreachable_before),
                "unreachable_after": list(unreachable_after),
            },
        ]

    def gc_garbage_types(self) -> list[dict[str, int]]:
        """Show types of objects in gc.garbage (uncollectable objects)."""
        counts: dict[str, int] = {}
        try:
            for obj in gc.garbage:
                try:
                    tname = _safe_type_name(obj)
                    counts[tname] = counts.get(tname, 0) + 1
                except Exception:
                    continue
        except Exception:
            pass
        sorted_counts = sorted(counts.items(), key=lambda x: -x[1])
        return [{"type": t, "count": c} for t, c in sorted_counts]

    # ------------------------------------------------------------------
    # Consolidated report
    # ------------------------------------------------------------------

    def report(self) -> dict[str, Any]:
        """Generate a comprehensive memory diagnostics report."""
        if not self._enabled:
            return {
                "enabled": False,
                "message": "Memory diagnostics not enabled (pass --memory-diag)",
            }

        current_traced, peak_traced = (0, 0)
        if tracemalloc.is_tracing():
            current_traced, peak_traced = tracemalloc.get_traced_memory()

        growth = self.diff_snapshots(top_n=30)
        top_sites = self.top_allocation_sites(top_n=15)
        gc_info = self.gc_stats()
        top_types = self.heap_by_type(top_n=30)
        cat_types = self.heap_by_category()
        accumulating = self.accumulating_types()
        growth_types = self.type_growth_since_start()

        return {
            "enabled": True,
            "python_version": sys.version,
            "incremental_gc": self._detect_incremental_gc(),
            "tracemalloc": {
                "current_bytes": current_traced,
                "current_mib": round(current_traced / (1024 * 1024), 3),
                "peak_bytes": peak_traced,
                "peak_mib": round(peak_traced / (1024 * 1024), 3),
            },
            "gc": gc_info,
            "growth_vs_baseline": growth,
            "top_allocation_sites": top_sites,
            "heap_by_type": top_types,
            "heap_by_category": cat_types,
            "accumulating_types": [{"type": t, "growth": c} for t, c in accumulating],
            "type_growth_since_start": [
                {"type": t, "growth": c} for t, c in growth_types
            ],
            "gc_freeze_count": getattr(gc, "freeze_count", 0),
            "snapshot_count": len(self._snapshots),
        }

    @staticmethod
    def _detect_incremental_gc() -> dict[str, Any]:
        """Detect if we're running on Python 3.14+ with incremental GC."""
        version_info = sys.version_info
        result: dict[str, Any] = {
            "is_incremental_gc": version_info >= (3, 14),
            "python_version": f"{version_info.major}.{version_info.minor}.{version_info.micro}",
        }
        if version_info >= (3, 14):
            thresh = gc.get_threshold()
            result["thresholds"] = list(thresh)
            result["note"] = (
                "Python 3.14+ uses incremental GC. "
                "Full collections may be deferred, causing cyclic garbage "
                "to linger. Check 'gc.deltas.gen2' growth."
            )
        return result


# ------------------------------------------------------------------
# Module-level convenience
# ------------------------------------------------------------------

_diag: Optional[MemoryDiagnostics] = None


def get_diagnostics() -> MemoryDiagnostics:
    global _diag
    if _diag is None:
        _diag = MemoryDiagnostics()
    return _diag


def take_heap_snapshot(include_tracemalloc: bool = True) -> dict[str, Any]:
    """Convenience function: take a one-shot heap snapshot.

    Useful for ``pdb`` / ``breakpoint()`` sessions::

        from meshchatx.src.backend.diagnostics import take_heap_snapshot
        report = take_heap_snapshot()
    """
    diag = get_diagnostics()
    was_enabled = diag.enabled
    if not was_enabled and include_tracemalloc:
        diag.start()
    diag.snapshot()
    report = diag.report()
    if not was_enabled and include_tracemalloc:
        diag.stop()
    return report
