# SPDX-License-Identifier: 0BSD

"""Filesystem and HTTP client helpers used at startup and in the web layer."""

import os
import sys
import tempfile

from aiohttp import web


def is_path_within_dir(path: str, directory: str) -> bool:
    """Return True when path resolves inside directory (realpath + separator)."""
    if not path or not directory:
        return False
    candidate = os.path.normcase(os.path.normpath(os.path.realpath(path)))
    root = os.path.normcase(os.path.normpath(os.path.realpath(directory)))
    return candidate == root or candidate.startswith(root + os.sep)


def safe_path_under_dir(directory: str, filename: str) -> str | None:
    """Resolve filename as a basename under directory, or None if unsafe.

    Rejects NUL, empty names, dot, dot-dot, and drive-letter basenames.
    The result is realpath-checked so it cannot escape directory.
    """
    if not isinstance(directory, str) or not directory:
        return None
    if not isinstance(filename, str) or not filename or "\x00" in filename:
        return None
    base = os.path.basename(filename.replace("\\", "/"))
    if not base or base in {".", ".."} or ":" in base:
        return None
    path = os.path.realpath(os.path.join(directory, base))
    root = os.path.realpath(directory)
    if path != root and not path.startswith(root + os.sep):
        return None
    return path


def resolve_path_under_dir(directory: str, user_path: str) -> str | None:
    """Join user_path under directory and return realpath if contained, else None.

    Unlike safe_path_under_dir, relative subpaths are allowed when they stay
    inside directory after realpath normalization.
    """
    if not isinstance(directory, str) or not directory:
        return None
    if not isinstance(user_path, str) or not user_path or "\x00" in user_path:
        return None
    cleaned = user_path.replace("\\", "/").lstrip("/")
    if not cleaned or cleaned in {".", ".."}:
        return None
    joined = os.path.join(directory, cleaned)
    if not is_path_within_dir(joined, directory):
        return None
    return os.path.realpath(joined)


def resolve_log_dir():
    """Choose a writable log directory across container, desktop, and Windows."""
    env_dir = os.environ.get("MESHCHAT_LOG_DIR")
    candidates = []
    if env_dir:
        candidates.append(env_dir)

    storage_dir = os.environ.get("MESHCHAT_STORAGE_DIR")
    if storage_dir:
        candidates.append(os.path.join(storage_dir, "logs"))

    candidates.append("/config/logs")

    if os.name == "nt":
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if appdata:
            candidates.append(os.path.join(appdata, "MeshChatX", "logs"))

    home_dir = os.path.expanduser("~")
    candidates.append(os.path.join(home_dir, ".reticulum-meshchatx", "logs"))
    candidates.append(os.path.join(tempfile.gettempdir(), "meshchatx", "logs"))

    for path in candidates:
        if not path:
            continue
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except PermissionError:
            continue
        except OSError:
            continue

    return None


def resolve_meshchat_data_roots(
    *,
    data_dir: str | None,
    storage_dir: str | None,
    reticulum_config_dir: str | None,
) -> tuple[str | None, str | None]:
    """Apply MESHCHAT_DATA_DIR / --data-dir when explicit roots are unset.

    Layout under data_dir:
      storage/     MeshChatX databases and identity tree
      .reticulum/  Reticulum interfaces and transport config
    """
    root = (data_dir or os.environ.get("MESHCHAT_DATA_DIR") or "").strip()
    if not root:
        return storage_dir, reticulum_config_dir
    root = os.path.abspath(os.path.expanduser(root))
    out_storage = storage_dir
    out_reticulum = reticulum_config_dir
    if not out_storage:
        out_storage = os.path.join(root, "storage")
    if not out_reticulum:
        out_reticulum = os.path.join(root, ".reticulum")
    return out_storage, out_reticulum


def request_client_ip(
    request: web.Request,
    trusted_proxy_cidrs: str | None = None,
) -> str:
    """Return the client IP, trusting X-Forwarded-For only from configured proxies.

    When trusted_proxy_cidrs is empty, X-Forwarded-For is ignored so clients
    cannot spoof allowlist or login lockout keys.
    """
    remote = (request.remote or "").strip()
    xff = request.headers.get("X-Forwarded-For")
    if xff and trusted_proxy_cidrs:
        from meshchatx.src.backend.ip_allowlist import client_ip_allowed

        if remote and client_ip_allowed(remote, trusted_proxy_cidrs):
            return xff.split(",")[0].strip()
    return remote


def get_file_path(filename):
    # NOTE: this is required to be able to pack our app with cxfreeze as an exe, otherwise it can't access bundled assets
    # this returns a file path based on if we are running meshchat.py directly, or if we have packed it as an exe with cxfreeze
    # https://cx-freeze.readthedocs.io/en/latest/faq.html#using-data-files
    # bearer:disable python_lang_path_traversal
    filename = filename.rstrip("/\\")

    if getattr(sys, "frozen", False):
        datadir = os.path.dirname(sys.executable)
        return os.path.join(datadir, filename)

    package_dir = os.path.dirname(os.path.dirname(__file__))
    package_path = os.path.join(package_dir, filename)
    if os.path.exists(package_path):
        return package_path

    repo_root = os.path.dirname(package_dir)
    repo_path = os.path.join(repo_root, filename)
    if os.path.exists(repo_path):
        return repo_path

    return package_path
