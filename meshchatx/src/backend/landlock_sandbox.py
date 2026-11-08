# SPDX-License-Identifier: 0BSD

"""Optional Landlock LSM filesystem sandbox for the backend (Linux only)."""

from __future__ import annotations

import logging
import os
import site
import sys
import tempfile

try:
    import landlockpy
    from landlockpy import AccessFS, AccessNet, Ruleset, Scope
except ImportError:  # pragma: no cover - dependency is declared, guard anyway
    landlockpy = None
    AccessFS = AccessNet = Ruleset = Scope = None

from meshchatx.src.env_utils import env_str
from meshchatx.src.path_utils import realpath_or_none

logger = logging.getLogger("meshchatx.landlock")

if landlockpy is not None:
    # ABI v1 filesystem rights. Newer rights are added only when the running
    # ABI supports them, and only granted on paths that already need write
    # or /dev.
    _FS_ACCESS_ABI1 = (
        AccessFS.EXECUTE
        | AccessFS.WRITE_FILE
        | AccessFS.READ_FILE
        | AccessFS.READ_DIR
        | AccessFS.REMOVE_DIR
        | AccessFS.REMOVE_FILE
        | AccessFS.MAKE_CHAR
        | AccessFS.MAKE_DIR
        | AccessFS.MAKE_REG
        | AccessFS.MAKE_SOCK
        | AccessFS.MAKE_FIFO
        | AccessFS.MAKE_BLOCK
        | AccessFS.MAKE_SYM
    )

    _READ_ACCESS_BASE = AccessFS.READ_FILE | AccessFS.READ_DIR | AccessFS.EXECUTE
    _RW_ACCESS_BASE = _READ_ACCESS_BASE | (
        AccessFS.WRITE_FILE
        | AccessFS.REMOVE_DIR
        | AccessFS.REMOVE_FILE
        | AccessFS.MAKE_CHAR
        | AccessFS.MAKE_DIR
        | AccessFS.MAKE_REG
        | AccessFS.MAKE_SOCK
        | AccessFS.MAKE_FIFO
        | AccessFS.MAKE_BLOCK
        | AccessFS.MAKE_SYM
    )
else:
    _FS_ACCESS_ABI1 = 0
    _READ_ACCESS_BASE = 0
    _RW_ACCESS_BASE = 0


def _parse_kernel_version(release: str) -> tuple[int, int, int]:
    base = (release or "").split("-", 1)[0]
    parts = base.split(".")
    nums: list[int] = []
    for part in parts[:3]:
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        nums.append(int(digits) if digits else 0)
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2]


def _kernel_version_meets_minimum(min_major: int = 5, min_minor: int = 13) -> bool:
    try:
        major, minor, _patch = _parse_kernel_version(os.uname().release)
    except (AttributeError, OSError, ValueError):
        return False
    if major > min_major:
        return True
    if major == min_major:
        return minor >= min_minor
    return False


def _landlock_env_override() -> bool | None:
    raw = env_str("MESHCHAT_LANDLOCK")
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in ("false", "0", "no", "off"):
        return False
    if val in ("true", "1", "yes", "on"):
        return True
    return None


_landlock_support_cached: bool | None = None
_landlock_abi_cached: int | None = None


def _handled_access_fs_for_abi(abi: int):
    """Return handled FS rights for a best-effort sandbox on this ABI.

    Intentionally omits network port rules and IPC scoping so mesh traffic,
    Unix sockets, and signals keep working. Omits RESOLVE_UNIX for the same
    reason. Rights we do handle are also granted on RW roots (including /dev).
    """
    if landlockpy is None or abi < 1:
        return AccessFS.NONE if landlockpy is not None else 0
    handled = _FS_ACCESS_ABI1
    if abi >= 2:
        handled |= AccessFS.REFER
    if abi >= 3:
        handled |= AccessFS.TRUNCATE
    if abi >= 5:
        handled |= AccessFS.IOCTL_DEV
    return handled


def _read_access_for_handled(handled):
    if landlockpy is None:
        return 0
    return _READ_ACCESS_BASE & handled


def _rw_access_for_handled(handled):
    if landlockpy is None:
        return 0
    access = _RW_ACCESS_BASE
    if handled & AccessFS.REFER:
        access |= AccessFS.REFER
    if handled & AccessFS.TRUNCATE:
        access |= AccessFS.TRUNCATE
    if handled & AccessFS.IOCTL_DEV:
        access |= AccessFS.IOCTL_DEV
    return access & handled


def _probe_landlock_abi() -> int:
    """Return the Landlock ABI version, or 0 when unavailable."""
    global _landlock_abi_cached
    if _landlock_abi_cached is not None:
        return _landlock_abi_cached
    if landlockpy is None:
        _landlock_abi_cached = 0
        return 0
    _landlock_abi_cached = int(landlockpy.abi_version())
    return _landlock_abi_cached


def _is_android() -> bool:
    """Return True when running under Android/Chaquopy.

    Android kernels may expose Landlock, but the app seccomp filter blocks
    the syscalls and raises SIGSYS. Landlock must never be enabled there.
    """
    return hasattr(sys, "getandroidapilevel")


def landlock_abi_version() -> int:
    """Return the probed Landlock ABI version, or 0 if unsupported."""
    if sys.platform != "linux" or _is_android():
        return 0
    if not _kernel_version_meets_minimum():
        return 0
    return _probe_landlock_abi()


def landlock_kernel_supported() -> bool:
    global _landlock_support_cached
    if _landlock_support_cached is not None:
        return _landlock_support_cached
    if sys.platform != "linux":
        _landlock_support_cached = False
        return False
    if _is_android():
        # Android seccomp blocks Landlock syscalls with SIGSYS.
        _landlock_support_cached = False
        return False
    if not _kernel_version_meets_minimum():
        _landlock_support_cached = False
        return False
    if landlockpy is None:
        _landlock_support_cached = False
        return False
    _landlock_support_cached = _probe_landlock_abi() >= 1
    return _landlock_support_cached


def landlock_requested() -> bool:
    if sys.platform != "linux":
        return False
    override = _landlock_env_override()
    if override is False:
        return False
    if override is True:
        return True
    return landlock_kernel_supported()


def landlock_auto_enabled() -> bool:
    return landlock_requested() and _landlock_env_override() is None


def landlock_disabled_by_env() -> bool:
    return _landlock_env_override() is False


def _existing_dir(path: str | None) -> str | None:
    if not path:
        return None
    resolved = os.path.abspath(os.path.expanduser(path))
    if os.path.isdir(resolved):
        return resolved
    parent = os.path.dirname(resolved)
    if parent and os.path.isdir(parent):
        return parent
    return None


def _unescape_mountinfo(field: str) -> str:
    r"""Decode the octal escapes (\040 for space, etc.) used in mountinfo."""
    out: list[str] = []
    i = 0
    while i < len(field):
        chunk = field[i : i + 4]
        if (
            len(chunk) == 4
            and chunk[0] == "\\"
            and all(c in "01234567" for c in chunk[1:])
        ):
            out.append(chr(int(chunk[1:], 8)))
            i += 4
        else:
            out.append(field[i])
            i += 1
    return "".join(out)


def _read_mountinfo(path: str = "/proc/self/mountinfo") -> list[tuple[str, str, str]]:
    """Return (mount_point, fstype, source) for each mount, in table order."""
    mounts: list[tuple[str, str, str]] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return mounts
    for line in lines:
        left, sep, right = line.partition(" - ")
        if not sep:
            continue
        left_fields = left.split()
        right_fields = right.split()
        if len(left_fields) < 5 or len(right_fields) < 2:
            continue
        mounts.append(
            (
                _unescape_mountinfo(left_fields[4]),
                right_fields[0],
                _unescape_mountinfo(right_fields[1]),
            ),
        )
    return mounts


def _mount_for_path(
    path: str,
    mounts: list[tuple[str, str, str]],
) -> tuple[str, str, str] | None:
    """Return the mount entry covering path (longest prefix, last one wins)."""
    best: tuple[str, str, str] | None = None
    for entry in mounts:
        mount_point = entry[0]
        if mount_point == "/":
            covers = True
        else:
            covers = path == mount_point or path.startswith(mount_point + "/")
        if covers and (best is None or len(mount_point) >= len(best[0])):
            best = entry
    return best


def _ecryptfs_lower_dirs(
    roots: list[str],
    mounts: list[tuple[str, str, str]] | None = None,
) -> tuple[list[str], list[str]]:
    """Find eCryptfs lower directories backing any of roots.

    eCryptfs is a stacked filesystem: opening a directory on the plaintext
    upper mount makes the kernel open the matching lower directory with the
    caller's credentials, which Landlock checks a second time. Returns
    (reachable lower dirs, unreachable eCryptfs sources). A source is
    unreachable when it does not exist in this mount namespace (containers,
    Flatpaks), where no rule can be added for it.
    """
    if mounts is None:
        mounts = _read_mountinfo()
    lower_dirs: list[str] = []
    unreachable: list[str] = []
    for root in roots:
        real = realpath_or_none(root) or root
        entry = _mount_for_path(real, mounts)
        if entry is None or entry[1] != "ecryptfs":
            continue
        source = entry[2]
        if os.path.isdir(source):
            resolved = realpath_or_none(source) or source
            if resolved not in lower_dirs:
                lower_dirs.append(resolved)
        elif source not in unreachable:
            unreachable.append(source)
    return lower_dirs, unreachable


def _collect_user_local_cli_roots() -> list[str]:
    """User-installed CLIs (pipx, rnsh/rnx wrappers, git-remote-rns, etc.)."""
    home = os.path.expanduser("~")
    if not home or home == "~":
        return []
    candidates = (
        os.path.join(home, ".local", "bin"),
        os.path.join(home, ".local", "share", "pipx"),
    )
    paths: list[str] = []
    for candidate in candidates:
        existing = _existing_dir(candidate)
        if existing and existing not in paths:
            paths.append(existing)
    return paths


def _collect_meshchatx_package_read_roots() -> list[str]:
    """Editable installs may load sources outside sys.path entries."""
    paths: list[str] = []
    try:
        import meshchatx as pkg
    except ImportError:
        return paths
    init_file = getattr(pkg, "__file__", None)
    if not init_file:
        return paths
    pkg_dir = _existing_dir(os.path.dirname(os.path.abspath(init_file)))
    if pkg_dir and pkg_dir not in paths:
        paths.append(pkg_dir)
    return paths


def _collect_read_roots() -> list[str]:
    roots = {
        "/usr",
        "/lib",
        "/lib64",
        "/etc",
        "/bin",
        "/sbin",
        # RNS get_interface_stats() uses psutil for rss, and psutil reads /proc/self.
        "/proc",
        # pyserial list_ports and RNode USB metadata read sysfs. Landlock still
        # allows stat/realpath on /sys while open() of idVendor fails, and
        # pyserial then raises TypeError from int(None, 16) which 500s
        # /api/v1/comports whenever a USB serial device is plugged in.
        "/sys",
    }
    for path in sys.path:
        existing = _existing_dir(path)
        if existing:
            roots.add(existing)
    for path in site.getsitepackages():
        existing = _existing_dir(path)
        if existing:
            roots.add(existing)
    user_site = site.getusersitepackages()
    existing = _existing_dir(user_site)
    if existing:
        roots.add(existing)
    # Allow execve of the running interpreter (uv-managed CPython lives outside
    # /usr, and bots, self-check, or rnsh re-spawn sys.executable under Landlock).
    for candidate in (sys.executable, os.path.realpath(sys.executable)):
        if not candidate:
            continue
        exe_dir = _existing_dir(os.path.dirname(candidate))
        if exe_dir:
            roots.add(exe_dir)
        # Venv layouts put pyvenv.cfg next to bin/, not under it. Allowing only
        # …/bin leaves child interpreters unable to read pyvenv.cfg (EACCES).
        venv_root = os.path.dirname(exe_dir) if exe_dir else None
        if venv_root and os.path.isfile(os.path.join(venv_root, "pyvenv.cfg")):
            existing_venv = _existing_dir(venv_root)
            if existing_venv:
                roots.add(existing_venv)
    # Prefer the install prefix (…/cpython-…/) so bin + lib are covered.
    for prefix_candidate in (
        getattr(sys, "base_prefix", None),
        sys.prefix,
        env_str("VIRTUAL_ENV"),
    ):
        prefix = _existing_dir(prefix_candidate)
        if prefix:
            roots.add(prefix)
    for root in _collect_user_local_cli_roots():
        roots.add(root)
    for root in _collect_meshchatx_package_read_roots():
        roots.add(root)
    return sorted(roots)


def _collect_rw_roots(
    storage_dir: str | None,
    reticulum_config_dir: str | None,
    log_dir: str | None,
) -> list[str]:
    # Reticulum creates its config dir only during deferred network setup,
    # which runs after restrict(). Create the directories we own now so
    # _existing_dir does not fall back to the parent and grant RW on the
    # whole home directory (including ~/.ssh) on first launch.
    for owned in (storage_dir, reticulum_config_dir):
        if owned:
            try:
                os.makedirs(os.path.expanduser(owned), exist_ok=True)
            except OSError:
                pass
    paths: list[str] = []
    for candidate in (
        storage_dir,
        reticulum_config_dir,
        log_dir,
        tempfile.gettempdir(),
        "/dev/shm",  # noqa: S108 - sandbox allowlist, not a temp file
        "/run",
    ):
        existing = _existing_dir(candidate)
        if existing and existing not in paths:
            paths.append(existing)
    if os.path.isdir("/dev"):
        paths.append("/dev")
    return paths


def _file_access_from_dir_access(access, handled):
    """Map a directory access mask to rights valid on a non-directory path."""
    file_bits = AccessFS.READ_FILE | AccessFS.WRITE_FILE
    if access & AccessFS.EXECUTE:
        file_bits |= AccessFS.EXECUTE
    if access & AccessFS.TRUNCATE:
        file_bits |= AccessFS.TRUNCATE
    if access & AccessFS.IOCTL_DEV:
        file_bits |= AccessFS.IOCTL_DEV
    return file_bits & access & handled


def _add_path_beneath_rule(ruleset, path: str, access, handled) -> None:
    if not path or not os.path.exists(path):
        return
    if not os.path.isdir(path):
        effective_access = _file_access_from_dir_access(access, handled)
    else:
        effective_access = access & handled
    if not effective_access:
        return
    try:
        ruleset.allow_path(path, effective_access)
    except landlockpy.LandlockError:
        raise
    except OSError:
        return


def _normalize_extra_landlock_read_root(path: str) -> str | None:
    """Return a realpath extra read root, or None when it would widen the jail.

    Rejects the filesystem root and the user home directory itself. A Sideband
    plugins folder may live under home. Home or / as the extra root would let
    a compromised plugin read ssh keys and the rest of the host tree.
    """
    if not isinstance(path, str) or not path.strip():
        return None
    resolved = realpath_or_none(os.path.abspath(os.path.expanduser(path.strip())))
    if not resolved or not os.path.isdir(resolved):
        return None
    fs_root = os.path.realpath(os.path.abspath(os.sep))
    if resolved == fs_root:
        return None
    home = os.path.expanduser("~")
    if home and home != "~":
        home_real = realpath_or_none(os.path.abspath(home)) or ""
        if home_real and resolved == home_real:
            return None
    return resolved


def extra_read_roots_from_app(app) -> list[str]:
    """Sideband command-plugin dirs chosen in settings, if they exist on disk.

    Does not fall back to the parent directory. A missing path must not widen
    Landlock to whatever folder happens to sit above it.
    """
    try:
        cfg = getattr(app, "config", None)
        path_cfg = (
            getattr(cfg, "command_plugins_path", None) if cfg is not None else None
        )
        raw = path_cfg.get() if path_cfg is not None else None
    except Exception:
        raw = None
    if not raw:
        return []
    resolved = _normalize_extra_landlock_read_root(str(raw))
    if resolved:
        return [resolved]
    return []


def apply_landlock_sandbox(
    *,
    storage_dir: str | None = None,
    reticulum_config_dir: str | None = None,
    public_dir: str | None = None,
    log_dir: str | None = None,
    extra_read_roots: list[str] | None = None,
    extra_rw_roots: list[str] | None = None,
) -> bool:
    """Apply Landlock rules. Returns True when the sandbox is active."""
    if not landlock_requested():
        return False

    if landlockpy is None or Ruleset is None or AccessFS is None:
        logger.warning("Landlock requested but landlockpy is not installed")
        return False

    abi = _probe_landlock_abi()
    if abi < 1:
        logger.warning("Landlock disabled: ABI probe failed")
        return False

    handled = _handled_access_fs_for_abi(abi)
    if not isinstance(handled, AccessFS):
        return False
    read_access = _read_access_for_handled(handled)
    rw_access = _rw_access_for_handled(handled)
    try:
        ruleset = Ruleset(
            handled_fs=handled,
            handled_net=AccessNet.NONE,
            scoped=Scope.NONE,
        )
    except OSError as exc:
        logger.warning("Landlock disabled: %s", exc)
        return False

    try:
        read_roots = list(_collect_read_roots())
        for extra in extra_read_roots or []:
            if not extra:
                continue
            resolved = _normalize_extra_landlock_read_root(str(extra))
            if resolved and resolved not in read_roots:
                read_roots.append(resolved)
        rw_roots = _collect_rw_roots(storage_dir, reticulum_config_dir, log_dir)
        public_existing = _existing_dir(public_dir)
        if public_existing and public_existing not in rw_roots:
            rw_roots.append(public_existing)
        for extra in extra_rw_roots or []:
            if not extra:
                continue
            resolved = _normalize_extra_landlock_read_root(str(extra))
            if resolved and resolved not in rw_roots:
                rw_roots.append(resolved)
        # The eCryptfs check must run before the first allow_path and see
        # every root: a root added later could sit on an eCryptfs mount the
        # check never saw, leaving directory listings broken under Landlock.
        lower_dirs, unreachable = _ecryptfs_lower_dirs(read_roots + rw_roots)
        if unreachable and _landlock_env_override() is not True:
            logger.warning(
                "Landlock disabled: allowed paths live on eCryptfs (%s) whose "
                "lower directory is not visible here, so directory listings "
                "would fail.",
                ", ".join(unreachable),
            )
            ruleset.close()
            return False
        for root in read_roots:
            _add_path_beneath_rule(ruleset, root, read_access, handled)
        # READ_DIR only: enough for the lower-directory opens eCryptfs
        # forwards to the caller's credentials. Exposes encrypted file
        # names, never plaintext contents or write access to the tree.
        for lower in lower_dirs:
            _add_path_beneath_rule(ruleset, lower, AccessFS.READ_DIR, handled)
        for root in rw_roots:
            _add_path_beneath_rule(ruleset, root, rw_access, handled)
        ruleset.restrict()
    except OSError as exc:
        logger.warning("Landlock disabled while adding rules: %s", exc)
        ruleset.close()
        return False

    ruleset.close()

    if landlock_auto_enabled():
        logger.info(
            "Landlock filesystem sandbox enabled (auto-detected on Linux, ABI %s)",
            abi,
        )
    else:
        logger.info("Landlock filesystem sandbox enabled (ABI %s)", abi)
    return True
