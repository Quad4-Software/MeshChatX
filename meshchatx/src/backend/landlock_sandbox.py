# SPDX-License-Identifier: 0BSD

"""Optional Landlock LSM filesystem sandbox for the backend (Linux only)."""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import logging
import os
import site
import sys
import tempfile

logger = logging.getLogger("meshchatx.landlock")

_LANDLOCK_ACCESS_FS_EXECUTE = 1 << 0
_LANDLOCK_ACCESS_FS_WRITE_FILE = 1 << 1
_LANDLOCK_ACCESS_FS_READ_FILE = 1 << 2
_LANDLOCK_ACCESS_FS_READ_DIR = 1 << 3
_LANDLOCK_ACCESS_FS_REMOVE_DIR = 1 << 4
_LANDLOCK_ACCESS_FS_REMOVE_FILE = 1 << 5
_LANDLOCK_ACCESS_FS_MAKE_CHAR = 1 << 6
_LANDLOCK_ACCESS_FS_MAKE_DIR = 1 << 7
_LANDLOCK_ACCESS_FS_MAKE_REG = 1 << 8
_LANDLOCK_ACCESS_FS_MAKE_SOCK = 1 << 9
_LANDLOCK_ACCESS_FS_MAKE_FIFO = 1 << 10
_LANDLOCK_ACCESS_FS_MAKE_BLOCK = 1 << 11
_LANDLOCK_ACCESS_FS_MAKE_SYM = 1 << 12

_LANDLOCK_CREATE_RULESET_VERSION = 1 << 0
_LANDLOCK_RULE_PATH_BENEATH = 1

_PR_SET_NO_NEW_PRIVS = 38

_READ_ACCESS = (
    _LANDLOCK_ACCESS_FS_READ_FILE
    | _LANDLOCK_ACCESS_FS_READ_DIR
    | _LANDLOCK_ACCESS_FS_EXECUTE
)
_RW_ACCESS = _READ_ACCESS | (
    _LANDLOCK_ACCESS_FS_WRITE_FILE
    | _LANDLOCK_ACCESS_FS_REMOVE_DIR
    | _LANDLOCK_ACCESS_FS_REMOVE_FILE
    | _LANDLOCK_ACCESS_FS_MAKE_CHAR
    | _LANDLOCK_ACCESS_FS_MAKE_DIR
    | _LANDLOCK_ACCESS_FS_MAKE_REG
    | _LANDLOCK_ACCESS_FS_MAKE_SOCK
    | _LANDLOCK_ACCESS_FS_MAKE_FIFO
    | _LANDLOCK_ACCESS_FS_MAKE_BLOCK
    | _LANDLOCK_ACCESS_FS_MAKE_SYM
)

_SYSCALL_NUMBERS = {
    "x86_64": (444, 445, 446),
    "aarch64": (444, 445, 446),
    "arm": (383, 384, 385),
    "riscv64": (444, 445, 446),
}


class _LandlockRulesetAttr(ctypes.Structure):
    _fields_ = [
        ("handled_access_fs", ctypes.c_uint64),
        ("handled_access_net", ctypes.c_uint64),
        ("scoped", ctypes.c_uint64),
    ]


class _LandlockPathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]
    _pack_ = 1


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
    raw = os.environ.get("MESHCHAT_LANDLOCK")
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in ("false", "0", "no", "off"):
        return False
    if val in ("true", "1", "yes", "on"):
        return True
    return None


_landlock_support_cached: bool | None = None


def _syscall_numbers():
    machine = os.uname().machine.lower()
    if machine in _SYSCALL_NUMBERS:
        return _SYSCALL_NUMBERS[machine]
    return _SYSCALL_NUMBERS.get("x86_64")


def _libc():
    name = ctypes.util.find_library("c")
    if not name:
        return None
    libc = ctypes.CDLL(name, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    return libc


def _syscall(libc, nr: int, *args):
    rc = libc.syscall(nr, *args)
    if rc < 0:
        err = ctypes.get_errno()
        msg = f"landlock syscall {nr} failed: errno {err}"
        raise OSError(err, os.strerror(err), msg)
    return rc


def _probe_landlock_create_ruleset() -> bool:
    libc = _libc()
    nums = _syscall_numbers()
    if libc is None or nums is None:
        return False
    create_nr, _, _ = nums
    try:
        abi = _syscall(libc, create_nr, 0, 0, _LANDLOCK_CREATE_RULESET_VERSION)
    except OSError as exc:
        if exc.errno in (errno.ENOSYS, errno.EOPNOTSUPP):
            return False
        return False
    return abi >= 1


def landlock_kernel_supported() -> bool:
    global _landlock_support_cached
    if _landlock_support_cached is not None:
        return _landlock_support_cached
    if sys.platform != "linux":
        _landlock_support_cached = False
        return False
    if not _kernel_version_meets_minimum():
        _landlock_support_cached = False
        return False
    _landlock_support_cached = _probe_landlock_create_ruleset()
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


def _set_no_new_privs(libc) -> None:
    rc = libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    if rc != 0:
        err = ctypes.get_errno()
        msg = f"prctl(PR_SET_NO_NEW_PRIVS) failed: errno {err}"
        raise OSError(msg)


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


def _collect_read_roots() -> list[str]:
    roots = {
        "/usr",
        "/lib",
        "/lib64",
        "/etc",
        "/bin",
        "/sbin",
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
    return sorted(roots)


def _collect_rw_roots(
    storage_dir: str | None,
    reticulum_config_dir: str | None,
    log_dir: str | None,
) -> list[str]:
    paths: list[str] = []
    for candidate in (
        storage_dir,
        reticulum_config_dir,
        log_dir,
        tempfile.gettempdir(),
        "/dev/shm",
        "/run",
    ):
        existing = _existing_dir(candidate)
        if existing and existing not in paths:
            paths.append(existing)
    if os.path.isdir("/dev"):
        paths.append("/dev")
    return paths


def _add_path_beneath_rule(
    libc,
    add_rule_nr: int,
    ruleset_fd: int,
    path: str,
    access: int,
) -> None:
    if not path or not os.path.exists(path):
        return
    effective_access = access
    if not os.path.isdir(path):
        effective_access = (
            _LANDLOCK_ACCESS_FS_READ_FILE | _LANDLOCK_ACCESS_FS_WRITE_FILE
        )
    open_flags = os.O_PATH | os.O_CLOEXEC | os.O_RDONLY
    try:
        fd = os.open(path, open_flags)
    except OSError:
        return
    try:
        attr = _LandlockPathBeneathAttr(allowed_access=effective_access, parent_fd=fd)
        _syscall(
            libc,
            add_rule_nr,
            ruleset_fd,
            _LANDLOCK_RULE_PATH_BENEATH,
            ctypes.byref(attr),
            0,
        )
    finally:
        os.close(fd)


def apply_landlock_sandbox(
    *,
    storage_dir: str | None = None,
    reticulum_config_dir: str | None = None,
    public_dir: str | None = None,
    log_dir: str | None = None,
) -> bool:
    """Apply Landlock rules. Returns True when the sandbox is active."""
    if not landlock_requested():
        return False

    libc = _libc()
    nums = _syscall_numbers()
    if libc is None or nums is None:
        logger.warning("Landlock requested but libc or syscall numbers are unavailable")
        return False

    create_nr, add_rule_nr, restrict_nr = nums
    try:
        _set_no_new_privs(libc)
    except OSError as exc:
        logger.warning("Landlock disabled: %s", exc)
        return False

    attr = _LandlockRulesetAttr(handled_access_fs=_RW_ACCESS)
    try:
        ruleset_fd = _syscall(
            libc,
            create_nr,
            ctypes.byref(attr),
            ctypes.sizeof(attr),
            0,
        )
    except OSError as exc:
        logger.warning("Landlock disabled: %s", exc)
        return False

    try:
        for root in _collect_read_roots():
            _add_path_beneath_rule(libc, add_rule_nr, ruleset_fd, root, _READ_ACCESS)
        rw_roots = _collect_rw_roots(storage_dir, reticulum_config_dir, log_dir)
        public_existing = _existing_dir(public_dir)
        if public_existing and public_existing not in rw_roots:
            rw_roots.append(public_existing)
        for root in rw_roots:
            _add_path_beneath_rule(libc, add_rule_nr, ruleset_fd, root, _RW_ACCESS)
        _syscall(libc, restrict_nr, ruleset_fd, 0)
    except OSError as exc:
        logger.warning("Landlock disabled while adding rules: %s", exc)
        try:
            os.close(ruleset_fd)
        except OSError:
            pass
        return False

    try:
        os.close(ruleset_fd)
    except OSError:
        pass

    if landlock_auto_enabled():
        logger.info("Landlock filesystem sandbox enabled (auto-detected on Linux)")
    else:
        logger.info("Landlock filesystem sandbox enabled")
    return True
