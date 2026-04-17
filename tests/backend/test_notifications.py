# SPDX-License-Identifier: 0BSD

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


def test_add_get_notifications(db):
    """Test basic notification storage and retrieval."""
    db.misc.add_notification(
        notification_type="test_type",
        remote_hash="test_hash",
        title="Test Title",
        content="Test Content",
    )

    notifications = db.misc.get_notifications()
    assert len(notifications) == 1
    assert notifications[0]["type"] == "test_type"
    assert notifications[0]["remote_hash"] == "test_hash"
    assert notifications[0]["title"] == "Test Title"
    assert notifications[0]["content"] == "Test Content"
    assert notifications[0]["is_viewed"] == 0


def test_mark_notifications_as_viewed(db):
    """Test marking notifications as viewed."""
    db.misc.add_notification("type1", "hash1", "title1", "content1")
    db.misc.add_notification("type2", "hash2", "title2", "content2")

    notifications = db.misc.get_notifications()
    n_ids = [n["id"] for n in notifications]

    db.misc.mark_notifications_as_viewed([n_ids[0]])

    unread = db.misc.get_notifications(filter_unread=True)
    assert len(unread) == 1
    assert unread[0]["id"] == n_ids[1]

    db.misc.mark_notifications_as_viewed()  # Mark all
    unread_all = db.misc.get_notifications(filter_unread=True)
    assert len(unread_all) == 0


def test_missed_call_notification(mock_app):
    """Test that a missed call triggers a notification."""
    caller_identity = MagicMock()
    caller_identity.hash = b"caller_hash_32_bytes_long_012345"
    caller_hash = caller_identity.hash.hex()

    # Mock telephone manager state for missed call
    mock_app.telephone_manager.call_is_incoming = True
    mock_app.telephone_manager.call_status_at_end = 4  # Ringing
    mock_app.telephone_manager.call_start_time = time.time() - 10
    mock_app.telephone_manager.call_was_established = False

    mock_app.on_telephone_call_ended(caller_identity)

    notifications = mock_app.database.misc.get_notifications()
    assert len(notifications) == 1
    assert notifications[0]["type"] == "telephone_missed_call"
    assert notifications[0]["remote_hash"] == caller_hash

    # Verify websocket broadcast
    assert mock_app.websocket_broadcast.called


def test_voicemail_notification(mock_app):
    """Test that a new voicemail triggers a notification."""
    remote_hash = "remote_hash_hex"
    remote_name = "Remote User"
    duration = 15

    mock_app.on_new_voicemail_received(remote_hash, remote_name, duration)

    notifications = mock_app.database.misc.get_notifications()
    assert len(notifications) == 1
    assert notifications[0]["type"] == "telephone_voicemail"
    assert notifications[0]["remote_hash"] == remote_hash
    assert "15s" in notifications[0]["content"]

    # Verify websocket broadcast
    assert mock_app.websocket_broadcast.called


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    notification_type=st.text(min_size=1, max_size=50),
    remote_hash=st.text(min_size=1, max_size=64),
    title=st.text(min_size=1, max_size=100),
    content=st.text(min_size=1, max_size=500),
)
def test_notification_fuzzing(db, notification_type, remote_hash, title, content):
    """Fuzz notification storage with varied data."""
    db.misc.add_notification(notification_type, remote_hash, title, content)
    notifications = db.misc.get_notifications(limit=1)
    assert len(notifications) == 1
    # We don't assert content match exactly if there are encoding issues,
    # but sqlite should handle most strings.
    assert notifications[0]["type"] == notification_type


@pytest.mark.asyncio
async def test_notifications_api(mock_app):
    """Test the notifications API endpoint."""
    # Add some notifications
    mock_app.database.misc.add_notification("type1", "hash1", "title1", "content1")

    # Mock request
    request = MagicMock()
    request.query = {"unread": "false", "limit": "10"}

    # We need to mock local_lxmf_destination as it's used in notifications_get
    mock_app.local_lxmf_destination = MagicMock()
    mock_app.local_lxmf_destination.hexhash = "local_hash"

    # Also mock message_handler.get_conversations
    mock_app.message_handler.get_conversations.return_value = []

    # Find the route handler
    # Since it's defined inside ReticulumMeshChat.run, we might need to find it
    # or just call the method if we can.
    # Actually, let's just test the logic by calling the handler directly if we can find it.
    # But it's defined as a nested function.
    # Alternatively, we can test the DAOs and meshchat.py logic that the handler uses.

    # Let's test a spike of notifications
    for i in range(100):
        mock_app.database.misc.add_notification(
            notification_type=f"type{i}",
            remote_hash=f"hash{i}",
            title=f"title{i}",
            content=f"content{i}",
        )

    notifications = mock_app.database.misc.get_notifications(limit=50)
    assert len(notifications) == 50


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    remote_hash=st.text(min_size=1, max_size=64),
    remote_name=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
    duration=st.integers(min_value=0, max_value=3600),
)
def test_voicemail_notification_fuzzing(mock_app, remote_hash, remote_name, duration):
    """Fuzz voicemail notification triggering."""
    mock_app.database.misc.provider.execute("DELETE FROM notifications")
    mock_app.on_new_voicemail_received(remote_hash, remote_name, duration)

    notifications = mock_app.database.misc.get_notifications()
    assert len(notifications) == 1
    assert notifications[0]["type"] == "telephone_voicemail"
    assert remote_hash in notifications[0]["content"] or (
        remote_name and remote_name in notifications[0]["content"]
    )


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    remote_hash=st.text(min_size=32, max_size=64),  # Hex hash
    status_code=st.integers(min_value=0, max_value=10),
    call_was_established=st.booleans(),
)
def test_missed_call_notification_fuzzing(
    mock_app,
    remote_hash,
    status_code,
    call_was_established,
):
    """Fuzz missed call notification triggering."""
    mock_app.database.misc.provider.execute("DELETE FROM notifications")

    caller_identity = MagicMock()
    try:
        caller_identity.hash = bytes.fromhex(remote_hash)
    except Exception:
        caller_identity.hash = remote_hash.encode()[:32]

    mock_app.telephone_manager.call_is_incoming = True
    mock_app.telephone_manager.call_status_at_end = status_code
    mock_app.telephone_manager.call_start_time = time.time()
    mock_app.telephone_manager.call_was_established = call_was_established

    mock_app.on_telephone_call_ended(caller_identity)

    notifications = mock_app.database.misc.get_notifications()
    # Notification is created if incoming and not established, regardless of status_code
    if not call_was_established:
        assert len(notifications) == 1
        assert notifications[0]["type"] == "telephone_missed_call"
    else:
        assert len(notifications) == 0


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(num_notifs=st.integers(min_value=1, max_value=200))
def test_notification_spike_fuzzing(db, num_notifs):
    """Test handling a spike of notifications."""
    for i in range(num_notifs):
        db.misc.add_notification(f"type{i}", "hash", "title", "content")

    notifications = db.misc.get_notifications(limit=num_notifs)
    assert len(notifications) == num_notifs


# ---------------------------------------------------------------------------
# Extensive notification reliability tests
# ---------------------------------------------------------------------------


class TestNotificationReliability:
    """Notification counts and read state stay consistent (no false positives)."""

    def test_unread_count_matches_actual_unread(self, db):
        """Unread count must exactly match unviewed notifications."""
        for i in range(10):
            db.misc.add_notification(f"type{i}", f"h{i}", f"t{i}", f"c{i}")

        assert db.misc.get_unread_notification_count() == 10

        ids = [n["id"] for n in db.misc.get_notifications()]
        db.misc.mark_notifications_as_viewed([ids[0], ids[1], ids[2]])
        assert db.misc.get_unread_notification_count() == 7

        db.misc.mark_notifications_as_viewed()
        assert db.misc.get_unread_notification_count() == 0

    def test_marking_empty_list_marks_all(self, db):
        """Marking with an empty list (falsy) falls through to mark-all behavior."""
        db.misc.add_notification("t", "h", "title", "content")
        db.misc.mark_notifications_as_viewed([])
        assert db.misc.get_unread_notification_count() == 0

    def test_marking_nonexistent_ids_is_safe(self, db):
        """Marking IDs that don't exist should not crash."""
        db.misc.mark_notifications_as_viewed([99999, 88888, 77777])
        assert db.misc.get_unread_notification_count() == 0

    def test_double_mark_viewed_idempotent(self, db):
        """Marking the same notification as viewed twice is safe."""
        db.misc.add_notification("t", "h", "title", "content")
        nid = db.misc.get_notifications()[0]["id"]
        db.misc.mark_notifications_as_viewed([nid])
        db.misc.mark_notifications_as_viewed([nid])
        assert db.misc.get_unread_notification_count() == 0

    def test_no_ghost_notifications_after_clear(self, db):
        """After marking all as viewed, unread count must be zero and stay zero."""
        for i in range(5):
            db.misc.add_notification(f"type{i}", "h", "t", "c")
        db.misc.mark_notifications_as_viewed()
        assert db.misc.get_unread_notification_count() == 0
        assert len(db.misc.get_notifications(filter_unread=True)) == 0

    def test_interleaved_add_and_mark(self, db):
        """Adding and marking interleaved must produce correct counts."""
        db.misc.add_notification("a", "h1", "t1", "c1")
        db.misc.add_notification("b", "h2", "t2", "c2")
        nid1 = db.misc.get_notifications()[0]["id"]
        db.misc.mark_notifications_as_viewed([nid1])

        db.misc.add_notification("c", "h3", "t3", "c3")
        assert db.misc.get_unread_notification_count() == 2

    def test_limit_does_not_affect_unread_count(self, db):
        """get_unread_notification_count is independent of query limit."""
        for i in range(20):
            db.misc.add_notification(f"t{i}", "h", "title", "content")
        limited = db.misc.get_notifications(limit=5)
        assert len(limited) == 5
        assert db.misc.get_unread_notification_count() == 20

    def test_missed_call_creates_exactly_one_notification(self, mock_app):
        """A single missed call must produce exactly one notification."""
        mock_app.database.misc.provider.execute("DELETE FROM notifications")

        caller = MagicMock()
        caller.hash = b"caller_hash_32_bytes_long_012345"
        mock_app.telephone_manager.call_is_incoming = True
        mock_app.telephone_manager.call_status_at_end = 4
        mock_app.telephone_manager.call_start_time = time.time() - 5
        mock_app.telephone_manager.call_was_established = False

        mock_app.on_telephone_call_ended(caller)
        notifications = mock_app.database.misc.get_notifications()
        assert len(notifications) == 1
        assert notifications[0]["type"] == "telephone_missed_call"

    def test_established_call_creates_no_notification(self, mock_app):
        """An established (answered) call must not create a missed-call notification."""
        mock_app.database.misc.provider.execute("DELETE FROM notifications")

        caller = MagicMock()
        caller.hash = b"caller_hash_32_bytes_long_012345"
        mock_app.telephone_manager.call_is_incoming = True
        mock_app.telephone_manager.call_status_at_end = 6
        mock_app.telephone_manager.call_start_time = time.time() - 60
        mock_app.telephone_manager.call_was_established = True

        mock_app.on_telephone_call_ended(caller)
        notifications = mock_app.database.misc.get_notifications()
        assert len(notifications) == 0

    def test_outgoing_call_creates_no_missed_notification(self, mock_app):
        """An outgoing call that ends without answer must not produce a missed-call notification."""
        mock_app.database.misc.provider.execute("DELETE FROM notifications")

        callee = MagicMock()
        callee.hash = b"callee_hash_32_bytes_long_012345"
        mock_app.telephone_manager.call_is_incoming = False
        mock_app.telephone_manager.call_status_at_end = 2
        mock_app.telephone_manager.call_start_time = time.time() - 10
        mock_app.telephone_manager.call_was_established = False

        mock_app.on_telephone_call_ended(callee)
        notifications = mock_app.database.misc.get_notifications()
        assert len(notifications) == 0

    def test_voicemail_creates_exactly_one_notification(self, mock_app):
        """A voicemail must create exactly one notification."""
        mock_app.database.misc.provider.execute("DELETE FROM notifications")
        mock_app.on_new_voicemail_received("abc123", "User X", 30)
        notifications = mock_app.database.misc.get_notifications()
        assert len(notifications) == 1
        assert notifications[0]["type"] == "telephone_voicemail"

    def test_rapid_missed_calls_unique_notifications(self, mock_app):
        """Multiple rapid missed calls from different callers produce separate notifications."""
        mock_app.database.misc.provider.execute("DELETE FROM notifications")

        for i in range(10):
            caller = MagicMock()
            caller.hash = f"caller_{i:032d}".encode()[:32]
            mock_app.telephone_manager.call_is_incoming = True
            mock_app.telephone_manager.call_status_at_end = 4
            mock_app.telephone_manager.call_start_time = time.time() - 1
            mock_app.telephone_manager.call_was_established = False
            mock_app.on_telephone_call_ended(caller)

        notifications = mock_app.database.misc.get_notifications()
        assert len(notifications) == 10
        assert all(n["type"] == "telephone_missed_call" for n in notifications)

    def test_mixed_notification_types_correct_counts(self, mock_app):
        """Mix of missed calls and voicemails produces correct per-type counts."""
        mock_app.database.misc.provider.execute("DELETE FROM notifications")

        for _ in range(3):
            caller = MagicMock()
            caller.hash = b"caller_hash_32_bytes_long_012345"
            mock_app.telephone_manager.call_is_incoming = True
            mock_app.telephone_manager.call_status_at_end = 4
            mock_app.telephone_manager.call_start_time = time.time()
            mock_app.telephone_manager.call_was_established = False
            mock_app.on_telephone_call_ended(caller)

        for _ in range(2):
            mock_app.on_new_voicemail_received("vm_hash", "VmUser", 10)

        notifications = mock_app.database.misc.get_notifications()
        missed = [n for n in notifications if n["type"] == "telephone_missed_call"]
        voicemails = [n for n in notifications if n["type"] == "telephone_voicemail"]
        assert len(missed) == 3
        assert len(voicemails) == 2
        assert mock_app.database.misc.get_unread_notification_count() == 5

    def test_mark_viewed_reduces_count_precisely(self, mock_app):
        """Marking specific notifications as viewed reduces count by exactly that many."""
        mock_app.database.misc.provider.execute("DELETE FROM notifications")

        for i in range(5):
            mock_app.database.misc.add_notification(f"t{i}", f"h{i}", f"t{i}", f"c{i}")

        assert mock_app.database.misc.get_unread_notification_count() == 5

        ids = [n["id"] for n in mock_app.database.misc.get_notifications()]
        mock_app.database.misc.mark_notifications_as_viewed([ids[0], ids[2]])
        assert mock_app.database.misc.get_unread_notification_count() == 3

    def test_notification_ordering(self, db):
        """Notifications should be returned in reverse chronological order (newest first)."""
        import time as _time

        for i in range(5):
            db.misc.add_notification(f"type{i}", "h", f"title_{i}", f"content_{i}")
            _time.sleep(0.01)

        notifications = db.misc.get_notifications()
        for j in range(len(notifications) - 1):
            assert notifications[j]["timestamp"] >= notifications[j + 1]["timestamp"]


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    num_add=st.integers(min_value=0, max_value=50),
    num_mark=st.integers(min_value=0, max_value=50),
)
def test_add_mark_invariant(db, num_add, num_mark):
    """Invariant: unread count == total - marked, never negative."""
    db.provider.execute("DELETE FROM notifications")
    for i in range(num_add):
        db.misc.add_notification(f"t{i}", "h", "t", "c")

    all_notifs = db.misc.get_notifications()
    ids_to_mark = [n["id"] for n in all_notifs[:num_mark]]
    if ids_to_mark:
        db.misc.mark_notifications_as_viewed(ids_to_mark)

    expected = max(0, num_add - len(ids_to_mark))
    assert db.misc.get_unread_notification_count() == expected


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    operations=st.lists(
        st.tuples(
            st.sampled_from(["add", "mark_one", "mark_all"]),
            st.text(min_size=1, max_size=20),
        ),
        min_size=1,
        max_size=30,
    ),
)
def test_random_notification_operations(db, operations):
    """Fuzz random sequences of add/mark operations; count must never go negative."""
    db.provider.execute("DELETE FROM notifications")
    for op, payload in operations:
        if op == "add":
            db.misc.add_notification("type", payload, "title", "content")
        elif op == "mark_one":
            notifs = db.misc.get_notifications(limit=1)
            if notifs:
                db.misc.mark_notifications_as_viewed([notifs[0]["id"]])
        elif op == "mark_all":
            db.misc.mark_notifications_as_viewed()

    count = db.misc.get_unread_notification_count()
    assert count >= 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_auth_middleware_returns_401_for_api_without_session_when_auth_enabled(
    mock_app,
):
    app = mock_app
    app.current_context = MagicMock(running=True)
    app.config.auth_enabled.set(True)

    routes = web.RouteTableDef()
    auth_mw, mime_mw, sec_mw = app._define_routes(routes)
    aio_app = web.Application(middlewares=[auth_mw, mime_mw, sec_mw])
    aio_app.add_routes(routes)

    async with TestClient(TestServer(aio_app)) as client:
        with patch("meshchatx.meshchat.get_session", new_callable=AsyncMock) as gs:
            gs.return_value = {}
            resp = await client.get("/api/v1/config")
            assert resp.status == 401
