# SPDX-License-Identifier: 0BSD

"""PageNode: Serves Micron pages and files over RNS.

Each PageNode owns an RNS Destination (SINGLE, IN) with the aspect
nomadnetwork.node and registers per-page request handlers at
paths like /page/index.mu. This makes page nodes compatible with
the standard NomadNet page browsing protocol (which is just RNS
request/response with specific path conventions).

Clients link to the destination and call link.request("/page/name.mu")
to fetch a page, or /file/name for files.

Supported page filename extensions are .mu, .md, .txt, and .html.
"""

import contextlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import threading
import time

import RNS

APP_NAME = "nomadnetwork"
ASPECT = "node"
DEFAULT_INDEX = "index.mu"

ALLOWED_PAGE_EXTENSIONS = frozenset({".mu", ".md", ".txt", ".html"})

DEFAULT_ANNOUNCE_INTERVAL_SECONDS = 900
MIN_ANNOUNCE_INTERVAL_SECONDS = 60
MAX_ANNOUNCE_INTERVAL_SECONDS = 86400
EXECUTABLE_PAGE_TIMEOUT_SECONDS = 15
MAX_UNIQUE_REMOTE_HASHES = 4096

PAGE_GENERATION_FAILED_MICRON = (
    ">Page Generation Failed\n\nThe page could not be generated.\n"
)

# Host env copied into executable page scripts. Request field_* / var_* cannot
# overwrite these names. Windows Python needs SYSTEMROOT to start.
_EXECUTABLE_PAGE_HOST_ENV_KEYS = (
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "SYSTEMDRIVE",
    "PATHEXT",
    "COMSPEC",
    "TEMP",
    "TMP",
)

_SHEBANG_INTERPRETER_ALIASES = {
    "python": ("python", "python3", "py"),
    "python3": ("python3", "python", "py"),
    "py": ("py", "python", "python3"),
    "node": ("node", "nodejs"),
    "nodejs": ("node", "nodejs"),
    "sh": ("bash", "sh"),
    "bash": ("bash", "sh"),
}


def normalize_announce_interval_seconds(
    value,
    default=DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
):
    """Clamp an announce interval to the supported range, or 0 to disable periodic announces."""
    if value is None:
        return int(default)
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return int(default)
    if seconds <= 0:
        return 0
    return max(
        MIN_ANNOUNCE_INTERVAL_SECONDS,
        min(MAX_ANNOUNCE_INTERVAL_SECONDS, seconds),
    )


def normalize_page_filename(name: str) -> str:
    """Return a safe basename with an allowed extension. Unknown extensions raise ValueError."""
    name = os.path.basename((name or "").strip())
    if not name or name in (".", ".."):
        raise ValueError("page name is required")
    if "/" in name or "\\" in name:
        raise ValueError("invalid page name")
    lower = name.lower()
    for ext in ALLOWED_PAGE_EXTENSIONS:
        if lower.endswith(ext):
            return name
    if "." in name:
        raise ValueError("unsupported page extension")
    return f"{name}.mu"


def is_allowed_page_filename(name: str) -> bool:
    lower = os.path.basename(name or "").lower()
    return any(lower.endswith(ext) for ext in ALLOWED_PAGE_EXTENSIONS)


def _safe_mesh_file_basename(name: str) -> str:
    """Reject empty, dot, or parent-segment names after basename (path traversal)."""
    base = os.path.basename((name or "").strip())
    if not base or base in (".", ".."):
        raise ValueError("invalid file name")
    if "/" in base or "\\" in base:
        raise ValueError("invalid file name")
    return base


def _path_is_under_root(resolved: str, root: str) -> bool:
    return resolved == root or resolved.startswith(root + os.sep)


def _is_windows_platform() -> bool:
    if os.name == "nt":
        return True
    try:
        return bool(RNS.vendor.platformutils.is_windows())
    except Exception:
        return False


def _page_generation_error_bytes(reason: str) -> bytes:
    text = PAGE_GENERATION_FAILED_MICRON
    if reason:
        text += f"\n{reason}\n"
    return text.encode("utf-8")


def _normalize_executable_page_names(names) -> list[str]:
    """Return unique allowed page filenames from a config list."""
    if not isinstance(names, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in names:
        if not isinstance(item, str):
            continue
        try:
            safe = normalize_page_filename(item)
        except ValueError:
            continue
        if safe in seen:
            continue
        seen.add(safe)
        out.append(safe)
    return out


def _parse_page_shebang(page_path: str) -> tuple[str, list[str]] | None:
    """Return (program, extra_args) from a page shebang, or None."""
    try:
        with open(page_path, "rb") as handle:
            first = handle.readline()
    except OSError:
        return None
    if not first.startswith(b"#!"):
        return None
    line = first[2:].decode("utf-8", errors="replace").strip()
    if not line:
        return None
    windows_path = len(line) >= 3 and line[0].isalpha() and line[1] == ":"
    try:
        tokens = shlex.split(line, posix=not windows_path)
    except ValueError:
        return None
    if not tokens:
        return None
    program = tokens[0]
    rest = tokens[1:]
    base = os.path.basename(program.replace("\\", "/"))
    if base.lower() in ("env", "env.exe") and rest:
        if rest[0] == "-S":
            rest = rest[1:]
        if not rest:
            return None
        return rest[0], rest[1:]
    return program, rest


def _shebang_lookup_names(name: str) -> tuple[str, ...]:
    stem = name
    if stem.lower().endswith(".exe"):
        stem = stem[:-4]
    aliases = _SHEBANG_INTERPRETER_ALIASES.get(stem.lower())
    if aliases:
        return aliases
    if stem != name:
        return (name, stem)
    return (name,)


def _resolve_shebang_interpreter(program: str) -> str | None:
    """Resolve a shebang program to an executable path on this host."""
    if os.path.isabs(program) and os.path.isfile(program):
        return program
    name = os.path.basename(program.replace("\\", "/"))
    if not name or name in (".", ".."):
        return None
    frozen = bool(getattr(sys, "frozen", False))
    for candidate in _shebang_lookup_names(name):
        found = shutil.which(candidate)
        if found:
            return found
    stem = name.lower()
    if stem.endswith(".exe"):
        stem = stem[:-4]
    if not frozen and stem in ("python", "python3", "py"):
        executable = sys.executable
        if executable and os.path.isfile(executable):
            return executable
    return None


def _windows_page_command(page_path: str) -> list[str] | None:
    """Build argv to run a page script on Windows via its shebang."""
    parsed = _parse_page_shebang(page_path)
    if parsed is None:
        return None
    program, extra = parsed
    interpreter = _resolve_shebang_interpreter(program)
    if interpreter is None:
        return None
    return [interpreter, *extra, page_path]


def _build_executable_page_env(
    data,
    link_id=None,
    remote_identity=None,
) -> dict[str, str]:
    env_map: dict[str, str] = {}
    for key in _EXECUTABLE_PAGE_HOST_ENV_KEYS:
        if key in os.environ:
            env_map[key] = os.environ[key]
    if link_id is not None:
        with contextlib.suppress(Exception):
            env_map["link_id"] = RNS.hexrep(link_id, delimit=False)
    if remote_identity is not None:
        with contextlib.suppress(Exception):
            remote_hash = getattr(remote_identity, "hash", None)
            if remote_hash is not None:
                env_map["remote_identity"] = RNS.hexrep(remote_hash, delimit=False)
    if data is not None and isinstance(data, dict):
        for key, value in data.items():
            if isinstance(key, str) and (
                key.startswith("field_") or key.startswith("var_")
            ):
                env_map[key] = str(value)
    return env_map


def _reject_name_component_too_long(parent_dir: str, component: str) -> None:
    """Raise ValueError if basename exceeds this directory's filename length limit."""
    try:
        if parent_dir and os.path.isdir(parent_dir):
            max_bytes = int(os.pathconf(parent_dir, "PC_NAME_MAX"))
        else:
            max_bytes = 255
    except (OSError, ValueError, TypeError, OverflowError):
        max_bytes = 255
    if len(os.fsencode(component)) > max_bytes:
        raise ValueError("name too long")


class PageNode:
    """A single page-serving node on the Reticulum mesh."""

    def __init__(
        self,
        node_id,
        name,
        base_dir,
        identity=None,
        identity_path=None,
        announce_enabled=True,
        announce_interval_seconds=DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
        executable_pages_enabled=False,
        executable_page_names=None,
        on_announce=None,
    ):
        self.node_id = node_id
        self.name = name
        self.base_dir = base_dir
        self.pages_dir = os.path.join(base_dir, "pages")
        self.files_dir = os.path.join(base_dir, "files")

        self.identity = identity
        self.identity_path = identity_path or os.path.join(base_dir, "identity")
        self.destination = None
        self.active_links = []
        self.running = False
        self._registered_page_paths = set()
        self._registered_file_paths = set()
        self._stats = {"pages_served": 0, "files_served": 0, "links_established": 0}
        self._serve_started_at = None
        self._unique_remote_hashes = set()

        self.announce_enabled = bool(announce_enabled)
        self.announce_interval_seconds = normalize_announce_interval_seconds(
            announce_interval_seconds,
        )
        self.executable_pages_enabled = bool(executable_pages_enabled)
        self._executable_page_names = set(
            _normalize_executable_page_names(executable_page_names),
        )
        self.last_announced_at = None
        self.on_announce = on_announce
        self._announce_timer = None

    def setup(self):
        """Create directories, load or create identity, set up RNS destination."""
        os.makedirs(self.pages_dir, exist_ok=True)
        os.makedirs(self.files_dir, exist_ok=True)

        if self.identity is None:
            if os.path.isfile(self.identity_path):
                self.identity = RNS.Identity.from_file(self.identity_path)
            else:
                self.identity = RNS.Identity()
                self.identity.to_file(self.identity_path)

        self.destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            APP_NAME,
            ASPECT,
        )

        self.destination.set_link_established_callback(self._link_established)

        self._register_existing_pages()
        self._register_existing_files()
        self._ensure_local_path()

        self.running = True
        self._serve_started_at = time.time()

        if self.announce_enabled:
            self.announce()
        self._sync_announce_timer()

        return self.destination.hash.hex()

    def announce(self):
        """Broadcast this node's presence on the mesh."""
        if self.destination and self.running:
            self._register_existing_files()
            app_data = self.name.encode("utf-8")
            self.destination.announce(app_data=app_data)
            self._ensure_local_path()
            self.last_announced_at = time.time()
            if self.on_announce is not None:
                with contextlib.suppress(Exception):
                    self.on_announce(self)

    def _cancel_announce_timer(self):
        """Cancel the pending periodic announce timer, if any."""
        timer = self._announce_timer
        self._announce_timer = None
        if timer is not None:
            with contextlib.suppress(Exception):
                timer.cancel()

    def _sync_announce_timer(self):
        """Reschedule the periodic announce timer to match current settings."""
        self._cancel_announce_timer()
        if not self.running or not self.announce_enabled:
            return
        interval = normalize_announce_interval_seconds(
            self.announce_interval_seconds,
            default=0,
        )
        if interval <= 0:
            return
        timer = threading.Timer(interval, self._announce_timer_fire)
        timer.daemon = True
        self._announce_timer = timer
        timer.start()

    def _announce_timer_fire(self):
        """Timer callback: announce then reschedule for the next interval."""
        self._announce_timer = None
        if not self.running or not self.announce_enabled:
            return
        with contextlib.suppress(Exception):
            self.announce()
        self._sync_announce_timer()

    def set_announce_settings(
        self, announce_enabled=None, announce_interval_seconds=None
    ):
        """Update announce enablement and/or interval, then resync the periodic timer."""
        if announce_enabled is not None:
            self.announce_enabled = bool(announce_enabled)
        if announce_interval_seconds is not None:
            self.announce_interval_seconds = normalize_announce_interval_seconds(
                announce_interval_seconds,
            )
        self._sync_announce_timer()

    def set_executable_pages_enabled(self, enabled):
        """Enable or disable dynamic executable page serving for this node."""
        self.executable_pages_enabled = bool(enabled)

    def teardown(self):
        """Deregister handlers and clean up."""
        self.running = False
        self._cancel_announce_timer()
        self._serve_started_at = None
        self._unique_remote_hashes.clear()
        if self.destination:
            for rpath in list(self._registered_page_paths):
                self.destination.deregister_request_handler(rpath)
            for rpath in list(self._registered_file_paths):
                self.destination.deregister_request_handler(rpath)
            self._registered_page_paths.clear()
            self._registered_file_paths.clear()

            RNS.Transport.deregister_destination(self.destination)
            self.destination = None

        for link in list(self.active_links):
            try:
                link.teardown()
            except Exception:
                pass
        self.active_links.clear()

    def _note_remote_identity(self, remote_identity):
        if remote_identity is None:
            return
        try:
            h = getattr(remote_identity, "hash", None)
            if h is not None:
                if len(self._unique_remote_hashes) >= MAX_UNIQUE_REMOTE_HASHES:
                    return
                self._unique_remote_hashes.add(h.hex())
        except Exception:
            pass

    def _link_established(self, link):
        self.active_links.append(link)
        self._stats["links_established"] += 1
        try:
            self._note_remote_identity(link.get_remote_identity())
        except Exception:
            pass
        link.set_link_closed_callback(self._link_closed)

    def _link_closed(self, link):
        if link in self.active_links:
            self.active_links.remove(link)

    def _ensure_local_path(self):
        """Register this identity in RNS.Identity.known_destinations.

        Lets Identity.recall() resolve the destination for local link setup.
        """
        if not self.destination:
            return
        RNS.Identity.remember(
            packet_hash=None,
            destination_hash=self.destination.hash,
            public_key=self.identity.get_public_key(),
            app_data=self.name.encode("utf-8"),
        )

    def _page_request_path(self, page_name):
        """Build the NomadNet-style request path for a page."""
        return f"/page/{page_name}"

    def _file_request_path(self, file_name):
        """Build the NomadNet-style request path for a file."""
        return f"/file/{file_name}"

    def _register_existing_pages(self):
        """Scan pages directory and register a handler for each page."""
        if not os.path.isdir(self.pages_dir):
            return
        for fname in os.listdir(self.pages_dir):
            if self._jail_page_path(fname, must_exist=True) is None:
                continue
            self._register_page_handler(fname)

    def _register_existing_files(self):
        """Scan files directory and register a handler for each file."""
        if not os.path.isdir(self.files_dir):
            return
        for fname in os.listdir(self.files_dir):
            if self._jail_file_path(fname, must_exist=True) is None:
                continue
            self._register_file_handler(fname)

    def _register_page_handler(self, page_name):
        """Register a request handler for a specific page."""
        if not self.destination:
            return
        rpath = self._page_request_path(page_name)
        if rpath in self._registered_page_paths:
            return
        self.destination.register_request_handler(
            rpath,
            response_generator=self._make_page_responder(page_name),
            allow=RNS.Destination.ALLOW_ALL,
        )
        self._registered_page_paths.add(rpath)

    def _deregister_page_handler(self, page_name):
        """Deregister the request handler for a specific page."""
        if not self.destination:
            return
        rpath = self._page_request_path(page_name)
        if rpath not in self._registered_page_paths:
            return
        self.destination.deregister_request_handler(rpath)
        self._registered_page_paths.discard(rpath)

    def _register_file_handler(self, file_name):
        """Register a request handler for a specific file."""
        if not self.destination:
            return
        rpath = self._file_request_path(file_name)
        if rpath in self._registered_file_paths:
            return
        self.destination.register_request_handler(
            rpath,
            response_generator=self._make_file_responder(file_name),
            allow=RNS.Destination.ALLOW_ALL,
        )
        self._registered_file_paths.add(rpath)

    def _deregister_file_handler(self, file_name):
        """Deregister the request handler for a specific file."""
        if not self.destination:
            return
        rpath = self._file_request_path(file_name)
        if rpath not in self._registered_file_paths:
            return
        self.destination.deregister_request_handler(rpath)
        self._registered_file_paths.discard(rpath)

    def _jail_page_path(self, name, *, must_exist=False):
        """Resolve a page name under pages_dir after realpath.

        Returns None when the name is invalid, the path escapes the jail
        (including symlink-out), or must_exist is set and the file is missing.
        """
        try:
            safe_name = normalize_page_filename(name)
            _reject_name_component_too_long(self.pages_dir, safe_name)
        except ValueError:
            return None
        if not os.path.isdir(self.pages_dir):
            return None
        root = os.path.realpath(self.pages_dir)
        raw = os.path.join(root, safe_name)
        resolved = os.path.realpath(raw)
        if not _path_is_under_root(resolved, root):
            return None
        if must_exist and not os.path.isfile(resolved):
            return None
        return resolved

    def _resolve_page_path(self, name):
        return self._jail_page_path(name, must_exist=True)

    def is_page_executable(self, name):
        """Return whether this page is marked executable for dynamic serving."""
        page_path = self._resolve_page_path(name)
        if page_path is None:
            return False
        return self._is_page_marked_executable(page_path)

    def _is_page_marked_executable(self, page_path):
        name = os.path.basename(page_path)
        if name in self._executable_page_names:
            return True
        if _is_windows_platform():
            return False
        return os.access(page_path, os.X_OK)

    def set_page_executable(self, name, enabled):
        """Mark or unmark a page as executable and persist the flag."""
        page_path = self._resolve_page_path(name)
        if page_path is None:
            raise ValueError("page not found")
        name = os.path.basename(page_path)
        if enabled:
            self._executable_page_names.add(name)
            if not _is_windows_platform():
                mode = os.stat(page_path).st_mode
                os.chmod(page_path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        else:
            self._executable_page_names.discard(name)
            if not _is_windows_platform():
                mode = os.stat(page_path).st_mode
                os.chmod(
                    page_path,
                    mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH),
                )
        self.save_config()

    def _should_execute_page(self, page_path):
        if not self.executable_pages_enabled:
            return False
        return self._is_page_marked_executable(page_path)

    def _read_static_page_bytes(self, page_path):
        with open(page_path, "rb") as f:
            return f.read()

    def _execute_page_bytes(
        self, page_path, data=None, link_id=None, remote_identity=None
    ):
        env_map = _build_executable_page_env(data, link_id, remote_identity)
        run_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
            "env": env_map,
            "timeout": EXECUTABLE_PAGE_TIMEOUT_SECONDS,
        }
        if _is_windows_platform():
            command = _windows_page_command(page_path)
            if command is None:
                return _page_generation_error_bytes(
                    "Could not resolve a script interpreter from the page shebang.",
                )
            env_map.setdefault("PYTHONIOENCODING", "utf-8")
            if os.name == "nt":
                run_kwargs["creationflags"] = getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0x08000000,
                )
        else:
            command = [page_path]
        try:
            generated = subprocess.run(command, **run_kwargs)
            return generated.stdout
        except subprocess.TimeoutExpired:
            return _page_generation_error_bytes("The page script timed out.")
        except OSError as e:
            return _page_generation_error_bytes(str(e))
        except Exception as e:
            return _page_generation_error_bytes(str(e))

    def serve_page_content(
        self,
        name,
        data=None,
        link_id=None,
        remote_identity=None,
    ):
        """Serve a page as static bytes or by executing it when enabled and executable."""
        page_path = self._resolve_page_path(name)
        if page_path is None:
            return None
        try:
            if self._should_execute_page(page_path):
                content = self._execute_page_bytes(
                    page_path,
                    data=data,
                    link_id=link_id,
                    remote_identity=remote_identity,
                )
            else:
                content = self._read_static_page_bytes(page_path)
            self._stats["pages_served"] += 1
            return content
        except Exception:
            return None

    def _make_page_responder(self, page_name):
        """Return a closure that serves a specific page."""

        def responder(path, data, request_id, link_id, remote_identity, requested_at):
            self._note_remote_identity(remote_identity)
            return self.serve_page_content(
                page_name,
                data=data,
                link_id=link_id,
                remote_identity=remote_identity,
            )

        return responder

    def _jail_file_path(self, name, *, must_exist=False):
        """Resolve a hosted file name under files_dir after realpath.

        Returns None when the name is invalid, the path escapes the jail
        (including symlink-out), or must_exist is set and the file is missing.
        """
        try:
            safe_name = _safe_mesh_file_basename(name)
            _reject_name_component_too_long(self.files_dir, safe_name)
        except ValueError:
            return None
        if not os.path.isdir(self.files_dir):
            return None
        root = os.path.realpath(self.files_dir)
        raw = os.path.join(root, safe_name)
        resolved = os.path.realpath(raw)
        if not _path_is_under_root(resolved, root):
            return None
        if must_exist and not os.path.isfile(resolved):
            return None
        return resolved

    def read_hosted_file(self, name):
        """Read a hosted file from the files jail.

        Returns (file_name, file_bytes), or None.
        """
        file_path = self._jail_file_path(name, must_exist=True)
        if file_path is None:
            return None
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except OSError:
            return None
        self._stats["files_served"] += 1
        return (os.path.basename(file_path), file_bytes)

    def _make_file_responder(self, file_name):
        """Return a closure that serves a specific file."""

        def responder(path, data, request_id, link_id, remote_identity, requested_at):
            self._note_remote_identity(remote_identity)
            file_path = self._jail_file_path(file_name, must_exist=True)
            if file_path is None:
                return None
            try:
                fh = open(file_path, "rb")
                metadata = {"name": os.path.basename(file_path).encode("utf-8")}
                self._stats["files_served"] += 1
                return [fh, metadata]
            except Exception:
                return None

        return responder

    def add_page(self, name, content, executable=None):
        """Write a page file and register its request handler."""
        os.makedirs(self.pages_dir, exist_ok=True)
        page_path = self._jail_page_path(name, must_exist=False)
        if page_path is None:
            raise ValueError("invalid page name")
        name = os.path.basename(page_path)
        if isinstance(content, str):
            content = content.encode("utf-8")
        with open(page_path, "wb") as f:
            f.write(content)
        if executable is not None:
            self.set_page_executable(name, bool(executable))
        if self.running:
            try:
                self._register_page_handler(name)
            except Exception as e:
                raise RuntimeError(
                    f"Page written but failed to register on mesh: {e}",
                ) from e
        return name

    def remove_page(self, name):
        """Remove a page and deregister its request handler."""
        page_path = self._jail_page_path(name, must_exist=True)
        if page_path is None:
            return False
        try:
            name = os.path.basename(page_path)
            os.remove(page_path)
        except OSError:
            return False
        self._executable_page_names.discard(name)
        self.save_config()
        self._deregister_page_handler(name)
        return True

    def list_pages(self):
        """Return page metadata dicts with name and executable state."""
        if not os.path.isdir(self.pages_dir):
            return []
        pages = []
        for fname in sorted(os.listdir(self.pages_dir)):
            fpath = self._jail_page_path(fname, must_exist=True)
            if fpath is None:
                continue
            pages.append(
                {
                    "name": fname,
                    "executable": self.is_page_executable(fname),
                },
            )
        return pages

    def get_page_content(self, name):
        """Read and return a page's content."""
        page_path = self._jail_page_path(name, must_exist=True)
        if page_path is None:
            return None
        with open(page_path, encoding="utf-8") as f:
            return f.read()

    def add_file(self, name, data):
        """Write a file and register its request handler."""
        os.makedirs(self.files_dir, exist_ok=True)
        name = _safe_mesh_file_basename(name)
        _reject_name_component_too_long(self.files_dir, name)
        file_path = self._jail_file_path(name, must_exist=False)
        if file_path is None:
            raise ValueError("invalid file name")
        if isinstance(data, str):
            data = data.encode("utf-8")
        with open(file_path, "wb") as f:
            f.write(data)
        if self.running:
            self._register_file_handler(name)
        return name

    def remove_file(self, name):
        """Remove a file and deregister its request handler."""
        file_path = self._jail_file_path(name, must_exist=True)
        if file_path is None:
            return False
        try:
            name = os.path.basename(file_path)
            os.remove(file_path)
        except OSError:
            return False
        self._deregister_file_handler(name)
        return True

    def list_files(self):
        """Return a list of file dicts with name and size."""
        if self.running:
            self._register_existing_files()
        if not os.path.isdir(self.files_dir):
            return []
        result = []
        for fname in sorted(os.listdir(self.files_dir)):
            fpath = self._jail_file_path(fname, must_exist=True)
            if fpath is None:
                continue
            result.append({"name": fname, "size": os.path.getsize(fpath)})
        return result

    def get_destination_hash(self):
        """Return the hex destination hash if running."""
        if self.destination:
            return self.destination.hash.hex()
        return None

    def get_status(self):
        """Return current node status dict."""
        uptime_seconds = 0
        if self.running and self._serve_started_at is not None:
            uptime_seconds = max(0, int(time.time() - self._serve_started_at))
        return {
            "node_id": self.node_id,
            "name": self.name,
            "running": self.running,
            "destination_hash": self.get_destination_hash(),
            "identity_hash": self.identity.hash.hex() if self.identity else None,
            "active_links": len(self.active_links),
            "unique_connections": len(self._unique_remote_hashes),
            "uptime_seconds": uptime_seconds,
            "pages": self.list_pages(),
            "files": self.list_files(),
            "stats": dict(self._stats),
            "announce_enabled": self.announce_enabled,
            "announce_interval_seconds": self.announce_interval_seconds,
            "executable_pages_enabled": self.executable_pages_enabled,
            "last_announced_at": self.last_announced_at,
        }

    def save_config(self):
        """Persist node configuration to disk."""
        config = {
            "node_id": self.node_id,
            "name": self.name,
            "announce_enabled": self.announce_enabled,
            "announce_interval_seconds": self.announce_interval_seconds,
            "executable_pages_enabled": self.executable_pages_enabled,
            "executable_page_names": sorted(self._executable_page_names),
        }
        config_path = os.path.join(self.base_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    @staticmethod
    def load_config(base_dir):
        """Load node configuration from disk. Returns dict or None."""
        config_path = os.path.join(base_dir, "config.json")
        if not os.path.isfile(config_path):
            return None
        with open(config_path) as f:
            return json.load(f)
