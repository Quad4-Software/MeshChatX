# SPDX-License-Identifier: 0BSD

"""Headless / Settings self-check helpers for critical cross-platform diagnostics."""

from __future__ import annotations

import contextlib
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from typing import Any

from meshchatx.src.backend import self_check_probe as _self_check_probe  # noqa: F401

_CRITICAL_IMPORTS = (
    "RNS",
    "LXMF",
    "lxmfy",
    "aiohttp",
    "bcrypt",
    "cbor2",
    "bleak",
    "websockets",
    "psutil",
)

_SELF_CHECK_PROBE_MODULE = "meshchatx.src.backend.self_check_probe"
_MESHCHATX_RUN_MODULE_FLAG = "--meshchatx-run-module"

SELF_CHECK_LABELS = {
    "stack_up": "Network Stack          ",
    "config_good": "Configuration Integrity",
    "db_good": "Database Connection    ",
    "read_write_good": "Storage Read/Write     ",
    "identity_good": "Identity Loaded        ",
    "imports_good": "Critical Imports       ",
    "storage_lock_good": "Storage Lock           ",
    "temp_fs_good": "Temp Filesystem        ",
    "public_assets_good": "Public Assets          ",
    "lxmf_router_good": "LXMF Router            ",
    "subprocess_good": "Subprocess Spawn       ",
    "run_module_good": "MeshChatX Run-Module   ",
    "bots_lifecycle": "Bot Create/Start/Stop  ",
}


def _status(ok: bool, reason: str = "") -> dict[str, str]:
    return {"status": "ok" if ok else "failed", "reason": reason or ""}


def check_python_runtime() -> dict[str, str]:
    if sys.version_info < (3, 11):
        return _status(
            False,
            f"Python {sys.version_info.major}.{sys.version_info.minor} is below 3.11",
        )
    if not sys.executable or not os.path.exists(sys.executable):
        return _status(False, f"sys.executable is missing: {sys.executable!r}")
    return _status(True)


def check_critical_imports() -> dict[str, str]:
    missing: list[str] = []
    errors: list[str] = []
    for name in _CRITICAL_IMPORTS:
        try:
            importlib.import_module(name)
        except ModuleNotFoundError:
            missing.append(name)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    if missing or errors:
        parts = []
        if missing:
            parts.append("missing " + ", ".join(missing))
        if errors:
            parts.append("errors " + " | ".join(errors))
        return _status(False, ". ".join(parts))
    return _status(True)


def check_identity(identity: Any) -> dict[str, str]:
    if identity is None:
        return _status(False, "Identity is not loaded")
    try:
        raw = getattr(identity, "hash", None)
        if raw is None:
            return _status(False, "Identity has no hash")
        if isinstance(raw, (bytes, bytearray, memoryview)):
            hx = bytes(raw).hex()
        else:
            hx = str(raw).strip().lower()
        if len(hx) != 32:
            return _status(False, f"Identity hash length is {len(hx)}, expected 32")
        return _status(True)
    except Exception as exc:
        return _status(False, f"Identity check failed: {exc}")


def check_lxmf_router(message_router: Any, local_destination: Any) -> dict[str, str]:
    if message_router is None:
        return _status(False, "LXMF message router is not initialized")
    if local_destination is None:
        return _status(False, "Local LXMF destination is not available")
    try:
        dest_hash = getattr(local_destination, "hash", None)
        if dest_hash is None:
            return _status(False, "Local LXMF destination has no hash")
    except Exception as exc:
        return _status(False, f"LXMF destination check failed: {exc}")
    return _status(True)


def check_storage_lock(base_dir: str) -> dict[str, str]:
    from meshchatx.src.backend.storage_lock import StorageLock, StorageLockError

    if not base_dir or not os.path.isdir(base_dir):
        return _status(False, "Storage directory does not exist")

    lock_dir = os.path.join(base_dir, ".self_test_storage_lock")
    try:
        if os.path.isdir(lock_dir):
            shutil.rmtree(lock_dir, ignore_errors=True)
        os.makedirs(lock_dir, exist_ok=True)

        first = StorageLock(lock_dir)
        first.acquire()
        second = StorageLock(lock_dir)
        contested = False
        try:
            second.acquire()
        except StorageLockError:
            contested = True
        except Exception as exc:
            first.release()
            return _status(False, f"Unexpected lock error: {exc}")
        else:
            second.release()
            first.release()
            return _status(False, "Second lock acquire should have failed while held")

        if not contested:
            first.release()
            return _status(False, "Storage lock did not reject a second holder")

        first.release()

        third = StorageLock(lock_dir)
        third.acquire()
        third.release()
        return _status(True)
    except Exception as exc:
        return _status(False, f"Storage lock check failed: {exc}")
    finally:
        with contextlib.suppress(Exception):
            if os.path.isdir(lock_dir):
                shutil.rmtree(lock_dir, ignore_errors=True)


def check_temp_filesystem() -> dict[str, str]:
    path = None
    try:
        fd, path = tempfile.mkstemp(prefix="meshchatx_self_check_")
        os.close(fd)
        payload = b"meshchatx-temp-check"
        with open(path, "wb") as handle:
            handle.write(payload)
        with open(path, "rb") as handle:
            if handle.read() != payload:
                return _status(False, "Temp file readback mismatch")
        return _status(True)
    except Exception as exc:
        return _status(False, f"Temp filesystem check failed: {exc}")
    finally:
        if path and os.path.exists(path):
            with contextlib.suppress(Exception):
                os.unlink(path)


def _is_frozen_executable() -> bool:
    return bool(getattr(sys, "frozen", False))


def _frontend_source_available() -> bool:
    """True when running from a source tree with Vite frontend sources.

    Built ``meshchatx/public/`` is gitignored and often absent in CI / E2E
    (Vite serves the UI). Frozen desktop builds still require bundled public.
    """
    try:
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        frontend = os.path.join(package_dir, "src", "frontend")
        return os.path.isdir(frontend) and os.path.isfile(
            os.path.join(frontend, "main.js")
        )
    except Exception:
        return False


def check_public_assets(public_path_fn: Callable[[str], str]) -> dict[str, str]:
    try:
        root = public_path_fn("")
        index_path = public_path_fn("index.html") if root else ""
        if root and os.path.isdir(root):
            if os.path.isfile(index_path):
                return _status(True)
            names = [n for n in os.listdir(root) if not n.startswith(".")]
            if names:
                return _status(True)

        # Source / CI / E2E: no built public dir, but frontend sources exist.
        if not _is_frozen_executable() and _frontend_source_available():
            return _status(True)

        if not root or not os.path.isdir(root):
            return _status(False, f"Public assets directory missing: {root!r}")
        return _status(False, "Public assets directory is empty")
    except Exception as exc:
        return _status(False, f"Public assets check failed: {exc}")


def check_meshchatx_run_module() -> dict[str, str]:
    """Verify ``--meshchatx-run-module`` re-entry used by bots/rnsh on frozen builds."""
    marker_dir = tempfile.mkdtemp(prefix="meshchatx_run_module_check_")
    marker = os.path.join(marker_dir, "probe.out")
    env = os.environ.copy()
    env["MESHCHATX_SELF_CHECK_PROBE_PATH"] = marker
    env["PYTHONUNBUFFERED"] = "1"
    env["MESHCHAT_SKIP_STORAGE_LOCK"] = "1"
    # Keep child logs/storage under the temp dir (Landlock RW + no user home writes).
    env["MESHCHAT_LOG_DIR"] = os.path.join(marker_dir, "logs")
    env["MESHCHAT_STORAGE_DIR"] = os.path.join(marker_dir, "storage")
    os.makedirs(env["MESHCHAT_LOG_DIR"], exist_ok=True)
    os.makedirs(env["MESHCHAT_STORAGE_DIR"], exist_ok=True)

    if _is_frozen_executable():
        cmd = [
            sys.executable,
            _MESHCHATX_RUN_MODULE_FLAG,
            _SELF_CHECK_PROBE_MODULE,
            "self-check",
        ]
    else:
        cmd = [
            sys.executable,
            "-m",
            "meshchatx.meshchat",
            _MESHCHATX_RUN_MODULE_FLAG,
            _SELF_CHECK_PROBE_MODULE,
            "self-check",
        ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
            env=env,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()[-500:]
            return _status(
                False,
                f"run-module exited {result.returncode}: {detail or 'no output'}",
            )
        if not os.path.isfile(marker):
            return _status(False, "Probe marker file was not written")
        with open(marker, encoding="utf-8") as handle:
            text = handle.read()
        if "ok" not in text or "self-check" not in text:
            return _status(False, f"Unexpected probe output: {text!r}")
        return _status(True)
    except subprocess.TimeoutExpired:
        return _status(False, "run-module probe timed out")
    except Exception as exc:
        return _status(False, f"run-module check failed: {exc}")
    finally:
        with contextlib.suppress(Exception):
            shutil.rmtree(marker_dir, ignore_errors=True)


def check_subprocess_spawn() -> dict[str, str]:
    """Spawn a short-lived child process (covers Windows CreateProcess / POSIX fork)."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "print('meshchatx-spawn-ok', flush=True)"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        if result.returncode != 0:
            return _status(
                False,
                f"spawn exited {result.returncode}: {(result.stderr or result.stdout or '')[-300:]}",
            )
        if "meshchatx-spawn-ok" not in (result.stdout or ""):
            return _status(False, f"Unexpected spawn output: {result.stdout!r}")
        return _status(True)
    except Exception as exc:
        return _status(False, f"Subprocess spawn check failed: {exc}")
