# SPDX-License-Identifier: 0BSD

"""Oracle tests for http uploads and error-response helpers."""

from __future__ import annotations

import asyncio
import base64
import itertools
import json
import uuid

import pytest
from aiohttp import web
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.http.errors import (
    http_error_from_exception,
    http_forbidden,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    DEFAULT_JSON_BODY_BYTES,
    DEFAULT_TEXT_FIELD_BYTES,
    UPLOAD_LIMITS,
    PayloadTooLargeError,
    read_body_limited,
    read_field_limited,
    read_field_text_limited,
    read_json_limited,
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


class _FakeTextField(_FakeField):
    """Field stub with aiohttp-style charset and transfer-decode hooks."""

    def __init__(self, chunks, *, charset=None, decoder=None):
        super().__init__(chunks)
        self._charset = charset
        self._decoder = decoder

    def get_charset(self, default="utf-8"):
        return self._charset or default

    def decode(self, raw):
        if self._decoder is None:
            return raw
        return self._decoder(raw)


class _FakeContent:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    async def iter_chunked(self, _size):
        for chunk in self._chunks:
            yield chunk


class _FakeRequest:
    def __init__(self, chunks):
        self.content = _FakeContent(chunks)


@st.composite
def chunked_bytes(draw, data_strategy):
    """Draw a payload plus a random split into non-empty chunks."""
    data = draw(data_strategy)
    if not data:
        return data, []
    cuts = sorted(draw(st.sets(st.integers(0, len(data)), max_size=8)))
    bounds = [0, *cuts, len(data)]
    chunks = [data[a:b] for a, b in itertools.pairwise(bounds)]
    return data, [chunk for chunk in chunks if chunk]


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


class TestReadFieldLimitedOracle:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("total", "split"),
        [
            (0, []),
            (63, [63]),
            (64, [64]),
            (64, [32, 32]),
            (64, [63, 1]),
            (65, [64, 1]),
            (65, [32, 33]),
            (66, [64, 1, 1]),
        ],
    )
    async def test_cap_boundaries_across_chunk_splits(self, total, split):
        cap = 64
        payload = b"p" * total
        chunks = []
        offset = 0
        for size in split:
            chunks.append(payload[offset : offset + size])
            offset += size
        field = _FakeField(chunks)
        if total <= cap:
            assert await read_field_limited(field, cap) == payload
        else:
            with pytest.raises(PayloadTooLargeError):
                await read_field_limited(field, cap)

    @given(
        pair=chunked_bytes(st.binary(min_size=0, max_size=4096)),
        cap=st.integers(min_value=0, max_value=4096),
    )
    @settings(max_examples=120, deadline=None)
    def test_cap_oracle(self, pair, cap):
        payload, chunks = pair
        field = _FakeField(chunks)
        try:
            out = asyncio.run(read_field_limited(field, cap))
        except PayloadTooLargeError:
            assert len(payload) > cap
        else:
            assert len(payload) <= cap
            assert out == payload

    @given(pair=chunked_bytes(st.binary(min_size=1, max_size=2048)))
    @settings(max_examples=60, deadline=None)
    def test_one_byte_over_cap_always_raises(self, pair):
        payload, chunks = pair
        field = _FakeField(chunks)
        with pytest.raises(PayloadTooLargeError):
            asyncio.run(read_field_limited(field, len(payload) - 1))


class TestReadFieldTextLimited:
    @pytest.mark.asyncio
    async def test_decodes_utf8_by_default(self):
        field = _FakeTextField(["héllo".encode()])
        assert await read_field_text_limited(field, 64) == "héllo"

    @pytest.mark.asyncio
    async def test_plain_field_without_hooks_decodes_utf8(self):
        field = _FakeField([b"plain text"])
        assert await read_field_text_limited(field, 64) == "plain text"

    @pytest.mark.asyncio
    async def test_empty_field(self):
        assert await read_field_text_limited(_FakeTextField([]), 16) == ""

    @pytest.mark.asyncio
    async def test_cap_enforced(self):
        field = _FakeTextField([b"ab", b"cd"])
        with pytest.raises(PayloadTooLargeError):
            await read_field_text_limited(field, 3)

    @pytest.mark.asyncio
    async def test_charset_respected(self):
        field = _FakeTextField(["café".encode("latin-1")], charset="latin-1")
        assert await read_field_text_limited(field, 64) == "café"

    @pytest.mark.asyncio
    async def test_broken_charset_falls_back(self):
        def bad_charset(_default="utf-8"):
            raise RuntimeError("no content-type")

        field = _FakeTextField([b"ok"])
        field.get_charset = bad_charset
        assert await read_field_text_limited(field, 16) == "ok"

    @pytest.mark.asyncio
    async def test_transfer_decode_honored(self):
        # A base64 content-transfer decoder runs before charset decode.
        plain = "hello world"
        field = _FakeTextField(
            [base64.b64encode(plain.encode())],
            decoder=base64.b64decode,
        )
        assert await read_field_text_limited(field, 1024) == plain

    @given(text=st.text(max_size=256))
    @settings(max_examples=60, deadline=None)
    def test_text_roundtrip(self, text):
        field = _FakeTextField([text.encode("utf-8")])
        out = asyncio.run(read_field_text_limited(field, 8192))
        assert out == text


class TestReadBodyLimited:
    @pytest.mark.asyncio
    async def test_reads_all_chunks(self):
        request = _FakeRequest([b"ab", b"cd", b"ef"])
        assert await read_body_limited(request, 16) == b"abcdef"

    @pytest.mark.asyncio
    async def test_empty_body(self):
        assert await read_body_limited(_FakeRequest([]), 16) == b""

    @pytest.mark.asyncio
    async def test_over_cap_raises(self):
        request = _FakeRequest([b"ab", b"cd"])
        with pytest.raises(PayloadTooLargeError):
            await read_body_limited(request, 3)

    @given(
        pair=chunked_bytes(st.binary(min_size=0, max_size=4096)),
        cap=st.integers(min_value=0, max_value=4096),
    )
    @settings(max_examples=100, deadline=None)
    def test_cap_oracle(self, pair, cap):
        payload, chunks = pair
        request = _FakeRequest(chunks)
        try:
            out = asyncio.run(read_body_limited(request, cap))
        except PayloadTooLargeError:
            assert len(payload) > cap
        else:
            assert len(payload) <= cap
            assert out == payload


class TestReadJsonLimited:
    @pytest.mark.asyncio
    async def test_valid_json_across_chunk_split(self):
        request = _FakeRequest([b'{"a": ', b"1,", b' "b": [2]}'])
        assert await read_json_limited(request) == {"a": 1, "b": [2]}

    @pytest.mark.asyncio
    async def test_malformed_raises_jsondecodeerror(self):
        request = _FakeRequest([b"{not json"])
        with pytest.raises(json.JSONDecodeError):
            await read_json_limited(request)

    @pytest.mark.asyncio
    async def test_oversized_raises_payload_too_large(self):
        request = _FakeRequest([b" " * 32])
        with pytest.raises(PayloadTooLargeError):
            await read_json_limited(request, 8)

    @given(
        payload=st.recursive(
            st.none()
            | st.booleans()
            | st.integers()
            | st.floats(allow_nan=False)
            | st.text(),
            lambda children: (
                st.lists(children, max_size=5)
                | st.dictionaries(st.text(), children, max_size=5)
            ),
            max_leaves=20,
        )
    )
    @settings(max_examples=80, deadline=None)
    def test_json_roundtrip_small_chunks(self, payload):
        raw = json.dumps(payload).encode()
        # Fixed tiny splits still vary boundaries via random payload length.
        chunks = [raw[i : i + 3] for i in range(0, len(raw), 3)]
        request = _FakeRequest(chunks)
        assert asyncio.run(read_json_limited(request)) == payload

    @given(pair=chunked_bytes(st.binary(max_size=512)))
    @settings(max_examples=80, deadline=None)
    def test_never_returns_partial_parse(self, pair):
        raw, chunks = pair
        request = _FakeRequest(chunks)
        try:
            out = asyncio.run(read_json_limited(request))
        except PayloadTooLargeError:
            return
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        assert out == json.loads(raw.decode("utf-8"))


class TestWriteFieldToPathOracle:
    @given(pair=chunked_bytes(st.binary(min_size=0, max_size=2048)))
    @settings(
        max_examples=60,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_streams_roundtrip_and_counts(self, pair, tmp_path):
        payload, chunks = pair
        dest = tmp_path / str(uuid.uuid4())
        field = _FakeField(chunks)
        written = asyncio.run(write_field_to_path(field, dest, len(payload) + 8))
        assert written == len(payload)
        assert dest.read_bytes() == payload

    @given(
        pair=chunked_bytes(st.binary(min_size=1, max_size=512)),
        data=st.data(),
    )
    @settings(
        max_examples=80,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_cap_breach_unlinks_partial(self, pair, data, tmp_path):
        payload, chunks = pair
        cap = data.draw(st.integers(min_value=0, max_value=len(payload) - 1))
        dest = tmp_path / str(uuid.uuid4())
        field = _FakeField(chunks)
        with pytest.raises(PayloadTooLargeError):
            asyncio.run(write_field_to_path(field, dest, cap))
        assert not dest.exists()


class TestUploadLimits:
    _EXPECTED_KEYS = frozenset(
        {
            "map_offline_mbtiles",
            "database_restore",
            "docs_zip",
            "page_node_file",
            "message_import",
            "translation_pack",
            "repository_upload",
            "audio_upload",
        }
    )

    def test_keys_match_documented_endpoints(self):
        assert set(UPLOAD_LIMITS) == self._EXPECTED_KEYS

    def test_all_limits_positive_ints(self):
        for name, limit in UPLOAD_LIMITS.items():
            assert isinstance(limit, int), name
            assert not isinstance(limit, bool), name
            assert limit > 0, name

    def test_default_caps_positive(self):
        assert DEFAULT_JSON_BODY_BYTES > 0
        assert DEFAULT_TEXT_FIELD_BYTES > 0


_PATH_JAIL_STATUS = {
    "required": 400,
    "invalid": 400,
    "absolute": 400,
    "escape": 403,
    "reserved": 403,
    "forbidden": 403,
    "not_found": 404,
}

_SAFE_MESSAGE = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    max_size=200,
)


def _exception_strategy():
    return st.one_of(
        st.builds(
            PathJailError,
            _SAFE_MESSAGE,
            reason=st.sampled_from(sorted(PathJailError.REASONS)),
        ),
        st.builds(FileNotFoundError, _SAFE_MESSAGE),
        st.builds(PermissionError, _SAFE_MESSAGE),
        st.builds(ValueError, _SAFE_MESSAGE),
        st.builds(OSError, _SAFE_MESSAGE),
        st.builds(Exception, _SAFE_MESSAGE),
    )


def _expected_status(exc, fallback_status):
    # Mirrors the dispatch order in http_error_from_exception.
    if isinstance(exc, PathJailError):
        return _PATH_JAIL_STATUS.get(exc.reason, 400)
    if isinstance(exc, FileNotFoundError):
        return 404
    if isinstance(exc, PermissionError):
        return 403
    if isinstance(exc, ValueError):
        return 400
    if isinstance(exc, OSError):
        return 500
    return fallback_status


def _expected_message(exc):
    if isinstance(exc, PathJailError):
        return str(exc)
    if isinstance(exc, FileNotFoundError):
        return "Not found"
    if isinstance(exc, PermissionError):
        return "Not allowed"
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, OSError):
        return "Internal server error"
    return "Request failed"


class TestHttpErrorFromExceptionOracle:
    @given(reason=st.sampled_from(sorted(PathJailError.REASONS)))
    @settings(max_examples=30, deadline=None)
    def test_jail_reason_status_stays_in_set(self, reason):
        resp = http_error_from_exception(PathJailError("jailed", reason=reason))
        assert resp.status in {400, 403, 404}
        assert resp.status == _PATH_JAIL_STATUS[reason]

    @given(exc=_exception_strategy(), fallback=st.integers(400, 599))
    @settings(max_examples=200, deadline=None)
    def test_status_and_message_oracle(self, exc, fallback):
        resp = http_error_from_exception(exc, fallback_status=fallback)
        assert resp.status == _expected_status(exc, fallback)
        body = json.loads(resp.text)
        assert body["error"] == _expected_message(exc)

    @given(message=_SAFE_MESSAGE)
    @settings(max_examples=80, deadline=None)
    def test_value_error_message_passes_through(self, message):
        resp = http_error_from_exception(ValueError(message))
        assert resp.status == 400
        assert json.loads(resp.text)["error"] == message


class TestErrorLeakOracle:
    @given(
        exc_kind=st.sampled_from([OSError, FileNotFoundError, PermissionError]),
        marker=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
            min_size=4,
            max_size=16,
        ),
    )
    @settings(
        max_examples=60,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_oserror_family_never_leaks_paths(self, exc_kind, marker, tmp_path):
        secret_dir = tmp_path / str(uuid.uuid4())
        secret_dir.mkdir()
        secret = str(secret_dir / f"secret-{marker}.bin")
        exc = exc_kind(f"cannot open {secret}")
        exc.filename = secret
        resp = http_error_from_exception(exc)
        assert secret not in resp.text
        body = json.loads(resp.text)
        assert secret not in body["error"]
        assert f"secret-{marker}.bin" not in body["error"]

    @given(
        marker=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
            min_size=4,
            max_size=16,
        )
    )
    @settings(
        max_examples=60,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_value_error_message_passes_through_verbatim(self, marker, tmp_path):
        # ValueError messages are user-facing by convention and DO echo.
        path_hint = str(tmp_path / str(uuid.uuid4()) / f"hint-{marker}.txt")
        resp = http_error_from_exception(ValueError(f"bad value at {path_hint}"))
        body = json.loads(resp.text)
        assert body["error"] == f"bad value at {path_hint}"


class TestErrorResponseShape:
    def test_extra_and_key_shape_the_payload(self):
        resp = http_error_from_exception(
            ValueError("nope"),
            key="detail",
            extra={"status": "error", "code": 7},
        )
        body = json.loads(resp.text)
        assert body == {"status": "error", "code": 7, "detail": "nope"}
        assert "error" not in body

    def test_extra_merges_on_generic_errors(self):
        resp = http_error_from_exception(
            OSError("internal path"),
            extra={"status": "error"},
        )
        body = json.loads(resp.text)
        assert body == {"status": "error", "error": "Internal server error"}

    def test_extra_none_and_default_key(self):
        resp = http_error_from_exception(ValueError("x"))
        assert json.loads(resp.text) == {"error": "x"}
