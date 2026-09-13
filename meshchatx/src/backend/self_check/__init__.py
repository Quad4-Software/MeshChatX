# SPDX-License-Identifier: 0BSD
"""Self check public API."""

from __future__ import annotations

# ruff: noqa: F401, F403, F405

from meshchatx.src.backend.self_check.core import *
from meshchatx.src.backend.self_check import core as _core

_status = _core._status
_check_storage_lock_soft_fallback = _core._check_storage_lock_soft_fallback
_is_frozen_executable = _core._is_frozen_executable
_frontend_source_available = _core._frontend_source_available
_probe_rns_link_api = _core._probe_rns_link_api
_WEB_PROBE_KEYS = _core._WEB_PROBE_KEYS
_CRITICAL_IMPORTS = _core._CRITICAL_IMPORTS
_SELF_CHECK_PROBE_MODULE = _core._SELF_CHECK_PROBE_MODULE
_MESHCHATX_RUN_MODULE_FLAG = _core._MESHCHATX_RUN_MODULE_FLAG
