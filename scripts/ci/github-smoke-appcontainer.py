#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Live AppContainer smoke for a frozen MeshChatX build on Windows.

Starts the frozen backend, waits for /api/v1/server/security, asserts that
AppContainer is active, and then asks the server to shut down.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_PORT = 9337
POLL_INTERVAL = 1.0
STARTUP_TIMEOUT = 90.0
SHUTDOWN_TIMEOUT = 30.0
ROOT = Path(__file__).resolve().parents[2]


def find_frozen_exe(build_dir: Path) -> Path | None:
    """Locate the frozen backend executable under build_dir."""
    names = ("ReticulumMeshChatX.exe", "ReticulumMeshChatX")
    for name in names:
        exe = build_dir / name
        if exe.exists():
            return exe
    for sub in build_dir.iterdir():
        if sub.is_dir():
            for name in names:
                exe = sub / name
                if exe.exists():
                    return exe
    return None


def appcontainer_supported() -> bool:
    """Probe the source module to see whether AppContainer APIs are present."""
    try:
        from meshchatx.src.backend import appcontainer_sandbox as ac

        return bool(ac.appcontainer_supported())
    except Exception:
        return False


def wait_for_security(port: int, timeout: float) -> dict:
    """Poll /api/v1/server/security until it returns JSON or timeout."""
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/api/v1/server/security"
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=POLL_INTERVAL) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = str(exc)
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"security endpoint not ready: {last_error}")


def shutdown_app(port: int) -> None:
    """Ask the backend to shut down cleanly."""
    url = f"http://127.0.0.1:{port}/api/v1/app/shutdown"
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            resp.read()
    except urllib.error.URLError:
        pass


def terminate_tree(pid: int) -> None:
    """Kill a process and its descendants on Windows."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            check=False,
            capture_output=True,
        )


def run_smoke(build_dir: Path) -> int:
    if sys.platform != "win32":
        print("AppContainer smoke only runs on Windows.")
        return 0

    exe = find_frozen_exe(build_dir)
    if not exe:
        print(f"frozen backend executable not found under {build_dir}", file=sys.stderr)
        return 1

    if not appcontainer_supported():
        print("AppContainer APIs are unavailable on this host; skipping live smoke.")
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="meshchatx_appcontainer_smoke_"))
    try:
        storage = tmp / "storage"
        reticulum = tmp / "reticulum"
        logs = tmp / "logs"
        storage.mkdir()
        reticulum.mkdir()
        logs.mkdir()

        args = [
            str(exe),
            "--headless",
            "--no-https",
            "--port",
            str(DEFAULT_PORT),
            "--storage-dir",
            str(storage),
            "--reticulum-config-dir",
            str(reticulum),
            "--log-dir",
            str(logs),
        ]
        proc = subprocess.Popen(args)  # noqa: S603
        try:
            data = wait_for_security(DEFAULT_PORT, STARTUP_TIMEOUT)

            required = (
                "appcontainer_supported",
                "appcontainer_requested",
                "appcontainer_auto_enabled",
                "appcontainer_active",
                "fs_sandbox_active",
            )
            for key in required:
                if not data.get(key):
                    print(
                        f"expected {key}=true, got {data!r}",
                        file=sys.stderr,
                    )
                    return 1

            print("AppContainer smoke passed.")
            shutdown_app(DEFAULT_PORT)
        finally:
            try:
                proc.wait(timeout=SHUTDOWN_TIMEOUT)
            except subprocess.TimeoutExpired:
                terminate_tree(proc.pid)
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run AppContainer smoke on a frozen build.",
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=ROOT / "build" / "exe",
    )
    return run_smoke(parser.parse_args().build_dir)


if __name__ == "__main__":
    raise SystemExit(main())
