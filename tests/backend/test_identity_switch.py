import os
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import ExitStack
import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns():
    # Save real Identity class to use as base class for our mock class
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"initial_hash_32_bytes_long_01234"
            self.hexhash = self.hash.hex()

    with ExitStack() as stack:
        # Define patches
        patches = [
            patch("RNS.Reticulum"),
            patch("RNS.Transport"),
            patch("RNS.Identity", MockIdentityClass),
            patch("threading.Thread"),
            patch("meshchatx.src.backend.identity_context.Database"),
            patch("meshchatx.src.backend.identity_context.ConfigManager"),
            patch("meshchatx.src.backend.identity_context.MessageHandler"),
            patch("meshchatx.src.backend.identity_context.AnnounceManager"),
            patch("meshchatx.src.backend.identity_context.ArchiverManager"),
            patch("meshchatx.src.backend.identity_context.MapManager"),
            patch("meshchatx.src.backend.identity_context.DocsManager"),
            patch("meshchatx.src.backend.identity_context.NomadNetworkManager"),
            patch("meshchatx.src.backend.identity_context.TelephoneManager"),
            patch("meshchatx.src.backend.identity_context.VoicemailManager"),
            patch("meshchatx.src.backend.identity_context.RingtoneManager"),
            patch("meshchatx.src.backend.identity_context.RNCPHandler"),
            patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
            patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
            patch("meshchatx.src.backend.identity_context.TranslatorHandler"),
            patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager"),
            patch("LXMF.LXMRouter"),
            patch("meshchatx.meshchat.IdentityContext"),
        ]

        # Apply patches
        mocks = {}
        for p in patches:
            attr_name = (
                p.attribute if hasattr(p, "attribute") else p.target.split(".")[-1]
            )
            mocks[attr_name] = stack.enter_context(p)

        # Mock class methods on MockIdentityClass
        mock_id_instance = MockIdentityClass()
        mock_id_instance.get_private_key = MagicMock(
            return_value=b"initial_private_key"
        )

        stack.enter_context(
            patch.object(MockIdentityClass, "from_file", return_value=mock_id_instance)
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "recall", return_value=mock_id_instance)
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "from_bytes", return_value=mock_id_instance)
        )

        # Access specifically the ones we need to configure
        mock_config = mocks["ConfigManager"]

        # Setup mock config
        mock_config.return_value.display_name.get.return_value = "Test User"

        yield {
            "Identity": MockIdentityClass,
            "id_instance": mock_id_instance,
            "IdentityContext": mocks["IdentityContext"],
        }


@pytest.mark.asyncio
async def test_hotswap_identity_success(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Setup new identity
    new_hash = "new_hash_123"
    identity_dir = os.path.join(temp_dir, "identities", new_hash)
    os.makedirs(identity_dir)
    identity_file = os.path.join(identity_dir, "identity")
    with open(identity_file, "wb") as f:
        f.write(b"new_private_key")

    new_id_instance = MagicMock()
    new_id_instance.hash = b"new_hash_32_bytes_long_012345678"
    mock_rns["Identity"].from_file.return_value = new_id_instance

    # Configure mock context
    mock_context = mock_rns["IdentityContext"].return_value
    mock_context.config.display_name.get.return_value = "New User"
    mock_context.identity_hash = new_hash

    # Mock methods
    app.teardown_identity = MagicMock()
    app.setup_identity = MagicMock(
        side_effect=lambda id: setattr(app, "current_context", mock_context)
    )
    app.websocket_broadcast = AsyncMock()

    # Perform hotswap
    result = await app.hotswap_identity(new_hash)

    assert result is True
    app.teardown_identity.assert_called_once()
    app.setup_identity.assert_called_once_with(new_id_instance)
    app.websocket_broadcast.assert_called_once()

    # Verify main identity file was updated
    main_identity_file = os.path.join(temp_dir, "identity")
    with open(main_identity_file, "rb") as f:
        assert f.read() == b"new_private_key"


@pytest.mark.asyncio
async def test_hotswap_identity_keep_alive(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Setup new identity
    new_hash = "new_hash_123"
    identity_dir = os.path.join(temp_dir, "identities", new_hash)
    os.makedirs(identity_dir)
    identity_file = os.path.join(identity_dir, "identity")
    with open(identity_file, "wb") as f:
        f.write(b"new_private_key")

    new_id_instance = MagicMock()
    new_id_instance.hash = b"new_hash_32_bytes_long_012345678"
    mock_rns["Identity"].from_file.return_value = new_id_instance

    # Configure mock context
    mock_context = mock_rns["IdentityContext"].return_value
    mock_context.config.display_name.get.return_value = "New User"
    mock_context.identity_hash = new_hash

    # Mock methods
    app.teardown_identity = MagicMock()
    app.setup_identity = MagicMock(
        side_effect=lambda id: setattr(app, "current_context", mock_context)
    )
    app.websocket_broadcast = AsyncMock()

    # Perform hotswap with keep_alive=True
    result = await app.hotswap_identity(new_hash, keep_alive=True)

    assert result is True
    app.teardown_identity.assert_not_called()
    app.setup_identity.assert_called_once_with(new_id_instance)


@pytest.mark.asyncio
async def test_hotswap_identity_file_missing(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Attempt hotswap with non-existent hash
    result = await app.hotswap_identity("non_existent_hash")

    assert result is False


@pytest.mark.asyncio
async def test_hotswap_identity_corrupted(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Setup "corrupted" identity
    new_hash = "corrupted_hash"
    identity_dir = os.path.join(temp_dir, "identities", new_hash)
    os.makedirs(identity_dir)
    identity_file = os.path.join(identity_dir, "identity")
    with open(identity_file, "wb") as f:
        f.write(b"corrupted_data")

    mock_rns["Identity"].from_file.return_value = None

    # Perform hotswap
    result = await app.hotswap_identity(new_hash)

    assert result is False


@pytest.mark.asyncio
async def test_hotswap_identity_recovery(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Save initial identity file
    main_identity_file = os.path.join(temp_dir, "identity")
    with open(main_identity_file, "wb") as f:
        f.write(b"initial_private_key")

    # Setup new identity
    new_hash = "new_hash_123"
    identity_dir = os.path.join(temp_dir, "identities", new_hash)
    os.makedirs(identity_dir)
    identity_file = os.path.join(identity_dir, "identity")
    with open(identity_file, "wb") as f:
        f.write(b"new_private_key")

    new_id_instance = MagicMock()
    new_id_instance.hash = b"new_hash_32_bytes_long_012345678"
    mock_rns["Identity"].from_file.return_value = new_id_instance

    # Mock setup_identity to fail first time (after hotswap start),
    # but the second call (recovery) should succeed.
    app.setup_identity = MagicMock(side_effect=[Exception("Setup failed"), None])
    app.teardown_identity = MagicMock()
    app.websocket_broadcast = AsyncMock()

    # Perform hotswap
    result = await app.hotswap_identity(new_hash)

    assert result is False
    assert app.setup_identity.call_count == 2

    # Verify main identity file was restored
    with open(main_identity_file, "rb") as f:
        assert f.read() == b"initial_private_key"


@pytest.mark.asyncio
async def test_hotswap_identity_ultimate_failure_emergency_identity(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Setup new identity
    new_hash = "new_hash_123"
    identity_dir = os.path.join(temp_dir, "identities", new_hash)
    os.makedirs(identity_dir)
    identity_file = os.path.join(identity_dir, "identity")
    with open(identity_file, "wb") as f:
        f.write(b"new_private_key")

    new_id_instance = MagicMock()
    new_id_instance.hash = b"new_hash_32_bytes_long_012345678"
    mock_rns["Identity"].from_file.return_value = new_id_instance

    # Mock setup_identity to fail ALL THE TIME
    app.setup_identity = MagicMock(side_effect=Exception("Ultimate failure"))
    app.teardown_identity = MagicMock()
    app.websocket_broadcast = AsyncMock()

    # Mock create_identity to return a new hash
    emergency_hash = "emergency_hash_456"
    app.create_identity = MagicMock(return_value={"hash": emergency_hash})

    # Mock RNS.Identity.from_file for the emergency identity
    emergency_id = MagicMock()
    emergency_id.hash = b"emergency_hash_32_bytes_long_012"

    # Ensure from_file returns the new identity when called for the emergency one
    def side_effect_from_file(path):
        if emergency_hash in path:
            return emergency_id
        return new_id_instance

    mock_rns["Identity"].from_file.side_effect = side_effect_from_file

    # Create the directory structure create_identity would have created
    emergency_dir = os.path.join(temp_dir, "identities", emergency_hash)
    os.makedirs(emergency_dir)
    with open(os.path.join(emergency_dir, "identity"), "wb") as f:
        f.write(b"emergency_private_key")

    # Perform hotswap
    result = await app.hotswap_identity(new_hash)

    assert result is False
    # Should have tried to setup identity 3 times:
    # 1. new_identity
    # 2. old_identity (recovery)
    # 3. emergency_identity (failsafe)
    assert app.setup_identity.call_count == 3
    app.create_identity.assert_called_once_with(display_name="Emergency Recovery")

    # Verify main identity file was updated to emergency one
    main_identity_file = os.path.join(temp_dir, "identity")
    with open(main_identity_file, "rb") as f:
        assert f.read() == b"emergency_private_key"
