# SPDX-License-Identifier: 0BSD

"""Request validation and manager state regression tests.

Each test pins a confirmed bug's fixed behavior: sender-clock unread
skew, non-dict/invalid JSON bodies, int-param normalization, page size
caps, ghost RRC ACLs, FileSync ACL fail-open, telephone call-state
leaks, and ended-event dedup.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.http.errors import parse_int_param
from meshchatx.src.backend.http.middleware import create_bad_request_middleware
from meshchatx.src.backend.http.uploads import JsonBodyError, read_json_limited
from meshchatx.src.backend.lxmf_utils import (
    compute_lxmf_conversation_unread_from_latest_row,
    lxmf_row_arrival_timestamp,
)
from meshchatx.src.backend.nomadnet_downloader import NomadnetPageDownloader
from meshchatx.src.backend.telephone_manager import TelephoneManager

from .http_request_stubs import RawContent

# ---------------------------------------------------------------------------
# parse_int_param
# ---------------------------------------------------------------------------


class TestParseIntParam:
    def test_missing_returns_default(self):
        assert parse_int_param(None, 42) == 42

    def test_valid_value(self):
        assert parse_int_param("17") == 17
        assert parse_int_param(5) == 5

    def test_invalid_returns_none(self):
        assert parse_int_param("abc") is None
        assert parse_int_param("1.5x") is None
        assert parse_int_param({"k": 1}) is None

    def test_bounds(self):
        assert parse_int_param("-1", minimum=0) is None
        assert parse_int_param("0", minimum=0) == 0
        assert parse_int_param("200", maximum=100) is None
        assert parse_int_param("100", maximum=100) == 100


# ---------------------------------------------------------------------------
# read_json_limited: non-dict bodies
# ---------------------------------------------------------------------------


def _request_with_body(body: bytes):
    request = MagicMock()
    request.content = RawContent([body])
    return request


class TestReadJsonLimitedShape:
    @pytest.mark.asyncio
    async def test_dict_passes(self):
        request = _request_with_body(b'{"a": 1}')
        assert await read_json_limited(request) == {"a": 1}

    @pytest.mark.asyncio
    async def test_array_body_rejected(self):
        request = _request_with_body(b"[1, 2, 3]")
        with pytest.raises(JsonBodyError):
            await read_json_limited(request)

    @pytest.mark.asyncio
    async def test_scalar_body_rejected(self):
        request = _request_with_body(b'"just a string"')
        with pytest.raises(JsonBodyError):
            await read_json_limited(request)

    @pytest.mark.asyncio
    async def test_malformed_json_still_decode_error(self):
        request = _request_with_body(b"{not json")
        with pytest.raises(json.JSONDecodeError):
            await read_json_limited(request)


# ---------------------------------------------------------------------------
# bad_request middleware: malformed body -> 400, not 500
# ---------------------------------------------------------------------------


class TestBadRequestMiddleware:
    @pytest.mark.asyncio
    async def test_malformed_json_maps_to_400(self):
        async def handler(request):
            raise json.JSONDecodeError("expecting value", "doc", 0)

        app = web.Application(
            middlewares=[create_bad_request_middleware(MagicMock())],
        )
        app.router.add_post("/api/v1/x", handler)
        async with TestClient(TestServer(app)) as client:
            response = await client.post("/api/v1/x", data=b"{bad")
            assert response.status == 400

    @pytest.mark.asyncio
    async def test_non_dict_body_maps_to_400(self):
        async def handler(request):
            raise JsonBodyError("expected a JSON object")

        app = web.Application(
            middlewares=[create_bad_request_middleware(MagicMock())],
        )
        app.router.add_post("/api/v1/x", handler)
        async with TestClient(TestServer(app)) as client:
            response = await client.post("/api/v1/x", json=[1, 2])
            assert response.status == 400

    @pytest.mark.asyncio
    async def test_unrelated_errors_still_500(self):
        async def handler(request):
            raise RuntimeError("real bug")

        app = web.Application(
            middlewares=[create_bad_request_middleware(MagicMock())],
        )
        app.router.add_post("/api/v1/x", handler)
        async with TestClient(TestServer(app)) as client:
            response = await client.post("/api/v1/x", json={})
            assert response.status == 500


# ---------------------------------------------------------------------------
# Sender-clock unread reference: created_at beats sender timestamp
# ---------------------------------------------------------------------------


class TestUnreadArrival:
    def test_arrival_timestamp_prefers_created_at(self):
        row = {"created_at": "2024-01-02T00:00:00+00:00", "timestamp": 9_999_999_999.0}
        assert lxmf_row_arrival_timestamp(row) == 1704153600.0

    def test_arrival_timestamp_falls_back_to_timestamp(self):
        row = {"timestamp": 1_700_000_000.0}
        assert lxmf_row_arrival_timestamp(row) == 1_700_000_000.0

    def test_future_sender_timestamp_does_not_poison_unread(self):
        # Sender clock far in the future but the row arrived before the
        # read cursor: must not report unread.
        row = {
            "is_incoming": True,
            "last_read_at": "2024-01-02T00:00:01+00:00",
            "created_at": "2024-01-02T00:00:00+00:00",
            "timestamp": 9_999_999_999.0,
        }
        assert compute_lxmf_conversation_unread_from_latest_row(row) is False

    def test_past_sender_timestamp_does_not_hide_unread(self):
        # Sender clock far in the past but the row arrived after the read
        # cursor: must still report unread.
        row = {
            "is_incoming": True,
            "last_read_at": "2024-01-02T00:00:00+00:00",
            "created_at": "2024-01-02T00:00:01+00:00",
            "timestamp": 1.0,
        }
        assert compute_lxmf_conversation_unread_from_latest_row(row) is True


# ---------------------------------------------------------------------------
# NomadnetPageDownloader max_bytes
# ---------------------------------------------------------------------------


def _page_downloader(on_ok, on_fail, max_bytes=None):
    return NomadnetPageDownloader(
        b"ab" * 8,
        "/page.mu",
        None,
        on_ok,
        on_fail,
        MagicMock(),
        max_bytes=max_bytes,
    )


class TestPageDownloaderSizeCap:
    def test_oversized_response_fails_before_decode(self):
        on_ok, on_fail = MagicMock(), MagicMock()
        pd = _page_downloader(on_ok, on_fail, max_bytes=4)
        rr = MagicMock()
        rr.response = b"x" * 5
        pd.on_download_success(rr)
        on_fail.assert_called_once_with("page_too_large")
        on_ok.assert_not_called()

    def test_within_cap_still_succeeds(self):
        on_ok, on_fail = MagicMock(), MagicMock()
        pd = _page_downloader(on_ok, on_fail, max_bytes=4)
        rr = MagicMock()
        rr.response = b"1234"
        pd.on_download_success(rr)
        on_ok.assert_called_once_with("1234")
        on_fail.assert_not_called()

    def test_no_cap_keeps_old_behavior(self):
        on_ok, on_fail = MagicMock(), MagicMock()
        pd = _page_downloader(on_ok, on_fail)
        rr = MagicMock()
        rr.response = b"page body"
        pd.on_download_success(rr)
        on_ok.assert_called_once_with("page body")


# ---------------------------------------------------------------------------
# RRC ghost ACL state
# ---------------------------------------------------------------------------


class TestRoomRegistryTransientState:
    def _registry(self):
        from meshchatx.src.backend.rrc.room_registry import RoomRegistry

        return RoomRegistry(MagicMock(), MagicMock())

    def test_unregistered_room_state_dropped(self):
        reg = self._registry()
        st = reg.ensure_state("#room")
        st["ops"].add("aa" * 16)
        reg.drop_transient_state("#room")
        fresh = reg.ensure_state("#room")
        assert "aa" * 16 not in fresh["ops"]

    def test_registered_room_state_kept(self):
        reg = self._registry()
        st = reg.ensure_state("#room")
        st["registered"] = True
        st["ops"].add("aa" * 16)
        reg.drop_transient_state("#room")
        assert "aa" * 16 in reg.ensure_state("#room")["ops"]


# ---------------------------------------------------------------------------
# FileSync ACL fail-open
# ---------------------------------------------------------------------------


class TestFileSyncAcl:
    def _handler(self, tmp_path):
        from meshchatx.src.backend.rns_filesync_handler import RnsFilesyncHandler

        storage = tmp_path / "identity"
        storage.mkdir(exist_ok=True)
        return RnsFilesyncHandler(
            reticulum_instance=MagicMock(name="reticulum"),
            identity=SimpleNamespace(hash=b"\xaa" * 16),
            storage_dir=str(storage),
        )

    def test_malformed_rules_text_rejected(self, tmp_path):
        handler = self._handler(tmp_path)
        result = handler.update_acl(rules_text="!!!not-a-rule\n???garbage")
        assert result["ok"] is False

    def test_valid_rules_text_accepted(self, tmp_path):
        handler = self._handler(tmp_path)
        result = handler.update_acl(rules_text="r:" + "ab" * 16)
        assert result["ok"] is True

    def test_empty_rules_text_accepted_as_clear(self, tmp_path):
        handler = self._handler(tmp_path)
        result = handler.update_acl(rules_text="", replace=True)
        assert result["ok"] is True


# ---------------------------------------------------------------------------
# Telephone call state lifecycle
# ---------------------------------------------------------------------------


class TestTelephoneCallState:
    def test_teardown_resets_in_flight_state(self):
        manager = TelephoneManager(identity=MagicMock())
        manager.initiation_status = "Ringing..."
        manager.initiation_target_hash = "ab" * 16
        manager.call_start_time = 123.0
        manager.call_is_incoming = True
        manager.call_stats = {"link": MagicMock()}
        manager.ptt_active = True
        manager.teardown()
        assert manager.initiation_status is None
        assert manager.initiation_target_hash is None
        assert manager.call_start_time is None
        assert manager.call_is_incoming is False
        assert manager.call_stats == {}
        assert manager.ptt_active is False

    def test_ended_event_records_only_once(self):
        manager = TelephoneManager(identity=MagicMock())
        calls = []
        manager.on_ended_callback = lambda ident: calls.append(ident)
        ident = MagicMock()
        # New call arms the latch.
        manager.on_telephone_ringing(ident)
        manager.on_telephone_call_ended(ident)
        manager.on_telephone_call_ended(ident)
        assert calls == [ident]

    def test_ended_latch_rearmed_by_new_call(self):
        manager = TelephoneManager(identity=MagicMock())
        calls = []
        manager.on_ended_callback = lambda ident: calls.append(ident)
        ident = MagicMock()
        manager.on_telephone_ringing(ident)
        manager.on_telephone_call_ended(ident)
        manager.on_telephone_ringing(ident)
        manager.on_telephone_call_ended(ident)
        assert calls == [ident, ident]
