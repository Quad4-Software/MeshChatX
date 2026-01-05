from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend.rnstatus_handler import RNStatusHandler


@pytest.fixture
def mock_reticulum_instance():
    mock = MagicMock()
    mock.get_interface_stats.return_value = {"interfaces": []}
    mock.get_link_count.return_value = 0
    return mock


def test_blackhole_status_enabled(mock_reticulum_instance):
    with (
        patch.object(RNS.Reticulum, "publish_blackhole_enabled", return_value=True),
        patch.object(
            RNS.Reticulum,
            "blackhole_sources",
            return_value=[b"\x01" * 16, b"\x02" * 16],
        ),
    ):
        handler = RNStatusHandler(mock_reticulum_instance)
        status = handler.get_status()

        assert status["blackhole_enabled"] is True
        assert len(status["blackhole_sources"]) == 2
        assert status["blackhole_sources"][0] == (b"\x01" * 16).hex()


def test_blackhole_status_disabled(mock_reticulum_instance):
    with (
        patch.object(RNS.Reticulum, "publish_blackhole_enabled", return_value=False),
        patch.object(RNS.Reticulum, "blackhole_sources", return_value=[]),
    ):
        handler = RNStatusHandler(mock_reticulum_instance)
        status = handler.get_status()

        assert status["blackhole_enabled"] is False
        assert status["blackhole_sources"] == []


def test_blackhole_status_missing_api(mock_reticulum_instance):
    # Test backward compatibility or when API is missing (e.g. older RNS version simulation)
    # We simulate this by making the attribute access raise AttributeError
    # However, since we import RNS in the module, we need to ensure the mock raises AttributeError

    # We can't easily remove attributes from the real RNS module if it's already imported.
    # But we can patch the RNS object inside rnstatus_handler module.

    with patch(
        "meshchatx.src.backend.rnstatus_handler.RNS.Reticulum",
    ) as mock_rns_class:
        del mock_rns_class.publish_blackhole_enabled

        handler = RNStatusHandler(mock_reticulum_instance)
        status = handler.get_status()

        # Should default to False/Empty on exception
        assert status["blackhole_enabled"] is False
        assert status["blackhole_sources"] == []
