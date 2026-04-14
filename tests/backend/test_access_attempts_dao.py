"""Tests and property-based checks for AccessAttemptsDAO."""

from __future__ import annotations

import time

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.database.access_attempts import (
    LOGIN_PATH,
    MAX_TRUSTED_FINGERPRINTS_PER_IDENTITY,
    SETUP_PATH,
    AccessAttemptsDAO,
    user_agent_hash,
)


def _id_hash() -> str:
    return "746573745f686173685f33325f62797465735f6c6f6e675f3031323334353637"


@pytest.fixture
def dao(db) -> AccessAttemptsDAO:
    return db.access_attempts


def test_user_agent_hash_deterministic():
    assert user_agent_hash("Mozilla/5.0") == user_agent_hash("Mozilla/5.0")
    assert user_agent_hash("") == user_agent_hash("")


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(s=st.text(min_size=0, max_size=600))
def test_user_agent_hash_hypothesis_stable(dao, s):
    h1 = user_agent_hash(s)
    h2 = user_agent_hash(s)
    assert h1 == h2
    assert len(h1) == 64


def test_insert_list_roundtrip(dao):
    ih = _id_hash()
    dao.insert(ih, "10.0.0.1", "TestAgent/1", LOGIN_PATH, "POST", "success", None)
    rows = dao.list_attempts(limit=10, offset=0)
    assert len(rows) >= 1
    top = rows[0]
    assert top["identity_hash"] == ih
    assert top["client_ip"] == "10.0.0.1"
    assert top["user_agent"] == "TestAgent/1"
    assert top["path"] == LOGIN_PATH
    assert top["method"] == "POST"
    assert top["outcome"] == "success"


def test_count_matches_list_for_no_filters(dao):
    ih = _id_hash()
    before = dao.count_attempts()
    dao.insert(ih, "10.0.0.2", "a", LOGIN_PATH, "POST", "failed_password", None)
    after = dao.count_attempts()
    assert after == before + 1


def test_search_filters(dao):
    ih = _id_hash()
    dao.insert(
        ih, "192.168.99.1", "UniqueSearchUA", LOGIN_PATH, "POST", "success", "detail-x",
    )
    found = dao.list_attempts(search="UniqueSearchUA", limit=50)
    assert any(r["user_agent"] == "UniqueSearchUA" for r in found)
    n = dao.count_attempts(search="UniqueSearchUA")
    assert n >= 1


def test_outcome_filter(dao):
    ih = _id_hash()
    dao.insert(ih, "10.0.0.3", "b", SETUP_PATH, "POST", "invalid_json", None)
    only = dao.list_attempts(outcome="invalid_json", limit=100)
    assert all(r["outcome"] == "invalid_json" for r in only)


def test_is_trusted_and_upsert(dao):
    ih = _id_hash()
    ua = "TrustedClient/2"
    h = user_agent_hash(ua)
    assert dao.is_trusted(ih, "10.0.0.4", h) is False
    dao.upsert_trusted(ih, "10.0.0.4", h)
    assert dao.is_trusted(ih, "10.0.0.4", h) is True


def test_count_lockout_excludes_trusted_fingerprint(dao):
    ih = _id_hash()
    ip = "10.0.0.5"
    ua_ok = "OkBrowser"
    ua_bad = "BadBrowser"
    h_ok = user_agent_hash(ua_ok)
    dao.upsert_trusted(ih, ip, h_ok)
    since = time.time() - 100
    for _ in range(6):
        dao.insert(ih, ip, ua_ok, LOGIN_PATH, "POST", "failed_password", None)
    assert dao.count_lockout_failures(ih, ip, since) == 0
    for _ in range(5):
        dao.insert(ih, ip, ua_bad, LOGIN_PATH, "POST", "failed_password", None)
    assert dao.count_lockout_failures(ih, ip, since) == 5


def test_prune_trusted_keeps_under_cap(dao):
    ih = _id_hash()
    ip = "10.0.0.6"
    for i in range(MAX_TRUSTED_FINGERPRINTS_PER_IDENTITY + 5):
        ua = f"Browser-{i}"
        dao.upsert_trusted(ih, ip, user_agent_hash(ua))
    row = dao.provider.fetchone(
        "SELECT COUNT(*) AS c FROM trusted_login_clients WHERE identity_hash = ?",
        (ih,),
    )
    assert int(row["c"]) == MAX_TRUSTED_FINGERPRINTS_PER_IDENTITY


def test_cleanup_old_removes_oldest_when_over_max(dao):
    ih = _id_hash()
    dao.cleanup_old(max_rows=3)
    for i in range(5):
        dao.insert(ih, f"10.0.1.{i}", "x", LOGIN_PATH, "POST", "success", None)
    dao.cleanup_old(max_rows=3)
    n = dao.count_attempts()
    assert n == 3


@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    ip=st.ip_addresses().map(str),
    ua=st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=0,
        max_size=200,
    ),
    outcome=st.sampled_from(
        ["success", "failed_password", "rate_limited", "invalid_json"],
    ),
)
def test_insert_list_hypothesis_invariants(dao, ip, ua, outcome):
    assume(ip)
    ih = _id_hash()
    before_total = dao.count_attempts()
    dao.insert(ih, ip, ua, LOGIN_PATH, "POST", outcome, "h")
    after_total = dao.count_attempts()
    assert after_total == before_total + 1
    rows = dao.list_attempts(limit=500, offset=0, outcome=outcome)
    assert any(r["client_ip"] == ip and r["outcome"] == outcome for r in rows)


def test_access_attempts_table_exists(db):
    row = db.provider.fetchone(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='access_attempts'",
    )
    assert row is not None
    row2 = db.provider.fetchone(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='trusted_login_clients'",
    )
    assert row2 is not None
