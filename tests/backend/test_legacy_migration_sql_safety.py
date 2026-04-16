# SPDX-License-Identifier: 0BSD

"""Legacy migration and schema: safe ATTACH paths, identifiers, and raw SQL helpers.

Covers ATTACH DATABASE path escaping in LegacyMigrator, column identifier filtering,
and DatabaseSchema _validate_identifier / _ensure_column behaviour.
"""

import os
import re
import sqlite3

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.database.legacy_migrator import LegacyMigrator
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema, _validate_identifier

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_env(tmp_path):
    """Provide an initialized DatabaseProvider + Schema in a temp directory."""
    db_path = str(tmp_path / "current.db")
    provider = DatabaseProvider(db_path)
    schema = DatabaseSchema(provider)
    schema.initialize()
    yield provider, schema, tmp_path
    provider.close()


def _make_legacy_db(legacy_dir, identity_hash, tables_sql):
    """Create a legacy database with the given CREATE TABLE + INSERT statements."""
    identity_dir = os.path.join(legacy_dir, "identities", identity_hash)
    os.makedirs(identity_dir, exist_ok=True)
    db_path = os.path.join(identity_dir, "database.db")
    conn = sqlite3.connect(db_path)
    for sql in tables_sql:
        conn.execute(sql)
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# 1. ATTACH DATABASE — single-quote escaping
# ---------------------------------------------------------------------------


class TestAttachDatabasePathEscaping:
    def test_path_without_quotes_migrates_normally(self, db_env):
        provider, _schema, tmp_path = db_env
        legacy_dir = str(tmp_path / "legacy_normal")
        identity_hash = "aabbccdd"
        _make_legacy_db(
            legacy_dir,
            identity_hash,
            [
                "CREATE TABLE config (key TEXT UNIQUE, value TEXT)",
                "INSERT INTO config (key, value) VALUES ('k1', 'v1')",
            ],
        )

        migrator = LegacyMigrator(provider, legacy_dir, identity_hash)
        assert migrator.migrate() is True

        row = provider.fetchone("SELECT value FROM config WHERE key = 'k1'")
        assert row is not None
        assert row["value"] == "v1"

    def test_path_with_single_quote_does_not_crash(self, db_env):
        """A path containing a single quote must not cause SQL injection or crash."""
        provider, _schema, tmp_path = db_env

        quoted_dir = tmp_path / "it's_a_test"
        quoted_dir.mkdir(parents=True, exist_ok=True)
        legacy_dir = str(quoted_dir)
        identity_hash = "aabbccdd"
        _make_legacy_db(
            legacy_dir,
            identity_hash,
            [
                "CREATE TABLE config (key TEXT UNIQUE, value TEXT)",
                "INSERT INTO config (key, value) VALUES ('q1', 'quoted_val')",
            ],
        )

        migrator = LegacyMigrator(provider, legacy_dir, identity_hash)
        result = migrator.migrate()
        assert result is True

        row = provider.fetchone("SELECT value FROM config WHERE key = 'q1'")
        assert row is not None
        assert row["value"] == "quoted_val"

    def test_path_with_multiple_quotes(self, db_env):
        """Multiple single quotes in the path are all escaped."""
        provider, _schema, tmp_path = db_env

        weird_dir = tmp_path / "a'b'c"
        weird_dir.mkdir(parents=True, exist_ok=True)
        legacy_dir = str(weird_dir)
        identity_hash = "11223344"
        _make_legacy_db(
            legacy_dir,
            identity_hash,
            [
                "CREATE TABLE config (key TEXT UNIQUE, value TEXT)",
                "INSERT INTO config (key, value) VALUES ('mq', 'multi_quote')",
            ],
        )

        migrator = LegacyMigrator(provider, legacy_dir, identity_hash)
        assert migrator.migrate() is True

        row = provider.fetchone("SELECT value FROM config WHERE key = 'mq'")
        assert row is not None
        assert row["value"] == "multi_quote"

    def test_path_with_sql_injection_attempt(self, db_env):
        """A path crafted to look like SQL injection is safely escaped."""
        provider, _schema, tmp_path = db_env

        evil_dir = tmp_path / "'; DROP TABLE config; --"
        evil_dir.mkdir(parents=True, exist_ok=True)
        legacy_dir = str(evil_dir)
        identity_hash = "deadbeef"
        _make_legacy_db(
            legacy_dir,
            identity_hash,
            [
                "CREATE TABLE config (key TEXT UNIQUE, value TEXT)",
                "INSERT INTO config (key, value) VALUES ('evil', 'nope')",
            ],
        )

        migrator = LegacyMigrator(provider, legacy_dir, identity_hash)
        migrator.migrate()

        tables = provider.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='config'",
        )
        assert len(tables) > 0, "config table must still exist after injection attempt"


# ---------------------------------------------------------------------------
# 2. Legacy migrator — malicious column names filtered out
# ---------------------------------------------------------------------------


class TestLegacyColumnFiltering:
    def test_normal_columns_migrate(self, db_env):
        """Standard column names pass through the identifier filter."""
        provider, _schema, tmp_path = db_env
        legacy_dir = str(tmp_path / "legacy_cols")
        identity_hash = "aabb0011"
        _make_legacy_db(
            legacy_dir,
            identity_hash,
            [
                "CREATE TABLE config (key TEXT UNIQUE, value TEXT)",
                "INSERT INTO config (key, value) VALUES ('c1', 'ok')",
            ],
        )

        migrator = LegacyMigrator(provider, legacy_dir, identity_hash)
        assert migrator.migrate() is True

        row = provider.fetchone("SELECT value FROM config WHERE key = 'c1'")
        assert row is not None

    def test_malicious_column_name_is_skipped(self, db_env):
        """A column with SQL metacharacters in its name must be silently skipped."""
        provider, _schema, tmp_path = db_env
        legacy_dir = str(tmp_path / "legacy_evil_col")
        identity_hash = "cc00dd00"

        identity_dir = os.path.join(legacy_dir, "identities", identity_hash)
        os.makedirs(identity_dir, exist_ok=True)
        db_path = os.path.join(identity_dir, "database.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            'CREATE TABLE config (key TEXT UNIQUE, value TEXT, "key; DROP TABLE config" TEXT)',
        )
        conn.execute("INSERT INTO config (key, value) VALUES ('safe', 'data')")
        conn.commit()
        conn.close()

        migrator = LegacyMigrator(provider, legacy_dir, identity_hash)
        assert migrator.migrate() is True

        row = provider.fetchone("SELECT value FROM config WHERE key = 'safe'")
        assert row is not None
        assert row["value"] == "data"

    def test_column_with_parentheses_is_skipped(self, db_env):
        """Columns with () in the name are rejected by the identifier regex."""
        provider, _schema, tmp_path = db_env
        legacy_dir = str(tmp_path / "legacy_parens_col")
        identity_hash = "ee00ff00"

        identity_dir = os.path.join(legacy_dir, "identities", identity_hash)
        os.makedirs(identity_dir, exist_ok=True)
        db_path = os.path.join(identity_dir, "database.db")
        conn = sqlite3.connect(db_path)
        conn.execute('CREATE TABLE config (key TEXT UNIQUE, value TEXT, "evil()" TEXT)')
        conn.execute("INSERT INTO config (key, value) VALUES ('p1', 'parens')")
        conn.commit()
        conn.close()

        migrator = LegacyMigrator(provider, legacy_dir, identity_hash)
        assert migrator.migrate() is True

        row = provider.fetchone("SELECT value FROM config WHERE key = 'p1'")
        assert row is not None


# ---------------------------------------------------------------------------
# 3. _validate_identifier — unit tests
# ---------------------------------------------------------------------------


class TestValidateIdentifier:
    @pytest.mark.parametrize(
        "name",
        [
            "config",
            "lxmf_messages",
            "A",
            "_private",
            "Column123",
            "a_b_c_d",
        ],
    )
    def test_valid_identifiers_pass(self, name):
        assert _validate_identifier(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "123abc",
            "table name",
            "col;drop",
            "a'b",
            'a"b',
            "col()",
            "x--y",
            "a,b",
            "hello\nworld",
            "tab\there",
            "col/**/name",
        ],
    )
    def test_invalid_identifiers_raise(self, name):
        with pytest.raises(ValueError, match="Invalid SQL"):
            _validate_identifier(name)


# ---------------------------------------------------------------------------
# 4. _ensure_column — rejects injection via table/column names
# ---------------------------------------------------------------------------


class TestEnsureColumnInjection:
    def test_ensure_column_rejects_malicious_table_name(self, db_env):
        _provider, schema, _tmp_path = db_env
        with pytest.raises(ValueError, match="Invalid SQL table name"):
            schema._ensure_column("config; DROP TABLE config", "new_col", "TEXT")

    def test_ensure_column_rejects_malicious_column_name(self, db_env):
        _provider, schema, _tmp_path = db_env
        with pytest.raises(ValueError, match="Invalid SQL column name"):
            schema._ensure_column("config", "col; DROP TABLE config", "TEXT")

    def test_ensure_column_works_for_valid_names(self, db_env):
        _provider, schema, _tmp_path = db_env
        result = schema._ensure_column("config", "test_new_col", "TEXT")
        assert result is True

    def test_ensure_column_idempotent(self, db_env):
        _provider, schema, _tmp_path = db_env
        schema._ensure_column("config", "idempotent_col", "TEXT")
        result = schema._ensure_column("config", "idempotent_col", "TEXT")
        assert result is True


# ---------------------------------------------------------------------------
# 5. Property-based tests — identifier regex
# ---------------------------------------------------------------------------

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@given(name=st.text(min_size=1, max_size=80))
@settings(deadline=None)
def test_validate_identifier_never_allows_sql_metacharacters(name):
    """No string accepted by _validate_identifier contains SQL metacharacters."""
    try:
        _validate_identifier(name)
    except ValueError:
        return

    assert ";" not in name
    assert "'" not in name
    assert '"' not in name
    assert "(" not in name
    assert ")" not in name
    assert " " not in name
    assert "-" not in name
    assert "/" not in name
    assert "\\" not in name
    assert "\n" not in name
    assert "\r" not in name
    assert "\t" not in name
    assert "," not in name
    assert _IDENTIFIER_RE.match(name)


@given(name=st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,30}", fullmatch=True))
@settings(deadline=None)
def test_validate_identifier_accepts_all_valid_identifiers(name):
    """Every string matching the identifier pattern is accepted."""
    assert _validate_identifier(name) == name


@given(
    name=st.text(
        alphabet=st.sampled_from(list(";'\"()- \t\n\r,/*")),
        min_size=1,
        max_size=30,
    ),
)
@settings(deadline=None)
def test_validate_identifier_rejects_pure_metacharacter_strings(name):
    """Strings composed entirely of SQL metacharacters are always rejected."""
    with pytest.raises(ValueError):
        _validate_identifier(name)


# ---------------------------------------------------------------------------
# 6. ATTACH path escaping — property-based
# ---------------------------------------------------------------------------


@given(
    path_segment=st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N", "P", "S", "Z"),
        ),
        min_size=1,
        max_size=60,
    ),
)
@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_attach_path_escaping_never_breaks_sql(path_segment):
    """Quote-doubled ATTACH paths stay inside the SQL string literal."""
    safe = path_segment.replace("'", "''")
    sql = f"ATTACH DATABASE '{safe}' AS test_alias"

    assert sql.count("ATTACH DATABASE '") == 1

    after_open = sql.split("ATTACH DATABASE '", 1)[1]
    in_literal = True
    i = 0
    while i < len(after_open):
        if after_open[i] == "'":
            if i + 1 < len(after_open) and after_open[i + 1] == "'":
                i += 2
                continue
            in_literal = False
            remainder = after_open[i + 1 :]
            break
        i += 1

    if not in_literal:
        assert remainder.strip() == "AS test_alias", (
            f"Unexpected SQL after literal end: {remainder!r}"
        )
