# SPDX-License-Identifier: 0BSD

"""Optional Windows AppContainer / LPAC filesystem sandbox for the backend.

Mirrors Landlock intent on Win10 and Win11: deny ambient write access and
grant RW only under MeshChatX storage, Reticulum config, logs, and temp.
Unlike Landlock, policy is applied at CreateProcess time via a launcher.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger("meshchatx.appcontainer")

APPCONTAINER_PROFILE_NAME = "MeshChatX.Backend"
APPCONTAINER_DISPLAY_NAME = "MeshChatX Backend"
CHILD_ENV_FLAG = "MESHCHAT_APPCONTAINER_CHILD"
ENV_VAR = "MESHCHAT_APPCONTAINER"
# Dedicated exchange dirs under the user profile. Do not ACL-grant all of
# Documents or Downloads. Attachments and exports use these subfolders only.
USER_EXCHANGE_DIR_NAME = "MeshChatX"

# Win32 constants
_ERROR_ALREADY_EXISTS = 183
_ERROR_SUCCESS = 0
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_GENERIC_EXECUTE = 0x20000000
_GENERIC_ALL = 0x10000000
_FILE_GENERIC_READ = 0x00120089
_FILE_GENERIC_WRITE = 0x00120116
_FILE_GENERIC_EXECUTE = 0x001200A0

_GRANT_ACCESS = 1
_REVOKE_ACCESS = 4
_TRUSTEE_IS_SID = 0
_TRUSTEE_IS_UNKNOWN = 0
_SUB_CONTAINERS_AND_OBJECTS_INHERIT = 0x3
_SE_FILE_OBJECT = 1
_DACL_SECURITY_INFORMATION = 0x00000004
_PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000

_SE_GROUP_ENABLED = 0x00000004

_CREATE_UNICODE_ENVIRONMENT = 0x00000400
_EXTENDED_STARTUPINFO_PRESENT = 0x00080000
_CREATE_NO_WINDOW = 0x08000000

# ProcThreadAttributeList numbers (Windows 8+)
_PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
_PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY = 0x0002000E
_PROCESS_CREATION_ALL_APPLICATION_PACKAGES_OPT_OUT = 1

# WELL_KNOWN_SID_TYPE for AppContainer network capabilities
_WinCapabilityInternetClientSid = 85
_WinCapabilityInternetClientServerSid = 86
_WinCapabilityPrivateNetworkClientServerSid = 84

_INFINITE = 0xFFFFFFFF
_WAIT_OBJECT_0 = 0

_MITIGATION_POLICY_EXTENSION_POINT_DISABLE = 6
_MITIGATION_POLICY_IMAGE_LOAD = 10
_MITIGATION_POLICY_STRICT_HANDLE_CHECK = 3


@dataclass(frozen=True)
class LaunchResult:
    """Outcome of launching a process into an AppContainer."""

    ok: bool
    exit_code: int | None = None
    error: str | None = None
    used_appcontainer: bool = False
    fell_back: bool = False


class _SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Sid", ctypes.c_void_p),
        ("Attributes", ctypes.c_ulong),
    ]


class _SECURITY_CAPABILITIES(ctypes.Structure):
    _fields_ = [
        ("AppContainerSid", ctypes.c_void_p),
        ("Capabilities", ctypes.POINTER(_SID_AND_ATTRIBUTES)),
        ("CapabilityCount", ctypes.c_ulong),
        ("Reserved", ctypes.c_ulong),
    ]


class _STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("lpReserved", ctypes.c_wchar_p),
        ("lpDesktop", ctypes.c_wchar_p),
        ("lpTitle", ctypes.c_wchar_p),
        ("dwX", ctypes.c_ulong),
        ("dwY", ctypes.c_ulong),
        ("dwXSize", ctypes.c_ulong),
        ("dwYSize", ctypes.c_ulong),
        ("dwXCountChars", ctypes.c_ulong),
        ("dwYCountChars", ctypes.c_ulong),
        ("dwFillAttribute", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("wShowWindow", ctypes.c_ushort),
        ("cbReserved2", ctypes.c_ushort),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", ctypes.c_void_p),
        ("hStdOutput", ctypes.c_void_p),
        ("hStdError", ctypes.c_void_p),
    ]


class _STARTUPINFOEX(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", _STARTUPINFO),
        ("lpAttributeList", ctypes.c_void_p),
    ]


class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", ctypes.c_void_p),
        ("hThread", ctypes.c_void_p),
        ("dwProcessId", ctypes.c_ulong),
        ("dwThreadId", ctypes.c_ulong),
    ]


class _TRUSTEE_W(ctypes.Structure):
    _fields_ = [
        ("pMultipleTrustee", ctypes.c_void_p),
        ("MultipleTrusteeOperation", ctypes.c_ulong),
        ("TrusteeForm", ctypes.c_ulong),
        ("TrusteeType", ctypes.c_ulong),
        ("ptstrName", ctypes.c_void_p),
    ]


class _EXPLICIT_ACCESS_W(ctypes.Structure):
    _fields_ = [
        ("grfAccessPermissions", ctypes.c_ulong),
        ("grfAccessMode", ctypes.c_ulong),
        ("grfInheritance", ctypes.c_ulong),
        ("Trustee", _TRUSTEE_W),
    ]


class _PROCESS_MITIGATION_EXTENSION_POINT_DISABLE_POLICY(ctypes.Structure):
    _fields_ = [("Flags", ctypes.c_ulong)]


class _PROCESS_MITIGATION_IMAGE_LOAD_POLICY(ctypes.Structure):
    _fields_ = [("Flags", ctypes.c_ulong)]


class _PROCESS_MITIGATION_STRICT_HANDLE_CHECK_POLICY(ctypes.Structure):
    _fields_ = [("Flags", ctypes.c_ulong)]


_appcontainer_support_cached: bool | None = None


def _env_override() -> bool | None:
    raw = os.environ.get(ENV_VAR)
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in ("false", "0", "no", "off"):
        return False
    if val in ("true", "1", "yes", "on"):
        return True
    return None


def is_appcontainer_child() -> bool:
    """Return True when this process was launched inside the AppContainer."""
    raw = os.environ.get(CHILD_ENV_FLAG, "")
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _windows_version_supported() -> bool:
    if sys.platform != "win32":
        return False
    try:
        ver = sys.getwindowsversion()
    except AttributeError:
        return False
    # AppContainer exists since Win8. LPAC and packaging we rely on need Win10+.
    return int(ver.major) >= 10


def _probe_appcontainer_apis() -> bool:
    if sys.platform != "win32":
        return False
    try:
        userenv = ctypes.WinDLL("userenv", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    except OSError:
        return False
    required = (
        hasattr(userenv, "CreateAppContainerProfile"),
        hasattr(userenv, "DeriveAppContainerSidFromAppContainerName"),
        hasattr(userenv, "DeleteAppContainerProfile"),
        hasattr(kernel32, "InitializeProcThreadAttributeList"),
        hasattr(kernel32, "UpdateProcThreadAttribute"),
        hasattr(kernel32, "DeleteProcThreadAttributeList"),
        hasattr(advapi32, "SetEntriesInAclW"),
        hasattr(advapi32, "GetNamedSecurityInfoW"),
        hasattr(advapi32, "SetNamedSecurityInfoW"),
        hasattr(advapi32, "CreateWellKnownSid"),
    )
    return all(required)


def appcontainer_supported() -> bool:
    global _appcontainer_support_cached
    if _appcontainer_support_cached is not None:
        return _appcontainer_support_cached
    if sys.platform != "win32":
        _appcontainer_support_cached = False
        return False
    if not _windows_version_supported():
        _appcontainer_support_cached = False
        return False
    _appcontainer_support_cached = _probe_appcontainer_apis()
    return _appcontainer_support_cached


def appcontainer_requested() -> bool:
    if sys.platform != "win32":
        return False
    override = _env_override()
    if override is False:
        return False
    if override is True:
        return True
    return False


def appcontainer_auto_enabled() -> bool:
    return appcontainer_requested() and _env_override() is None


def appcontainer_disabled_by_env() -> bool:
    return _env_override() is False


def appcontainer_forced() -> bool:
    return _env_override() is True


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


def _ensure_dir(path: str | None) -> str | None:
    if not path:
        return None
    resolved = os.path.abspath(os.path.expanduser(path))
    try:
        os.makedirs(resolved, exist_ok=True)
    except OSError:
        return None
    if os.path.isdir(resolved):
        return resolved
    return None


def _windows_known_folder(folder_id: str) -> str | None:
    """Resolve a Windows Known Folder GUID to a path (handles OneDrive redirects)."""
    if sys.platform != "win32":
        return None
    try:
        from ctypes import wintypes

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", wintypes.BYTE * 8),
            ]

        def _parse_guid(value: str) -> _GUID:
            hex_part = value.strip("{}")
            parts = hex_part.split("-")
            data4_hex = parts[3] + parts[4]
            data4 = (wintypes.BYTE * 8)(
                *[int(data4_hex[i : i + 2], 16) for i in range(0, 16, 2)]
            )
            return _GUID(
                int(parts[0], 16),
                int(parts[1], 16),
                int(parts[2], 16),
                data4,
            )

        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)
        path_ptr = ctypes.c_wchar_p()
        fid = _parse_guid(folder_id)
        # KF_FLAG_DEFAULT = 0
        hr = shell32.SHGetKnownFolderPath(
            ctypes.byref(fid),
            0,
            None,
            ctypes.byref(path_ptr),
        )
        if hr != 0 or not path_ptr.value:
            return None
        try:
            return str(path_ptr.value)
        finally:
            ole32.CoTaskMemFree(path_ptr)
    except Exception:
        return None


def _user_profile_dir() -> str | None:
    if sys.platform == "win32":
        for key in ("USERPROFILE", "HOME"):
            raw = os.environ.get(key)
            if raw:
                return os.path.abspath(raw)
    home = os.path.expanduser("~")
    if home and home != "~":
        return os.path.abspath(home)
    return None


def collect_user_exchange_roots(*, create: bool = True) -> list[str]:
    """Return Documents/Downloads/Pictures MeshChatX subfolders for attachments.

    Grants RW only under these app-owned exchange dirs, never the entire
    Documents or Downloads tree.
    """
    roots: list[str] = []
    profile = _user_profile_dir()

    known = {
        "documents": _windows_known_folder("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"),
        "downloads": _windows_known_folder("{374DE290-123F-4565-9164-39C4925E467B}"),
        "pictures": _windows_known_folder("{33E28130-4E1E-4676-835A-98395C3BC3BB}"),
    }
    # Fallback when Known Folder APIs are unavailable (tests / non-Windows).
    if profile:
        if not known["documents"]:
            known["documents"] = os.path.join(profile, "Documents")
        if not known["downloads"]:
            known["downloads"] = os.path.join(profile, "Downloads")
        if not known["pictures"]:
            known["pictures"] = os.path.join(profile, "Pictures")

    for parent in (known["documents"], known["downloads"], known["pictures"]):
        if not parent:
            continue
        exchange = os.path.join(parent, USER_EXCHANGE_DIR_NAME)
        if create:
            ensured = _ensure_dir(exchange)
            if ensured and ensured not in roots:
                roots.append(ensured)
            continue
        existing = _existing_dir(exchange)
        if existing and existing not in roots:
            roots.append(existing)
    return roots


def collect_rw_roots(
    storage_dir: str | None,
    reticulum_config_dir: str | None,
    log_dir: str | None,
    *,
    exe_dir: str | None = None,
) -> list[str]:
    """Collect directories that need Package-SID write access."""
    paths: list[str] = []
    for candidate in (
        storage_dir,
        reticulum_config_dir,
        log_dir,
        tempfile.gettempdir(),
        os.environ.get("TMP"),
        os.environ.get("TEMP"),
        os.environ.get("TMPDIR"),
    ):
        existing = _existing_dir(candidate)
        if existing and existing not in paths:
            paths.append(existing)
    # Ensure parents exist for storage/config/log even before first write.
    for candidate in (storage_dir, reticulum_config_dir, log_dir):
        if not candidate:
            continue
        resolved = os.path.abspath(os.path.expanduser(candidate))
        try:
            os.makedirs(resolved, exist_ok=True)
        except OSError:
            continue
        if resolved not in paths:
            paths.append(resolved)
    for exchange in collect_user_exchange_roots(create=True):
        if exchange not in paths:
            paths.append(exchange)
    return paths


def collect_ro_roots(*, exe_dir: str | None = None) -> list[str]:
    """Collect directories that need Package-SID read/execute access under LPAC."""
    paths: list[str] = []
    for candidate in (
        exe_dir,
        os.path.dirname(sys.executable) if sys.executable else None,
        getattr(sys, "prefix", None),
        getattr(sys, "base_prefix", None),
    ):
        existing = _existing_dir(candidate)
        if existing and existing not in paths:
            paths.append(existing)
    return paths


def _as_void_p(ptr: ctypes.c_void_p | int | None) -> ctypes.c_void_p:
    if isinstance(ptr, ctypes.c_void_p):
        return ptr
    return ctypes.c_void_p(ptr)


def _local_free(ptr: ctypes.c_void_p | int | None) -> None:
    if not ptr:
        return
    try:
        ctypes.windll.kernel32.LocalFree(_as_void_p(ptr))
    except Exception:
        pass


def _create_capability_sid(well_known: int) -> ctypes.c_void_p | None:
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    size = ctypes.c_ulong(0)
    advapi32.CreateWellKnownSid(
        well_known,
        None,
        None,
        ctypes.byref(size),
    )
    if size.value == 0:
        return None
    buf = (ctypes.c_ubyte * size.value)()
    ok = advapi32.CreateWellKnownSid(
        well_known,
        None,
        ctypes.byref(buf),
        ctypes.byref(size),
    )
    if not ok:
        return None
    # Keep buffer alive by attaching to a c_void_p holder via identity.
    holder = ctypes.cast(buf, ctypes.c_void_p)
    holder._sid_buffer = buf  # type: ignore[attr-defined]
    return holder


def ensure_appcontainer_profile(
    profile_name: str = APPCONTAINER_PROFILE_NAME,
) -> ctypes.c_void_p:
    """Create or derive the AppContainer package SID for profile_name."""
    userenv = ctypes.WinDLL("userenv", use_last_error=True)
    sid = ctypes.c_void_p()
    hr = userenv.CreateAppContainerProfile(
        ctypes.c_wchar_p(profile_name),
        ctypes.c_wchar_p(profile_name),
        ctypes.c_wchar_p(APPCONTAINER_DISPLAY_NAME),
        None,
        0,
        ctypes.byref(sid),
    )
    # HRESULT: S_OK (0) or HRESULT_FROM_WIN32(ERROR_ALREADY_EXISTS)
    if hr == 0 and sid.value:
        return sid
    # Already exists or create returned SID unset: derive it.
    if sid.value:
        try:
            ctypes.windll.kernel32.LocalFree(sid)
        except Exception:
            pass
    sid = ctypes.c_void_p()
    hr = userenv.DeriveAppContainerSidFromAppContainerName(
        ctypes.c_wchar_p(profile_name),
        ctypes.byref(sid),
    )
    if hr != 0 or not sid.value:
        err = ctypes.get_last_error()
        raise OSError(
            err, f"DeriveAppContainerSidFromAppContainerName failed: hr={hr} err={err}"
        )
    return sid


def delete_appcontainer_profile(profile_name: str = APPCONTAINER_PROFILE_NAME) -> None:
    userenv = ctypes.WinDLL("userenv", use_last_error=True)
    hr = userenv.DeleteAppContainerProfile(ctypes.c_wchar_p(profile_name))
    if hr not in (0,):
        # Best effort cleanup. Profile may be in use.
        logger.debug("DeleteAppContainerProfile hr=%s", hr)


def _set_path_access(
    path: str, sid: ctypes.c_void_p, access_mask: int, mode: int
) -> None:
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    ea = _EXPLICIT_ACCESS_W()
    ea.grfAccessPermissions = access_mask
    ea.grfAccessMode = mode
    ea.grfInheritance = _SUB_CONTAINERS_AND_OBJECTS_INHERIT
    ea.Trustee.pMultipleTrustee = None
    ea.Trustee.MultipleTrusteeOperation = 0
    ea.Trustee.TrusteeForm = _TRUSTEE_IS_SID
    ea.Trustee.TrusteeType = _TRUSTEE_IS_UNKNOWN
    ea.Trustee.ptstrName = sid

    # Merge with the existing DACL so we do not wipe user or system ACEs.
    p_sd = ctypes.c_void_p()
    p_dacl = ctypes.c_void_p()
    get_status = advapi32.GetNamedSecurityInfoW(
        ctypes.c_wchar_p(path),
        _SE_FILE_OBJECT,
        _DACL_SECURITY_INFORMATION,
        None,
        None,
        ctypes.byref(p_dacl),
        None,
        ctypes.byref(p_sd),
    )
    if get_status != _ERROR_SUCCESS:
        err = ctypes.get_last_error()
        raise OSError(
            err, f"GetNamedSecurityInfoW failed for {path}: status={get_status}"
        )

    new_acl = ctypes.c_void_p()
    try:
        status = advapi32.SetEntriesInAclW(
            1,
            ctypes.byref(ea),
            p_dacl,
            ctypes.byref(new_acl),
        )
        if status != _ERROR_SUCCESS or not new_acl.value:
            err = ctypes.get_last_error()
            raise OSError(err, f"SetEntriesInAclW failed for {path}: status={status}")

        result = advapi32.SetNamedSecurityInfoW(
            ctypes.c_wchar_p(path),
            _SE_FILE_OBJECT,
            _DACL_SECURITY_INFORMATION,
            None,
            None,
            new_acl,
            None,
        )
        if result != _ERROR_SUCCESS:
            err = ctypes.get_last_error()
            raise OSError(
                err, f"SetNamedSecurityInfoW failed for {path}: result={result}"
            )
    finally:
        _local_free(new_acl.value)
        _local_free(p_sd.value)


def grant_path_access(sid: ctypes.c_void_p, path: str, *, write: bool) -> None:
    if write:
        mask = _GENERIC_READ | _GENERIC_WRITE | _GENERIC_EXECUTE | _GENERIC_ALL
    else:
        mask = _GENERIC_READ | _GENERIC_EXECUTE
    _set_path_access(path, sid, mask, _GRANT_ACCESS)


def revoke_path_access(sid: ctypes.c_void_p, path: str) -> None:
    try:
        _set_path_access(
            path,
            sid,
            _GENERIC_READ | _GENERIC_WRITE | _GENERIC_EXECUTE | _GENERIC_ALL,
            _REVOKE_ACCESS,
        )
    except OSError as exc:
        logger.debug("revoke_path_access %s: %s", path, exc)


def _build_command_line(exe: str, args: list[str]) -> str:
    parts = [exe, *args]

    def quote(part: str) -> str:
        if not part:
            return '""'
        if any(ch in part for ch in (" ", "\t", '"')):
            escaped = part.replace('"', '\\"')
            return f'"{escaped}"'
        return part

    return " ".join(quote(p) for p in parts)


def _wait_process(handle: ctypes.c_void_p) -> int:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    wait = kernel32.WaitForSingleObject(handle, _INFINITE)
    if wait != _WAIT_OBJECT_0:
        raise OSError(ctypes.get_last_error(), "WaitForSingleObject failed")
    code = ctypes.c_ulong()
    if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
        raise OSError(ctypes.get_last_error(), "GetExitCodeProcess failed")
    return int(code.value)


def create_process_in_appcontainer(
    exe: str,
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    use_lpac: bool = True,
    cwd: str | None = None,
) -> tuple[ctypes.c_void_p, ctypes.c_void_p, int]:
    """Create a child process inside the MeshChatX AppContainer profile.

    Returns (hProcess, hThread, pid). Caller must CloseHandle both handles.
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    sid = ensure_appcontainer_profile()

    capability_types = (
        _WinCapabilityInternetClientSid,
        _WinCapabilityInternetClientServerSid,
        _WinCapabilityPrivateNetworkClientServerSid,
    )
    capability_holders: list[ctypes.c_void_p] = []
    for wk in capability_types:
        cap = _create_capability_sid(wk)
        if cap is not None and cap.value:
            capability_holders.append(cap)

    caps_array = (_SID_AND_ATTRIBUTES * max(1, len(capability_holders)))()
    for i, holder in enumerate(capability_holders):
        caps_array[i].Sid = holder
        caps_array[i].Attributes = _SE_GROUP_ENABLED

    sec_caps = _SECURITY_CAPABILITIES()
    sec_caps.AppContainerSid = sid
    if capability_holders:
        sec_caps.Capabilities = ctypes.cast(
            caps_array, ctypes.POINTER(_SID_AND_ATTRIBUTES)
        )
        sec_caps.CapabilityCount = len(capability_holders)
    else:
        sec_caps.Capabilities = None
        sec_caps.CapabilityCount = 0
    sec_caps.Reserved = 0

    attr_count = 2 if use_lpac else 1
    size = ctypes.c_size_t(0)
    kernel32.InitializeProcThreadAttributeList(None, attr_count, 0, ctypes.byref(size))
    if size.value == 0:
        raise OSError(
            ctypes.get_last_error(), "InitializeProcThreadAttributeList size failed"
        )
    attr_buf = (ctypes.c_ubyte * size.value)()
    attr_list = ctypes.cast(attr_buf, ctypes.c_void_p)
    if not kernel32.InitializeProcThreadAttributeList(
        attr_list, attr_count, 0, ctypes.byref(size)
    ):
        raise OSError(
            ctypes.get_last_error(), "InitializeProcThreadAttributeList failed"
        )

    try:
        if not kernel32.UpdateProcThreadAttribute(
            attr_list,
            0,
            _PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
            ctypes.byref(sec_caps),
            ctypes.sizeof(sec_caps),
            None,
            None,
        ):
            raise OSError(
                ctypes.get_last_error(),
                "UpdateProcThreadAttribute SECURITY_CAPABILITIES failed",
            )

        lpac_policy = ctypes.c_ulong(_PROCESS_CREATION_ALL_APPLICATION_PACKAGES_OPT_OUT)
        if use_lpac:
            if not kernel32.UpdateProcThreadAttribute(
                attr_list,
                0,
                _PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY,
                ctypes.byref(lpac_policy),
                ctypes.sizeof(lpac_policy),
                None,
                None,
            ):
                raise OSError(
                    ctypes.get_last_error(),
                    "UpdateProcThreadAttribute LPAC policy failed",
                )

        siex = _STARTUPINFOEX()
        siex.StartupInfo.cb = ctypes.sizeof(siex)
        siex.lpAttributeList = attr_list

        pi = _PROCESS_INFORMATION()
        cmdline = ctypes.create_unicode_buffer(_build_command_line(exe, args))

        child_env = dict(os.environ if env is None else env)
        child_env[CHILD_ENV_FLAG] = "1"
        child_env.pop("MESHCHAT_APPCONTAINER_LAUNCHER", None)
        # Build environment block (null-separated, double-null terminated).
        env_block = "\0".join(f"{k}={v}" for k, v in child_env.items()) + "\0\0"
        env_buf = ctypes.create_unicode_buffer(env_block)

        creation_flags = (
            _EXTENDED_STARTUPINFO_PRESENT
            | _CREATE_UNICODE_ENVIRONMENT
            | _CREATE_NO_WINDOW
        )
        ok = kernel32.CreateProcessW(
            ctypes.c_wchar_p(exe),
            cmdline,
            None,
            None,
            True,
            creation_flags,
            env_buf,
            ctypes.c_wchar_p(cwd) if cwd else None,
            ctypes.byref(siex),
            ctypes.byref(pi),
        )
        if not ok:
            raise OSError(ctypes.get_last_error(), "CreateProcessW AppContainer failed")
        return pi.hProcess, pi.hThread, int(pi.dwProcessId)
    finally:
        kernel32.DeleteProcThreadAttributeList(attr_list)
        # Free derived package SID after CreateProcess has copied capabilities.
        try:
            ctypes.windll.kernel32.LocalFree(sid)
        except Exception:
            pass


def create_process_unsandboxed(
    exe: str,
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
) -> tuple[ctypes.c_void_p, ctypes.c_void_p, int]:
    """Create a normal child process (auto-fallback path)."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    si = _STARTUPINFO()
    si.cb = ctypes.sizeof(si)
    pi = _PROCESS_INFORMATION()
    cmdline = ctypes.create_unicode_buffer(_build_command_line(exe, args))
    child_env = dict(os.environ if env is None else env)
    child_env.pop(CHILD_ENV_FLAG, None)
    child_env.pop("MESHCHAT_APPCONTAINER_LAUNCHER", None)
    env_block = "\0".join(f"{k}={v}" for k, v in child_env.items()) + "\0\0"
    env_buf = ctypes.create_unicode_buffer(env_block)
    ok = kernel32.CreateProcessW(
        ctypes.c_wchar_p(exe),
        cmdline,
        None,
        None,
        True,
        _CREATE_UNICODE_ENVIRONMENT | _CREATE_NO_WINDOW,
        env_buf,
        ctypes.c_wchar_p(cwd) if cwd else None,
        ctypes.byref(si),
        ctypes.byref(pi),
    )
    if not ok:
        raise OSError(ctypes.get_last_error(), "CreateProcessW unsandboxed failed")
    return pi.hProcess, pi.hThread, int(pi.dwProcessId)


def close_handle(handle: ctypes.c_void_p | int | None) -> None:
    if not handle:
        return
    try:
        ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(_as_void_p(handle))
    except Exception:
        pass


def launch_backend_sandboxed(
    exe: str,
    args: list[str],
    *,
    storage_dir: str | None,
    reticulum_config_dir: str | None,
    log_dir: str | None,
    forced: bool | None = None,
    use_lpac: bool = True,
) -> LaunchResult:
    """Grant ACLs, launch into AppContainer, wait, revoke ACLs.

    Auto mode (forced=False): on AppContainer failure, fall back to unsandboxed.
    Forced mode: return error without fallback.
    """
    if forced is None:
        forced = appcontainer_forced()

    rw_roots = collect_rw_roots(storage_dir, reticulum_config_dir, log_dir)
    ro_roots = collect_ro_roots(exe_dir=os.path.dirname(exe) if exe else None)
    sid: ctypes.c_void_p | None = None
    granted: list[tuple[str, bool]] = []

    try:
        sid = ensure_appcontainer_profile()
        for path in rw_roots:
            grant_path_access(sid, path, write=True)
            granted.append((path, True))
        for path in ro_roots:
            if path in rw_roots:
                continue
            grant_path_access(sid, path, write=False)
            granted.append((path, False))

        h_process, h_thread, _pid = create_process_in_appcontainer(
            exe,
            args,
            use_lpac=use_lpac,
        )
        try:
            close_handle(h_thread)
            exit_code = _wait_process(h_process)
        finally:
            close_handle(h_process)
        return LaunchResult(
            ok=True,
            exit_code=exit_code,
            used_appcontainer=True,
            fell_back=False,
        )
    except OSError as exc:
        logger.exception("AppContainer launch failed: %s", exc)
        if forced:
            return LaunchResult(
                ok=False,
                error=str(exc),
                used_appcontainer=False,
                fell_back=False,
            )
        logger.warning("Falling back to unsandboxed backend launch")
        try:
            h_process, h_thread, _pid = create_process_unsandboxed(exe, args)
            try:
                close_handle(h_thread)
                exit_code = _wait_process(h_process)
            finally:
                close_handle(h_process)
            return LaunchResult(
                ok=True,
                exit_code=exit_code,
                used_appcontainer=False,
                fell_back=True,
            )
        except OSError as fallback_exc:
            return LaunchResult(
                ok=False,
                error=str(fallback_exc),
                used_appcontainer=False,
                fell_back=True,
            )
    finally:
        if sid is not None:
            for path, _write in reversed(granted):
                revoke_path_access(sid, path)
            try:
                if sys.platform == "win32":
                    ctypes.windll.kernel32.LocalFree(sid)
            except Exception:
                pass


def apply_windows_process_mitigations() -> bool:
    """Apply compatible process mitigations inside the sandboxed child.

    Does not enable NoChildProcessCreation because bots, rnsh, and rnx still
    re-enter via --meshchatx-run-module.
    """
    if sys.platform != "win32":
        return False
    if not is_appcontainer_child():
        return False
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except OSError:
        return False
    if not hasattr(kernel32, "SetProcessMitigationPolicy"):
        return False

    applied = False

    # DisableExtensionPoints = 1
    ext = _PROCESS_MITIGATION_EXTENSION_POINT_DISABLE_POLICY()
    ext.Flags = 0x1
    if kernel32.SetProcessMitigationPolicy(
        _MITIGATION_POLICY_EXTENSION_POINT_DISABLE,
        ctypes.byref(ext),
        ctypes.sizeof(ext),
    ):
        applied = True
    else:
        logger.debug(
            "SetProcessMitigationPolicy extension-point failed: %s",
            ctypes.get_last_error(),
        )

    # PreferSystem32Images = 1 (bit 2), NoRemoteImages = 1 (bit 0) when compatible
    img = _PROCESS_MITIGATION_IMAGE_LOAD_POLICY()
    img.Flags = 0x1 | 0x4
    if kernel32.SetProcessMitigationPolicy(
        _MITIGATION_POLICY_IMAGE_LOAD,
        ctypes.byref(img),
        ctypes.sizeof(img),
    ):
        applied = True
    else:
        logger.debug(
            "SetProcessMitigationPolicy image-load failed: %s",
            ctypes.get_last_error(),
        )

    # RaiseExceptionOnInvalidHandleReference | HandleExceptionsPermanently
    strict = _PROCESS_MITIGATION_STRICT_HANDLE_CHECK_POLICY()
    strict.Flags = 0x1 | 0x2
    if kernel32.SetProcessMitigationPolicy(
        _MITIGATION_POLICY_STRICT_HANDLE_CHECK,
        ctypes.byref(strict),
        ctypes.sizeof(strict),
    ):
        applied = True
    else:
        logger.debug(
            "SetProcessMitigationPolicy strict-handle failed: %s",
            ctypes.get_last_error(),
        )

    if applied:
        logger.info("Windows process mitigations applied under AppContainer")
    return applied


# Hook type for tests that inject fake launchers.
LaunchBackendFn = Callable[..., LaunchResult]
