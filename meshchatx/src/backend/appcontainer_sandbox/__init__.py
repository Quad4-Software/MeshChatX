# SPDX-License-Identifier: 0BSD
"""appcontainer_sandbox public API."""

from __future__ import annotations

# ruff: noqa: F401, F403, F405

from meshchatx.src.backend.appcontainer_sandbox.core import *  # noqa: F403

from meshchatx.src.backend.appcontainer_sandbox import core as _core

_env_override = _core._env_override
_windows_version_supported = _core._windows_version_supported
_probe_appcontainer_apis = _core._probe_appcontainer_apis
_existing_dir = _core._existing_dir
_ensure_dir = _core._ensure_dir
_windows_known_folder = _core._windows_known_folder
_user_profile_dir = _core._user_profile_dir
_as_void_p = _core._as_void_p
_local_free = _core._local_free
_create_capability_sid = _core._create_capability_sid
_set_path_access = _core._set_path_access
_build_command_line = _core._build_command_line
_wait_process = _core._wait_process
_SID_AND_ATTRIBUTES = _core._SID_AND_ATTRIBUTES
_SECURITY_CAPABILITIES = _core._SECURITY_CAPABILITIES
_STARTUPINFO = _core._STARTUPINFO
_STARTUPINFOEX = _core._STARTUPINFOEX
_PROCESS_INFORMATION = _core._PROCESS_INFORMATION
_TRUSTEE_W = _core._TRUSTEE_W
_EXPLICIT_ACCESS_W = _core._EXPLICIT_ACCESS_W
_PROCESS_MITIGATION_EXTENSION_POINT_DISABLE_POLICY = (
    _core._PROCESS_MITIGATION_EXTENSION_POINT_DISABLE_POLICY
)
_PROCESS_MITIGATION_IMAGE_LOAD_POLICY = _core._PROCESS_MITIGATION_IMAGE_LOAD_POLICY
_PROCESS_MITIGATION_STRICT_HANDLE_CHECK_POLICY = (
    _core._PROCESS_MITIGATION_STRICT_HANDLE_CHECK_POLICY
)
_ERROR_ALREADY_EXISTS = _core._ERROR_ALREADY_EXISTS
_ERROR_SUCCESS = _core._ERROR_SUCCESS
_INVALID_HANDLE_VALUE = _core._INVALID_HANDLE_VALUE
_GENERIC_READ = _core._GENERIC_READ
_GENERIC_WRITE = _core._GENERIC_WRITE
_GENERIC_EXECUTE = _core._GENERIC_EXECUTE
_GENERIC_ALL = _core._GENERIC_ALL
_FILE_GENERIC_READ = _core._FILE_GENERIC_READ
_FILE_GENERIC_WRITE = _core._FILE_GENERIC_WRITE
_FILE_GENERIC_EXECUTE = _core._FILE_GENERIC_EXECUTE
_GRANT_ACCESS = _core._GRANT_ACCESS
_REVOKE_ACCESS = _core._REVOKE_ACCESS
_TRUSTEE_IS_SID = _core._TRUSTEE_IS_SID
_TRUSTEE_IS_UNKNOWN = _core._TRUSTEE_IS_UNKNOWN
_SUB_CONTAINERS_AND_OBJECTS_INHERIT = _core._SUB_CONTAINERS_AND_OBJECTS_INHERIT
_SE_FILE_OBJECT = _core._SE_FILE_OBJECT
_DACL_SECURITY_INFORMATION = _core._DACL_SECURITY_INFORMATION
_PROTECTED_DACL_SECURITY_INFORMATION = _core._PROTECTED_DACL_SECURITY_INFORMATION
_SE_GROUP_ENABLED = _core._SE_GROUP_ENABLED
_CREATE_UNICODE_ENVIRONMENT = _core._CREATE_UNICODE_ENVIRONMENT
_EXTENDED_STARTUPINFO_PRESENT = _core._EXTENDED_STARTUPINFO_PRESENT
_CREATE_NO_WINDOW = _core._CREATE_NO_WINDOW
_PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = (
    _core._PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES
)
_PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY = (
    _core._PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY
)
_PROCESS_CREATION_ALL_APPLICATION_PACKAGES_OPT_OUT = (
    _core._PROCESS_CREATION_ALL_APPLICATION_PACKAGES_OPT_OUT
)
_WinCapabilityInternetClientSid = _core._WinCapabilityInternetClientSid
_WinCapabilityInternetClientServerSid = _core._WinCapabilityInternetClientServerSid
_WinCapabilityPrivateNetworkClientServerSid = (
    _core._WinCapabilityPrivateNetworkClientServerSid
)
_INFINITE = _core._INFINITE
_WAIT_OBJECT_0 = _core._WAIT_OBJECT_0
_MITIGATION_POLICY_EXTENSION_POINT_DISABLE = (
    _core._MITIGATION_POLICY_EXTENSION_POINT_DISABLE
)
_MITIGATION_POLICY_IMAGE_LOAD = _core._MITIGATION_POLICY_IMAGE_LOAD
_MITIGATION_POLICY_STRICT_HANDLE_CHECK = _core._MITIGATION_POLICY_STRICT_HANDLE_CHECK
