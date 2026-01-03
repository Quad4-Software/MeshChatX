import pytest
import asyncio
from unittest.mock import MagicMock, patch
from meshchatx.src.backend.community_interfaces import CommunityInterfacesManager
from meshchatx.src.backend.rnstatus_handler import RNStatusHandler


@pytest.mark.asyncio
async def test_community_interfaces_manager_health_check():
    manager = CommunityInterfacesManager()

    # Mock check_health to always return True for some, False for others
    with patch.object(
        CommunityInterfacesManager,
        "check_health",
        side_effect=[True, False, True, False, True, False, True],
    ):
        interfaces = await manager.get_interfaces()

        assert len(interfaces) == 7
        # First one should be online because we sort by online status
        assert interfaces[0]["online"] is True
        # Check that we have both online and offline
        online_count = sum(1 for iface in interfaces if iface["online"])
        assert online_count == 4


@pytest.mark.asyncio
async def test_rnstatus_integration_simulated():
    # Simulate how rnstatus would see these interfaces if they were added
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
                "name": "Quad4 TCP Node 1",
                "status": False,
                "rxb": 0,
                "txb": 0,
            },
        ]
    }

    handler = RNStatusHandler(mock_reticulum)
    status = handler.get_status()

    assert len(status["interfaces"]) == 2
    assert status["interfaces"][0]["name"] == "noDNS1"
    assert status["interfaces"][0]["status"] == "Up"
    assert status["interfaces"][1]["name"] == "Quad4 TCP Node 1"
    assert status["interfaces"][1]["status"] == "Down"


@pytest.mark.asyncio
async def test_community_interfaces_dynamic_update():
    manager = CommunityInterfacesManager()

    # Mock check_health to return different values over time
    with patch.object(CommunityInterfacesManager, "check_health") as mock_check:
        # First check: all online
        mock_check.return_value = True
        ifaces1 = await manager.get_interfaces()
        assert all(iface["online"] for iface in ifaces1)

        # Force update by clearing last_check and mock all offline
        manager.last_check = 0
        mock_check.return_value = False
        ifaces2 = await manager.get_interfaces()
        assert all(not iface["online"] for iface in ifaces2)
