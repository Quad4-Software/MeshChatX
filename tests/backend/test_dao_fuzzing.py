"""Property-based and fuzz tests for DAO layers, MessageHandler, and utility functions.

Covers gaps identified in the existing test suite:
  - ContactsDAO: add, search, update with adversarial strings
  - ConfigDAO: get/set/delete round-trip with arbitrary keys and values
  - MiscDAO: spam keywords, notifications, keyboard shortcuts
  - TelephoneDAO: add + search with adversarial strings
  - VoicemailDAO: add + search
  - DebugLogsDAO: insert + search + count consistency
  - RingtoneDAO: add + update with adversarial display names
  - MapDrawingsDAO: upsert + update with arbitrary JSON data
  - MessageDAO: folder create/rename
  - MessageHandler: search_messages, get_conversations with adversarial search terms
  - _safe_href: URL sanitization (XSS vectors)
  - parse_bool_query_param: arbitrary strings
  - message_fields_have_attachments: arbitrary JSON
"""

import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.markdown_renderer import _safe_href
from meshchatx.src.backend.meshchat_utils import (
    message_fields_have_attachments,
    parse_bool_query_param,
)
from meshchatx.src.backend.message_handler import MessageHandler


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strings that are valid for most text columns but include adversarial chars
st_nasty_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z", "C")),
    min_size=0,
    max_size=300,
)

st_sql_payloads = st.sampled_from(
    [
        "'; DROP TABLE config; --",
        "' OR '1'='1",
        '" OR "1"="1',
        "1; SELECT * FROM sqlite_master",
        "Robert'); DROP TABLE lxmf_messages;--",
        "%",
        "%%",
        "_",
        "\x00",
        "' UNION SELECT key, value FROM config --",
        "NULL",
        "1=1",
        "admin'--",
        "' AND 1=CONVERT(int,(SELECT TOP 1 table_name FROM information_schema.tables))--",
    ]
)

st_search_term = st.one_of(st_nasty_text, st_sql_payloads)

st_hex_hash = st.from_regex(r"[0-9a-f]{16,64}", fullmatch=True)


# ---------------------------------------------------------------------------
# Fixture: initialised in-memory database
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    database = Database(":memory:")
    database.initialize()
    yield database
    database.close()


@pytest.fixture
def handler(db):
    return MessageHandler(db)


# ===================================================================
# ContactsDAO
# ===================================================================


class TestContactsDAOFuzzing:
    @given(
        name=st_nasty_text,
        identity_hash=st_hex_hash,
        lxmf_addr=st.one_of(st.none(), st_hex_hash),
        lxst_addr=st.one_of(st.none(), st_hex_hash),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=60,
    )
    def test_add_contact_roundtrip(self, db, name, identity_hash, lxmf_addr, lxst_addr):
        db.contacts.add_contact(
            name=name,
            remote_identity_hash=identity_hash,
            lxmf_address=lxmf_addr,
            lxst_address=lxst_addr,
        )
        row = db.contacts.get_contact_by_identity_hash(identity_hash)
        assert row is not None
        assert row["name"] == name

    @given(search=st_search_term)
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=80,
    )
    def test_search_contacts_never_crashes(self, db, search):
        results = db.contacts.get_contacts(search=search)
        assert isinstance(results, list)
        count = db.contacts.get_contacts_count(search=search)
        assert isinstance(count, int)
        assert count >= 0

    @given(
        name=st_nasty_text,
        identity_hash=st_hex_hash,
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_update_contact_never_crashes(self, db, name, identity_hash):
        db.contacts.add_contact(name="orig", remote_identity_hash=identity_hash)
        row = db.contacts.get_contact_by_identity_hash(identity_hash)
        assert row is not None
        db.contacts.update_contact(row["id"], name=name)
        updated = db.contacts.get_contact(row["id"])
        assert updated["name"] == name


# ===================================================================
# ConfigDAO
# ===================================================================


class TestConfigDAOFuzzing:
    @given(key=st_nasty_text.filter(lambda x: len(x) > 0), value=st_nasty_text)
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=80,
    )
    def test_config_set_get_roundtrip(self, db, key, value):
        db.config.set(key, value)
        got = db.config.get(key)
        assert got == value

    @given(key=st_nasty_text.filter(lambda x: len(x) > 0))
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_config_delete_never_crashes(self, db, key):
        db.config.set(key, "temp")
        db.config.delete(key)
        assert db.config.get(key) is None

    @given(key=st_sql_payloads)
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_config_sql_injection_keys(self, db, key):
        db.config.set(key, "injected?")
        assert db.config.get(key) == "injected?"
        tables = db.provider.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = {r["name"] for r in tables}
        assert "config" in table_names


# ===================================================================
# MiscDAO — spam keywords, notifications, keyboard shortcuts
# ===================================================================


class TestMiscDAOFuzzing:
    @given(keyword=st_nasty_text.filter(lambda x: len(x) > 0))
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=50,
    )
    def test_spam_keyword_roundtrip(self, db, keyword):
        db.misc.add_spam_keyword(keyword)
        keywords = db.misc.get_spam_keywords()
        assert any(k["keyword"] == keyword for k in keywords)

    @given(title=st_nasty_text, content=st_nasty_text)
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=50,
    )
    def test_check_spam_never_crashes(self, db, title, content):
        result = db.misc.check_spam_keywords(title, content)
        assert isinstance(result, bool)

    @given(
        ntype=st.sampled_from(["message", "call", "voicemail", "system"]),
        remote_hash=st_hex_hash,
        title=st_nasty_text,
        content=st_nasty_text,
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_add_notification_never_crashes(
        self, db, ntype, remote_hash, title, content
    ):
        db.misc.add_notification(ntype, remote_hash, title, content)
        notifications = db.misc.get_notifications()
        assert isinstance(notifications, list)

    @given(
        action=st_nasty_text.filter(lambda x: len(x) > 0),
        keys=st_nasty_text,
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_keyboard_shortcut_roundtrip(self, db, action, keys):
        identity = "testhash"
        db.misc.upsert_keyboard_shortcut(identity, action, keys)
        shortcuts = db.misc.get_keyboard_shortcuts(identity)
        assert any(s["action"] == action and s["keys"] == keys for s in shortcuts)

    @given(
        query=st_search_term,
        dest=st.one_of(st.none(), st_hex_hash),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_archived_pages_search_never_crashes(self, db, query, dest):
        results = db.misc.get_archived_pages_paginated(
            destination_hash=dest,
            query=query if query else None,
        )
        assert isinstance(results, list)


# ===================================================================
# TelephoneDAO
# ===================================================================


class TestTelephoneDAOFuzzing:
    @given(
        name=st_nasty_text,
        identity_hash=st_hex_hash,
        status=st.sampled_from(["answered", "missed", "rejected", "busy"]),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_add_call_history_never_crashes(self, db, name, identity_hash, status):
        import time

        db.telephone.add_call_history(
            remote_identity_hash=identity_hash,
            remote_identity_name=name,
            is_incoming=True,
            status=status,
            duration_seconds=42,
            timestamp=time.time(),
        )
        history = db.telephone.get_call_history()
        assert isinstance(history, list)
        assert len(history) > 0

    @given(search=st_search_term)
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=60,
    )
    def test_call_history_search_never_crashes(self, db, search):
        results = db.telephone.get_call_history(search=search)
        assert isinstance(results, list)

    @given(search=st_search_term)
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=60,
    )
    def test_call_recordings_search_never_crashes(self, db, search):
        results = db.telephone.get_call_recordings(search=search)
        assert isinstance(results, list)


# ===================================================================
# VoicemailDAO
# ===================================================================


class TestVoicemailDAOFuzzing:
    @given(
        name=st_nasty_text,
        identity_hash=st_hex_hash,
        filename=st_nasty_text,
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_add_voicemail_never_crashes(self, db, name, identity_hash, filename):
        import time

        db.voicemails.add_voicemail(
            remote_identity_hash=identity_hash,
            remote_identity_name=name,
            filename=filename,
            duration_seconds=10,
            timestamp=time.time(),
        )
        vms = db.voicemails.get_voicemails()
        assert isinstance(vms, list)

    @given(search=st_search_term)
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=60,
    )
    def test_voicemail_search_never_crashes(self, db, search):
        results = db.voicemails.get_voicemails(search=search)
        assert isinstance(results, list)


# ===================================================================
# DebugLogsDAO
# ===================================================================


class TestDebugLogsDAOFuzzing:
    @given(
        level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        module=st_nasty_text,
        message=st_nasty_text,
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=50,
    )
    def test_insert_log_never_crashes(self, db, level, module, message):
        db.debug_logs.insert_log(level, module, message)
        total = db.debug_logs.get_total_count()
        assert total > 0

    @given(
        search=st_search_term,
        level=st.one_of(st.none(), st.sampled_from(["DEBUG", "INFO", "ERROR"])),
        module=st.one_of(st.none(), st_nasty_text),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=60,
    )
    def test_search_logs_never_crashes(self, db, search, level, module):
        results = db.debug_logs.get_logs(search=search, level=level, module=module)
        assert isinstance(results, list)
        count = db.debug_logs.get_total_count(search=search, level=level, module=module)
        assert isinstance(count, int)
        assert count >= 0

    @given(
        search=st_search_term,
        level=st.one_of(st.none(), st.sampled_from(["DEBUG", "INFO", "ERROR"])),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_count_matches_result_length(self, db, search, level):
        """get_total_count must be consistent with len(get_logs) when no limit truncation."""
        results = db.debug_logs.get_logs(
            search=search,
            level=level,
            limit=100000,
            offset=0,
        )
        count = db.debug_logs.get_total_count(search=search, level=level)
        assert count == len(results)


# ===================================================================
# RingtoneDAO
# ===================================================================


class TestRingtoneDAOFuzzing:
    @given(
        filename=st_nasty_text.filter(lambda x: len(x) > 0),
        display_name=st_nasty_text.filter(lambda x: len(x) > 0),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_add_ringtone_roundtrip(self, db, filename, display_name):
        rid = db.ringtones.add(filename, f"store_{filename[:20]}", display_name)
        assert rid is not None
        row = db.ringtones.get_by_id(rid)
        assert row is not None
        assert row["display_name"] == display_name

    @given(new_name=st_nasty_text.filter(lambda x: len(x) > 0))
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=30,
    )
    def test_update_display_name(self, db, new_name):
        rid = db.ringtones.add("test.ogg", "store_test.ogg", "Original")
        db.ringtones.update(rid, display_name=new_name)
        row = db.ringtones.get_by_id(rid)
        assert row["display_name"] == new_name


# ===================================================================
# MapDrawingsDAO
# ===================================================================


class TestMapDrawingsDAOFuzzing:
    @given(
        name=st_nasty_text.filter(lambda x: len(x) > 0),
        data=st.one_of(
            st_nasty_text,
            st.builds(
                json.dumps,
                st.dictionaries(
                    st.text(max_size=10), st.text(max_size=50), max_size=10
                ),
            ),
        ),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_upsert_drawing_roundtrip(self, db, name, data):
        identity = "deadbeef01234567"
        db.map_drawings.upsert_drawing(identity, name, data)
        drawings = db.map_drawings.get_drawings(identity)
        assert any(d["name"] == name for d in drawings)


# ===================================================================
# MessageDAO — folders
# ===================================================================


class TestMessageDAOFoldersFuzzing:
    @given(name=st_nasty_text.filter(lambda x: len(x) > 0))
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_create_folder_roundtrip(self, db, name):
        db.messages.create_folder(name)
        folders = db.messages.get_all_folders()
        assert any(f["name"] == name for f in folders)

    @given(
        original=st_nasty_text.filter(lambda x: len(x) > 0),
        renamed=st_nasty_text.filter(lambda x: len(x) > 0),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=30,
    )
    def test_rename_folder(self, db, original, renamed):
        db.provider.execute("DELETE FROM lxmf_folders")
        cursor = db.messages.create_folder(original)
        folder_id = cursor.lastrowid
        db.messages.rename_folder(folder_id, renamed)
        folders = db.messages.get_all_folders()
        found = [f for f in folders if f["id"] == folder_id]
        assert len(found) == 1
        assert found[0]["name"] == renamed


# ===================================================================
# MessageHandler — search
# ===================================================================


class TestMessageHandlerFuzzing:
    @given(search=st_search_term)
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=80,
    )
    def test_search_messages_never_crashes(self, handler, search):
        results = handler.search_messages("local_hash", search)
        assert isinstance(results, list)

    @given(search=st_search_term)
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=60,
    )
    def test_get_conversations_search_never_crashes(self, handler, search):
        results = handler.get_conversations("local_hash", search=search)
        assert isinstance(results, list)

    @given(
        search=st_search_term,
        folder_id=st.one_of(st.none(), st.integers(min_value=0, max_value=1000)),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_get_conversations_with_filters(self, handler, search, folder_id):
        results = handler.get_conversations(
            "local_hash",
            search=search,
            folder_id=folder_id,
            filter_unread=True,
        )
        assert isinstance(results, list)

    @given(
        dest=st_hex_hash,
        after_id=st.one_of(st.none(), st.integers(min_value=-1000, max_value=1000)),
        before_id=st.one_of(st.none(), st.integers(min_value=-1000, max_value=1000)),
    )
    @settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=40,
    )
    def test_get_conversation_messages_never_crashes(
        self, handler, dest, after_id, before_id
    ):
        results = handler.get_conversation_messages(
            "local_hash",
            dest,
            after_id=after_id,
            before_id=before_id,
        )
        assert isinstance(results, list)


# ===================================================================
# _safe_href — URL sanitization
# ===================================================================


class TestSafeHrefFuzzing:
    @given(url=st.text(max_size=500))
    @settings(deadline=None, max_examples=200)
    def test_safe_href_never_returns_dangerous_protocol(self, url):
        result = _safe_href(url)
        lower = result.strip().lower()
        assert not lower.startswith("javascript:")
        assert not lower.startswith("data:")
        assert not lower.startswith("vbscript:")
        assert not lower.startswith("file:")

    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "JAVASCRIPT:alert(1)",
            "  javascript:alert(1)  ",
            "jAvAsCrIpT:alert(document.cookie)",
            "data:text/html,<script>alert(1)</script>",
            "DATA:text/html;base64,PHNjcmlwdD4=",
            "vbscript:MsgBox('xss')",
            "file:///etc/passwd",
        ],
    )
    def test_safe_href_blocks_xss_vectors(self, url):
        assert _safe_href(url) == "#"

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com",
            "http://example.com",
            "/relative/path",
            "#anchor",
            "mailto:test@example.com",
        ],
    )
    def test_safe_href_allows_safe_urls(self, url):
        assert _safe_href(url) == url

    @given(
        url=st.from_regex(
            r"(javascript|data|vbscript|file):[A-Za-z0-9()=;,/+]+",
            fullmatch=True,
        )
    )
    @settings(deadline=None, max_examples=100)
    def test_safe_href_blocks_all_generated_dangerous_urls(self, url):
        assert _safe_href(url) == "#"

    @given(
        scheme=st.text(min_size=1, max_size=20).filter(
            lambda s: ":" not in s and "/" not in s
        )
    )
    @settings(deadline=None, max_examples=60)
    def test_safe_href_blocks_unknown_schemes(self, scheme):
        """Any unknown scheme like 'foo:bar' should be blocked."""
        url = f"{scheme}:something"
        result = _safe_href(url)
        lower = url.strip().lower()
        if any(
            lower.startswith(p) for p in ("https://", "http://", "/", "#", "mailto:")
        ):
            assert result == url
        else:
            assert result == "#"


# ===================================================================
# parse_bool_query_param
# ===================================================================


class TestParseBoolQueryParam:
    @given(value=st.text(max_size=100))
    @settings(deadline=None, max_examples=200)
    def test_never_crashes_and_returns_bool(self, value):
        result = parse_bool_query_param(value)
        assert isinstance(result, bool)

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("1", True),
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("yes", True),
            ("YES", True),
            ("on", True),
            ("ON", True),
            ("0", False),
            ("false", False),
            ("no", False),
            ("off", False),
            ("", False),
            ("maybe", False),
            (None, False),
        ],
    )
    def test_known_values(self, value, expected):
        assert parse_bool_query_param(value) is expected


# ===================================================================
# message_fields_have_attachments
# ===================================================================


class TestMessageFieldsHaveAttachments:
    @given(data=st.text(max_size=500))
    @settings(deadline=None, max_examples=100)
    def test_never_crashes_on_arbitrary_text(self, data):
        result = message_fields_have_attachments(data)
        assert isinstance(result, bool)

    @given(
        obj=st.dictionaries(
            st.text(max_size=20),
            st.one_of(st.text(max_size=50), st.integers(), st.booleans(), st.none()),
            max_size=10,
        )
    )
    @settings(deadline=None, max_examples=80)
    def test_never_crashes_on_arbitrary_json_objects(self, obj):
        result = message_fields_have_attachments(json.dumps(obj))
        assert isinstance(result, bool)

    @pytest.mark.parametrize(
        "fields_json,expected",
        [
            (None, False),
            ("", False),
            ("{}", False),
            ("not json", False),
            ('{"image": "base64data"}', True),
            ('{"audio": "base64data"}', True),
            ('{"file_attachments": [{"name": "f.txt"}]}', True),
            ('{"file_attachments": []}', False),
            ('{"other_field": "value"}', False),
        ],
    )
    def test_known_cases(self, fields_json, expected):
        assert message_fields_have_attachments(fields_json) is expected

    @given(
        data=st.recursive(
            st.one_of(st.text(max_size=20), st.integers(), st.booleans(), st.none()),
            lambda children: (
                st.lists(children, max_size=5)
                | st.dictionaries(st.text(max_size=10), children, max_size=5)
            ),
            max_leaves=30,
        )
    )
    @settings(deadline=None, max_examples=60)
    def test_deeply_nested_json_never_crashes(self, data):
        result = message_fields_have_attachments(json.dumps(data))
        assert isinstance(result, bool)
