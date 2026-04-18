# SPDX-License-Identifier: 0BSD

"""Tests for the Reticulum Config Editor backend endpoints and helpers."""

import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat


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


def _make_request(json_body=None):
    request = MagicMock()

    async def _json():
        if json_body is None:
            raise ValueError("no json body")
        return json_body

    request.json = _json
    return request


def test_default_reticulum_config_text_contains_required_sections():
    text = ReticulumMeshChat._default_reticulum_config_text()
    assert "[reticulum]" in text
    assert "[interfaces]" in text
    assert "[logging]" in text
    assert "AutoInterface" in text


def test_default_config_text_is_idempotent_across_calls():
    a = ReticulumMeshChat._default_reticulum_config_text()
    b = ReticulumMeshChat._default_reticulum_config_text()
    assert a == b


@pytest.mark.asyncio
async def test_endpoint_get_returns_current_config(app_instance):
    handler = _find_handler(app_instance, "GET", "/api/v1/reticulum/config/raw")

    response = await handler(_make_request())
    assert response.status == 200
    payload = json.loads(response.body)
    assert "[reticulum]" in payload["content"]
    assert "[interfaces]" in payload["content"]
    assert payload["path"].endswith("config")


@pytest.mark.asyncio
async def test_endpoint_put_writes_valid_config(app_instance):
    handler = _find_handler(app_instance, "PUT", "/api/v1/reticulum/config/raw")

    new_content = (
        "[reticulum]\n  enable_transport = False\n\n"
        "[interfaces]\n  [[Default Interface]]\n    type = AutoInterface\n"
    )
    response = await handler(_make_request({"content": new_content}))
    assert response.status == 200
    payload = json.loads(response.body)
    assert payload["path"].endswith("config")

    with open(app_instance._reticulum_config_file_path()) as f:
        on_disk = f.read()
    assert on_disk == new_content


@pytest.mark.asyncio
async def test_endpoint_put_rejects_missing_sections(app_instance):
    handler = _find_handler(app_instance, "PUT", "/api/v1/reticulum/config/raw")

    response = await handler(_make_request({"content": "garbage"}))
    assert response.status == 400
    payload = json.loads(response.body)
    assert "[reticulum]" in payload["error"]


@pytest.mark.asyncio
async def test_endpoint_put_rejects_non_string_content(app_instance):
    handler = _find_handler(app_instance, "PUT", "/api/v1/reticulum/config/raw")

    response = await handler(_make_request({"content": 123}))
    assert response.status == 400


@pytest.mark.asyncio
async def test_endpoint_put_rejects_invalid_json(app_instance):
    handler = _find_handler(app_instance, "PUT", "/api/v1/reticulum/config/raw")

    response = await handler(_make_request())
    assert response.status == 400


@pytest.mark.asyncio
async def test_endpoint_reset_restores_defaults(app_instance):
    reset_handler = _find_handler(
        app_instance,
        "POST",
        "/api/v1/reticulum/config/reset",
    )

    config_path = app_instance._reticulum_config_file_path()
    with open(config_path, "w") as f:
        f.write(
            "[reticulum]\n  enable_transport = True\n\n"
            "[interfaces]\n  [[X]]\n    type = AutoInterface\n",
        )

    response = await reset_handler(_make_request())
    assert response.status == 200
    payload = json.loads(response.body)
    assert payload["content"] == ReticulumMeshChat._default_reticulum_config_text()

    with open(config_path) as f:
        on_disk = f.read()
    assert on_disk == ReticulumMeshChat._default_reticulum_config_text()


@pytest.mark.asyncio
async def test_endpoint_get_recreates_config_if_missing(app_instance):
    config_path = app_instance._reticulum_config_file_path()
    os.remove(config_path)
    assert not os.path.exists(config_path)

    handler = _find_handler(app_instance, "GET", "/api/v1/reticulum/config/raw")
    response = await handler(_make_request())
    assert response.status == 200
    assert os.path.exists(config_path)
