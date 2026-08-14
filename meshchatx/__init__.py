# SPDX-License-Identifier: 0BSD

"""Reticulum MeshChatX - A mesh network communications app."""

# Synced from package.json via scripts/sync_version.js (also writes meshchatx/src/version.py).
__version__ = "4.8.4"
# LXST vendored pyogg can NameError on import when libopus is present but
# libogg is not. Apply before any meshchatx module imports LXST.
try:
    from meshchatx.src.backend.lxst_pyogg_ctypes_compat import (
        ensure_lxst_pyogg_ctypes_compat,
    )

    ensure_lxst_pyogg_ctypes_compat()
except (ImportError, OSError, ValueError):
    pass
