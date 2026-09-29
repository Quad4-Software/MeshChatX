#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Shared helpers for spawning a real MeshChatX backend in tests.

All helpers bind 127.0.0.1 only and take an isolated storage dir, so
tests never touch the public network or a developer's state. Used by
the crash-consistency and shared-instance live suites.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def backend_env(tmp: str) -> dict:
    return {
        **os.environ,
        "MESHCHAT_NO_HTTPS": "1",
        "MESHCHAT_TRUSTED_PROXIES": "127.0.0.1/32",
        "MESHCHAT_LANDLOCK": "0",
        "MESHCHAT_LOG_DIR": os.path.join(tmp, "logs"),
    }


def spawn_backend(tmp: str, port: int, log_path: str | None = None) -> tuple:
    """Start a headless backend; returns (proc, log_handle)."""
    os.makedirs(os.path.join(tmp, "storage"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "rns"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "logs"), exist_ok=True)
    log = open(log_path or os.path.join(tmp, "backend.log"), "ab")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "meshchatx.meshchat",
            "--headless",
            "--no-https",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--storage-dir",
            os.path.join(tmp, "storage"),
            "--reticulum-config-dir",
            os.path.join(tmp, "rns"),
        ],
        cwd=ROOT,
        env=backend_env(tmp),
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    return proc, log


def write_rns_config(tmp: str, extra: str = "") -> str:
    """Write a minimal isolated reticulum config for the backend."""
    path = os.path.join(tmp, "rns")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "config"), "w") as f:
        f.write(
            "[reticulum]\n"
            "  enable_transport = False\n"
            "  share_instance = No\n"
            + (extra if extra.endswith("\n") else extra + "\n")
        )
    return path


def request(port: int, path: str, data=None, method=None, timeout=20, jar=None):
    jar = jar if jar is not None else request.__dict__.setdefault("_jar", {})
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=body, method=method
    )
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if jar.get("cookie"):
        req.add_header("Cookie", jar["cookie"])
    if jar.get("csrf") and method in ("POST", "PUT", "DELETE"):
        req.add_header("X-CSRF-Token", jar["csrf"])
    resp = urllib.request.urlopen(req, timeout=timeout)
    sc = resp.headers.get("Set-Cookie")
    if sc and "cookie" not in jar:
        jar["cookie"] = sc.split(";")[0]
    payload = resp.read()
    try:
        out = json.loads(payload)
    except Exception:
        return {"raw": payload[:400].decode(errors="replace")}, resp.status
    if isinstance(out, dict) and out.get("csrf_token"):
        jar["csrf"] = out["csrf_token"]
    return out, resp.status


def wait_ready(port: int, timeout_s: float = 240) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            d, _ = request(port, "/api/v1/status", timeout=5)
            if d.get("status") == "ok" or d.get("network_ready"):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def kill_proc(proc, hard=True):
    """SIGKILL (or SIGTERM) a proc and wait; no-op if already dead."""
    if proc is None or proc.poll() is not None:
        return
    with contextlib.suppress(Exception):
        proc.send_signal(signal.SIGKILL if hard else signal.SIGTERM)
    with contextlib.suppress(Exception):
        proc.wait(timeout=15)
