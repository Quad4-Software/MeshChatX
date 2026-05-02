from unittest.mock import MagicMock, patch

import RNS

from lxmfy import BotConfig, LXMFBot


def test_link_request_initiation():
    """Test requesting an RNS link."""
    config = BotConfig(link_support_enabled=True, test_mode=True)
    bot = LXMFBot(**config.__dict__)

    # Create a real RNS.Identity for testing
    real_identity = RNS.Identity()
    with patch("lxmfy.core.RNS.Identity.recall", return_value=real_identity):
        with patch("lxmfy.core.RNS.Link") as mock_link_class:
            mock_link = MagicMock()
            mock_link_class.return_value = mock_link

            dest_hash = "abc123def456"
            link = bot.request_link(dest_hash)

            assert link == mock_link
            assert dest_hash in bot.links
            mock_link_class.assert_called_once()


def test_link_request_custom_appdata():
    """Test requesting an RNS link with custom app_name and aspects."""
    config = BotConfig(link_support_enabled=True, test_mode=True)
    bot = LXMFBot(**config.__dict__)

    real_identity = RNS.Identity()
    with patch("lxmfy.core.RNS.Identity.recall", return_value=real_identity):
        with patch("lxmfy.core.RNS.Destination") as mock_dest_class:
            with patch("lxmfy.core.RNS.Link"):
                dest_hash = "abc123def456"
                bot.request_link(dest_hash, None, "custom_app", "aspect1", "aspect2")

                mock_dest_class.assert_called_once_with(
                    real_identity,
                    RNS.Destination.OUT,
                    RNS.Destination.SINGLE,
                    "custom_app",
                    "aspect1",
                    "aspect2",
                )


def test_link_established_callback_routing():
    """Test link established callback handling."""
    config = BotConfig(link_support_enabled=True, test_mode=True)
    bot = LXMFBot(**config.__dict__)

    link_called = False

    def on_link(link):
        nonlocal link_called
        link_called = True

    bot.on_link(on_link)

    # Mock an incoming link
    mock_link = MagicMock()
    mock_link.destination.hash = b"mock_hash"

    bot._link_established(mock_link)

    assert link_called is True
    assert "6d6f636b5f68617368" in bot.links  # hex of b"mock_hash"
