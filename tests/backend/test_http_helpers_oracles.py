# SPDX-License-Identifier: 0BSD

"""Oracle tests for http uploads and error-response helpers."""

from __future__ import annotations

import uuid

import pytest
from aiohttp import web

from meshchatx.src.backend.http.errors import (
    http_error_from_exception,
    http_forbidden,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_field_limited,
    write_field_to_path,
)
from meshchatx.src.path_utils import PathJailError


class _FakeField:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    async def read_chunk(self, size=8192):
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class TestReadFieldLimited:
    @pytest.mark.asyncio
    async def test_reads_all_chunks(self):
        field = _FakeField([b"ab", b"cd", b""])
        assert await read_field_limited(field, 10) == b"abcd"

    @pytest.mark.asyncio
    async def test_exact_cap_allowed(self):
        field = _FakeField([b"ab", b"cd"])
        assert await read_field_limited(field, 4) == b"abcd"

    @pytest.mark.asyncio
    async def test_over_cap_raises(self):
        field = _FakeField([b"ab", b"cd"])
        with pytest.raises(PayloadTooLargeError):
            await read_field_limited(field, 3)

    @pytest.mark.asyncio
    async def test_empty_field(self):
        assert await read_field_limited(_FakeField([]), 5) == b""


class TestWriteFieldToPath:
    @pytest.mark.asyncio
    async def test_writes_and_counts(self, tmp_path):
        dest = tmp_path / str(uuid.uuid4())
        field = _FakeField([b"hello ", b"world"])
        assert await write_field_to_path(field, dest, 64) == 11
        assert dest.read_bytes() == b"hello world"

    @pytest.mark.asyncio
    async def test_over_cap_unlinks_partial(self, tmp_path):
        dest = tmp_path / str(uuid.uuid4())
        field = _FakeField([b"ab", b"cd"])
        with pytest.raises(PayloadTooLargeError):
            await write_field_to_path(field, dest, 3)
        assert not dest.exists()

    @pytest.mark.asyncio
    async def test_write_error_unlinks_partial(self, tmp_path, monkeypatch):
        dest = tmp_path / str(uuid.uuid4())
        field = _FakeField([b"ab", b"cd"])

        real_open = open

        def flaky_open(path, *a, **kw):
            handle = real_open(path, *a, **kw)
            if str(path) == str(dest):
                orig_write = handle.write

                def boom(data):
                    if data == b"cd":
                        raise OSError("disk full")
                    return orig_write(data)

                handle.write = boom
            return handle

        monkeypatch.setattr("builtins.open", flaky_open)
        with pytest.raises(OSError):
            await write_field_to_path(field, dest, 64)
        assert not dest.exists()


def _body(response: web.Response):
    import json

    return json.loads(response.text)


class TestHttpErrorFromException:
    def test_path_jail_reasons_map(self):
        cases = {
            "required": 400,
            "invalid": 400,
            "absolute": 400,
            "escape": 403,
            "reserved": 403,
            "forbidden": 403,
            "not_found": 404,
        }
        for reason, status in cases.items():
            resp = http_error_from_exception(PathJailError("msg", reason=reason))
            assert resp.status == status, reason

    def test_file_not_found(self):
        resp = http_error_from_exception(FileNotFoundError("/secret/abs/path"))
        assert resp.status == 404
        assert "secret" not in resp.text and "/abs" not in resp.text

    def test_permission(self):
        resp = http_error_from_exception(PermissionError("/etc/shadow"))
        assert resp.status == 403
        assert "shadow" not in resp.text

    def test_value_error_passes_message(self):
        resp = http_error_from_exception(ValueError("bad widget"))
        assert resp.status == 400
        assert _body(resp)["error"] == "bad widget"

    def test_oserror_is_generic(self):
        resp = http_error_from_exception(OSError("/abs/path leaked"))
        assert resp.status == 500
        assert "leaked" not in resp.text
        assert "abs" not in resp.text

    def test_unknown_exception_generic(self):
        resp = http_error_from_exception(RuntimeError("internals"))
        assert _body(resp)["error"] == "Request failed"

    def test_custom_key(self):
        resp = http_error_from_exception(ValueError("x"), key="message")
        assert "message" in _body(resp)


class TestStatusHelpers:
    def test_forbidden(self):
        assert http_forbidden().status == 403

    def test_not_found(self):
        assert http_not_found().status == 404

    def test_payload_too_large(self):
        assert http_payload_too_large().status == 413
