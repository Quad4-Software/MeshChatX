# SPDX-License-Identifier: 0BSD

"""Runtime policy for limited bandwidth mode.

The stored user intervals are authoritative. Helpers in this module only
compute effective runtime values so disabling the mode restores the previous
behaviour without a migration or rewrite pass.
"""

from __future__ import annotations

import os
import sqlite3
import urllib.parse

from meshchatx.src.backend.constants import MIN_ANNOUNCE_INTERVAL_SECONDS
from meshchatx.src.backend.meshchat_utils import clamp_interval_floor

LIMITED_BANDWIDTH_ANNOUNCE_MIN_INTERVAL_SECONDS = 6 * 60 * 60
LIMITED_BANDWIDTH_TELEMETRY_MIN_INTERVAL_SECONDS = 15 * 60


def limited_bandwidth_enabled(config) -> bool:
    """Return True only for a real boolean true config value.

    Tests often use MagicMock config objects where unknown attributes are
    truthy. Treating exactly True as opt-in prevents those unrelated tests
    from accidentally entering the limited mode.
    """
    field = getattr(config, "limited_bandwidth_enabled", None) if config else None
    if field is None or not hasattr(field, "get"):
        return False
    try:
        return field.get() is True
    except Exception:
        return False


def periodic_mesh_interval_floor(config) -> int:
    """Runtime floor for periodic mesh control traffic."""
    if limited_bandwidth_enabled(config):
        return max(
            MIN_ANNOUNCE_INTERVAL_SECONDS,
            LIMITED_BANDWIDTH_ANNOUNCE_MIN_INTERVAL_SECONDS,
        )
    return MIN_ANNOUNCE_INTERVAL_SECONDS


def clamp_periodic_mesh_interval(config, interval_seconds):
    """Clamp an interval for this runtime without persisting the result."""
    return clamp_interval_floor(
        interval_seconds,
        floor_seconds=periodic_mesh_interval_floor(config),
    )


def telemetry_request_minimum_interval(config) -> int:
    """Runtime minimum interval for periodic peer telemetry requests."""
    if limited_bandwidth_enabled(config):
        return LIMITED_BANDWIDTH_TELEMETRY_MIN_INTERVAL_SECONDS
    return 1


def crawler_runtime_enabled(config) -> bool:
    """Whether the crawler may perform network work right now."""
    if limited_bandwidth_enabled(config):
        return False
    field = getattr(config, "crawler_enabled", None) if config else None
    if field is None or not hasattr(field, "get"):
        return False
    try:
        return bool(field.get())
    except Exception:
        return False


def read_stored_limited_bandwidth_enabled(database_path: str | None) -> bool:
    """Read the flag directly from an identity database before full setup.

    Reticulum discovery starts inside ``RNS.Reticulum`` construction, before
    IdentityContext opens the database through the normal DAO layer. This
    read-only lookup lets startup apply the same autoconnect policy without
    copying the value into the Reticulum config file.
    """
    if not database_path or not os.path.exists(database_path):
        return False
    connection = None
    try:
        absolute = os.path.abspath(database_path)
        uri = "file:" + urllib.parse.quote(absolute) + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        row = connection.execute(
            "SELECT value FROM config WHERE key = ?",
            ("limited_bandwidth_enabled",),
        ).fetchone()
        return bool(row and str(row[0]).strip().lower() == "true")
    except (OSError, sqlite3.Error):
        return False
    finally:
        if connection is not None:
            connection.close()
