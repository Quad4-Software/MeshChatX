# SPDX-License-Identifier: 0BSD
"""Live observation of AutoPropagationManager against a shared rnsd instance.

Usage (from repo root, with rnsd already running as shared instance)::

    MESHCHAT_LANDLOCK=0 MESHCHAT_SECCOMP=0 uv run python scripts/live_auto_propagation_observe.py
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import RNS

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.auto_propagation_manager import (
    MEMORY_CONFIG_KEY,
    AutoPropagationManager,
)


def _pretty(node_hex: str | None) -> str:
    if not node_hex:
        return "(none)"
    try:
        return RNS.prettyhexrep(bytes.fromhex(node_hex))
    except Exception:
        return node_hex[:12] + "..."


async def main() -> int:
    reticulum_config_dir = os.path.expanduser("~/.reticulum")
    if not Path(reticulum_config_dir, "config").is_file():
        print("FAIL: missing ~/.reticulum/config (need shared rnsd)")
        return 2

    tmp = tempfile.mkdtemp(prefix="mcx-live-autoprops-")
    log_path = Path(tmp) / "observe.json"
    print(f"temp storage: {tmp}")
    print(f"reticulum config: {reticulum_config_dir}")

    identity = RNS.Identity()
    app = ReticulumMeshChat(
        identity,
        storage_dir=tmp,
        reticulum_config_dir=reticulum_config_dir,
        defer_network_setup=False,
        headless=True,
        plugins_enabled=False,
    )

    report: dict = {
        "started_at": time.time(),
        "network_ready": False,
        "announce_wait_s": 45,
        "propagation_announces": 0,
        "candidates": {},
        "before_preferred": None,
        "after_preferred": None,
        "memory": {},
        "path_ok": None,
        "hops": None,
        "error": None,
    }

    try:
        ready = app.wait_until_network_ready(timeout=90)
        report["network_ready"] = bool(ready)
        print(f"network_ready={ready}")
        if not ready:
            report["error"] = "network_not_ready"
            log_path.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
            return 1

        ctx = app.current_context
        if ctx is None or ctx.auto_propagation_manager is None:
            report["error"] = "no_auto_propagation_manager"
            log_path.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
            return 1

        manager: AutoPropagationManager = ctx.auto_propagation_manager
        ctx.config.lxmf_preferred_propagation_node_auto_select.set(True)

        print(f"waiting {report['announce_wait_s']}s for lxmf.propagation announces...")
        await asyncio.sleep(report["announce_wait_s"])

        announces = (
            ctx.database.announces.get_announces(aspect="lxmf.propagation") or []
        )
        report["propagation_announces"] = len(announces)
        print(f"propagation announces stored: {len(announces)}")

        best, announced = manager._collect_candidates()
        report["candidates"] = {
            "count": len(best),
            "announced_count": len(announced),
            "sample": [
                {
                    "dest": _pretty(h),
                    "hops": hops if hops < 10**8 else None,
                    "announced": h in announced,
                    "path_ok": manager._path_quality_ok(bytes.fromhex(h)),
                }
                for h, hops in list(best.items())[:8]
            ],
        }
        print(
            f"candidates={len(best)} announced={len(announced)} "
            f"sample={report['candidates']['sample']}",
        )

        before = ctx.config.lxmf_preferred_propagation_node_destination_hash.get()
        report["before_preferred"] = before
        print(f"before preferred: {_pretty(before)}")

        t0 = time.monotonic()
        await manager.check_and_update_propagation_node()
        elapsed = time.monotonic() - t0
        report["check_elapsed_s"] = round(elapsed, 2)

        after = ctx.config.lxmf_preferred_propagation_node_destination_hash.get()
        report["after_preferred"] = after
        raw_mem = ctx.config.get(MEMORY_CONFIG_KEY, default_value=None)
        report["memory"] = json.loads(raw_mem) if raw_mem else {}
        print(f"after preferred: {_pretty(after)} ({elapsed:.1f}s)")

        if after:
            dest = bytes.fromhex(after)
            report["path_ok"] = manager._path_quality_ok(dest)
            report["hops"] = manager._hops_to(dest)
            outbound = ctx.message_router.get_outbound_propagation_node()
            report["outbound_matches"] = (
                outbound is not None and outbound.hex() == after.lower()
            )
            print(
                f"path_ok={report['path_ok']} hops={report['hops']} "
                f"outbound_matches={report['outbound_matches']}",
            )

        # Second pass should stay sticky without thrashing when recently verified.
        if after:
            await manager.check_and_update_propagation_node()
            sticky = ctx.config.lxmf_preferred_propagation_node_destination_hash.get()
            report["sticky_preferred"] = sticky
            report["sticky_ok"] = sticky == after
            print(f"sticky preferred: {_pretty(sticky)} ok={report['sticky_ok']}")

        log_path.write_text(json.dumps(report, indent=2) + "\n")
        print("--- report ---")
        print(json.dumps(report, indent=2))

        if not best:
            print(
                "NOTE: no enabled lxmf.propagation candidates heard yet. "
                "Logic ran, but live selection could not be proven this cycle.",
            )
            return 0

        if after and report.get("path_ok") and report.get("outbound_matches"):
            print("PASS: selected verified preferred peer with usable path")
            return 0

        if after:
            print("PARTIAL: preferred set but path/outbound not fully confirmed")
            return 0

        print("NOTE: check finished without selecting a preferred peer")
        return 0
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        log_path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        raise
    finally:
        with contextlib.suppress(Exception):
            if getattr(app, "current_context", None) is not None:
                app.current_context.stop()
        print(f"report file: {log_path}")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
