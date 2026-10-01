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

            dest_hash = "aa" * 16
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
                dest_hash = "aa" * 16
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


def test_delivery_link_established_runs_lxmf_and_lxmfy():
    """Inbound delivery links must get LXMF callbacks and lxmfy tracking.

    Regression test: assigning _link_established directly to the delivery
    destination replaces LXMF's delivery_link_established, which wires the
    packet and resource callbacks. Without it, inbound link-based delivery
    stalls and the link dies.
    """
    config = BotConfig(link_support_enabled=True, test_mode=True)
    bot = LXMFBot(**config.__dict__)

    calls = []
    router = MagicMock()
    router.delivery_link_established = lambda link: calls.append("lxmf")
    bot.router = router

    handler_calls = []
    bot.on_link(lambda link: handler_calls.append(link))

    mock_link = MagicMock()
    mock_link.destination.hash = b"mock_hash"

    bot._delivery_link_established(mock_link)

    assert calls == ["lxmf"]
    assert handler_calls == [mock_link]
    assert "6d6f636b5f68617368" in bot.links


def test_delivery_link_established_without_router():
    """In test mode there is no router, handlers still run."""
    config = BotConfig(link_support_enabled=True, test_mode=True)
    bot = LXMFBot(**config.__dict__)

    handler_calls = []
    bot.on_link(lambda link: handler_calls.append(link))

    mock_link = MagicMock()
    mock_link.destination.hash = b"mock_hash"

    bot._delivery_link_established(mock_link)

    assert handler_calls == [mock_link]


def test_delivery_destination_registers_chained_callback(reticulum_instance, tmp_path):
    """The delivery destination must point at the chained callback.

    A plain assignment of _link_established here would silently replace
    LXMF's delivery_link_established again, so assert the wiring itself,
    not just the handler's behavior. The router threads stay daemonized;
    cleanup is skipped because it would tear down the shared Reticulum
    instance used by other tests.
    """
    bot = LXMFBot(
        test_mode=False,
        announce_enabled=False,
        announce_immediately=False,
        landlock_enabled=False,
        config_path=str(tmp_path / "cfg"),
        storage_path=str(tmp_path / "data"),
        storage_type="memory",
        reticulum_config_dir=str(tmp_path / "rns"),
    )

    callback = bot.local.callbacks.link_established
    assert callback.__self__ is bot
    assert callback.__func__ is LXMFBot._delivery_link_established
