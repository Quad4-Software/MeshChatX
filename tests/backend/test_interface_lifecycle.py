# SPDX-License-Identifier: 0BSD

"""RNS 1.5.5 runtime interface lifecycle endpoints (attach/detach/reload)."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
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
def app(temp_dir):
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.generate_ssl_certificate"),
    ):
        reticulum = mock_rns.return_value
        reticulum.configpath = os.path.join(temp_dir, "config")
        reticulum.is_connected_to_shared_instance = False
        identity = MagicMock(spec=RNS.Identity)
        identity.hash = b"test_hash_32_bytes_long_01234567"
        identity.hexhash = identity.hash.hex()
        identity.get_private_key.return_value = b"test_private_key"
        instance = ReticulumMeshChat(
            identity=identity,
            storage_dir=temp_dir,
            reticulum_config_dir=os.path.join(temp_dir, ".reticulum"),
        )
        instance.reticulum.config = {
            "reticulum": {},
            "interfaces": {
                "Test Iface": {
                    "type": "UDPInterface",
                    "interface_enabled": "True",
                },
            },
        }
        # Deterministic running set for _running_interface_names.
        RNS.Transport.interfaces = []
        yield instance


def _find_handler(app_instance, method, path):
    for route in app_instance.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    raise AssertionError(f"Handler not found: {method} {path}")


class _Request:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


def _body(response):
    return json.loads(response.body)


@pytest.mark.asyncio
async def test_attach_returns_applied_live(app):
    app.reticulum.attach_interface = MagicMock(return_value=True)
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/attach")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 200, _body(response)
    assert _body(response)["applied_live"] is True
    app.reticulum.attach_interface.assert_called_once_with("Test Iface")


@pytest.mark.asyncio
async def test_detach_returns_applied_live(app):
    app.reticulum.detach_interface = MagicMock(return_value=True)
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/detach")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 200, _body(response)
    assert _body(response)["applied_live"] is True
    app.reticulum.detach_interface.assert_called_once_with("Test Iface")


@pytest.mark.asyncio
async def test_reload_returns_applied_live(app):
    app.reticulum.reload_interface = MagicMock(return_value=True)
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/reload")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 200, _body(response)
    assert _body(response)["applied_live"] is True
    app.reticulum.reload_interface.assert_called_once_with("Test Iface")


@pytest.mark.asyncio
async def test_attach_requires_name(app):
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/attach")
    for payload in ({}, {"name": ""}, {"name": "   "}, {"name": None}, {"name": 5}):
        response = await handler(_Request(payload))
        assert response.status == 422, payload


@pytest.mark.asyncio
async def test_attach_unknown_interface_is_404(app):
    app.reticulum.attach_interface = MagicMock(return_value=True)
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/attach")
    response = await handler(_Request({"name": "Missing Iface"}))
    assert response.status == 404, _body(response)
    app.reticulum.attach_interface.assert_not_called()


@pytest.mark.asyncio
async def test_detach_does_not_require_config_entry(app):
    # Spawned runtime interfaces (discovery, backbone clients) have no
    # config section but can still be detached.
    app.reticulum.detach_interface = MagicMock(return_value=True)
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/detach")
    response = await handler(_Request({"name": "Spawned Peer"}))
    assert response.status == 200, _body(response)


@pytest.mark.asyncio
async def test_refused_maps_to_422(app):
    app.reticulum.attach_interface = MagicMock(return_value=False)
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/attach")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 422, _body(response)


@pytest.mark.asyncio
async def test_detach_not_attached_maps_to_422(app):
    app.reticulum.detach_interface = MagicMock(return_value=None)
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/detach")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 422, _body(response)
    assert "not currently attached" in _body(response)["error"]


@pytest.mark.asyncio
async def test_unavailable_when_reticulum_missing(app):
    app.reticulum = None
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/detach")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 409, _body(response)


@pytest.mark.asyncio
async def test_unsupported_on_old_rns(app):
    app.reticulum = MagicMock(spec=["config", "configpath"])
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/detach")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 409, _body(response)


@pytest.mark.asyncio
async def test_operation_exception_is_500(app):
    app.reticulum.detach_interface = MagicMock(side_effect=RuntimeError("boom"))
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/detach")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 500, _body(response)


@pytest.mark.asyncio
async def test_operation_timeout_is_504(app, monkeypatch):
    app.reticulum.detach_interface = MagicMock(side_effect=lambda name: time.sleep(2))
    monkeypatch.setattr(
        "meshchatx.src.backend.http.routes.interfaces._INTERFACE_MANAGE_TIMEOUT_S",
        0.05,
    )
    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/detach")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 504, _body(response)


@pytest.mark.asyncio
async def test_enable_attaches_live(app):
    app._sync_interfaces_from_disk = lambda: None
    app._get_interfaces_snapshot = lambda: dict(app.reticulum.config["interfaces"])
    app._write_reticulum_config = lambda **kw: True
    app.reticulum.config["interfaces"]["Test Iface"]["interface_enabled"] = "False"
    app.reticulum.attach_interface = MagicMock(return_value=True)

    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/enable")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 200, _body(response)
    assert _body(response)["applied_live"] is True
    app.reticulum.attach_interface.assert_called_once_with("Test Iface")


@pytest.mark.asyncio
async def test_enable_skips_attach_when_already_running(app):
    _mark_running("Test Iface")
    app._sync_interfaces_from_disk = lambda: None
    app._get_interfaces_snapshot = lambda: dict(app.reticulum.config["interfaces"])
    app._write_reticulum_config = lambda **kw: True
    app.reticulum.config["interfaces"]["Test Iface"]["interface_enabled"] = "False"
    app.reticulum.attach_interface = MagicMock(return_value=False)

    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/enable")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 200, _body(response)
    assert _body(response)["applied_live"] is True
    app.reticulum.attach_interface.assert_not_called()


@pytest.mark.asyncio
async def test_disable_skips_detach_when_not_running(app):
    app._sync_interfaces_from_disk = lambda: None
    app._get_interfaces_snapshot = lambda: dict(app.reticulum.config["interfaces"])
    app._write_reticulum_config = lambda **kw: True
    app.reticulum.detach_interface = MagicMock(return_value=True)

    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/disable")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 200, _body(response)
    assert _body(response)["applied_live"] is True
    app.reticulum.detach_interface.assert_not_called()


@pytest.mark.asyncio
async def test_enable_without_live_apply_marks_restart(app):
    app._sync_interfaces_from_disk = lambda: None
    app._get_interfaces_snapshot = lambda: dict(app.reticulum.config["interfaces"])
    app._write_reticulum_config = lambda **kw: True
    app.reticulum.config["interfaces"]["Test Iface"]["interface_enabled"] = "False"
    app.reticulum.attach_interface = MagicMock(return_value=False)

    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/enable")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 200, _body(response)
    assert _body(response)["applied_live"] is False


def _mark_running(name):
    iface = MagicMock()
    iface.name = name
    RNS.Transport.interfaces = [iface]


@pytest.mark.asyncio
async def test_disable_detaches_live(app):
    _mark_running("Test Iface")
    app._sync_interfaces_from_disk = lambda: None
    app._get_interfaces_snapshot = lambda: dict(app.reticulum.config["interfaces"])
    app._write_reticulum_config = lambda **kw: True
    app.reticulum.detach_interface = MagicMock(return_value=True)

    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/disable")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 200, _body(response)
    assert _body(response)["applied_live"] is True
    app.reticulum.detach_interface.assert_called_once_with("Test Iface")


@pytest.mark.asyncio
async def test_delete_detaches_running_interface(app):
    _mark_running("Test Iface")
    app._sync_interfaces_from_disk = lambda: None
    app._get_interfaces_snapshot = lambda: dict(app.reticulum.config["interfaces"])
    app._write_reticulum_config = lambda **kw: True
    app.reticulum.detach_interface = MagicMock(return_value=True)

    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/delete")
    response = await handler(_Request({"name": "Test Iface"}))
    assert response.status == 200, _body(response)
    assert "Test Iface" not in app.reticulum.config["interfaces"]
    app.reticulum.detach_interface.assert_called_once_with("Test Iface")


@pytest.mark.asyncio
async def test_bitrates_reload_uses_per_interface_reload(app):
    app._get_interfaces_snapshot = lambda: dict(app.reticulum.config["interfaces"])
    app._write_reticulum_config = lambda **kw: True
    app.reticulum.reload_interface = MagicMock(return_value=True)
    app.reload_reticulum = MagicMock(return_value=asyncio.sleep(0, result=True))

    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/bitrates")
    response = await handler(
        _Request({"bitrates": {"Test Iface": 9600}, "reload": True})
    )
    body = _body(response)
    assert response.status == 200, body
    assert body["reloaded_live"] is True
    assert body["reloaded"] is False
    app.reticulum.reload_interface.assert_called_once_with("Test Iface")
    app.reload_reticulum.assert_not_called()


@pytest.mark.asyncio
async def test_bitrates_falls_back_to_full_reload(app):
    app._get_interfaces_snapshot = lambda: dict(app.reticulum.config["interfaces"])
    app._write_reticulum_config = lambda **kw: True
    app.reticulum.reload_interface = MagicMock(return_value=False)

    async def _fake_reload():
        return True

    app.reload_reticulum = _fake_reload

    handler = _find_handler(app, "POST", "/api/v1/reticulum/interfaces/bitrates")
    response = await handler(
        _Request({"bitrates": {"Test Iface": 9600}, "reload": True})
    )
    body = _body(response)
    assert response.status == 200, body
    assert body["reloaded"] is True
    assert body["reloaded_live"] is False
