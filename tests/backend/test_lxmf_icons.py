# SPDX-License-Identifier: 0BSD

import shutil
import tempfile
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import LXMF
import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.meshchat_utils import parse_lxmf_icon_appearance


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ([], None),
        (["user", b"\xff\xff\xff"], None),
        (
            ("user", b"\xff\xff\xff", b"\x00\x00\x00", "extra"),
            ("user", "#ffffff", "#000000"),
        ),
        (["user", b"\xff\xff", b"\x00\x00\x00"], None),
        (["user", "#ffffff", b"\x00\x00\x00"], None),
        ([b"user", b"\xff\xff\xff", b"\x00\x00\x00"], None),
        (["", b"\xff\xff\xff", b"\x00\x00\x00"], None),
        (["x" * 65, b"\xff\xff\xff", b"\x00\x00\x00"], None),
        (["bad\nname", b"\xff\xff\xff", b"\x00\x00\x00"], None),
        (["user", b"\xaa\xbb\xcc", b"\x11\x22\x33"], ("user", "#aabbcc", "#112233")),
    ],
)
def test_parse_lxmf_icon_appearance_oracle(value, expected):
    assert parse_lxmf_icon_appearance(value) == expected


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns():
    # Save real Identity class to use as base for our mock class
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
            patch("RNS.Destination"),
            patch("threading.Thread"),
            patch("meshchatx.src.backend.identity_context.core.Database"),
            patch("meshchatx.src.backend.identity_context.core.ConfigManager"),
            patch("meshchatx.src.backend.identity_context.core.MessageHandler"),
            patch("meshchatx.src.backend.identity_context.core.AnnounceManager"),
            patch("meshchatx.src.backend.identity_context.core.ArchiverManager"),
            patch("meshchatx.src.backend.identity_context.core.MapManager"),
            patch("meshchatx.src.backend.identity_context.core.DocsManager"),
            patch("meshchatx.src.backend.identity_context.core.NomadNetworkManager"),
            patch("meshchatx.src.backend.identity_context.core.TelephoneManager"),
            patch("meshchatx.src.backend.identity_context.core.VoicemailManager"),
            patch("meshchatx.src.backend.identity_context.core.RingtoneManager"),
            patch("meshchatx.src.backend.identity_context.core.RNCPHandler"),
            patch("meshchatx.src.backend.identity_context.core.RNStatusHandler"),
            patch("meshchatx.src.backend.identity_context.core.RNProbeHandler"),
            patch("meshchatx.src.backend.identity_context.core.TranslatorHandler"),
            patch(
                "meshchatx.src.backend.identity_context.core.CommunityInterfacesManager"
            ),
            patch("LXMF.LXMRouter"),
            patch("LXMF.LXMessage"),
            patch("meshchatx.meshchat.IdentityContext"),
        ]

        # Apply patches
        mocks = {}
        for p in patches:
            attr_name = (
                p.attribute if hasattr(p, "attribute") else p.target.split(".")[-1]
            )
            mocks[attr_name] = stack.enter_context(p)

        # Access specifically the ones we need to configure
        mock_config = mocks["ConfigManager"]

        # Setup mock config
        mock_config.return_value.display_name.get.return_value = "Test User"
        mock_config.return_value.lxmf_user_icon_name.get.return_value = "user"
        mock_config.return_value.lxmf_user_icon_foreground_colour.get.return_value = (
            "#ffffff"
        )
        mock_config.return_value.lxmf_user_icon_background_colour.get.return_value = (
            "#000000"
        )
        mock_config.return_value.auto_send_failed_messages_to_propagation_node.get.return_value = False

        # Mock class methods on MockIdentityClass
        mock_id_instance = MockIdentityClass()
        mock_id_instance.get_private_key = MagicMock(
            return_value=b"initial_private_key",
        )

        stack.enter_context(
            patch.object(MockIdentityClass, "from_file", return_value=mock_id_instance),
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "recall", return_value=mock_id_instance),
        )
        stack.enter_context(
            patch.object(
                MockIdentityClass,
                "from_bytes",
                return_value=mock_id_instance,
            ),
        )

        # Setup mock LXMessage
        def lx_message_init(dest, source, content, title=None, desired_method=None):
            m = MagicMock()
            m.dest = dest
            m.source = source
            m.content = content.encode("utf-8") if isinstance(content, str) else content
            m.title = title.encode("utf-8") if isinstance(title, str) else title
            m.fields = {}
            m.hash = b"msg_hash_32_bytes_long_012345678"
            m.source_hash = b"source_hash_32_bytes_long_012345"
            m.destination_hash = b"dest_hash_32_bytes_long_01234567"
            m.incoming = False
            m.progress = 0.5
            m.rssi = -50
            m.snr = 10
            m.q = 1.0
            m.delivery_attempts = 0
            m.timestamp = 1234567890.0
            m.next_delivery_attempt = 0.0
            return m

        mocks["LXMessage"].side_effect = lx_message_init

        yield {
            "Identity": MockIdentityClass,
            "id_instance": mock_id_instance,
            "IdentityContext": mocks["IdentityContext"],
            "ConfigManager": mock_config,
            "LXMessage": mocks["LXMessage"],
            "Transport": mocks["Transport"],
        }


@pytest.mark.asyncio
async def test_send_message_attaches_icon_on_first_message(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Configure mock context
    mock_context = mock_rns["IdentityContext"].return_value
    mock_context.config = mock_rns["ConfigManager"].return_value
    mock_context.database.misc.get_last_sent_icon_hash.return_value = None
    app.current_context = mock_context

    dest_hash = "abc123"
    content = "Hello"

    # Mock methods
    app.db_upsert_lxmf_message = MagicMock()
    app.websocket_broadcast = AsyncMock()
    app.handle_lxmf_message_progress = AsyncMock()

    # Perform send
    lxmf_message = await app.send_message(dest_hash, content)

    # Verify icon field was added
    assert LXMF.FIELD_ICON_APPEARANCE in lxmf_message.fields
    assert lxmf_message.fields[LXMF.FIELD_ICON_APPEARANCE][0] == "user"

    # Verify last sent hash was updated
    mock_context.database.misc.update_last_sent_icon_hash.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_does_not_attach_icon_if_already_sent(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Configure mock context
    mock_context = mock_rns["IdentityContext"].return_value
    mock_context.config = mock_rns["ConfigManager"].return_value
    app.current_context = mock_context

    # Calculate current icon hash
    current_hash = app.get_current_icon_hash()
    mock_context.database.misc.get_last_sent_icon_hash.return_value = current_hash

    dest_hash = "abc123"
    content = "Hello again"

    # Mock methods
    app.db_upsert_lxmf_message = MagicMock()
    app.websocket_broadcast = AsyncMock()
    app.handle_lxmf_message_progress = AsyncMock()

    # Perform send
    lxmf_message = await app.send_message(dest_hash, content)

    # Verify icon field was NOT added
    assert LXMF.FIELD_ICON_APPEARANCE not in lxmf_message.fields

    # Verify last sent hash was NOT updated again
    mock_context.database.misc.update_last_sent_icon_hash.assert_not_called()


@pytest.mark.asyncio
async def test_send_message_attaches_icon_if_changed(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Configure mock context
    mock_context = mock_rns["IdentityContext"].return_value
    mock_context.config = mock_rns["ConfigManager"].return_value
    app.current_context = mock_context

    # Simulate old hash being different
    mock_context.database.misc.get_last_sent_icon_hash.return_value = "old_hash"

    dest_hash = "abc123"
    content = "Hello after change"

    # Mock methods
    app.db_upsert_lxmf_message = MagicMock()
    app.websocket_broadcast = AsyncMock()
    app.handle_lxmf_message_progress = AsyncMock()

    # Perform send
    lxmf_message = await app.send_message(dest_hash, content)

    # Verify icon field was added
    assert LXMF.FIELD_ICON_APPEARANCE in lxmf_message.fields

    # Verify last sent hash was updated
    mock_context.database.misc.update_last_sent_icon_hash.assert_called_once()


@pytest.mark.asyncio
async def test_receive_message_updates_icon(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Configure mock context
    mock_context = mock_rns["IdentityContext"].return_value
    mock_context.database.misc.is_destination_blocked.return_value = False
    app.current_context = mock_context

    # Create mock incoming message
    mock_msg = MagicMock()
    mock_msg.source_hash = b"source_hash_bytes"
    mock_msg.get_fields.return_value = {
        LXMF.FIELD_ICON_APPEARANCE: [
            "new_icon",
            b"\xff\xff\xff",  # #ffffff
            b"\x00\x00\x00",  # #000000
        ],
    }
    mock_msg.signature_validated = True
    mock_msg.unverified_reason = None

    # Mock methods
    app.db_upsert_lxmf_message = MagicMock()
    app.update_lxmf_user_icon = MagicMock()
    app.is_destination_blocked = MagicMock(return_value=False)

    # Perform delivery
    app.on_lxmf_delivery(mock_msg)

    # Verify icon update was called
    app.update_lxmf_user_icon.assert_called_once_with(
        mock_msg.source_hash.hex(),
        "new_icon",
        "#ffffff",
        "#000000",
        context=mock_context,
    )


@pytest.mark.asyncio
async def test_receive_message_rejects_malformed_icon(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    mock_context = mock_rns["IdentityContext"].return_value
    mock_context.database.misc.is_destination_blocked.return_value = False
    app.current_context = mock_context

    mock_msg = MagicMock()
    mock_msg.source_hash = b"source_hash_bytes"
    mock_msg.unverified_reason = None
    mock_msg.get_fields.return_value = {
        LXMF.FIELD_ICON_APPEARANCE: ["bad", "#ffffff", "#000000"],
    }

    app.db_upsert_lxmf_message = MagicMock()
    app.update_lxmf_user_icon = MagicMock()
    app.is_destination_blocked = MagicMock(return_value=False)

    app.on_lxmf_delivery(mock_msg)

    app.update_lxmf_user_icon.assert_not_called()
    app.db_upsert_lxmf_message.assert_called_once()


@pytest.mark.asyncio
async def test_receive_message_drops_invalid_signature(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    mock_context = mock_rns["IdentityContext"].return_value
    app.current_context = mock_context

    mock_msg = MagicMock()
    mock_msg.source_hash = b"source_hash_bytes"
    mock_msg.unverified_reason = LXMF.LXMessage.SIGNATURE_INVALID
    mock_msg.get_fields.return_value = {}

    app.db_upsert_lxmf_message = MagicMock()
    app.update_lxmf_user_icon = MagicMock()
    app.is_destination_blocked = MagicMock(return_value=False)

    app.on_lxmf_delivery(mock_msg)

    app.db_upsert_lxmf_message.assert_not_called()
    app.is_destination_blocked.assert_not_called()
