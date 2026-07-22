# SPDX-License-Identifier: 0BSD

"""Optional seccomp-BPF syscall denylist for the backend (Linux only).

Complements Landlock filesystem rules. Default action is ALLOW with a small
denylist of kernel-admin and process-introspection syscalls a mesh client never
needs. When libseccomp or the kernel filter is unavailable, apply falls back to
a no-op so the process still starts.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import logging
import os
import sys

logger = logging.getLogger("meshchatx.seccomp")

# From linux/seccomp.h / libseccomp.h
_SCMP_ACT_ALLOW = 0x7FFF0000
_SCMP_ACT_ERRNO_BASE = 0x00050000

# Dangerous or unused by MeshChatX. Names are resolved via libseccomp so unknown
# names on older kernels are skipped instead of failing the whole filter.
_DENIED_SYSCALLS = (
    "mount",
    "umount",
    "umount2",
    "pivot_root",
    "reboot",
    "kexec_load",
    "kexec_file_load",
    "init_module",
    "finit_module",
    "delete_module",
    "swapon",
    "swapoff",
    "bpf",
    "userfaultfd",
    "open_by_handle_at",
    "name_to_handle_at",
    "setns",
    "unshare",
    "acct",
    "ioperm",
    "iopl",
    "perf_event_open",
    "ptrace",
    "process_vm_readv",
    "process_vm_writev",
    "syslog",
    "quotactl",
    "lookup_dcookie",
    "fanotify_init",
    "open_tree",
    "move_mount",
    "fsopen",
    "fsconfig",
    "fsmount",
    "fspick",
    "mount_setattr",
    "vhangup",
    "uselib",
    "create_module",
    "query_module",
    "get_kernel_syms",
    "nfsservctl",
    "vm86",
    "vm86old",
    "_sysctl",
    "modify_ldt",
)


def _seccomp_env_override() -> bool | None:
    raw = os.environ.get("MESHCHAT_SECCOMP")
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in ("false", "0", "no", "off"):
        return False
    if val in ("true", "1", "yes", "on"):
        return True
    return None


def _is_android() -> bool:
    return hasattr(sys, "getandroidapilevel")


_seccomp_support_cached: bool | None = None
_seccomp_lib_cached = None
_seccomp_lib_failed = False


def _load_libseccomp():
    """Return a loaded libseccomp CDLL, or None when unavailable."""
    global _seccomp_lib_cached, _seccomp_lib_failed
    if _seccomp_lib_failed:
        return None
    if _seccomp_lib_cached is not None:
        return _seccomp_lib_cached

    candidates: list[str | None] = [
        ctypes.util.find_library("seccomp"),
        "libseccomp.so.2",
        "libseccomp.so",
    ]
    for name in candidates:
        if not name:
            continue
        try:
            lib = ctypes.CDLL(name)
        except OSError:
            continue
        required = (
            "seccomp_init",
            "seccomp_rule_add",
            "seccomp_load",
            "seccomp_release",
            "seccomp_syscall_resolve_name",
        )
        if any(not hasattr(lib, attr) for attr in required):
            continue

        lib.seccomp_init.argtypes = [ctypes.c_uint32]
        lib.seccomp_init.restype = ctypes.c_void_p
        lib.seccomp_rule_add.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        lib.seccomp_rule_add.restype = ctypes.c_int
        lib.seccomp_load.argtypes = [ctypes.c_void_p]
        lib.seccomp_load.restype = ctypes.c_int
        lib.seccomp_release.argtypes = [ctypes.c_void_p]
        lib.seccomp_release.restype = None
        lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
        lib.seccomp_syscall_resolve_name.restype = ctypes.c_int

        _seccomp_lib_cached = lib
        return lib

    _seccomp_lib_failed = True
    return None


def _act_errno(code: int = errno.EPERM) -> int:
    return _SCMP_ACT_ERRNO_BASE | (int(code) & 0xFFFF)


def seccomp_library_available() -> bool:
    """Return True when libseccomp can be loaded with the symbols we need."""
    return _load_libseccomp() is not None


def seccomp_kernel_supported() -> bool:
    """Return True when this host can install a user seccomp-BPF filter."""
    global _seccomp_support_cached
    if _seccomp_support_cached is not None:
        return _seccomp_support_cached
    if sys.platform != "linux" or _is_android():
        _seccomp_support_cached = False
        return False
    if not seccomp_library_available():
        _seccomp_support_cached = False
        return False
    # Probe by building an empty ALLOW filter without loading it.
    lib = _load_libseccomp()
    if lib is None:
        _seccomp_support_cached = False
        return False
    ctx = lib.seccomp_init(_SCMP_ACT_ALLOW)
    if not ctx:
        _seccomp_support_cached = False
        return False
    lib.seccomp_release(ctx)
    _seccomp_support_cached = True
    return True


def seccomp_requested() -> bool:
    if sys.platform != "linux" or _is_android():
        return False
    override = _seccomp_env_override()
    if override is False:
        return False
    if override is True:
        return True
    return seccomp_kernel_supported()


def seccomp_auto_enabled() -> bool:
    return seccomp_requested() and _seccomp_env_override() is None


def seccomp_disabled_by_env() -> bool:
    return _seccomp_env_override() is False


def apply_seccomp_sandbox() -> bool:
    """Install the denylist filter. Returns True when seccomp-BPF is active.

    Falls back to False (no filter) when unsupported, forced off, or install
    fails. Never raises into the caller for probe or load failures.
    """
    if not seccomp_requested():
        return False

    lib = _load_libseccomp()
    if lib is None:
        logger.warning(
            "Seccomp requested but libseccomp is unavailable; continuing without it",
        )
        return False

    ctx = lib.seccomp_init(_SCMP_ACT_ALLOW)
    if not ctx:
        logger.warning("Seccomp disabled: seccomp_init failed")
        return False

    denied = 0
    loaded = False
    try:
        for name in _DENIED_SYSCALLS:
            nr = lib.seccomp_syscall_resolve_name(name.encode("ascii"))
            if nr < 0:
                continue
            rc = lib.seccomp_rule_add(ctx, _act_errno(errno.EPERM), nr, 0)
            if rc != 0:
                logger.debug(
                    "Seccomp skip rule for %s: libseccomp rc %s",
                    name,
                    rc,
                )
                continue
            denied += 1

        if denied == 0:
            logger.warning("Seccomp disabled: no denylist rules could be installed")
            return False

        rc = lib.seccomp_load(ctx)
        if rc != 0:
            logger.warning("Seccomp disabled: seccomp_load failed with rc %s", rc)
            return False
        loaded = True
    except Exception as exc:
        logger.warning("Seccomp disabled: %s", exc)
        return False
    finally:
        lib.seccomp_release(ctx)

    if not loaded:
        return False

    if seccomp_auto_enabled():
        logger.info(
            "Seccomp-BPF syscall denylist enabled (auto-detected, %s rules)",
            denied,
        )
    else:
        logger.info("Seccomp-BPF syscall denylist enabled (%s rules)", denied)
    return True
