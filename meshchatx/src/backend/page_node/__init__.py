# SPDX-License-Identifier: 0BSD
"""Page node public API."""

from __future__ import annotations

# ruff: noqa: F401, F403, F405

from meshchatx.src.backend.page_node.core import *  # noqa: F403

from meshchatx.src.backend.page_node import core as _core

_safe_mesh_file_basename = _core._safe_mesh_file_basename
_path_is_under_root = _core._path_is_under_root
_is_windows_platform = _core._is_windows_platform
_page_generation_error_bytes = _core._page_generation_error_bytes
_normalize_executable_page_names = _core._normalize_executable_page_names
_parse_page_shebang = _core._parse_page_shebang
_shebang_lookup_names = _core._shebang_lookup_names
_resolve_shebang_interpreter = _core._resolve_shebang_interpreter
_windows_page_command = _core._windows_page_command
_build_executable_page_env = _core._build_executable_page_env
_reject_name_component_too_long = _core._reject_name_component_too_long
