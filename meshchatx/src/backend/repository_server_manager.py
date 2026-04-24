# SPDX-License-Identifier: 0BSD

"""Wheel and file repository under identity storage (uploads + refreshed PyPI wheels)."""

from __future__ import annotations

import html
import http.server
import json
import logging
import os
import re
import shutil
import socketserver
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

_PYPI_USER_AGENT = "MeshChatXRepositoryBundler/1 (+https://github.com/)"

_MESHCHATX_BUNDLE_PIP_NAME = "reticulum-meshchatx"

_DEFAULT_PACKAGES = (
    "rns",
    "rnspure",
    "lxmf",
    "rnsh",
    "nomadnet",
    _MESHCHATX_BUNDLE_PIP_NAME,
)


def _parse_extra_packages() -> tuple[str, ...]:
    raw = (os.environ.get("MESHCHAT_REPOSITORY_EXTRA_PIP") or "").strip()
    if not raw:
        return ()
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    return tuple(dict.fromkeys(parts))


def bundled_pip_targets() -> tuple[str, ...]:
    return tuple(dict.fromkeys(_DEFAULT_PACKAGES + _parse_extra_packages()))


def meshchat_bundle_project_root() -> Path | None:
    """Directory containing ``pyproject.toml`` for this MeshChatX tree (repo layout helper)."""
    here = Path(__file__).resolve()
    for anc in here.parents:
        meta = anc / "pyproject.toml"
        if not meta.is_file():
            continue
        try:
            head = meta.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        if "reticulum-meshchatx" not in head.lower():
            continue
        if (anc / "meshchatx").is_dir():
            return anc
    return None


REPOSITORY_BUNDLED_PUBLIC_PARTS = ("repository-server-bundled", "bundled")


def public_bundled_wheels_dir(public_dir: str) -> str:
    """Directory under ``public_dir`` where build-staged wheels live (HTTP + optional pip fallback)."""
    return os.path.join(public_dir, *REPOSITORY_BUNDLED_PUBLIC_PARTS)


def _pip_spec_stem(spec: str) -> str:
    s = spec.strip().split("[", 1)[0].strip()
    for op in ("===", "==", ">=", "<=", "!=", "~=", ">", "<"):
        if op in s:
            s = s.split(op, 1)[0].strip()
            break
    return s.strip() or spec.strip()


def _pypi_project_json(canonical_name: str) -> dict[str, Any] | None:
    safe = urllib.parse.quote(canonical_name)
    url = f"https://pypi.org/pypi/{safe}/json"
    req = urllib.request.Request(url, headers={"User-Agent": _PYPI_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        logging.warning("PyPI HTTP error for %s: %s %s", canonical_name, e.code, body)
        return None
    except Exception:
        logging.exception("PyPI JSON fetch failed for %s", canonical_name)
        return None


def _pypi_pick_wheel_entry(urls: list[dict[str, Any]]) -> dict[str, Any] | None:
    wheels = [
        u
        for u in urls
        if isinstance(u, dict)
        and u.get("packagetype") == "bdist_wheel"
        and u.get("url")
        and u.get("filename")
    ]
    if not wheels:
        return None

    def sort_key(u: dict[str, Any]) -> tuple[int, int, str]:
        fn = str(u.get("filename") or "").lower()
        if fn.endswith("py3-none-any.whl") or fn.endswith("py2.py3-none-any.whl"):
            tier = 0
        elif "-none-any.whl" in fn:
            tier = 1
        elif "none-any" in fn:
            tier = 2
        elif "any.whl" in fn:
            tier = 3
        else:
            tier = 10
        size = int(u.get("size") or 0)
        return (tier, -size, fn)

    wheels.sort(key=sort_key)
    return wheels[0]


def _download_http_to_file(url: str, dest_path: Path, timeout: float = 900.0) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": _PYPI_USER_AGENT})
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    part = dest_path.with_name(dest_path.name + ".part")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        part.write_bytes(data)
        part.replace(dest_path)
    finally:
        if part.is_file():
            try:
                part.unlink()
            except OSError:
                pass


def _download_wheel_via_pypi_index(
    package_spec: str,
    dest: Path,
    *,
    timeout: float = 900.0,
) -> tuple[bool, str | None]:
    name = _pip_spec_stem(package_spec)
    data = _pypi_project_json(name)
    if data is None:
        return False, "pypi_not_found"
    urls = data.get("urls")
    if not isinstance(urls, list):
        return False, "pypi_no_urls"
    entry = _pypi_pick_wheel_entry(urls)
    if not entry:
        return False, "pypi_no_wheel_file"
    url = str(entry.get("url") or "")
    fn = str(entry.get("filename") or "")
    if not url or not fn.endswith(".whl"):
        return False, "pypi_bad_wheel_entry"
    target = dest / fn
    try:
        _download_http_to_file(url, target, timeout=timeout)
    except Exception as e:
        return False, str(e)[:2000]
    return True, None


def stage_local_meshchatx_wheel_into_bundled_dir(dest: Path) -> Path | None:
    """If ``dist/reticulum_meshchatx-*.whl`` exists under the project root, copy the newest into ``dest``.

    Replaces any PyPI-downloaded ``reticulum_meshchatx-*.whl`` so APK/offline bundles ship this tree's wheel.
    """
    root = meshchat_bundle_project_root()
    if root is None:
        return None
    dist_dir = root / "dist"
    if not dist_dir.is_dir():
        return None
    candidates = sorted(
        dist_dir.glob("reticulum_meshchatx-*.whl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    chosen = candidates[0]
    for old in dest.glob("reticulum_meshchatx-*.whl"):
        try:
            old.unlink()
        except OSError:
            logging.warning("Could not remove prior wheel %s", old)
    target = dest / chosen.name
    shutil.copy2(chosen, target)
    logging.info("Staged local MeshChatX wheel into bundled dir: %s", target.name)
    return target


def download_bundled_wheels_to_directory(
    dest: Path,
    *,
    on_package: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Populate ``dest`` with wheels for :func:`bundled_pip_targets`.

    Uses PyPI project metadata JSON and HTTPS downloads via ``urllib`` only.
    """
    dest.mkdir(parents=True, exist_ok=True)
    packages = list(bundled_pip_targets())
    total = len(packages)
    ok: list[str] = []
    failed: dict[str, str] = {}
    for i, pkg in enumerate(packages):
        if on_package is not None:
            on_package(i, total, pkg)
        g_http, e_http = _download_wheel_via_pypi_index(pkg, dest)
        if g_http:
            ok.append(pkg)
        else:
            failed[pkg] = f"pypi:{e_http or 'failed'}"
    staged = stage_local_meshchatx_wheel_into_bundled_dir(dest)
    if staged is not None:
        failed.pop(_MESHCHATX_BUNDLE_PIP_NAME, None)
        if _MESHCHATX_BUNDLE_PIP_NAME not in ok:
            ok.append(_MESHCHATX_BUNDLE_PIP_NAME)
    return {
        "ok": bool(ok),
        "downloaded": ok,
        "failed": failed,
    }


def _normalize_listen_host(host: str) -> str | None:
    h = (host or "").strip()
    if not h or len(h) > 200 or any(c in h for c in (" ", "\n", "\r", "\t")):
        return None
    return h


_REPOSITORY_INDEX_HTML = "repository-server-index.html"
_FILE_LIST_MARKER = "<!--FILE_LISTS-->"


def _repository_index_template_path(public_dir: str | None) -> Path | None:
    """Resolve the repository index HTML (Vite public / built ``public`` / source tree)."""
    if public_dir:
        candidate = Path(public_dir) / _REPOSITORY_INDEX_HTML
        if candidate.is_file():
            return candidate
    here = Path(__file__).resolve().parent
    src_public = here.parent / "frontend" / "public" / _REPOSITORY_INDEX_HTML
    if src_public.is_file():
        return src_public
    return None


def _format_index_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _list_index_files(subdir: str) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    if not os.path.isdir(subdir):
        return rows
    for name in sorted(os.listdir(subdir), key=str.lower):
        path = os.path.join(subdir, name)
        if not os.path.isfile(path):
            continue
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        rows.append((name, size))
    return rows


def _index_file_section(
    title: str, url_prefix: str, file_rows: list[tuple[str, int]]
) -> str:
    lines: list[str] = [f'<h2 class="section">{html.escape(title)}</h2>']
    if not file_rows:
        lines.append('<p class="empty">Nothing here yet.</p>')
        return "\n".join(lines)
    lines.append('<table class="files">')
    lines.append('<thead><tr><th>Name</th><th class="size">Size</th></tr></thead>')
    lines.append("<tbody>")
    for name, size in file_rows:
        q = urllib.parse.quote(name, safe="@%+.-_")
        lines.append(
            "<tr><td>"
            f'<a href="{html.escape(url_prefix + q, quote=True)}">{html.escape(name)}</a>'
            f'</td><td class="size">{html.escape(_format_index_size(size))}</td></tr>'
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def build_repository_index_html(
    bundled_dir: str,
    uploads_dir: str,
    public_dir: str | None = None,
) -> str:
    """HTML shell with live bundled and uploads file tables (for ``/`` and ``/index.html``)."""
    template = _repository_index_template_path(public_dir)
    shell: str
    if template is not None:
        try:
            shell = template.read_text(encoding="utf-8")
        except OSError:
            logging.exception("repository index template read failed: %s", template)
            shell = (
                '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
                "<title>MeshChatX repository</title></head><body><!--FILE_LISTS--></body></html>"
            )
    else:
        logging.warning(
            "repository index template not found (expected under public_dir or src/frontend/public)",
        )
        shell = (
            '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            "<title>MeshChatX repository</title></head><body><!--FILE_LISTS--></body></html>"
        )
    bundled_rows = _list_index_files(bundled_dir)
    upload_rows = _list_index_files(uploads_dir)
    injected = "\n".join(
        (
            _index_file_section("Bundled", "bundled/", bundled_rows),
            _index_file_section("Uploads", "uploads/", upload_rows),
        )
    )
    if _FILE_LIST_MARKER in shell:
        return shell.replace(_FILE_LIST_MARKER, injected, 1)
    return shell + injected


def make_repository_http_request_handler(
    root: str,
    public_dir: str | None = None,
) -> type[http.server.SimpleHTTPRequestHandler]:
    """``SimpleHTTPRequestHandler`` subclass: dynamic index listing at ``/`` and ``/index.html``."""
    root_abs = os.path.abspath(root)
    uploads_dir = os.path.join(root_abs, "uploads")
    bundled_dir = os.path.join(root_abs, "bundled")
    template_public = os.path.abspath(public_dir) if public_dir else None

    class RepositoryHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=root_abs, **kwargs)

        def _index_request_path(self) -> bool:
            parsed = urllib.parse.urlparse(self.path)
            norm = urllib.parse.unquote(parsed.path)
            if norm in ("/", ""):
                return True
            return norm.rstrip("/") == "/index.html"

        def _send_index(self, include_body: bool) -> None:
            body = build_repository_index_html(
                bundled_dir,
                uploads_dir,
                public_dir=template_public,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def do_GET(self) -> None:
            if self._index_request_path():
                self._send_index(True)
                return
            super().do_GET()

        def do_HEAD(self) -> None:
            if self._index_request_path():
                self._send_index(False)
                return
            super().do_HEAD()

    return RepositoryHTTPRequestHandler


def _safe_any_upload_filename(name: str) -> str | None:
    base = os.path.basename(name)
    if not base or base != name or ".." in base:
        return None
    if not re.fullmatch(r"[A-Za-z0-9._+\-]+", base):
        return None
    return base


class RepositoryServerManager:
    """Keeps user uploads and a ``bundled`` directory of wheels (PyPI over HTTPS, stdlib only)."""

    def __init__(self, storage_path: str, public_dir: str | None = None) -> None:
        self.root = os.path.join(storage_path, "repository-server")
        self.uploads_dir = os.path.join(self.root, "uploads")
        self.bundled_dir = os.path.join(self.root, "bundled")
        self._public_dir = os.path.abspath(public_dir) if public_dir else None
        self._last_refresh_error: str | None = None
        self._last_refresh_ok: list[str] = []
        self._last_refresh_failed: dict[str, str] = {}
        self._http_lock = threading.RLock()
        self._httpd: socketserver.ThreadingTCPServer | None = None
        self._http_thread: threading.Thread | None = None
        self._http_listen_host: str | None = None
        self._http_listen_port: int | None = None
        self._http_last_host: str | None = None
        self._http_last_port: int | None = None
        self._refresh_progress: dict[str, Any] = {
            "running": False,
            "current": None,
            "completed": 0,
            "total": 0,
        }
        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.bundled_dir, exist_ok=True)
        self._seed_bundled_from_public()

    def _buildtime_bundled_source(self) -> str | None:
        if not self._public_dir or not os.path.isdir(self._public_dir):
            return None
        return public_bundled_wheels_dir(self._public_dir)

    def _seed_bundled_from_public(self) -> None:
        """Copy build-staged wheels into identity storage when missing (offline installs)."""
        src_root = self._buildtime_bundled_source()
        if not src_root or not os.path.isdir(src_root):
            return
        try:
            names = [
                n
                for n in os.listdir(src_root)
                if n.endswith(".whl") and os.path.isfile(os.path.join(src_root, n))
            ]
        except OSError:
            return
        if not names:
            return
        try:
            existing = {
                n
                for n in os.listdir(self.bundled_dir)
                if n.endswith(".whl")
                and os.path.isfile(os.path.join(self.bundled_dir, n))
            }
        except OSError:
            existing = set()
        for name in names:
            src = os.path.join(src_root, name)
            dest = os.path.join(self.bundled_dir, name)
            if name in existing:
                try:
                    if os.path.getsize(src) == os.path.getsize(dest):
                        continue
                except OSError:
                    continue
            try:
                shutil.copy2(src, dest)
            except OSError as e:
                logging.warning(
                    "repository bundled seed copy failed for %s: %s", name, e
                )

    def _http_status_block(self) -> dict[str, Any]:
        running = self._httpd is not None
        url = None
        if (
            running
            and self._http_listen_host is not None
            and self._http_listen_port is not None
        ):
            url = f"http://{self._http_listen_host}:{self._http_listen_port}/"
        return {
            "running": running,
            "host": self._http_listen_host,
            "port": self._http_listen_port,
            "url": url,
            "last_host": self._http_last_host,
            "last_port": self._http_last_port,
        }

    def status(self) -> dict[str, Any]:
        return {
            "root": os.path.abspath(self.root),
            "uploads_dir": os.path.abspath(self.uploads_dir),
            "bundled_dir": os.path.abspath(self.bundled_dir),
            "bundled_targets": list(bundled_pip_targets()),
            "last_refresh_error": self._last_refresh_error,
            "last_refresh_ok": list(self._last_refresh_ok),
            "last_refresh_failed": dict(self._last_refresh_failed),
            "refresh_progress": dict(self._refresh_progress),
            "buildtime_bundled_wheels_dir": self._buildtime_bundled_source(),
            "http": self._http_status_block(),
        }

    def start_http_server(
        self, host: str | None = None, port: int | None = None
    ) -> dict[str, Any]:
        """Serve ``repository-server`` root over plain HTTP (no TLS) on a background thread."""
        bind_host = _normalize_listen_host(host or self._http_last_host or "127.0.0.1")
        if not bind_host:
            return {"ok": False, "error": "invalid_host"}
        bind_port = (
            int(port)
            if port is not None
            else (self._http_last_port if self._http_last_port is not None else 8787)
        )
        if bind_port < 0 or bind_port > 65535:
            return {"ok": False, "error": "invalid_port"}

        handler = make_repository_http_request_handler(
            self.root, public_dir=self._public_dir
        )

        class _RepoHTTPServer(socketserver.ThreadingTCPServer):
            allow_reuse_address = True

        with self._http_lock:
            if self._httpd is not None:
                return {"ok": False, "error": "already_running"}
            try:
                self._httpd = _RepoHTTPServer((bind_host, bind_port), handler)
            except OSError as e:
                self._httpd = None
                return {"ok": False, "error": "bind_failed", "message": str(e)}
            addr = self._httpd.server_address
            if isinstance(addr, tuple) and len(addr) >= 2:
                self._http_listen_host = str(addr[0])
                self._http_listen_port = int(addr[1])
            else:
                self.stop_http_server()
                return {"ok": False, "error": "address_error"}
            self._http_last_host = bind_host
            self._http_last_port = self._http_listen_port
            self._http_thread = threading.Thread(
                target=self._httpd.serve_forever,
                name="meshchat-repository-http",
                daemon=True,
            )
            self._http_thread.start()

        url = f"http://{self._http_listen_host}:{self._http_listen_port}/"
        return {
            "ok": True,
            "host": self._http_listen_host,
            "port": self._http_listen_port,
            "url": url,
        }

    def stop_http_server(self) -> dict[str, Any]:
        with self._http_lock:
            httpd = self._httpd
            thread = self._http_thread
            self._httpd = None
            self._http_thread = None
            self._http_listen_host = None
            self._http_listen_port = None
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                logging.exception("repository HTTP shutdown")
            try:
                httpd.server_close()
            except Exception:
                logging.exception("repository HTTP server_close")
        if thread is not None and thread.is_alive():
            thread.join(timeout=8.0)
        return {"ok": True}

    def restart_http_server(
        self, host: str | None = None, port: int | None = None
    ) -> dict[str, Any]:
        self.stop_http_server()
        use_host = host if host is not None else self._http_last_host
        use_port = port if port is not None else self._http_last_port
        return self.start_http_server(use_host, use_port)

    def list_entries(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for sub, source in (
            (self.bundled_dir, "bundled"),
            (self.uploads_dir, "upload"),
        ):
            if not os.path.isdir(sub):
                continue
            for name in sorted(os.listdir(sub), key=str.lower):
                path = os.path.join(sub, name)
                if not os.path.isfile(path):
                    continue
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                rows.append({"name": name, "bytes": size, "source": source})
        return rows

    def save_upload(self, filename: str, data: bytes) -> tuple[bool, str | None]:
        safe = _safe_any_upload_filename(filename)
        if not safe:
            return False, "invalid_filename"
        if len(data) > 256 * 1024 * 1024:
            return False, "file_too_large"
        dest = os.path.join(self.uploads_dir, safe)
        try:
            with open(dest, "wb") as f:
                f.write(data)
        except OSError as e:
            logging.exception("repository upload failed: %s", e)
            return False, str(e)
        return True, None

    def delete_upload(self, filename: str) -> tuple[bool, str | None]:
        safe = _safe_any_upload_filename(filename)
        if not safe:
            return False, "invalid_filename"
        path = os.path.join(self.uploads_dir, safe)
        if not os.path.isfile(path):
            return False, "not_found"
        try:
            os.remove(path)
        except OSError as e:
            return False, str(e)
        return True, None

    def _set_refresh_progress(
        self,
        *,
        running: bool,
        current: str | None,
        completed: int,
        total: int,
    ) -> None:
        t = max(0, total)
        c = min(max(0, completed), t)
        self._refresh_progress = {
            "running": running,
            "current": current,
            "completed": c,
            "total": t,
        }

    def refresh_bundled_wheels(self) -> dict[str, Any]:
        """Download wheels into ``bundled_dir`` (PyPI JSON + ``urllib``)."""
        self._last_refresh_error = None
        self._last_refresh_ok = []
        self._last_refresh_failed = {}

        dest = Path(self.bundled_dir)
        dest.mkdir(parents=True, exist_ok=True)
        for old in dest.glob("*.whl"):
            try:
                old.unlink()
            except OSError:
                pass

        total = len(bundled_pip_targets())
        ok: list[str] = []
        failed: dict[str, str] = {}
        self._set_refresh_progress(running=True, current=None, completed=0, total=total)
        try:

            def _on_pkg(i: int, t: int, pkg: str) -> None:
                self._set_refresh_progress(
                    running=True, current=pkg, completed=i, total=t
                )

            result = download_bundled_wheels_to_directory(dest, on_package=_on_pkg)
            ok = result["downloaded"]
            failed = result["failed"]
        finally:
            self._set_refresh_progress(
                running=False,
                current=None,
                completed=total,
                total=total,
            )

        self._last_refresh_ok = ok
        self._last_refresh_failed = failed
        if not ok and failed:
            self._last_refresh_error = "all_downloads_failed"
        elif failed:
            self._last_refresh_error = "partial_failure"

        return {
            "ok": bool(ok),
            "downloaded": ok,
            "failed": failed,
        }
