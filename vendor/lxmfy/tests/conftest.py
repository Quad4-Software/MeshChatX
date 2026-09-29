"""Test configuration and fixtures for LXMFy tests."""

import os
import tempfile
from pathlib import Path

import pytest
import RNS
from LXMF import LXMRouter

from lxmfy import BotConfig, LXMFBot


@pytest.fixture(scope="session")
def test_config_dir():
    """Create a temporary directory for test configurations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config"
        config_path.mkdir(exist_ok=True)
        yield config_path


@pytest.fixture(scope="session")
def reticulum_instance(test_config_dir):
    """Initialize a Reticulum instance for testing."""
    config_dir = test_config_dir / "reticulum"
    config_dir.mkdir(exist_ok=True)

    # Initialize Reticulum with test config
    reticulum = RNS.Reticulum(
        configdir=str(config_dir),
        loglevel=RNS.LOG_CRITICAL,  # Minimize logging in tests
        verbosity=0,
    )
    yield reticulum

    # Cleanup
    try:
        RNS.Reticulum.exit_handler()
    except Exception:
        pass


@pytest.fixture(scope="function")
def test_identity(reticulum_instance, test_config_dir):
    """Create a test identity."""
    identity = RNS.Identity()
    return identity


@pytest.fixture(scope="function")
def test_destination(test_identity, test_config_dir):
    """Create a test destination for messaging."""
    dest = RNS.Destination(
        test_identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        "lxmf",
        "test",
    )
    dest.set_proof_strategy(RNS.Destination.PROVE_NONE)  # Disable proof for tests
    return dest


@pytest.fixture(scope="function")
def lxmf_router(test_identity, test_config_dir):
    """Create an LXMF router for testing."""
    storage_path = test_config_dir / "lxmf_storage"
    storage_path.mkdir(exist_ok=True)

    router = LXMRouter(
        identity=test_identity,
        storagepath=str(storage_path),
        autopeer=False,  # Disable auto-peering in tests
        propagation_limit=10,
        delivery_limit=10,
    )

    # Register delivery identity (creates destination internally)
    delivery_destination = router.register_delivery_identity(
        test_identity,
        display_name="TestRouter",
    )

    # Store the delivery destination for tests
    router._test_delivery_dest = delivery_destination

    return router


@pytest.fixture(scope="function")
def test_bot_config(test_config_dir):
    """Create a test bot configuration."""
    return BotConfig(
        name="TestBot",
        announce=0,  # Disable announcing in tests
        announce_enabled=False,
        admins=set(),
        hot_reloading=False,
        rate_limit=100,  # High rate limit for tests
        cooldown=1,
        max_warnings=10,
        warning_timeout=60,
        command_prefix="/",
        cogs_enabled=False,
        permissions_enabled=False,
        storage_type="json",
        storage_path=str(test_config_dir / "bot_storage"),
        first_message_enabled=False,
        signature_verification_enabled=False,
        require_message_signatures=False,
        require_stamps=False,
        stamp_cost=None,
        test_mode=True,  # Enable test mode to skip RNS initialization
    )


@pytest.fixture(scope="function")
def test_bot(test_bot_config, test_config_dir):
    """Create a test bot instance."""
    # Override config_path for testing
    # Use a unique config path per test
    import uuid

    unique_config_path = test_config_dir / f"bot_{uuid.uuid4().hex[:8]}"
    unique_config_path.mkdir(exist_ok=True)

    config = test_bot_config.__dict__.copy()
    config["storage_path"] = str(unique_config_path / "storage")

    bot = LXMFBot(**config)
    bot.config_path = str(unique_config_path)

    yield bot

    # Cleanup
    try:
        bot.cleanup()
    except Exception:
        pass


@pytest.fixture(scope="function")
def test_message_data():
    """Sample message data for testing."""
    return {
        "content": "Test message content",
        "title": "Test Title",
        "source_hash": "abc123def456",
        "destination_hash": "def456abc789",
    }


@pytest.fixture(scope="function")
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Test file content")
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def cleanup_reticulum():
    """Clean up Reticulum state between tests."""
    yield
    # Force cleanup of any lingering links or destinations
    try:
        # This is a best-effort cleanup
        pass
    except Exception:
        pass
