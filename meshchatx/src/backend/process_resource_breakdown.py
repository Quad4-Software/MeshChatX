# SPDX-License-Identifier: 0BSD
"""Process RSS/CPU breakdown helpers for About usage insights."""

from __future__ import annotations


def _safe_child_name(proc) -> str:
    try:
        name = proc.name()
        if name:
            return str(name)[:64]
    except Exception:
        pass
    try:
        return f"pid:{proc.pid}"
    except Exception:
        return "child"


def build_resource_breakdown(process, *, max_children: int = 8) -> list[dict]:
    """Return process and child RSS/CPU rows sorted by RSS descending.

    Values are best-effort. Restricted hosts (Android Landlock) may return
    only the parent row or an empty list.
    """
    if process is None:
        return []

    rows: list[dict] = []

    def add_row(label: str, proc) -> None:
        rss = None
        cpu = None
        try:
            rss = int(proc.memory_info().rss)
        except Exception:
            rss = None
        try:
            # Non-blocking sample. First call after create may be 0.0.
            cpu = float(proc.cpu_percent(interval=None))
        except Exception:
            cpu = None
        if rss is None and cpu is None:
            return
        rows.append(
            {
                "name": label,
                "rss": rss,
                "cpu_percent": cpu,
            }
        )

    add_row("backend", process)

    try:
        children = list(process.children(recursive=True))
    except Exception:
        children = []

    # Prefer largest children so About can show a useful top consumer.
    scored = []
    for child in children:
        try:
            scored.append((int(child.memory_info().rss), child))
        except Exception:
            try:
                scored.append((0, child))
            except Exception:
                continue
    scored.sort(key=lambda item: item[0], reverse=True)

    for _, child in scored[: max(0, int(max_children))]:
        add_row(f"child:{_safe_child_name(child)}", child)

    rows.sort(key=lambda row: int(row.get("rss") or 0), reverse=True)
    return rows


def top_by_rss(rows: list[dict] | None) -> dict | None:
    if not rows:
        return None
    best = max(rows, key=lambda row: int(row.get("rss") or 0))
    if best.get("rss") is None:
        return None
    return best


def top_by_cpu(rows: list[dict] | None) -> dict | None:
    if not rows:
        return None
    scored = [row for row in rows if row.get("cpu_percent") is not None]
    if not scored:
        return None
    return max(scored, key=lambda row: float(row.get("cpu_percent") or 0.0))
