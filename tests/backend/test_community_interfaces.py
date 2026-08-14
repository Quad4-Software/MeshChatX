# SPDX-License-Identifier: 0BSD

import json
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.community_interfaces import CommunityInterfacesManager
from meshchatx.src.backend.rnstatus_handler import RNStatusHandler


@pytest.mark.asyncio
async def test_community_interfaces_manager_no_probe():
    manager = CommunityInterfacesManager()
    interfaces = await manager.get_interfaces()
    assert len(interfaces) >= 1
    for iface in interfaces:
        assert "name" in iface and "target_host" in iface and "target_port" in iface
        assert iface.get("online") is None
        assert iface.get("last_check") == 0


@pytest.mark.asyncio
async def test_rnstatus_integration_simulated():
    mock_reticulum = MagicMock()
    mock_reticulum.get_interface_stats.return_value = {
        "interfaces": [
            {
                "name": "noDNS1",
                "status": True,
                "rxb": 100,
                "txb": 200,
            },
            {
                "name": "Remote TCP relay",
                "status": False,
                "rxb": 0,
                "txb": 0,
            },
        ],
    }

    handler = RNStatusHandler(mock_reticulum)
    status = handler.get_status()

    assert len(status["interfaces"]) == 2
    assert status["interfaces"][0]["name"] == "noDNS1"
    assert status["interfaces"][0]["status"] == "Up"
    assert status["interfaces"][1]["name"] == "Remote TCP relay"
    assert status["interfaces"][1]["status"] == "Down"


@pytest.mark.asyncio
async def test_community_interfaces_static_list():
    manager = CommunityInterfacesManager()
    ifaces1 = await manager.get_interfaces()
    ifaces2 = await manager.get_interfaces()
    assert ifaces1 == ifaces2
    assert all(iface.get("online") is None for iface in ifaces1)


@pytest.mark.asyncio
async def test_community_interfaces_public_override_beats_bundled(tmp_path):
    public = tmp_path / "public.json"
    public.write_text(
        json.dumps(
            {
                "interfaces": [
                    {
                        "name": "FromPublic",
                        "type": "TCPClientInterface",
                        "target_host": "10.0.0.2",
                        "target_port": 4242,
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    manager = CommunityInterfacesManager(public_override_path=str(public))
    ifaces = await manager.get_interfaces()
    assert len(ifaces) == 1
    assert ifaces[0]["name"] == "FromPublic"
