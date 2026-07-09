# SPDX-License-Identifier: 0BSD

import json
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.favourites_layout import (
    MAX_HASH_LEN,
    MAX_HASHES_PER_SECTION,
    MAX_LAYOUT_JSON_BYTES,
    MAX_SECTION_ID_LEN,
    MAX_SECTION_NAME_LEN,
    MAX_SECTIONS,
    MAX_TOTAL_HASHES,
    layout_payload_too_large,
    normalize_favourites_layout,
)


def test_normalize_favourites_layout_rejects_invalid():
    assert normalize_favourites_layout(None) is None
    assert normalize_favourites_layout({}) is None
    assert normalize_favourites_layout({"sections": []}) is None
    assert normalize_favourites_layout([]) is None
    assert normalize_favourites_layout("nope") is None


def test_normalize_favourites_layout_sanitizes():
    layout = normalize_favourites_layout(
        {
            "sections": [
                {"id": "default", "name": "Favourites", "collapsed": False},
                {"id": "custom", "name": "Custom", "collapsed": True},
                {"id": "default", "name": "dup"},
            ],
            "sectionOrder": ["custom", "missing"],
            "favouritesBySection": {
                "custom": ["abc", 12],
                "orphan": ["x"],
            },
        }
    )
    assert layout is not None
    assert [s["id"] for s in layout["sections"]] == ["default", "custom"]
    assert layout["sectionOrder"] == ["custom", "default"]
    assert layout["favouritesBySection"]["custom"] == ["abc"]
    assert layout["favouritesBySection"]["default"] == []
    assert "orphan" not in layout["favouritesBySection"]


def test_normalize_rejects_prototype_pollution_keys():
    layout = normalize_favourites_layout(
        {
            "sections": [
                {"id": "__proto__", "name": "bad"},
                {"id": "constructor", "name": "bad"},
                {"id": "ok", "name": "Good"},
            ],
            "sectionOrder": ["__proto__", "ok"],
            "favouritesBySection": {
                "__proto__": ["a" * 32],
                "ok": ["b" * 32],
            },
        }
    )
    assert layout is not None
    assert [s["id"] for s in layout["sections"]] == ["ok"]
    assert "__proto__" not in layout["favouritesBySection"]
    assert layout["favouritesBySection"]["ok"] == ["b" * 32]


def test_normalize_enforces_caps():
    sections = [
        {"id": f"s{i}", "name": "x" * (MAX_SECTION_NAME_LEN + 20)}
        for i in range(MAX_SECTIONS + 10)
    ]
    hashes = [f"{i:032x}" for i in range(MAX_HASHES_PER_SECTION + 50)]
    layout = normalize_favourites_layout(
        {
            "sections": sections,
            "sectionOrder": [s["id"] for s in sections],
            "favouritesBySection": {sections[0]["id"]: hashes},
        }
    )
    assert layout is not None
    assert len(layout["sections"]) == MAX_SECTIONS
    assert len(layout["sections"][0]["name"]) == MAX_SECTION_NAME_LEN
    assert (
        len(layout["favouritesBySection"][sections[0]["id"]]) == MAX_HASHES_PER_SECTION
    )


def test_normalize_enforces_total_hash_cap():
    sections = [{"id": f"s{i}", "name": f"S{i}"} for i in range(4)]
    per = (MAX_TOTAL_HASHES // 4) + 10
    layout = normalize_favourites_layout(
        {
            "sections": sections,
            "sectionOrder": [s["id"] for s in sections],
            "favouritesBySection": {
                s["id"]: [f"{s['id']}{i:028x}"[:32] for i in range(per)]
                for s in sections
            },
        }
    )
    assert layout is not None
    total = sum(len(v) for v in layout["favouritesBySection"].values())
    assert total <= MAX_TOTAL_HASHES


def test_normalize_dedupes_hashes_and_trims():
    layout = normalize_favourites_layout(
        {
            "sections": [{"id": "  default  ", "name": "  Name  "}],
            "sectionOrder": ["  default  "],
            "favouritesBySection": {
                "default": ["  abc  ", "abc", "x" * (MAX_HASH_LEN + 5), ""],
            },
        }
    )
    assert layout["sections"][0]["id"] == "default"
    assert layout["sections"][0]["name"] == "  Name  "[:MAX_SECTION_NAME_LEN]
    assert layout["favouritesBySection"]["default"] == ["abc"]


def test_layout_payload_too_large():
    assert layout_payload_too_large(MAX_LAYOUT_JSON_BYTES + 1) is True
    assert layout_payload_too_large(MAX_LAYOUT_JSON_BYTES) is False
    assert layout_payload_too_large("nope") is False


@given(
    payload=st.one_of(
        st.none(),
        st.booleans(),
        st.integers(),
        st.text(),
        st.binary(),
        st.lists(st.integers()),
    )
)
@settings(max_examples=80, suppress_health_check=[HealthCheck.too_slow])
def test_normalize_never_throws_on_garbage(payload):
    assert normalize_favourites_layout(payload) is None or isinstance(
        normalize_favourites_layout(payload),
        dict,
    )


@given(
    section_ids=st.lists(
        st.text(min_size=1, max_size=MAX_SECTION_ID_LEN + 8),
        min_size=0,
        max_size=MAX_SECTIONS + 5,
    ),
    names=st.lists(
        st.text(max_size=MAX_SECTION_NAME_LEN + 20), max_size=MAX_SECTIONS + 5
    ),
    hashes=st.lists(st.text(max_size=MAX_HASH_LEN + 8), max_size=40),
)
@settings(
    max_examples=60,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
def test_normalize_fuzz_structured(section_ids, names, hashes):
    sections = []
    for i, sid in enumerate(section_ids):
        sections.append(
            {
                "id": sid,
                "name": names[i] if i < len(names) else 123,
                "collapsed": i % 2 == 0,
            }
        )
    raw = {
        "sections": sections,
        "sectionOrder": section_ids[::-1] + ["missing"],
        "favouritesBySection": {sid: hashes for sid in section_ids[:3]},
    }
    out = normalize_favourites_layout(raw)
    if out is None:
        return
    assert len(out["sections"]) <= MAX_SECTIONS
    assert len(out["sectionOrder"]) == len(out["sections"])
    assert set(out["sectionOrder"]) == {s["id"] for s in out["sections"]}
    total = 0
    for sid, values in out["favouritesBySection"].items():
        assert sid in {s["id"] for s in out["sections"]}
        assert len(values) <= MAX_HASHES_PER_SECTION
        assert len(values) == len(set(values))
        total += len(values)
    assert total <= MAX_TOTAL_HASHES


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns_minimal():
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


@pytest.mark.asyncio
async def test_favourites_layout_get_put(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        get_handler = None
        put_handler = None
        for route in app.get_routes():
            if route.path == "/api/v1/favourites/layout" and route.method == "GET":
                get_handler = route.handler
            if route.path == "/api/v1/favourites/layout" and route.method == "PUT":
                put_handler = route.handler
        assert get_handler is not None
        assert put_handler is not None

        empty = await get_handler(MagicMock())
        assert json.loads(empty.body)["layout"] is None

        layout = {
            "sections": [
                {"id": "default", "name": "Favourites", "collapsed": False},
                {"id": "custom", "name": "Custom", "collapsed": False},
            ],
            "sectionOrder": ["default", "custom"],
            "favouritesBySection": {
                "default": [],
                "custom": ["a" * 32],
            },
        }
        body = json.dumps({"layout": layout}).encode("utf-8")
        request = MagicMock()
        request.content_length = len(body)
        request.read = AsyncMock(return_value=body)
        put_response = await put_handler(request)
        put_data = json.loads(put_response.body)
        assert put_data["layout"]["favouritesBySection"]["custom"] == ["a" * 32]

        get_response = await get_handler(MagicMock())
        get_data = json.loads(get_response.body)
        assert get_data["layout"]["sectionOrder"] == ["default", "custom"]

        bad_body = json.dumps({"layout": {"sections": []}}).encode("utf-8")
        bad = MagicMock()
        bad.content_length = len(bad_body)
        bad.read = AsyncMock(return_value=bad_body)
        bad_response = await put_handler(bad)
        assert bad_response.status == 400


@pytest.mark.asyncio
async def test_favourites_layout_put_rejects_oversized_body(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        put_handler = None
        for route in app.get_routes():
            if route.path == "/api/v1/favourites/layout" and route.method == "PUT":
                put_handler = route.handler
                break
        assert put_handler is not None

        request = MagicMock()
        request.content_length = MAX_LAYOUT_JSON_BYTES + 1
        request.read = AsyncMock(return_value=b"{}")
        response = await put_handler(request)
        assert response.status == 413
