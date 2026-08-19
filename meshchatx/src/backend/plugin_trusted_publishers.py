# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import dataclass

from meshchatx.src.path_utils import atomic_write_text

TRUSTED_PUBLISHERS_DIGEST_KEY = "plugins.trusted_publishers_digest"

_trusted_lock = threading.RLock()
_user_tampered = False
_user_tamper_reason = ""


@dataclass
class TrustedPublisher:
    identity: str
    name: str


def _bundled_publishers_path() -> str:
    return os.path.join(os.path.dirname(__file__), "data", "trusted_publishers.json")


def user_trusted_publishers_path(plugins_root: str) -> str:
    return os.path.join(plugins_root, "trusted_publishers.json")


def _load_json_publishers(path: str) -> list[TrustedPublisher]:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return []
    publishers = data.get("publishers") if isinstance(data, dict) else None
    if not isinstance(publishers, list):
        return []
    out: list[TrustedPublisher] = []
    for item in publishers:
        if not isinstance(item, dict):
            continue
        identity = str(item.get("identity") or "").strip().lower()
        if not identity:
            continue
        name = str(item.get("name") or identity).strip()
        out.append(TrustedPublisher(identity=identity, name=name))
    return out


def digest_user_trusted_publishers_raw(raw: bytes) -> str:
    data = json.loads(raw.decode("utf-8"))
    canonical = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _ensure_settings_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS plugin_settings (
          setting_key TEXT PRIMARY KEY,
          setting_value TEXT NOT NULL
        )
        """,
    )


def _get_digest(state_db_path: str) -> str:
    with sqlite3.connect(state_db_path) as conn:
        _ensure_settings_table(conn)
        row = conn.execute(
            "SELECT setting_value FROM plugin_settings WHERE setting_key = ?",
            (TRUSTED_PUBLISHERS_DIGEST_KEY,),
        ).fetchone()
    return (row[0] if row else "").strip()


def _set_digest(state_db_path: str, digest: str) -> None:
    with sqlite3.connect(state_db_path) as conn:
        _ensure_settings_table(conn)
        conn.execute(
            """
            INSERT INTO plugin_settings (setting_key, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
            """,
            (TRUSTED_PUBLISHERS_DIGEST_KEY, digest),
        )
        conn.commit()


def init_trusted_publishers_integrity(state_db_path: str, plugins_root: str) -> None:
    verify_user_trusted_publishers_integrity(state_db_path, plugins_root)


def user_trusted_publishers_tampered() -> tuple[bool, str]:
    with _trusted_lock:
        return _user_tampered, _user_tamper_reason


def verify_user_trusted_publishers_integrity(
    state_db_path: str,
    plugins_root: str,
) -> None:
    global _user_tampered, _user_tamper_reason
    path = user_trusted_publishers_path(plugins_root)
    if not os.path.isfile(path):
        with _trusted_lock:
            _user_tampered = False
            _user_tamper_reason = ""
        _set_digest(state_db_path, "")
        return
    with open(path, "rb") as handle:
        raw = handle.read()
    current = digest_user_trusted_publishers_raw(raw)
    stored = _get_digest(state_db_path)
    with _trusted_lock:
        if not stored:
            _user_tampered = False
            _user_tamper_reason = ""
            _set_digest(state_db_path, current)
            return
        if stored != current:
            _user_tampered = True
            _user_tamper_reason = (
                "trusted publisher list was modified outside MeshChatX"
            )
            return
        _user_tampered = False
        _user_tamper_reason = ""


def list_trusted_publishers(
    plugins_root: str,
    state_db_path: str,
) -> list[dict[str, str]]:
    verify_user_trusted_publishers_integrity(state_db_path, plugins_root)
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for pub in _load_json_publishers(_bundled_publishers_path()):
        if pub.identity in seen:
            continue
        seen.add(pub.identity)
        rows.append({"identity": pub.identity, "name": pub.name or pub.identity})
    tampered, _reason = user_trusted_publishers_tampered()
    if not tampered:
        for pub in _load_json_publishers(user_trusted_publishers_path(plugins_root)):
            if pub.identity in seen:
                continue
            seen.add(pub.identity)
            rows.append({"identity": pub.identity, "name": pub.name or pub.identity})
    return rows


def lookup_trusted_publisher_in_storage(
    signer_hex: str,
    plugins_root: str,
    state_db_path: str,
) -> tuple[str, bool]:
    needle = (signer_hex or "").strip().lower()
    if not needle:
        return "", False
    for pub in list_trusted_publishers(plugins_root, state_db_path):
        if pub["identity"] == needle:
            return pub.get("name") or needle, True
    return "", False


def add_user_trusted_publisher(
    plugins_root: str,
    state_db_path: str,
    identity: str,
    name: str,
) -> None:
    global _user_tampered, _user_tamper_reason
    identity = (identity or "").strip().lower()
    if not identity:
        raise ValueError("publisher identity is required")
    name = (name or identity).strip()
    path = user_trusted_publishers_path(plugins_root)
    publishers: list[dict[str, str]] = []
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("trusted publishers file is unreadable") from exc
        if not isinstance(data, dict) or not isinstance(data.get("publishers"), list):
            raise ValueError("trusted publishers file is unreadable")
        publishers = [item for item in data["publishers"] if isinstance(item, dict)]
    for item in publishers:
        if str(item.get("identity") or "").strip().lower() == identity:
            return
    publishers.append({"identity": identity, "name": name})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    raw = json.dumps({"publishers": publishers}, indent=2) + "\n"
    atomic_write_text(path, raw)
    digest = digest_user_trusted_publishers_raw(raw.encode("utf-8"))
    _set_digest(state_db_path, digest)
    with _trusted_lock:
        _user_tampered = False
        _user_tamper_reason = ""


def remove_user_trusted_publisher(
    plugins_root: str,
    state_db_path: str,
    identity: str,
) -> bool:
    global _user_tampered, _user_tamper_reason
    identity = (identity or "").strip().lower()
    path = user_trusted_publishers_path(plugins_root)
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    publishers = data.get("publishers") if isinstance(data, dict) else []
    if not isinstance(publishers, list):
        return False
    kept = [
        item
        for item in publishers
        if isinstance(item, dict)
        and str(item.get("identity") or "").strip().lower() != identity
    ]
    if len(kept) == len(publishers):
        return False
    raw = json.dumps({"publishers": kept}, indent=2) + "\n"
    atomic_write_text(path, raw)
    digest = digest_user_trusted_publishers_raw(raw.encode("utf-8"))
    _set_digest(state_db_path, digest)
    with _trusted_lock:
        _user_tampered = False
        _user_tamper_reason = ""
    return True


class PluginStateSettingsStore:
    def __init__(self, state_db_path: str):
        self.state_db_path = state_db_path

    def get_setting(self, key: str) -> str:
        with sqlite3.connect(self.state_db_path) as conn:
            _ensure_settings_table(conn)
            row = conn.execute(
                "SELECT setting_value FROM plugin_settings WHERE setting_key = ?",
                (key,),
            ).fetchone()
        return row[0] if row else ""

    def set_setting(self, key: str, value: str) -> None:
        with sqlite3.connect(self.state_db_path) as conn:
            _ensure_settings_table(conn)
            conn.execute(
                """
                INSERT INTO plugin_settings (setting_key, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
                """,
                (key, value),
            )
            conn.commit()


@dataclass
class TrustedPublisherRecord:
    identity: str
    name: str

    def to_dict(self) -> dict[str, str]:
        return {"identity": self.identity, "name": self.name}


class TrustedPublishersStore:
    def __init__(self, plugins_root: str, settings_store: PluginStateSettingsStore):
        self.plugins_root = plugins_root
        self.settings_store = settings_store
        init_trusted_publishers_integrity(settings_store.state_db_path, plugins_root)

    def lookup(self, signer_hex: str) -> tuple[str, bool]:
        return lookup_trusted_publisher_in_storage(
            signer_hex,
            self.plugins_root,
            self.settings_store.state_db_path,
        )

    def list_publishers(self) -> list[TrustedPublisherRecord]:
        rows = list_trusted_publishers(
            self.plugins_root,
            self.settings_store.state_db_path,
        )
        return [
            TrustedPublisherRecord(
                identity=row["identity"],
                name=row.get("name") or row["identity"],
            )
            for row in rows
        ]

    def add_publisher(self, identity: str, name: str = "") -> None:
        add_user_trusted_publisher(
            self.plugins_root,
            self.settings_store.state_db_path,
            identity,
            name,
        )

    def remove_publisher(self, identity: str) -> bool:
        return remove_user_trusted_publisher(
            self.plugins_root,
            self.settings_store.state_db_path,
            identity,
        )

    def user_tampered(self) -> tuple[bool, str]:
        verify_user_trusted_publishers_integrity(
            self.settings_store.state_db_path,
            self.plugins_root,
        )
        return user_trusted_publishers_tampered()
