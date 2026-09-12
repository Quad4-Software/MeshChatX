# SPDX-License-Identifier: 0BSD

"""Filesystem and HTTP client helpers used at startup and in the web layer."""

import contextlib
import os
import sys
import tempfile

from aiohttp import web


def is_path_within_dir(path: str, directory: str) -> bool:
    """Return True when path resolves inside directory (realpath + separator)."""
    if not path or not directory or "\x00" in str(path):
        return False
    try:
        candidate = os.path.normcase(os.path.normpath(os.path.realpath(path)))
        root = os.path.normcase(os.path.normpath(os.path.realpath(directory)))
    except (OSError, ValueError):
        return False
    return candidate == root or candidate.startswith(root + os.sep)


def is_under_root(candidate: str, root: str) -> bool:
    """Return True when candidate equals root or sits under root + os.sep.

    Pure string check. Both paths must already be realpath-resolved; use
    is_path_within_dir for unresolved inputs. This is the membership test
    required by .agents/conventions/path-jail.md.
    """
    if not candidate or not root:
        return False
    return candidate == root or candidate.startswith(root + os.sep)


def realpath_or_none(path: str | os.PathLike[str] | None) -> str | None:
    """os.path.realpath that returns None on OSError or embedded NUL.

    realpath raises ValueError for embedded null characters on 3.11+, see
    https://docs.python.org/3/library/os.path.html#os.path.realpath
    """
    if not path:
        return None
    try:
        return os.path.realpath(path)
    except (OSError, ValueError):
        return None


class PathJailError(ValueError):
    """Raised when a client-supplied path fails jail validation.

    Carries a machine-stable reason from REASONS so callers can map to their
    own error type or message without parsing text.
    """

    REASONS = frozenset(
        {
            "required",
            "invalid",
            "absolute",
            "escape",
            "reserved",
            "forbidden",
            "not_found",
        }
    )

    def __init__(self, message: str, *, reason: str = "invalid") -> None:
        self.reason = reason if reason in self.REASONS else "invalid"
        super().__init__(message)


def normalize_relpath(
    relpath: str,
    *,
    reserved_names: frozenset[str] | set[str] = frozenset(),
    reserved_prefixes: tuple[str, ...] = (),
    forbidden_part=None,
    strict: bool = False,
) -> str:
    """Normalize a client-supplied relative path, or raise PathJailError.

    Rejects empty, NUL, absolute, drive-letter, and UNC inputs. os.path.normpath
    collapses internal dot-dot segments (a/../b becomes b) because the result
    still stays under the jail root; strict=True instead rejects any literal
    dot-dot segment for callers that treat them as hostile input.

    reserved_names / reserved_prefixes reject per-segment protocol sidecars
    (for example .rns-xfer- journal files). forbidden_part is an optional
    callable(name) -> bool applied to every segment.
    """
    if not isinstance(relpath, str) or not relpath or "\x00" in relpath:
        raise PathJailError("invalid relative path", reason="invalid")
    # Reject Windows drive and UNC style paths even on POSIX so a path that is
    # harmless here cannot become absolute when it reaches a Windows host.
    if relpath.startswith(("/", "\\")) or os.path.isabs(relpath):
        raise PathJailError("absolute paths are not allowed", reason="absolute")
    if len(relpath) >= 2 and relpath[1] == ":":
        raise PathJailError("absolute paths are not allowed", reason="absolute")
    if relpath.startswith("\\\\") or relpath.startswith("//"):
        raise PathJailError("absolute paths are not allowed", reason="absolute")
    if strict and ".." in relpath.replace("\\", "/").split("/"):
        raise PathJailError("path escape attempt", reason="escape")

    # ntpath.normpath emits backslashes on Windows; re-normalize to forward
    # slashes so segment checks and callers behave identically cross-platform.
    cleaned = os.path.normpath(relpath.replace("\\", "/")).replace("\\", "/")
    if cleaned in (".", ""):
        raise PathJailError("empty relative path", reason="invalid")
    parts = cleaned.split("/")
    if any(part in ("", "..") for part in parts):
        raise PathJailError("path escape attempt", reason="escape")
    if cleaned.startswith("../") or cleaned == "..":
        raise PathJailError("path escape attempt", reason="escape")
    for part in parts:
        if part in reserved_names or any(
            part.startswith(prefix) for prefix in reserved_prefixes
        ):
            raise PathJailError("reserved path", reason="reserved")
        if forbidden_part is not None and forbidden_part(part):
            raise PathJailError("forbidden path segment", reason="forbidden")
    return cleaned


def resolve_under_root(
    root: str,
    relpath: str | None,
    *,
    reserved_names: frozenset[str] | set[str] = frozenset(),
    reserved_prefixes: tuple[str, ...] = (),
    forbidden_part=None,
    strict: bool = False,
    allow_root: bool = False,
    must_exist: bool = False,
    must_be_file: bool = False,
    check_symlinked_parents: bool = False,
) -> str:
    """Resolve relpath under root and return the real path, jailed.

    Raises PathJailError on any rule failure. allow_root returns the root
    itself for empty input and permits results that equal the root.
    must_exist requires os.path.lexists so a broken symlink still counts;
    must_be_file requires a regular file. check_symlinked_parents re-verifies
    realpath of the parent directory for extra defense in depth on missing
    leaves (realpath already resolves symlinked parents, so this is belt and
    suspenders for features that had the check historically).
    """
    root_real = realpath_or_none(root)
    if not root_real:
        raise PathJailError("jail root is not available", reason="invalid")
    if relpath is None or (isinstance(relpath, str) and not relpath.strip()):
        if allow_root:
            return root_real
        raise PathJailError("path is required", reason="required")
    safe_rel = normalize_relpath(
        relpath,
        reserved_names=reserved_names,
        reserved_prefixes=reserved_prefixes,
        forbidden_part=forbidden_part,
        strict=strict,
    )
    joined = os.path.join(root_real, safe_rel)

    if check_symlinked_parents:
        parent = os.path.dirname(joined)
        if parent != root_real:
            parent_real = realpath_or_none(parent)
            if not parent_real or not is_under_root(parent_real, root_real):
                raise PathJailError("path escapes root", reason="escape")

    # In-jail symlinks are allowed but must resolve back under the root.
    if os.path.lexists(joined) and os.path.islink(joined):
        real = realpath_or_none(joined)
        if not real or not is_under_root(real, root_real):
            raise PathJailError("path escapes root", reason="escape")
        if must_exist and not os.path.exists(real):
            raise PathJailError("path not found", reason="not_found")
        if must_be_file and not os.path.isfile(real):
            raise PathJailError("path not found", reason="not_found")
        if not allow_root and real == root_real:
            raise PathJailError("path escapes root", reason="escape")
        return real

    if must_exist and not os.path.lexists(joined):
        raise PathJailError("path not found", reason="not_found")
    real = realpath_or_none(joined)
    if not real or not is_under_root(real, root_real):
        raise PathJailError("path escapes root", reason="escape")
    if not allow_root and real == root_real:
        raise PathJailError("path escapes root", reason="escape")
    if must_be_file and not os.path.isfile(real):
        raise PathJailError("path not found", reason="not_found")
    return real


def relative_to_root(
    root: str,
    abspath: str,
    *,
    reserved_names: frozenset[str] | set[str] = frozenset(),
    reserved_prefixes: tuple[str, ...] = (),
    forbidden_part=None,
) -> str:
    """Return abspath as a jailed relative path under root.

    Raises PathJailError when abspath is not inside root or the result fails
    normalize_relpath (for example when abspath is the root itself).
    """
    root_real = realpath_or_none(root)
    path_real = realpath_or_none(abspath)
    if not root_real or not path_real:
        raise PathJailError("invalid path", reason="invalid")
    if not is_under_root(path_real, root_real):
        raise PathJailError("path escapes root", reason="escape")
    rel = os.path.relpath(path_real, root_real)
    return normalize_relpath(
        rel,
        reserved_names=reserved_names,
        reserved_prefixes=reserved_prefixes,
        forbidden_part=forbidden_part,
    )


def resolve_user_path(
    user_path: str,
    *,
    default_root: str | None = None,
    allowed_roots=(),
    expanduser: bool = False,
    forbidden_names: frozenset[str] | set[str] = frozenset(),
    forbidden_prefixes: tuple[str, ...] = (),
) -> str:
    """Resolve an absolute-or-relative user path under a set of allowed roots.

    Relative inputs join under default_root; expanduser handles tilde first.
    The realpath result must stay under one of allowed_roots (roots are
    realpath-resolved too). forbidden_names rejects any resolved component
    (for example .ssh or .gnupg) and forbidden_prefixes rejects resolved paths
    under literal system prefixes. Order matches the legacy callers: jail
    membership first, then forbidden checks.
    """
    if not isinstance(user_path, str):
        raise PathJailError("path must be a string", reason="invalid")
    raw = user_path.strip()
    if not raw or "\x00" in raw:
        raise PathJailError("invalid path", reason="invalid")
    expanded = os.path.expanduser(raw) if expanduser else raw
    if not os.path.isabs(expanded):
        if not default_root:
            raise PathJailError("relative path has no root", reason="invalid")
        expanded = os.path.join(default_root, expanded)
    real = realpath_or_none(expanded)
    if not real:
        raise PathJailError("invalid path", reason="invalid")

    roots = []
    for root in allowed_roots:
        root_real = realpath_or_none(root)
        if root_real:
            roots.append(root_real)
    if not roots:
        raise PathJailError("no allowed roots configured", reason="invalid")
    if not any(is_under_root(real, root) for root in roots):
        raise PathJailError("path is outside the allowed roots", reason="escape")

    if forbidden_names:
        parts = {part for part in real.split(os.sep) if part}
        if parts & set(forbidden_names):
            raise PathJailError("path contains a forbidden name", reason="forbidden")
    for prefix in forbidden_prefixes:
        prefix_root = prefix.rstrip("/\\") if isinstance(prefix, str) else ""
        if prefix_root and is_under_root(real, prefix_root):
            raise PathJailError("path is under a forbidden prefix", reason="forbidden")
    return real


def safe_basename(filename: str, *, forbidden=None) -> str | None:
    """Return filename reduced to a safe basename, or None when unsafe.

    Rejects non-str, NUL, empty, dot, dot-dot, and any name that still holds a
    path separator after basename. forbidden is an optional callable(name) ->
    bool for per-feature reserved names.
    """
    if not isinstance(filename, str):
        return None
    raw = filename.strip()
    if not raw or "\x00" in raw:
        return None
    base = os.path.basename(raw.replace("\\", "/"))
    if not base or base in (".", "..") or "/" in base or "\\" in base:
        return None
    if forbidden is not None and forbidden(base):
        return None
    return base


# Windows device basenames stay reserved even with an extension (NUL.txt).
_WINDOWS_DEVICE_STEMS = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
)


def is_safe_archive_member(name: str) -> bool:
    """Return True when a zip or tar member name is safe to extract.

    Rejects non-str, NUL, absolute, drive or UNC forms, literal dot-dot
    segments (strict), empty or dot results, any colon, Windows device
    basenames, and trailing dot or space segments (Windows silently strips
    them, so a member could alias a different file on extraction).
    """
    if not isinstance(name, str) or "\x00" in name:
        return False
    try:
        cleaned = normalize_relpath(name, strict=True)
    except PathJailError:
        return False
    if ":" in cleaned:
        return False
    for part in cleaned.split("/"):
        if part.endswith((" ", ".")):
            return False
        if part.split(".", 1)[0].lower() in _WINDOWS_DEVICE_STEMS:
            return False
    return True


def is_direct_child(path: str, root: str) -> bool:
    """Return True when realpath(path) is a direct child of realpath(root)."""
    path_real = realpath_or_none(path)
    dir_real = realpath_or_none(root)
    if not path_real or not dir_real or path_real == dir_real:
        return False
    prefix = dir_real + os.sep
    if not path_real.startswith(prefix):
        return False
    rel = path_real[len(prefix) :]
    return bool(rel) and os.sep not in rel and "/" not in rel and "\\" not in rel


def first_component_under(candidate: str, root: str) -> str | None:
    """First path component of candidate relative to root, else None.

    Returns None when candidate is not strictly under root (resolved strings).
    """
    if not candidate or not root or candidate == root:
        return None
    if not is_under_root(candidate, root):
        return None
    return os.path.relpath(candidate, root).split(os.sep, 1)[0]


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
    path = realpath_or_none(os.path.join(directory, base))
    root = realpath_or_none(directory)
    if not path or not root or not is_under_root(path, root):
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
    return realpath_or_none(joined)


def atomic_write_bytes(
    path: str | os.PathLike[str],
    data: bytes,
    *,
    mode: int = 0o644,
) -> None:
    """Write data to path via a sibling tmp file, then os.replace.

    The tmp sibling is opened with O_NOFOLLOW where the platform supports it
    so a planted symlink cannot redirect the write. fchmod pins mode even
    when a stale regular tmp is truncated in place; pass 0o600 for private
    state.
    """
    path = os.fspath(path)
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    if os.path.lexists(tmp) and (os.path.islink(tmp) or os.path.isdir(tmp)):
        raise OSError("invalid atomic write destination")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(tmp, flags, mode)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    os.replace(tmp, path)


def atomic_write_text(
    path: str | os.PathLike[str],
    text: str,
    *,
    encoding: str = "utf-8",
    mode: int = 0o644,
) -> None:
    """Write text to path via atomic_write_bytes."""
    atomic_write_bytes(os.fspath(path), text.encode(encoding), mode=mode)


def resolve_log_dir():
    """Choose a writable log directory across container, desktop, and Windows.

    Honors MESHCHAT_STORAGE_DIR first, then falls back to deriving a logs
    directory from MESHCHAT_DATA_DIR (portable mode) when storage dir is
    unset, matching resolve_meshchat_data_roots precedence.
    """
    env_dir = os.environ.get("MESHCHAT_LOG_DIR")
    candidates = []
    if env_dir:
        candidates.append(env_dir)

    storage_dir = os.environ.get("MESHCHAT_STORAGE_DIR")
    if storage_dir:
        candidates.append(os.path.join(storage_dir, "logs"))
    else:
        data_dir = os.environ.get("MESHCHAT_DATA_DIR")
        if data_dir:
            candidates.append(
                os.path.join(
                    os.path.abspath(os.path.expanduser(data_dir)),
                    "storage",
                    "logs",
                ),
            )

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
