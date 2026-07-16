# SPDX-License-Identifier: 0BSD

"""Regression: worker-thread SQLite connections must use MEMORY temp under Landlock."""

import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.landlock_sandbox import landlock_kernel_supported


@pytest.fixture(autouse=True)
def reset_provider():
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
    DatabaseProvider._instance = None
    yield
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
    DatabaseProvider._instance = None


def test_provider_configures_temp_store_memory_on_new_connections(tmp_path):
    db_path = str(tmp_path / "database.db")
    provider = DatabaseProvider.get_instance(db_path)
    conn = provider.connection
    mode = conn.execute("PRAGMA temp_store").fetchone()[0]
    # SQLite returns 0=DEFAULT, 1=FILE, 2=MEMORY
    assert int(mode) == 2


def test_provider_memory_pressure_prefers_file_temp(tmp_path):
    db_path = str(tmp_path / "database.db")
    provider = DatabaseProvider.get_instance(db_path)
    provider.prefer_temp_store_file = True
    provider.close()
    conn = provider.connection
    mode = conn.execute("PRAGMA temp_store").fetchone()[0]
    assert int(mode) == 1


def test_worker_threads_inherit_memory_temp_store(tmp_path):
    db_path = str(tmp_path / "database.db")
    provider = DatabaseProvider.get_instance(db_path)
    modes: list[int] = []
    errors: list[str] = []

    def worker(_i: int) -> None:
        try:
            conn = provider.connection
            modes.append(int(conn.execute("PRAGMA temp_store").fetchone()[0]))
        except Exception as exc:
            errors.append(str(exc))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(worker, range(16)))

    assert not errors
    assert modes
    assert all(mode == 2 for mode in modes)


@pytest.mark.skipif(
    not landlock_kernel_supported(),
    reason="Landlock not available on this kernel",
)
def test_landlock_worker_heavy_query_ok_with_memory_temp():
    """Worker-thread heavy conversation queries must work under Landlock.

    Runs in a subprocess because Landlock can only restrict a process once.
    """
    script = textwrap.dedent(
        r"""
        import os, sqlite3, sys, tempfile, time
        from concurrent.futures import ThreadPoolExecutor
        from meshchatx.src.backend.database.provider import DatabaseProvider
        from meshchatx.src.backend.landlock_sandbox import apply_landlock_sandbox

        td = tempfile.mkdtemp(prefix="ll_sqlite_reg_")
        storage = os.path.join(td, "storage")
        os.makedirs(storage)
        os.environ["MESHCHAT_LANDLOCK"] = "1"

        db = os.path.join(storage, "database.db")
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE lxmf_messages ("
            "id INTEGER PRIMARY KEY, peer_hash TEXT, content TEXT, fields TEXT, "
            "title TEXT, timestamp REAL, is_incoming INT, state TEXT)"
        )
        big_content = "x" * 200000
        big_fields = '{"image":{"image_bytes":"' + ("A" * 40000) + '"}}'
        for i in range(80):
            conn.execute(
                "INSERT INTO lxmf_messages VALUES (?,?,?,?,?,?,?,?)",
                (i, f"peer{i%16}", big_content, big_fields, "t", time.time(), 1, "delivered"),
            )
        conn.commit()
        conn.close()

        ok = apply_landlock_sandbox(
            storage_dir=storage,
            reticulum_config_dir=storage,
            log_dir=storage,
        )
        if not ok:
            print("LANDLOCK_NOT_APPLIED")
            sys.exit(2)

        heavy = '''
        SELECT m1.id, substr(COALESCE(m1.content,''),1,240) AS content,
               CASE WHEN instr(m1.fields,'"image"')>0 THEN 1 ELSE 0 END AS has_image
        FROM lxmf_messages m1
        INNER JOIN (
            SELECT peer_hash, MAX(id) AS max_id FROM lxmf_messages
            WHERE peer_hash IS NOT NULL GROUP BY peer_hash
        ) m2 ON m1.peer_hash=m2.peer_hash AND m1.id=m2.max_id
        GROUP BY m1.peer_hash ORDER BY m1.id DESC LIMIT 50
        '''

        DatabaseProvider._instance = None
        provider = DatabaseProvider.get_instance(db)
        mem_errors = []
        def mem_worker(_i):
            try:
                rows = provider.fetchall(heavy)
                if not rows:
                    mem_errors.append("empty")
            except Exception as e:
                mem_errors.append(str(e))

        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(mem_worker, range(24)))

        print("MEM_ERRORS", len(mem_errors))
        if mem_errors:
            print(mem_errors[:3])
            sys.exit(4)
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
    assert "MEM_ERRORS 0" in result.stdout


@pytest.mark.skipif(
    not landlock_kernel_supported(),
    reason="Landlock not available on this kernel",
)
def test_landlock_memory_pressure_keeps_memory_temp_and_queries_ok():
    """Memory-pressure must not switch to FILE temp under Landlock."""
    script = textwrap.dedent(
        r"""
        import os, sqlite3, sys, tempfile, time
        from concurrent.futures import ThreadPoolExecutor
        from meshchatx.src.backend.database import Database
        from meshchatx.src.backend.database.provider import DatabaseProvider
        from meshchatx.src.backend.landlock_sandbox import apply_landlock_sandbox

        td = tempfile.mkdtemp(prefix="ll_pressure_")
        storage = os.path.join(td, "storage")
        os.makedirs(storage)
        os.environ["MESHCHAT_LANDLOCK"] = "1"
        db_path = os.path.join(storage, "database.db")

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE lxmf_messages ("
            "id INTEGER PRIMARY KEY, peer_hash TEXT, content TEXT, fields TEXT, "
            "title TEXT, timestamp REAL, is_incoming INT, state TEXT)"
        )
        big_content = "x" * 120000
        big_fields = '{"image":{"image_bytes":"' + ("A" * 60000) + '"}}'
        for i in range(200):
            conn.execute(
                "INSERT INTO lxmf_messages VALUES (?,?,?,?,?,?,?,?)",
                (i, f"peer{i%40}", big_content, big_fields, "t", time.time(), 1, "delivered"),
            )
        conn.commit()
        conn.close()

        ok = apply_landlock_sandbox(
            storage_dir=storage,
            reticulum_config_dir=storage,
            log_dir=storage,
        )
        if not ok:
            print("LANDLOCK_NOT_APPLIED")
            sys.exit(2)

        DatabaseProvider._instance = None
        db = Database(db_path)
        # Skip full schema init; only need pressure pragma path + provider.
        assert db.apply_memory_pressure_pragmas(True, landlock_active=True)
        mode = int(db.provider.connection.execute("PRAGMA temp_store").fetchone()[0])
        print("TEMP_MODE", mode)
        if mode != 2:
            sys.exit(3)
        if db.provider.prefer_temp_store_file:
            sys.exit(4)

        heavy = '''
        SELECT m1.id, substr(COALESCE(m1.content,''),1,240) AS content,
               CASE WHEN instr(m1.fields,'"image"')>0 THEN 1 ELSE 0 END AS has_image
        FROM lxmf_messages m1
        INNER JOIN (
            SELECT peer_hash, MAX(id) AS max_id FROM lxmf_messages
            WHERE peer_hash IS NOT NULL GROUP BY peer_hash
        ) m2 ON m1.peer_hash=m2.peer_hash AND m1.id=m2.max_id
        GROUP BY m1.peer_hash ORDER BY m1.id DESC LIMIT 50
        '''
        errors = []
        def worker(_i):
            try:
                rows = db.provider.fetchall(heavy)
                if not rows:
                    errors.append("empty")
            except Exception as e:
                errors.append(str(e))
        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(worker, range(24)))
        print("PRESSURE_ERRORS", len(errors))
        if errors:
            print(errors[:3])
            sys.exit(5)
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
    assert "TEMP_MODE 2" in result.stdout
    assert "PRESSURE_ERRORS 0" in result.stdout
