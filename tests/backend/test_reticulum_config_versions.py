# SPDX-License-Identifier: 0BSD

"""Tests for Reticulum config snapshot storage and the version endpoints."""

import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend import reticulum_config_versions as rcv
from tests.backend.http_request_stubs import JsonContent, RawContent


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


@pytest.fixture
def app_instance(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=os.path.join(temp_dir, ".reticulum"),
        )
        yield instance


def _find_handler(app, method, path):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    raise AssertionError(f"Handler not found: {method} {path}")


def _make_request(version_id=None, json_body=None):
    request = MagicMock()

    async def _json():
        if json_body is None:
            raise ValueError("no json body")
        return json_body

    request.json = _json
    request.content = (
        JsonContent(json_body) if json_body is not None else RawContent([])
    )
    request.match_info = {"version_id": version_id} if version_id else {}
    return request


def _write_config(app, content):
    config_path = app._reticulum_config_file_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)
    return config_path


VALID_CONFIG = (
    "[reticulum]\n  enable_transport = False\n\n"
    "[interfaces]\n  [[Default Interface]]\n    type = AutoInterface\n"
)


# ---------------------------------------------------------------------------
# store helpers


def test_snapshot_config_creates_listed_version(temp_dir):
    config_path = os.path.join(temp_dir, "config")
    _write = VALID_CONFIG
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(_write)

    meta = rcv.snapshot_config(temp_dir, config_path, label="before save")

    assert meta is not None
    assert meta["label"] == "before save"
    assert meta["id"]
    assert "content" not in meta

    versions = rcv.list_versions(temp_dir)
    assert [v["id"] for v in versions] == [meta["id"]]
    assert versions[0]["size"] == len(_write.encode("utf-8"))

    record = rcv.get_version(temp_dir, meta["id"])
    assert record["content"] == _write


def test_snapshot_config_returns_none_without_config(temp_dir):
    missing = os.path.join(temp_dir, "config")
    assert rcv.snapshot_config(temp_dir, missing) is None
    assert rcv.list_versions(temp_dir) == []


def test_list_versions_skips_malformed_files(temp_dir):
    config_path = os.path.join(temp_dir, "config")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(VALID_CONFIG)
    rcv.snapshot_config(temp_dir, config_path, label="good")

    directory = rcv.versions_dir(temp_dir)
    with open(os.path.join(directory, "broken.json"), "w") as f:
        f.write("{not json")
    with open(os.path.join(directory, "20200101T000000-deadbeef.json"), "w") as f:
        json.dump({"id": "x", "content": 42}, f)

    versions = rcv.list_versions(temp_dir)
    assert len(versions) == 1
    assert versions[0]["label"] == "good"


def test_get_version_rejects_bad_ids(temp_dir):
    for bad in ("../x", "..", "a/b", "", "notanid", "20200101T000000-zzzzzzzz"):
        assert rcv.get_version(temp_dir, bad) is None


def test_prune_versions_keeps_newest(temp_dir):
    config_path = os.path.join(temp_dir, "config")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(VALID_CONFIG)
    for i in range(5):
        rcv.snapshot_config(temp_dir, config_path, label=f"s{i}")

    rcv.prune_versions(temp_dir, keep=2)
    versions = rcv.list_versions(temp_dir)
    assert len(versions) == 2
    # Newest first ordering is by created_at which ties within a second,
    # so just assert the count and that records are still readable.
    assert all(rcv.get_version(temp_dir, v["id"]) for v in versions)


# ---------------------------------------------------------------------------
# endpoints


@pytest.mark.asyncio
async def test_versions_list_endpoint_empty(app_instance):
    handler = _find_handler(app_instance, "GET", "/api/v1/reticulum/config/versions")
    response = await handler(_make_request())
    assert response.status == 200
    assert json.loads(response.body)["versions"] == []


@pytest.mark.asyncio
async def test_put_snapshots_previous_config(app_instance):
    _write_config(app_instance, VALID_CONFIG)
    put_handler = _find_handler(app_instance, "PUT", "/api/v1/reticulum/config/raw")

    new_content = (
        "[reticulum]\n  enable_transport = True\n\n"
        "[interfaces]\n  [[X]]\n    type = AutoInterface\n"
    )
    response = await put_handler(_make_request(json_body={"content": new_content}))
    assert response.status == 200

    config_dir = app_instance._normalize_reticulum_config_dir(
        app_instance.reticulum_config_dir,
    )
    versions = rcv.list_versions(config_dir)
    assert len(versions) == 1
    record = rcv.get_version(config_dir, versions[0]["id"])
    assert record["content"] == VALID_CONFIG
    assert record["label"] == "before save"


@pytest.mark.asyncio
async def test_restore_endpoint_roundtrip(app_instance):
    config_path = _write_config(app_instance, VALID_CONFIG)
    config_dir = app_instance._normalize_reticulum_config_dir(
        app_instance.reticulum_config_dir,
    )
    meta = rcv.snapshot_config(config_dir, config_path, label="checkpoint")

    newer = (
        "[reticulum]\n  enable_transport = True\n\n"
        "[interfaces]\n  [[Y]]\n    type = AutoInterface\n"
    )
    _write_config(app_instance, newer)

    handler = _find_handler(
        app_instance,
        "POST",
        "/api/v1/reticulum/config/versions/{version_id}/restore",
    )
    response = await handler(_make_request(meta["id"]))
    assert response.status == 200
    payload = json.loads(response.body)
    assert payload["content"] == VALID_CONFIG

    with open(config_path, encoding="utf-8") as f:
        assert f.read() == VALID_CONFIG

    # The pre-restore state was snapshotted too.
    labels = {v["label"] for v in rcv.list_versions(config_dir)}
    assert "before restore" in labels


@pytest.mark.asyncio
async def test_restore_unknown_version_404(app_instance):
    handler = _find_handler(
        app_instance,
        "POST",
        "/api/v1/reticulum/config/versions/{version_id}/restore",
    )
    response = await handler(_make_request("20200101T000000-deadbeef"))
    assert response.status == 404


@pytest.mark.asyncio
async def test_restore_rejects_bad_version_id(app_instance):
    handler = _find_handler(
        app_instance,
        "POST",
        "/api/v1/reticulum/config/versions/{version_id}/restore",
    )
    response = await handler(_make_request("../escape"))
    assert response.status == 404


@pytest.mark.asyncio
async def test_get_version_endpoint_returns_content(app_instance):
    config_path = _write_config(app_instance, VALID_CONFIG)
    config_dir = app_instance._normalize_reticulum_config_dir(
        app_instance.reticulum_config_dir,
    )
    meta = rcv.snapshot_config(config_dir, config_path, label="x")

    handler = _find_handler(
        app_instance,
        "GET",
        "/api/v1/reticulum/config/versions/{version_id}",
    )
    response = await handler(_make_request(meta["id"]))
    assert response.status == 200
    assert json.loads(response.body)["version"]["content"] == VALID_CONFIG


@pytest.mark.asyncio
async def test_restore_rejects_snapshot_missing_sections(app_instance):
    config_dir = app_instance._normalize_reticulum_config_dir(
        app_instance.reticulum_config_dir,
    )
    os.makedirs(rcv.versions_dir(config_dir), exist_ok=True)
    version_id = "20200101T000000-deadbeef"
    with open(
        os.path.join(rcv.versions_dir(config_dir), f"{version_id}.json"),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "id": version_id,
                "created_at": "2020-01-01T00:00:00+00:00",
                "label": "bad",
                "content": "garbage without sections",
            },
            f,
        )

    handler = _find_handler(
        app_instance,
        "POST",
        "/api/v1/reticulum/config/versions/{version_id}/restore",
    )
    response = await handler(_make_request(version_id))
    assert response.status == 400
