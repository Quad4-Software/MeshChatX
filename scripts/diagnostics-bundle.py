#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Export a sanitized diagnostics bundle for support requests.

Collects build/env metadata, recent crash history rows, mirrored crash
reports, and the tail of the app log into a single .tar.gz. Everything
textual passes through log_redaction.redact_diagnostic_text.

Usage:
    uv run python scripts/diagnostics-bundle.py \
        --storage-dir ~/.config/meshchatx \
        --out-dir .
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sqlite3
import sys
import tarfile
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from meshchatx.src.backend.log_redaction import redact_diagnostic_text

MAX_LOG_BYTES = 512 * 1024
MAX_REPORTS = 20


def _app_version() -> str:
    for line in (REPO_ROOT / "pyproject.toml").read_text().splitlines():
        if line.startswith("version"):
            return line.split("=", 1)[1].strip().strip('"')
    return "unknown"


def _collect_meta(out: Path, storage_dir: Path) -> None:
    from meshchatx.src import build_meta

    backend_version = _app_version()
    meta = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "backend_version": backend_version,
        "storage_dir": str(storage_dir),
        "build": build_meta.as_dict(backend_version),
    }
    (out / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8"
    )


def _collect_env(out: Path) -> None:
    env = {
        k: redact_diagnostic_text(v)
        for k, v in sorted(os.environ.items())
        if k.startswith(("MESHCHAT", "RNS_", "UV_"))
    }
    (out / "env.json").write_text(
        json.dumps(env, indent=2, sort_keys=True), encoding="utf-8"
    )


def _find_db(storage_dir: Path) -> Path | None:
    for name in ("meshchatx.db", "database.db", "meshchat.db"):
        for cand in storage_dir.rglob(name):
            return cand
    return None


def _collect_crash_history(out: Path, storage_dir: Path) -> None:
    db_path = _find_db(storage_dir)
    if db_path is None:
        return
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM crash_history ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
        con.close()
    except sqlite3.Error as e:
        (out / "crash-history-error.txt").write_text(str(e), encoding="utf-8")
        return
    data = [
        {k: redact_diagnostic_text(str(row[k])) for k in row.keys()} for row in rows
    ]
    (out / "crash-history.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def _collect_crash_reports(out: Path, storage_dir: Path) -> None:
    report_dir = storage_dir / "crash_reports"
    if not report_dir.is_dir():
        return
    target = out / "crash-reports"
    target.mkdir()
    files = sorted(
        (p for p in report_dir.iterdir() if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:MAX_REPORTS]
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        (target / f.name).write_text(redact_diagnostic_text(text), encoding="utf-8")


def _collect_logs(out: Path, log_dir: Path | None) -> None:
    if log_dir is None or not log_dir.is_dir():
        return
    target = out / "logs"
    target.mkdir()
    for f in sorted(log_dir.iterdir()):
        if not f.is_file() or f.stat().st_size == 0:
            continue
        try:
            data = f.read_bytes()[-MAX_LOG_BYTES:]
        except OSError:
            continue
        text = data.decode("utf-8", errors="replace")
        (target / f.name).write_text(redact_diagnostic_text(text), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--storage-dir", required=True, type=Path)
    ap.add_argument("--log-dir", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=Path("."))
    args = ap.parse_args()

    storage_dir = args.storage_dir.expanduser()
    if not storage_dir.is_dir():
        print(f"storage dir not found: {storage_dir}", file=sys.stderr)
        return 1

    log_dir = args.log_dir or Path(
        os.environ.get("MESHCHAT_LOG_DIR", storage_dir / "logs")
    )

    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    bundle = args.out_dir / f"meshchatx-diagnostics-{stamp}.tar.gz"
    bundle.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "bundle"
        work.mkdir()
        _collect_meta(work, storage_dir)
        _collect_env(work)
        _collect_crash_history(work, storage_dir)
        _collect_crash_reports(work, storage_dir)
        _collect_logs(work, log_dir)
        with tarfile.open(bundle, "w:gz") as tar:
            tar.add(work, arcname="diagnostics")

    print(bundle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
