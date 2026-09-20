# SPDX-License-Identifier: 0BSD
"""Versioned snapshots of the Reticulum config file.

Each snapshot is stored as a JSON document inside
``<reticulum_config_dir>/config_versions/<id>.json`` with the shape::

    {"id": str, "created_at": str, "label": str, "content": str}

Snapshots are taken before a raw config write or a reset so the previous
state can always be restored from the config editor.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from datetime import UTC, datetime

VERSIONS_DIR_NAME = "config_versions"
MAX_VERSIONS = 25

_VERSION_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}-[0-9a-f]{8}$")


def versions_dir(config_dir: str) -> str:
    return os.path.join(config_dir, VERSIONS_DIR_NAME)


def _version_path(config_dir: str, version_id: str) -> str | None:
    if not _VERSION_ID_RE.fullmatch(version_id or ""):
        return None
    path = os.path.join(versions_dir(config_dir), f"{version_id}.json")
    # Belt and braces: never allow the resolved path to escape the dir.
    if os.path.dirname(os.path.abspath(path)) != os.path.abspath(
        versions_dir(config_dir)
    ):
        return None
    return path


def _new_version_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{secrets.token_hex(4)}"


def _read_version(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("content"), str):
        return None
    return data


def snapshot_config(config_dir: str, config_path: str, label: str = "") -> dict | None:
    """Copy the current config file into the version store.

    Returns the snapshot metadata, or None when there is nothing to snapshot.
    """
    if not os.path.isfile(config_path):
        return None
    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return None

    os.makedirs(versions_dir(config_dir), exist_ok=True)
    version_id = _new_version_id()
    record = {
        "id": version_id,
        "created_at": datetime.now(UTC).isoformat(),
        "label": str(label or ""),
        "content": content,
    }
    tmp_path = os.path.join(versions_dir(config_dir), f"{version_id}.json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(record, f)
    target_path = _version_path(config_dir, version_id)
    if target_path is None:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return None
    os.replace(tmp_path, target_path)

    prune_versions(config_dir)
    return {k: v for k, v in record.items() if k != "content"}


def list_versions(config_dir: str) -> list[dict]:
    """Return snapshot metadata sorted newest first."""
    directory = versions_dir(config_dir)
    if not os.path.isdir(directory):
        return []
    records = []
    try:
        names = os.listdir(directory)
    except OSError:
        return []
    for name in names:
        if not name.endswith(".json"):
            continue
        data = _read_version(os.path.join(directory, name))
        if data is None:
            continue
        records.append(
            {
                "id": data.get("id") or name[:-5],
                "created_at": data.get("created_at") or "",
                "label": data.get("label") or "",
                "size": len(data["content"].encode("utf-8", "replace")),
            }
        )
    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records


def get_version(config_dir: str, version_id: str) -> dict | None:
    path = _version_path(config_dir, version_id)
    if path is None or not os.path.isfile(path):
        return None
    return _read_version(path)


def prune_versions(config_dir: str, keep: int = MAX_VERSIONS) -> None:
    records = list_versions(config_dir)
    for record in records[keep:]:
        path = _version_path(config_dir, record["id"])
        if path is not None:
            try:
                os.remove(path)
            except OSError:
                pass
