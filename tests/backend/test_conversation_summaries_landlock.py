# SPDX-License-Identifier: 0BSD

"""Landlock coverage for conversation summary list queries."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from meshchatx.src.backend.landlock_sandbox import landlock_kernel_supported


@pytest.mark.skipif(
    not landlock_kernel_supported(),
    reason="Landlock not available on this kernel",
)
def test_landlock_conversation_summaries_list_query_ok():
    """List-shaped summary queries must work under Landlock MEMORY temp."""
    script = textwrap.dedent(
        r"""
        import os
        import secrets
        import sys
        import tempfile
        import time

        from meshchatx.src.backend.database import Database
        from meshchatx.src.backend.database.provider import DatabaseProvider
        from meshchatx.src.backend.landlock_sandbox import apply_landlock_sandbox
        from meshchatx.src.backend.message_handler import MessageHandler

        td = tempfile.mkdtemp(prefix="ll_conv_sum_")
        storage = os.path.join(td, "storage")
        os.makedirs(storage)
        os.environ["MESHCHAT_LANDLOCK"] = "1"
        db_path = os.path.join(storage, "database.db")

        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
            DatabaseProvider._instance = None
        db = Database(db_path)
        db.initialize()
        handler = MessageHandler(db)

        for i in range(80):
            peer = secrets.token_hex(16)
            db.messages.upsert_lxmf_message(
                {
                    "hash": secrets.token_hex(16),
                    "source_hash": peer,
                    "destination_hash": "localhashlocalhashlocalhashlo12",
                    "peer_hash": peer,
                    "state": "delivered",
                    "progress": 1.0,
                    "is_incoming": 1,
                    "method": "direct",
                    "delivery_attempts": 1,
                    "next_delivery_attempt_at": None,
                    "title": f"t{i}",
                    "content": "hello " + ("x" * 400),
                    "fields": "{}",
                    "timestamp": time.time() - i,
                    "rssi": -50,
                    "snr": 5.0,
                    "quality": 3,
                    "is_spam": 0,
                    "reply_to_hash": None,
                }
            )

        ok = apply_landlock_sandbox(
            storage_dir=storage,
            reticulum_config_dir=storage,
            log_dir=storage,
        )
        if not ok:
            print("LANDLOCK_NOT_APPLIED")
            sys.exit(2)

        rows = handler.get_conversations("local", limit=50, offset=0)
        if len(rows) != 50:
            print("BAD_COUNT", len(rows))
            sys.exit(3)
        for row in rows:
            row = dict(row)
            if "fields" in row:
                print("FIELDS_PRESENT")
                sys.exit(4)
            if len(row.get("content") or "") > 240:
                print("PREVIEW_TOO_LONG")
                sys.exit(5)
        print("OK")
        sys.exit(0)
        """,
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(Path(__file__).resolve().parents[2]),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if "LANDLOCK_NOT_APPLIED" in result.stdout:
        pytest.skip("Landlock could not be applied in this environment")
    assert result.returncode == 0, (
        f"stdout={result.stdout!r} stderr={result.stderr!r} code={result.returncode}"
    )
    assert "OK" in result.stdout
