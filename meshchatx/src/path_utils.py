# SPDX-License-Identifier: 0BSD

"""Filesystem and HTTP client helpers used at startup and in the web layer."""

import os
import sys
import tempfile

from aiohttp import web


def resolve_log_dir():
    """Choose a writable log directory across container, desktop, and Windows."""
    env_dir = os.environ.get("MESHCHAT_LOG_DIR")
    candidates = []
    if env_dir:
        candidates.append(env_dir)

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


def request_client_ip(request: web.Request) -> str:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    if request.remote:
        return request.remote
    return ""


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
