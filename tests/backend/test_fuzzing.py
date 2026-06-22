# SPDX-License-Identifier: 0BSD

import os
import random
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
import RNS
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser
from meshchatx.src.backend.lxmf_message_fields import (
    LxmfAudioField,
    LxmfFileAttachment,
    LxmfImageField,
)
from meshchatx.src.backend.meshchat_utils import (
    parse_lxmf_display_name,
    parse_nomadnetwork_node_display_name,
)
from meshchatx.src.backend.page_node import normalize_page_filename


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(config_text=st.text(min_size=0, max_size=5000))
def test_interface_config_parsing_fuzzing(config_text):
    """Fuzz the interface configuration parser with random text."""
    try:
        InterfaceConfigParser.parse(config_text)
    except Exception as e:
        pytest.fail(f"InterfaceConfigParser crashed with input: {e}")


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(name=st.text(min_size=0, max_size=500))
def test_normalize_page_filename_fuzzing(name):
    """Fuzz mesh server page filename normalization."""
    try:
        result = normalize_page_filename(name)
        assert isinstance(result, str)
        assert "/" not in result
        assert "\\" not in result
    except ValueError:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(app_data_base64=st.one_of(st.none(), st.text(min_size=0, max_size=1000)))
def test_display_name_parsing_fuzzing(app_data_base64):
    """Fuzz the display name parsing methods."""
    try:
        parse_lxmf_display_name(app_data_base64)
        parse_nomadnetwork_node_display_name(app_data_base64)
    except Exception as e:
        pytest.fail(f"Display name parsing crashed with data {app_data_base64}: {e}")


@pytest.fixture
def temp_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def mock_app(temp_dir):
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"test_hash_32_bytes_long_01234567"
            self.hexhash = self.hash.hex()

    with ExitStack() as stack:
        stack.enter_context(patch("meshchatx.src.backend.identity_context.Database"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.ConfigManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.MessageHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.AnnounceManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.ArchiverManager"),
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.MapManager"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TelephoneManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.VoicemailManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RingtoneManager"),
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.RNCPHandler"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TranslatorHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager"),
        )
        mock_async_utils = stack.enter_context(patch("meshchatx.meshchat.AsyncUtils"))
        stack.enter_context(patch("LXMF.LXMRouter"))
        stack.enter_context(patch("LXST.Primitives.Telephony"))
        stack.enter_context(patch("RNS.Identity", MockIdentityClass))
        mock_reticulum_class = stack.enter_context(patch("RNS.Reticulum"))
        mock_reticulum_class.MTU = 1200
        mock_reticulum_class.return_value.MTU = 1200

        mock_transport_class = stack.enter_context(patch("RNS.Transport"))
        mock_transport_class.MTU = 1200
        mock_transport_class.return_value.MTU = 1200

        stack.enter_context(patch("threading.Thread"))
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "announce_loop",
                new=MagicMock(return_value=None),
            ),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "announce_sync_propagation_nodes",
                new=MagicMock(return_value=None),
            ),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "crawler_loop",
                new=MagicMock(return_value=None),
            ),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "auto_backup_loop",
                new=MagicMock(return_value=None),
            ),
        )

        mock_id = MockIdentityClass()
        mock_id.get_private_key = MagicMock(return_value=b"test_private_key")

        stack.enter_context(
            patch.object(MockIdentityClass, "from_file", return_value=mock_id),
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "recall", return_value=mock_id),
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "from_bytes", return_value=mock_id),
        )

        def mock_run_async(coro):
            import asyncio

            if asyncio.iscoroutine(coro):
                coro.close()

        mock_async_utils.run_async = MagicMock(side_effect=mock_run_async)

        app = ReticulumMeshChat(
            identity=mock_id,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        app.config = MagicMock()
        app.config.display_name.get.return_value = "Test User"
        app.config.auto_announce_enabled.get.return_value = True
        app.config.auto_announce_interval_seconds.get.return_value = 600
        app.config.last_announced_at.get.return_value = 0
        app.config.theme.get.return_value = "dark"
        app.config.language.get.return_value = "en"
        app.config.auto_resend_failed_messages_when_announce_received.get.return_value = True
        app.config.allow_auto_resending_failed_messages_with_attachments.get.return_value = False
        app.config.auto_send_failed_messages_to_propagation_node.get.return_value = True
        app.config.show_suggested_community_interfaces.get.return_value = True
        app.config.lxmf_local_propagation_node_enabled.get.return_value = False
        app.config.lxmf_preferred_propagation_node_destination_hash.get.return_value = (
            None
        )
        app.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get.return_value = 3600
        app.config.lxmf_preferred_propagation_node_last_synced_at.get.return_value = 0
        app.config.lxmf_user_icon_name.get.return_value = "user"
        app.config.lxmf_user_icon_foreground_colour.get.return_value = "#ffffff"
        app.config.lxmf_user_icon_background_colour.get.return_value = "#000000"
        app.config.lxmf_auto_sync_propagation_nodes_enabled.get.return_value = True
        app.config.lxmf_auto_sync_propagation_nodes_interval_seconds.get.return_value = 3600
        app.config.lxmf_auto_sync_propagation_nodes_last_synced_at.get.return_value = 0
        app.config.lxmf_auto_sync_propagation_nodes_min_hops.get.return_value = 1
        app.config.lxmf_auto_sync_propagation_nodes_max_hops.get.return_value = 5
        app.config.lxmf_auto_sync_propagation_nodes_max_count.get.return_value = 10
        app.config.lxmf_auto_sync_propagation_nodes_max_age_seconds.get.return_value = (
            86400
        )
        app.config.lxmf_auto_sync_propagation_nodes_max_size_bytes.get.return_value = (
            1000000
        )
        app.config.lxmf_auto_sync_propagation_nodes_max_total_size_bytes.get.return_value = 10000000
        app.config.lxmf_auto_sync_propagation_nodes_max_total_count.get.return_value = (
            100
        )
        app.config.lxmf_auto_sync_propagation_nodes_max_total_age_seconds.get.return_value = 864000
        app.config.lxmf_auto_sync_propagation_nodes_max_total_size_bytes_per_node.get.return_value = 1000000
        app.config.lxmf_auto_sync_propagation_nodes_max_total_count_per_node.get.return_value = 100
        app.config.lxmf_auto_sync_propagation_nodes_max_total_age_seconds_per_node.get.return_value = 864000

        app.websocket_broadcast = MagicMock(side_effect=lambda data: None)
        app.is_destination_blocked = MagicMock(return_value=False)
        app.check_spam_keywords = MagicMock(return_value=False)
        app.db_upsert_lxmf_message = MagicMock()
        app.handle_forwarding = MagicMock()
        app.convert_db_announce_to_dict = MagicMock(return_value={})
        app.get_config_dict = MagicMock(return_value={"test_config": "test_value"})
        app.resend_failed_messages_for_destination = MagicMock(
            side_effect=lambda dest, context=None: None,
        )

        yield app


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    num_announces=st.integers(min_value=10, max_value=100),
)
def test_announce_overload(mock_app, num_announces):
    """Test handling of multiple announces in rapid succession."""
    mock_app.announce_manager.upsert_announce.reset_mock()
    mock_app.websocket_broadcast.reset_mock()

    aspect = "lxmf.delivery"
    app_data = b"test_app_data"

    mock_app.database.announces.get_announce_by_hash.return_value = {
        "aspect": "lxmf.delivery",
        "destination_hash": "some_hash",
        "display_name": "Test Peer",
    }

    for i in range(num_announces):
        destination_hash = os.urandom(16)
        announced_identity = MagicMock()
        announced_identity.hash = os.urandom(32)
        announce_packet_hash = os.urandom(16)

        mock_app.on_lxmf_announce_received(
            aspect,
            destination_hash,
            announced_identity,
            app_data,
            announce_packet_hash,
        )

    assert mock_app.announce_manager.upsert_announce.call_count == num_announces


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    num_messages=st.integers(min_value=10, max_value=100),
)
def test_message_spamming(mock_app, num_messages):
    """Test handling of many LXMF messages in rapid succession."""
    mock_app.db_upsert_lxmf_message.reset_mock()

    for i in range(num_messages):
        mock_message = MagicMock()
        mock_message.source_hash = os.urandom(16)
        mock_message.hash = os.urandom(16)
        mock_message.get_fields.return_value = {}
        mock_message.title = f"Spam Title {i}"
        mock_message.content = f"Spam Content {i}"

        mock_app.on_lxmf_delivery(mock_message)

    assert mock_app.db_upsert_lxmf_message.call_count == num_messages


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    num_messages=st.integers(min_value=10, max_value=50),
    payload_size=st.integers(min_value=1000, max_value=50000),
)
def test_message_spamming_large_payloads(mock_app, num_messages, payload_size):
    """Test handling of many LXMF messages with large payloads."""
    mock_app.db_upsert_lxmf_message.reset_mock()

    for i in range(num_messages):
        mock_message = MagicMock()
        mock_message.source_hash = os.urandom(16)
        mock_message.hash = os.urandom(16)
        mock_message.get_fields.return_value = {}
        mock_message.title = f"Spam Title {i}"
        mock_message.content = "A" * payload_size

        mock_app.on_lxmf_delivery(mock_message)

    assert mock_app.db_upsert_lxmf_message.call_count == num_messages


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    audio_bytes=st.binary(min_size=0, max_size=5000),
    image_bytes=st.binary(min_size=0, max_size=10000),
)
def test_lxmf_field_fuzzing(audio_bytes, image_bytes):
    """Fuzz the LXMF field helper classes."""
    try:
        LxmfAudioField(audio_mode=random.randint(0, 10), audio_bytes=audio_bytes)
        LxmfImageField(
            image_type=random.choice(["png", "jpg", "webp", "invalid"]),
            image_bytes=image_bytes,
        )
        LxmfFileAttachment(file_name="test.txt", file_bytes=audio_bytes)
    except Exception as e:
        pytest.fail(f"LXMF field classes crashed: {e}")
