# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import hashlib
import time
from typing import Any

from .provider import DatabaseProvider

LOGIN_PATH = "/api/v1/auth/login"
SETUP_PATH = "/api/v1/auth/setup"

WINDOW_RATE_UNTRUSTED_S = 60
MAX_UNTRUSTED_LOGIN_PER_WINDOW = 20
WINDOW_RATE_TRUSTED_S = 60
MAX_TRUSTED_LOGIN_PER_WINDOW = 120

WINDOW_LOCKOUT_S = 900
MAX_FAILED_BEFORE_LOCKOUT = 5

MAX_TRUSTED_FINGERPRINTS_PER_IDENTITY = 100


def user_agent_hash(user_agent: str) -> str:
    raw = (user_agent or "").encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


class AccessAttemptsDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def insert(
        self,
        identity_hash: str,
        client_ip: str,
        user_agent: str,
        path: str,
        method: str,
        outcome: str,
        detail: str | None = None,
    ) -> None:
        ua_short = (user_agent or "")[:512]
        ua_h = user_agent_hash(user_agent or "")
        ts = time.time()
        self.provider.execute(
            """
            INSERT INTO access_attempts (
                created_at, identity_hash, client_ip, user_agent, user_agent_hash,
                path, method, outcome, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                identity_hash,
                client_ip or "",
                ua_short,
                ua_h,
                path,
                method,
                outcome,
                detail,
            ),
        )

    def is_trusted(self, identity_hash: str, client_ip: str, ua_h: str) -> bool:
        row = self.provider.fetchone(
            """
            SELECT 1 FROM trusted_login_clients
            WHERE identity_hash = ? AND client_ip = ? AND user_agent_hash = ?
            """,
            (identity_hash, client_ip or "", ua_h),
        )
        return row is not None

    def upsert_trusted(self, identity_hash: str, client_ip: str, ua_h: str) -> None:
        now = time.time()
        self.provider.execute(
            """
            INSERT INTO trusted_login_clients (
                identity_hash, client_ip, user_agent_hash, last_success_at, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(identity_hash, client_ip, user_agent_hash) DO UPDATE SET
                last_success_at = excluded.last_success_at
            """,
            (identity_hash, client_ip or "", ua_h, now, now),
        )
        self._prune_trusted(identity_hash)

    def _prune_trusted(self, identity_hash: str) -> None:
        row = self.provider.fetchone(
            """
            SELECT COUNT(*) AS c FROM trusted_login_clients WHERE identity_hash = ?
            """,
            (identity_hash,),
        )
        count = row["c"] if row else 0
        if count <= MAX_TRUSTED_FINGERPRINTS_PER_IDENTITY:
            return
        excess = count - MAX_TRUSTED_FINGERPRINTS_PER_IDENTITY
        self.provider.execute(
            """
            DELETE FROM trusted_login_clients
            WHERE identity_hash = ?
            AND rowid IN (
                SELECT rowid FROM trusted_login_clients
                WHERE identity_hash = ?
                ORDER BY last_success_at ASC
                LIMIT ?
            )
            """,
            (identity_hash, identity_hash, excess),
        )

    def count_login_attempts_ip(
        self,
        client_ip: str,
        path: str,
        since_ts: float,
    ) -> int:
        row = self.provider.fetchone(
            """
            SELECT COUNT(*) AS c FROM access_attempts
            WHERE client_ip = ? AND path = ? AND created_at >= ?
            """,
            (client_ip or "", path, since_ts),
        )
        return int(row["c"]) if row else 0

    def count_login_attempts_ip_ua(
        self,
        client_ip: str,
        ua_h: str,
        path: str,
        since_ts: float,
    ) -> int:
        row = self.provider.fetchone(
            """
            SELECT COUNT(*) AS c FROM access_attempts
            WHERE client_ip = ? AND user_agent_hash = ? AND path = ? AND created_at >= ?
            """,
            (client_ip or "", ua_h, path, since_ts),
        )
        return int(row["c"]) if row else 0

    def count_lockout_failures(
        self,
        identity_hash: str,
        client_ip: str,
        since_ts: float,
    ) -> int:
        row = self.provider.fetchone(
            """
            SELECT COUNT(*) AS c FROM access_attempts aa
            WHERE aa.identity_hash = ?
            AND aa.client_ip = ?
            AND aa.outcome = 'failed_password'
            AND aa.created_at >= ?
            AND NOT EXISTS (
                SELECT 1 FROM trusted_login_clients t
                WHERE t.identity_hash = aa.identity_hash
                AND t.client_ip = aa.client_ip
                AND t.user_agent_hash = aa.user_agent_hash
            )
            """,
            (identity_hash, client_ip or "", since_ts),
        )
        return int(row["c"]) if row else 0

    def list_attempts(
        self,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        outcome: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id, created_at, identity_hash, client_ip, user_agent, path, method, outcome, detail
            FROM access_attempts WHERE 1=1
        """
        params: list[Any] = []
        if search:
            sql += """ AND (
                client_ip LIKE ? OR user_agent LIKE ? OR path LIKE ? OR outcome LIKE ?
                OR IFNULL(detail,'') LIKE ?
            )"""
            q = f"%{search}%"
            params.extend([q, q, q, q, q])
        if outcome:
            sql += " AND outcome = ?"
            params.append(outcome)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.provider.fetchall(sql, tuple(params))
        return [dict(r) for r in rows]

    def count_attempts(
        self,
        search: str | None = None,
        outcome: str | None = None,
    ) -> int:
        sql = "SELECT COUNT(*) AS c FROM access_attempts WHERE 1=1"
        params: list[Any] = []
        if search:
            sql += """ AND (
                client_ip LIKE ? OR user_agent LIKE ? OR path LIKE ? OR outcome LIKE ?
                OR IFNULL(detail,'') LIKE ?
            )"""
            q = f"%{search}%"
            params.extend([q, q, q, q, q])
        if outcome:
            sql += " AND outcome = ?"
            params.append(outcome)
        row = self.provider.fetchone(sql, tuple(params))
        return int(row["c"]) if row else 0

    def cleanup_old(self, max_rows: int = 50_000) -> None:
        row = self.provider.fetchone("SELECT COUNT(*) AS c FROM access_attempts")
        count = int(row["c"]) if row else 0
        if count <= max_rows:
            return
        excess = count - max_rows
        self.provider.execute(
            """
            DELETE FROM access_attempts WHERE rowid IN (
                SELECT rowid FROM access_attempts ORDER BY created_at ASC LIMIT ?
            )
            """,
            (excess,),
        )
