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
    "email.header",
    "RNS",
    "LXMF",
    "lxmfy",
    "rns_filesync",
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
    "fs_sandbox_good": "FS Sandbox Modules     ",
    "public_assets_good": "Public Assets          ",
    "lxmf_router_good": "LXMF Router            ",
    "subprocess_good": "Subprocess Spawn       ",
    "run_module_good": "MeshChatX Run-Module   ",
    "sqlite_roundtrip": "SQLite Roundtrip       ",
    "identity_roundtrip": "Identity File Roundtrip",
    "loopback_tcp": "Loopback TCP Bind      ",
    "unicode_path_good": "Unicode Path I/O       ",
    "rnode_support_good": "RNode Support Module   ",
    "bot_launcher_good": "Bot Launcher Argv      ",
    "http_status_good": "HTTP /api/v1/status    ",
    "http_app_info_good": "HTTP /api/v1/app/info  ",
    "http_config_good": "HTTP /api/v1/config    ",
    "http_db_health_good": "HTTP Database Health   ",
    "http_auth_csrf_good": "HTTP Auth CSRF         ",
    "http_bots_status_good": "HTTP Bots Status       ",
    "http_security_good": "HTTP Server Security   ",
    "http_interfaces_good": "HTTP RNS Interfaces    ",
    "http_reticulum_instance_good": "HTTP RNS Instance      ",
    "http_identities_good": "HTTP Identities        ",
    "http_favourites_good": "HTTP Favourites        ",
    "http_telephone_good": "HTTP Telephone Status  ",
    "http_plugins_good": "HTTP Plugins API       ",
    "http_plugins_trust_good": "HTTP Plugin Trust List ",
    "http_sideband_plugins_good": "HTTP Sideband Plugins  ",
    "http_sideband_config_good": "HTTP Sideband Config   ",
    "http_rrc_hubs_good": "HTTP RRC Hubs          ",
    "http_rrc_servers_good": "HTTP RRC Servers       ",
    "plugins_runtime_good": "Plugin Manager Runtime ",
    "websocket_good": "WebSocket /ws          ",
    "websocket_rns_link_good": "WebSocket RNS Link API ",
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
    """Verify StorageLock acquire/contest/release (native flock/msvcrt or soft)."""
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
        mode = "soft" if getattr(first, "_soft", False) else "native"
        second = StorageLock(lock_dir)
        contested = False
        try:
            second.acquire()
        except StorageLockError:
            contested = True
        except Exception as exc:
            first.release()
            return _status(False, f"Unexpected lock error ({mode}): {exc}")
        else:
            second.release()
            first.release()
            return _status(
                False,
                f"Second lock acquire should have failed while held ({mode})",
            )

        if not contested:
            first.release()
            return _status(
                False,
                f"Storage lock did not reject a second holder ({mode})",
            )

        first.release()

        third = StorageLock(lock_dir)
        third.acquire()
        third.release()

        # Soft-lock path used when flock is ENOSYS (Android / some FS). Exercise it
        # on every CI OS so regressions in the fallback are caught on Win/macOS/Linux.
        soft_dir = os.path.join(base_dir, ".self_test_storage_lock_soft")
        if os.path.isdir(soft_dir):
            shutil.rmtree(soft_dir, ignore_errors=True)
        os.makedirs(soft_dir, exist_ok=True)
        soft_result = _check_storage_lock_soft_fallback(soft_dir)
        if soft_result["status"] != "ok":
            return soft_result

        return _status(True)
    except Exception as exc:
        return _status(False, f"Storage lock check failed: {exc}")
    finally:
        with contextlib.suppress(Exception):
            if os.path.isdir(lock_dir):
                shutil.rmtree(lock_dir, ignore_errors=True)
            soft_dir = os.path.join(base_dir, ".self_test_storage_lock_soft")
            if os.path.isdir(soft_dir):
                shutil.rmtree(soft_dir, ignore_errors=True)


def _check_storage_lock_soft_fallback(lock_dir: str) -> dict[str, str]:
    """Force ENOSYS flock path and verify soft PID lock contest/release."""
    import errno
    from unittest.mock import patch

    from meshchatx.src.backend.storage_lock import StorageLock, StorageLockError

    if sys.platform == "win32":
        # Windows uses msvcrt, so soft fallback is Unix-only. Still verify a second
        # native holder is rejected (covered above) and return ok here.
        return _status(True)

    def _enosys_flock(*_args, **_kwargs):
        raise OSError(errno.ENOSYS, "Function not implemented")

    with patch("fcntl.flock", side_effect=_enosys_flock):
        first = StorageLock(lock_dir)
        first.acquire()
        if not getattr(first, "_soft", False):
            first.release()
            return _status(False, "Expected soft lock after flock ENOSYS")
        second = StorageLock(lock_dir)
        try:
            second.acquire()
        except StorageLockError:
            pass
        else:
            second.release()
            first.release()
            return _status(False, "Soft lock did not reject same-process second holder")
        first.release()
        third = StorageLock(lock_dir)
        third.acquire()
        if not getattr(third, "_soft", False):
            third.release()
            return _status(False, "Soft re-acquire after release did not use soft mode")
        third.release()
    return _status(True)


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


def check_fs_sandbox() -> dict[str, str]:
    """Verify Landlock/AppContainer/Seccomp helpers import and report status.

    Does not enable sandboxes. Confirms modules load and exchange-folder
    helpers create MeshChatX subdirs under a fake profile root.
    """
    try:
        from meshchatx.src.backend import appcontainer_sandbox as ac
        from meshchatx.src.backend import landlock_sandbox as ll
        from meshchatx.src.backend import seccomp_sandbox as sc
    except Exception as exc:
        return _status(False, f"sandbox import failed: {exc}")

    bool_checks = (
        ("landlock_kernel_supported", ll.landlock_kernel_supported()),
        ("landlock_requested", ll.landlock_requested()),
        ("landlock_disabled_by_env", ll.landlock_disabled_by_env()),
        ("appcontainer_supported", ac.appcontainer_supported()),
        ("appcontainer_requested", ac.appcontainer_requested()),
        ("appcontainer_disabled_by_env", ac.appcontainer_disabled_by_env()),
        ("appcontainer_forced", ac.appcontainer_forced()),
        ("is_appcontainer_child", ac.is_appcontainer_child()),
        ("seccomp_kernel_supported", sc.seccomp_kernel_supported()),
        ("seccomp_requested", sc.seccomp_requested()),
        ("seccomp_disabled_by_env", sc.seccomp_disabled_by_env()),
    )
    for name, value in bool_checks:
        if not isinstance(value, bool):
            return _status(False, f"{name} returned non-bool: {type(value)!r}")

    if ac.USER_EXCHANGE_DIR_NAME != "MeshChatX":
        return _status(
            False,
            f"unexpected USER_EXCHANGE_DIR_NAME={ac.USER_EXCHANGE_DIR_NAME!r}",
        )

    try:
        with tempfile.TemporaryDirectory(prefix="meshchatx_exchange_") as tmp:
            documents = os.path.join(tmp, "Documents")
            downloads = os.path.join(tmp, "Downloads")
            pictures = os.path.join(tmp, "Pictures")
            os.makedirs(documents)
            os.makedirs(downloads)
            os.makedirs(pictures)

            original_profile = ac._user_profile_dir
            original_known = ac._windows_known_folder
            try:
                ac._user_profile_dir = lambda: tmp  # type: ignore[assignment]
                ac._windows_known_folder = lambda _fid: None  # type: ignore[assignment]
                roots = ac.collect_user_exchange_roots(create=True)
            finally:
                ac._user_profile_dir = original_profile  # type: ignore[assignment]
                ac._windows_known_folder = original_known  # type: ignore[assignment]

            expected = {
                os.path.join(documents, "MeshChatX"),
                os.path.join(downloads, "MeshChatX"),
                os.path.join(pictures, "MeshChatX"),
            }
            if set(roots) != expected:
                return _status(
                    False,
                    f"exchange roots mismatch: got={roots!r} expected={sorted(expected)!r}",
                )
            for path in expected:
                if not os.path.isdir(path):
                    return _status(False, f"exchange dir missing: {path}")
    except Exception as exc:
        return _status(False, f"exchange roots check failed: {exc}")

    return _status(True)


def _is_frozen_executable() -> bool:
    return bool(getattr(sys, "frozen", False))


def _frontend_source_available() -> bool:
    """True when running from a source tree with Vite frontend sources.

    Built meshchatx/public/ is gitignored and often absent in CI / E2E
    (Vite serves the UI). Frozen desktop builds still require bundled public.
    """
    try:
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        frontend = os.path.join(package_dir, "src", "frontend")
        return os.path.isdir(frontend) and os.path.isfile(
            os.path.join(frontend, "main.js"),
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
    """Verify --meshchatx-run-module re-entry used by bots/rnsh on frozen builds."""
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
            stdin=subprocess.DEVNULL,
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
    """Spawn a short-lived child process (covers Windows CreateProcess / POSIX fork).

    Frozen desktop builds (AppImage / EXE / macOS) set sys.executable to
    MeshChatX itself, which rejects Python -c. Those builds re-enter via
    --meshchatx-run-module like bots and rnsh.
    """
    try:
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        if _is_frozen_executable():
            env["MESHCHAT_SKIP_STORAGE_LOCK"] = "1"
            cmd = [
                sys.executable,
                _MESHCHATX_RUN_MODULE_FLAG,
                _SELF_CHECK_PROBE_MODULE,
                "spawn-ok",
            ]
            expected = "meshchatx-self-check-probe"
        else:
            cmd = [
                sys.executable,
                "-c",
                "print('meshchatx-spawn-ok', flush=True)",
            ]
            expected = "meshchatx-spawn-ok"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return _status(
                False,
                f"spawn exited {result.returncode}: {(result.stderr or result.stdout or '')[-300:]}",
            )
        if expected not in (result.stdout or ""):
            return _status(False, f"Unexpected spawn output: {result.stdout!r}")
        return _status(True)
    except Exception as exc:
        return _status(False, f"Subprocess spawn check failed: {exc}")


def check_sqlite_roundtrip(base_dir: str | None = None) -> dict[str, str]:
    """Create a temp SQLite DB, write a row, read it back, then delete the file."""
    import sqlite3

    root = base_dir if base_dir and os.path.isdir(base_dir) else tempfile.gettempdir()
    path = None
    try:
        fd, path = tempfile.mkstemp(
            prefix="meshchatx_self_check_",
            suffix=".db",
            dir=root,
        )
        os.close(fd)
        conn = sqlite3.connect(path)
        try:
            conn.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY, note TEXT)")
            conn.execute(
                "INSERT INTO probe (note) VALUES (?)",
                ("meshchatx-sqlite-ok",),
            )
            conn.commit()
            row = conn.execute("SELECT note FROM probe WHERE id = 1").fetchone()
        finally:
            conn.close()
        if not row or row[0] != "meshchatx-sqlite-ok":
            return _status(False, f"Unexpected SQLite readback: {row!r}")
        return _status(True)
    except Exception as exc:
        return _status(False, f"SQLite roundtrip failed: {exc}")
    finally:
        if path and os.path.exists(path):
            with contextlib.suppress(Exception):
                os.unlink(path)


def check_identity_file_roundtrip(base_dir: str | None = None) -> dict[str, str]:
    """Generate a Reticulum identity, save to disk, reload, and compare hashes."""
    try:
        import RNS
    except Exception as exc:
        return _status(False, f"RNS import failed: {exc}")

    root = base_dir if base_dir and os.path.isdir(base_dir) else tempfile.gettempdir()
    path = None
    try:
        fd, path = tempfile.mkstemp(
            prefix="meshchatx_id_",
            suffix=".identity",
            dir=root,
        )
        os.close(fd)
        identity = RNS.Identity(create_keys=True)
        orig_hash = identity.hash
        if orig_hash is None:
            return _status(False, "Generated identity hash is None")
        original = bytes(orig_hash)
        priv_key = identity.get_private_key()
        if priv_key is None:
            return _status(False, "Generated private key is None")
        with open(path, "wb") as handle:
            handle.write(priv_key)
        loaded = RNS.Identity(create_keys=False)
        loaded.load(path)
        loaded_hash = loaded.hash
        if loaded_hash is None:
            return _status(False, "Loaded identity hash is None")
        if bytes(loaded_hash) != original:
            return _status(False, "Reloaded identity hash mismatch")
        return _status(True)
    except Exception as exc:
        return _status(False, f"Identity file roundtrip failed: {exc}")
    finally:
        if path and os.path.exists(path):
            with contextlib.suppress(Exception):
                os.unlink(path)


def check_loopback_tcp() -> dict[str, str]:
    """Bind and accept a short-lived TCP connection on 127.0.0.1."""
    import socket
    import threading

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        host, port = server.getsockname()
        received: dict[str, bytes] = {}

        def _accept():
            conn, _addr = server.accept()
            try:
                received["data"] = conn.recv(64)
                conn.sendall(b"meshchatx-tcp-ok")
            finally:
                conn.close()

        thread = threading.Thread(target=_accept, daemon=True)
        thread.start()
        client = socket.create_connection((host, port), timeout=5)
        try:
            client.sendall(b"ping")
            reply = client.recv(64)
        finally:
            client.close()
        thread.join(timeout=5)
        server.close()
        if received.get("data") != b"ping":
            return _status(False, f"Server received {received.get('data')!r}")
        if reply != b"meshchatx-tcp-ok":
            return _status(False, f"Unexpected client reply: {reply!r}")
        return _status(True)
    except Exception as exc:
        return _status(False, f"Loopback TCP check failed: {exc}")


def check_unicode_path(base_dir: str | None = None) -> dict[str, str]:
    """Write and read a file whose name contains non-ASCII characters."""
    root = base_dir if base_dir and os.path.isdir(base_dir) else tempfile.gettempdir()
    path = os.path.join(root, "meshchatx_self_check_ユニコード.txt")
    try:
        payload = "meshchatx-unicode-ok-αβγ"
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(payload)
        with open(path, encoding="utf-8") as handle:
            if handle.read() != payload:
                return _status(False, "Unicode path readback mismatch")
        return _status(True)
    except Exception as exc:
        return _status(False, f"Unicode path check failed: {exc}")
    finally:
        with contextlib.suppress(Exception):
            if os.path.exists(path):
                os.unlink(path)


def check_rnode_support() -> dict[str, str]:
    """Import rnode_support and verify transport classification helpers."""
    try:
        from meshchatx.src.backend import rnode_support as rn

        cases = (
            ({"port": "tcp://127.0.0.1"}, "tcp"),
            ({"port": "ble://aa:bb:cc:dd:ee:ff"}, "ble"),
            ({"port": "/dev/ttyUSB0"}, "serial"),
            ({"port": "", "allow_bluetooth": "true"}, "bluetooth_classic"),
        )
        for iface, expected in cases:
            got = rn._rnode_iface_transport(iface)
            if got != expected:
                return _status(
                    False,
                    f"transport for {iface!r} was {got!r}, expected {expected!r}",
                )
        if not rn.rnode_port_is_tcp("tcp://127.0.0.1"):
            return _status(False, "rnode_port_is_tcp rejected tcp://127.0.0.1")
        if rn.rnode_port_is_tcp("/dev/ttyUSB0"):
            return _status(False, "rnode_port_is_tcp accepted serial path")
        return _status(True)
    except Exception as exc:
        return _status(False, f"RNode support check failed: {exc}")


def check_bot_launcher() -> dict[str, str]:
    """Verify BotHandler launcher argv for frozen and unfrozen modes."""
    try:
        from unittest.mock import patch

        from meshchatx.src.backend.bot_handler import (
            _BOT_PROCESS_MODULE,
            _MESHCHATX_RUN_MODULE_FLAG,
            BotHandler,
        )

        handler = BotHandler.__new__(BotHandler)
        handler.runner_path = os.path.join("fake", "bot_process.py")

        with patch.object(BotHandler, "_is_frozen_executable", return_value=False):
            unfrozen = handler._resolve_bot_launcher()
        if unfrozen != [sys.executable, handler.runner_path]:
            return _status(False, f"Unexpected unfrozen launcher: {unfrozen!r}")

        with patch.object(BotHandler, "_is_frozen_executable", return_value=True):
            frozen = handler._resolve_bot_launcher()
        expected_frozen = [
            sys.executable,
            _MESHCHATX_RUN_MODULE_FLAG,
            _BOT_PROCESS_MODULE,
        ]
        if frozen != expected_frozen:
            return _status(False, f"Unexpected frozen launcher: {frozen!r}")
        return _status(True)
    except Exception as exc:
        return _status(False, f"Bot launcher check failed: {exc}")


def _ensure_app_session_secret(app: Any) -> None:
    if getattr(app, "session_secret_key", None):
        return
    secret = None
    try:
        if app.config is not None:
            secret = app.config.auth_session_secret.get()
    except Exception:
        secret = None
    if not secret:
        import secrets

        secret = secrets.token_urlsafe(32)
        with contextlib.suppress(Exception):
            if app.config is not None:
                app.config.auth_session_secret.set(secret)
    app.session_secret_key = secret


def _ensure_awaitable_method(app: Any, name: str) -> None:
    """Ensure app.name is awaitable (unit tests often patch with sync MagicMock)."""
    import asyncio

    method = getattr(app, name, None)
    if method is None:
        return
    try:
        result = method()
    except TypeError:
        return
    except Exception:
        return
    if asyncio.iscoroutine(result):
        result.close()
        return

    async def _noop(*_args, **_kwargs):
        return None

    try:
        object.__setattr__(app, name, _noop)
    except Exception:
        setattr(app, name, _noop)


async def _build_probe_aio_app(app: Any):
    import asyncio

    from aiohttp import web
    from aiohttp_session import setup as setup_session

    _ensure_app_session_secret(app)
    _ensure_awaitable_method(app, "send_config_to_websocket_clients")
    broadcast = getattr(app, "websocket_broadcast", None)
    if callable(broadcast):
        try:
            maybe = broadcast("{}")
            if asyncio.iscoroutine(maybe):
                maybe.close()
            else:

                async def _broadcast(_data):
                    return None

                try:
                    object.__setattr__(app, "websocket_broadcast", _broadcast)
                except Exception:
                    app.websocket_broadcast = _broadcast
        except Exception:
            pass
    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw, demo_mw = app._define_routes(routes)
    aio_app = web.Application(
        middlewares=[auth_mw, mime_mw, sec_mw, csrf_mw, ip_mw, demo_mw],
    )
    setup_session(aio_app, app._encrypted_cookie_storage(use_https=False))
    aio_app.add_routes(routes)
    return aio_app


_WEB_PROBE_KEYS = (
    "http_status_good",
    "http_app_info_good",
    "http_config_good",
    "http_db_health_good",
    "http_auth_csrf_good",
    "http_bots_status_good",
    "http_security_good",
    "http_interfaces_good",
    "http_reticulum_instance_good",
    "http_identities_good",
    "http_favourites_good",
    "http_telephone_good",
    "http_plugins_good",
    "http_plugins_trust_good",
    "http_sideband_plugins_good",
    "http_sideband_config_good",
    "http_rrc_hubs_good",
    "http_rrc_servers_good",
    "websocket_good",
    "websocket_rns_link_good",
)


def check_plugins_runtime(app: Any) -> dict[str, str]:
    """Verify plugin manager is wired and bundled example is available when enabled."""
    manager = getattr(app, "plugin_manager", None)
    if manager is None:
        return _status(False, "plugin_manager is not initialized")
    try:
        plugins = manager.list_plugins()
    except Exception as exc:
        return _status(False, f"list_plugins failed: {exc}")
    if not isinstance(plugins, list):
        return _status(False, "list_plugins did not return a list")
    plugins_enabled = bool(getattr(app, "plugins_enabled", True))
    if not plugins_enabled:
        return _status(True)
    bundled_id = "com.meshchatx.mcx-bugs"
    if any(isinstance(item, dict) and item.get("id") == bundled_id for item in plugins):
        return _status(True)
    try:
        manager.install_bundled_examples()
        plugins = manager.list_plugins()
    except Exception as exc:
        return _status(False, f"install_bundled_examples failed: {exc}")
    if any(isinstance(item, dict) and item.get("id") == bundled_id for item in plugins):
        return _status(True)
    return _status(False, f"bundled plugin {bundled_id} missing after install")


async def _probe_rns_link_api(ws: Any, *, timeout: float = 10.0) -> dict[str, str]:
    """Exercise generic rns.link.* handlers without requiring a live mesh peer."""
    import asyncio
    import json

    from aiohttp import WSMsgType

    request_id = "self-check-rns-link"
    try:
        await ws.send_str(
            json.dumps(
                {
                    "type": "rns.link.close",
                    "destination_hash": "aa" * 16,
                    "aspect": "meshchatx.selfcheck",
                    "request_id": request_id,
                },
            ),
        )
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                return _status(False, "rns.link.close reply timed out")
            msg = await asyncio.wait_for(ws.receive(), timeout=remaining)
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                payload = json.loads(msg.data)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            if payload.get("type") != "rns.link.close":
                continue
            if payload.get("request_id") != request_id:
                continue
            status = payload.get("status")
            if status not in ("success", "failure"):
                return _status(False, f"unexpected status={status!r}")
            # No cached link is expected in self-check, so failure is the normal path.
            if status == "failure" and payload.get("failure_reason") not in (
                None,
                "no_active_link",
            ):
                return _status(
                    False,
                    f"unexpected failure_reason={payload.get('failure_reason')!r}",
                )
            return _status(True)
    except TimeoutError:
        return _status(False, "rns.link.close reply timed out")
    except Exception as exc:
        return _status(False, str(exc))


async def _probe_json_get(
    client: Any,
    path: str,
    *,
    require_keys: tuple[str, ...] = (),
    require_nested: tuple[tuple[str, type], ...] = (),
    validate: Callable[[dict[str, Any]], str | None] | None = None,
    timeout: float = 15.0,
) -> dict[str, str]:
    import asyncio

    async def _once() -> dict[str, str]:
        resp = await client.get(path)
        body = await resp.json()
        if resp.status != 200 or not isinstance(body, dict):
            return _status(False, f"{path} status={resp.status}")
        for key in require_keys:
            if key not in body:
                return _status(False, f"{path} missing key {key!r}")
        for key, expected_type in require_nested:
            value = body.get(key)
            if not isinstance(value, expected_type):
                return _status(
                    False,
                    f"{path} key {key!r} type={type(value).__name__}",
                )
        if validate is not None:
            reason = validate(body)
            if reason:
                return _status(False, reason)
        return _status(True)

    try:
        return await asyncio.wait_for(_once(), timeout=timeout)
    except TimeoutError:
        return _status(False, f"{path} timed out after {timeout:.0f}s")
    except Exception as exc:
        return _status(False, f"{path}: {exc}")


async def _run_web_api_probes(app: Any) -> dict[str, dict[str, str]]:
    """Hit critical HTTP + WebSocket endpoints on an ephemeral TestServer."""
    import asyncio
    import json

    from aiohttp import WSMsgType
    from aiohttp.test_utils import TestClient, TestServer

    results: dict[str, dict[str, str]] = {
        key: _status(False, "not run") for key in _WEB_PROBE_KEYS
    }

    try:
        aio_app = await _build_probe_aio_app(app)
    except Exception as exc:
        failed = _status(False, f"Failed to build probe app: {exc}")
        return dict.fromkeys(results, failed)

    try:
        async with TestClient(TestServer(aio_app)) as client:
            results["http_status_good"] = await _probe_json_get(
                client,
                "/api/v1/status",
                require_keys=("status",),
                validate=lambda body: (
                    None if body.get("status") == "ok" else f"status body={body!r}"
                ),
            )
            results["http_app_info_good"] = await _probe_json_get(
                client,
                "/api/v1/app/info",
                require_nested=(("app_info", dict),),
                validate=lambda body: (
                    None
                    if body.get("app_info", {}).get("version")
                    and isinstance(
                        body.get("app_info", {}).get("appcontainer_supported"),
                        bool,
                    )
                    and isinstance(
                        body.get("app_info", {}).get("landlock_active"),
                        bool,
                    )
                    and isinstance(
                        body.get("app_info", {}).get("fs_sandbox_active"),
                        bool,
                    )
                    and isinstance(body.get("app_info", {}).get("seccomp_active"), bool)
                    else "app_info missing version or FS sandbox status fields"
                ),
            )
            results["http_config_good"] = await _probe_json_get(
                client,
                "/api/v1/config",
                require_nested=(("config", dict),),
            )
            results["http_db_health_good"] = await _probe_json_get(
                client,
                "/api/v1/database/health",
                require_nested=(("database", dict),),
            )

            try:
                resp = await asyncio.wait_for(
                    client.get("/api/v1/auth/csrf"),
                    timeout=15,
                )
                body = await resp.json()
                token = body.get("csrf_token") if isinstance(body, dict) else None
                if resp.status != 200 or not token:
                    results["http_auth_csrf_good"] = _status(
                        False,
                        f"csrf status={resp.status}",
                    )
                else:
                    auth_resp = await asyncio.wait_for(
                        client.get("/api/v1/auth/status"),
                        timeout=15,
                    )
                    auth_body = await auth_resp.json()
                    if auth_resp.status != 200 or "auth_enabled" not in auth_body:
                        results["http_auth_csrf_good"] = _status(
                            False,
                            f"auth/status status={auth_resp.status}",
                        )
                    else:
                        results["http_auth_csrf_good"] = _status(True)
            except TimeoutError:
                results["http_auth_csrf_good"] = _status(False, "auth csrf timed out")
            except Exception as exc:
                results["http_auth_csrf_good"] = _status(False, str(exc))

            results["http_bots_status_good"] = await _probe_json_get(
                client,
                "/api/v1/bots/status",
                require_keys=("status", "templates"),
            )
            results["http_security_good"] = await _probe_json_get(
                client,
                "/api/v1/server/security",
                require_keys=(
                    "listen_host",
                    "listen_port",
                    "auth_enabled",
                    "landlock_kernel_supported",
                    "landlock_requested",
                    "landlock_auto_enabled",
                    "landlock_disabled_by_env",
                    "landlock_active",
                    "appcontainer_supported",
                    "appcontainer_requested",
                    "appcontainer_auto_enabled",
                    "appcontainer_disabled_by_env",
                    "appcontainer_active",
                    "fs_sandbox_active",
                    "seccomp_kernel_supported",
                    "seccomp_requested",
                    "seccomp_auto_enabled",
                    "seccomp_disabled_by_env",
                    "seccomp_active",
                ),
            )
            results["http_interfaces_good"] = await _probe_json_get(
                client,
                "/api/v1/reticulum/interfaces",
                require_nested=(("interfaces", dict),),
            )
            results["http_reticulum_instance_good"] = await _probe_json_get(
                client,
                "/api/v1/reticulum/instance",
                require_nested=(("instance", dict),),
                validate=lambda body: (
                    None
                    if isinstance(body.get("instance"), dict)
                    and "share_instance" in body["instance"]
                    and "local_hops_delta" in body["instance"]
                    else "instance missing share_instance/local_hops_delta"
                ),
            )
            results["http_identities_good"] = await _probe_json_get(
                client,
                "/api/v1/identities",
                require_nested=(("identities", list),),
            )
            results["http_favourites_good"] = await _probe_json_get(
                client,
                "/api/v1/favourites",
                require_nested=(("favourites", list),),
            )
            results["http_telephone_good"] = await _probe_json_get(
                client,
                "/api/v1/telephone/status",
                require_keys=("enabled",),
            )
            results["http_plugins_good"] = await _probe_json_get(
                client,
                "/api/v1/plugins",
                require_keys=("plugins_enabled",),
                require_nested=(("plugins", list),),
            )
            results["http_plugins_trust_good"] = await _probe_json_get(
                client,
                "/api/v1/plugins/trusted-publishers",
                require_keys=("tampered",),
                require_nested=(("publishers", list),),
            )
            results["http_sideband_plugins_good"] = await _probe_json_get(
                client,
                "/api/v1/sideband-plugins",
                require_nested=(("config", dict), ("plugins", list)),
            )
            results["http_sideband_config_good"] = await _probe_json_get(
                client,
                "/api/v1/sideband-plugins/config",
                require_keys=(
                    "service_plugins_enabled",
                    "command_plugins_enabled",
                ),
            )
            results["http_rrc_hubs_good"] = await _probe_json_get(
                client,
                "/api/v1/rrc/hubs",
                require_nested=(("hubs", list),),
            )
            results["http_rrc_servers_good"] = await _probe_json_get(
                client,
                "/api/v1/rrc/servers",
                require_nested=(("hubs", list),),
            )

            try:
                ws = await asyncio.wait_for(client.ws_connect("/ws"), timeout=15)
                try:
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=5)
                    except TimeoutError:
                        if ws.closed:
                            results["websocket_good"] = _status(
                                False,
                                "ws closed without first message",
                            )
                        else:
                            # Connection works, and first push may be absent under test doubles.
                            results["websocket_good"] = _status(True)
                    else:
                        if msg.type not in (WSMsgType.TEXT, WSMsgType.BINARY):
                            results["websocket_good"] = _status(
                                False,
                                f"unexpected ws message type={msg.type}",
                            )
                        elif msg.type == WSMsgType.TEXT:
                            try:
                                payload = json.loads(msg.data)
                                ok = isinstance(payload, dict)
                            except Exception:
                                ok = False
                            results["websocket_good"] = _status(
                                ok,
                                "" if ok else "first ws message was not JSON object",
                            )
                        else:
                            results["websocket_good"] = _status(True)

                    if results["websocket_good"]["status"] == "ok":
                        results["websocket_rns_link_good"] = await _probe_rns_link_api(
                            ws,
                        )
                    else:
                        results["websocket_rns_link_good"] = _status(
                            False,
                            "skipped: websocket_good failed",
                        )
                finally:
                    await ws.close()
            except Exception as exc:
                results["websocket_good"] = _status(False, str(exc))
                results["websocket_rns_link_good"] = _status(False, str(exc))
    except Exception as exc:
        failed = _status(False, f"Web probe client failed: {exc}")
        for key in results:
            if results[key]["status"] != "ok":
                results[key] = failed

    return results


def check_web_stack(app: Any) -> dict[str, dict[str, str]]:
    """Run HTTP/WebSocket probes against an ephemeral aiohttp TestServer."""
    import asyncio

    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_run_web_api_probes(app))

        # Already inside an event loop (e.g. aiohttp request handler).
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(_run_web_api_probes(app))).result(
                timeout=90,
            )
    except Exception as exc:
        failed = _status(False, f"Web stack check failed: {exc}")
        return dict.fromkeys(_WEB_PROBE_KEYS, failed)
