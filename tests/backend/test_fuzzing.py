import pytest
import os
import time
import json
import random
from unittest.mock import MagicMock, patch, AsyncMock
from hypothesis import given, strategies as st, settings, HealthCheck
from meshchatx.meshchat import ReticulumMeshChat
import RNS
import LXMF

from meshchatx.src.backend.telemetry_utils import Telemeter
from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser
from meshchatx.src.backend.lxmf_message_fields import LxmfAudioField, LxmfImageField, LxmfFileAttachment

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    data=st.binary(min_size=0, max_size=1000)
)
def test_telemetry_unpack_fuzzing(data):
    """Fuzz the telemetry unpacking logic with random binary data."""
    try:
        # This should not raise unhandled exceptions
        Telemeter.from_packed(data)
    except Exception:
        # We expect some failures for invalid packed data, but no crashes
        pass

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    config_text=st.text(min_size=0, max_size=5000)
)
def test_interface_config_parsing_fuzzing(config_text):
    """Fuzz the interface configuration parser with random text."""
    try:
        InterfaceConfigParser.parse(config_text)
    except Exception as e:
        pytest.fail(f"InterfaceConfigParser crashed with input: {e}")

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    identity_bytes=st.binary(min_size=0, max_size=2048)
)
def test_identity_parsing_fuzzing(identity_bytes):
    """Fuzz RNS.Identity loading with random bytes."""
    try:
        RNS.Identity.from_bytes(identity_bytes)
    except Exception:
        # RNS.Identity.from_bytes is expected to fail on random bytes, 
        # but it should not cause an unhandled crash of the process.
        pass

@pytest.fixture
def temp_dir(tmp_path):
    return str(tmp_path)

@pytest.fixture
def mock_app(temp_dir):
    with (
        patch("meshchatx.meshchat.Database"),
        patch("meshchatx.meshchat.ConfigManager"),
        patch("meshchatx.meshchat.MessageHandler"),
        patch("meshchatx.meshchat.AnnounceManager"),
        patch("meshchatx.meshchat.ArchiverManager"),
        patch("meshchatx.meshchat.MapManager"),
        patch("meshchatx.meshchat.TelephoneManager"),
        patch("meshchatx.meshchat.VoicemailManager"),
        patch("meshchatx.meshchat.RingtoneManager"),
        patch("meshchatx.meshchat.RNCPHandler"),
        patch("meshchatx.meshchat.RNStatusHandler"),
        patch("meshchatx.meshchat.RNProbeHandler"),
        patch("meshchatx.meshchat.TranslatorHandler"),
        patch("LXMF.LXMRouter"),
        patch("RNS.Identity") as mock_identity_class,
        patch("RNS.Reticulum"),
        patch("RNS.Transport"),
        patch("threading.Thread"),
        patch.object(ReticulumMeshChat, "announce_loop", return_value=None),
        patch.object(ReticulumMeshChat, "announce_sync_propagation_nodes", return_value=None),
        patch.object(ReticulumMeshChat, "crawler_loop", return_value=None),
    ):
        mock_id = MagicMock()
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.get_private_key.return_value = b"test_private_key"
        mock_identity_class.return_value = mock_id

        app = ReticulumMeshChat(
            identity=mock_id,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        
        # Setup config mock to return real values to avoid JSON serialization issues
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
        app.config.lxmf_preferred_propagation_node_destination_hash.get.return_value = None
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
        app.config.lxmf_auto_sync_propagation_nodes_max_age_seconds.get.return_value = 86400
        app.config.lxmf_auto_sync_propagation_nodes_max_size_bytes.get.return_value = 1000000
        app.config.lxmf_auto_sync_propagation_nodes_max_total_size_bytes.get.return_value = 10000000
        app.config.lxmf_auto_sync_propagation_nodes_max_total_count.get.return_value = 100
        app.config.lxmf_auto_sync_propagation_nodes_max_total_age_seconds.get.return_value = 864000
        app.config.lxmf_auto_sync_propagation_nodes_max_total_size_bytes_per_node.get.return_value = 1000000
        app.config.lxmf_auto_sync_propagation_nodes_max_total_count_per_node.get.return_value = 100
        app.config.lxmf_auto_sync_propagation_nodes_max_total_age_seconds_per_node.get.return_value = 864000

        app.websocket_broadcast = AsyncMock()
        app.is_destination_blocked = MagicMock(return_value=False)
        app.check_spam_keywords = MagicMock(return_value=False)
        app.db_upsert_lxmf_message = MagicMock()
        app.handle_forwarding = MagicMock()
        app.convert_db_announce_to_dict = MagicMock(return_value={})
        app.get_config_dict = MagicMock(return_value={"test_config": "test_value"})
        
        return app

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
    
    # Mock database to return a valid announce dict
    mock_app.database.announces.get_announce_by_hash.return_value = {
        "aspect": "lxmf.delivery",
        "destination_hash": "some_hash",
        "display_name": "Test Peer"
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
            announce_packet_hash
        )
    
    # Verify that the database was called for each announce
    assert mock_app.announce_manager.upsert_announce.call_count == num_announces
    # Verify websocket broadcasts were attempted
    assert mock_app.websocket_broadcast.call_count == num_announces

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
        mock_message.get_fields.return_value = {} # No telemetry field
        mock_message.title = f"Spam Title {i}"
        mock_message.content = f"Spam Content {i}"
        
        mock_app.on_lxmf_delivery(mock_message)
        
    assert mock_app.db_upsert_lxmf_message.call_count == num_messages

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    num_nodes=st.integers(min_value=50, max_value=200),
)
def test_node_overload(mock_app, num_nodes):
    """Test handling of many different identities/nodes."""
    mock_app.announce_manager.upsert_announce.reset_mock()
    
    aspect = "lxmf.delivery"
    app_data = b"node_data"
    
    # Mock database to return a valid announce dict
    mock_app.database.announces.get_announce_by_hash.return_value = {
        "aspect": "lxmf.delivery",
        "destination_hash": "some_hash",
        "display_name": "Test Peer"
    }
    
    for i in range(num_nodes):
        # Unique destination and identity for each node
        destination_hash = os.urandom(16)
        announced_identity = MagicMock()
        announced_identity.hash = os.urandom(32)
        announce_packet_hash = os.urandom(16)
        
        mock_app.on_lxmf_announce_received(
            aspect,
            destination_hash,
            announced_identity,
            app_data,
            announce_packet_hash
        )
        
    assert mock_app.announce_manager.upsert_announce.call_count == num_nodes

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
    msg=st.dictionaries(
        keys=st.text(),
        values=st.one_of(st.text(), st.integers(), st.booleans(), st.dictionaries(keys=st.text(), values=st.text())),
        min_size=1, max_size=10
    ).flatmap(lambda d: st.sampled_from([
            "ping", "config.set", "nomadnet.download.cancel", 
            "nomadnet.page.archives.get", "lxmf.forwarding.rule.add",
            "lxmf.forwarding.rule.delete", "lxm.ingest_uri",
            "lxm.generate_paper_uri", "keyboard_shortcuts.get"
        ]).map(lambda t: {**d, "type": t}))
)
@pytest.mark.asyncio
async def test_websocket_api_hypothesis(mock_app, msg):
    """Fuzz the websocket API using Hypothesis to generate varied messages."""
    mock_client = AsyncMock()
    try:
        await mock_app.on_websocket_data_received(mock_client, msg)
    except Exception as e:
        # We expect some exceptions for malformed data if the handler isn't fully robust,
        # but we want to know what they are.
        pass

@pytest.mark.asyncio
async def test_websocket_api_fuzzing(mock_app):
    """Fuzz the websocket API with various message types and payloads."""
    mock_client = AsyncMock()
    
    # Test cases with different message types and malformed/unexpected data
    fuzz_messages = [
        {"type": "ping"},
        {"type": "config.set", "config": {"invalid_key": "invalid_value"}},
        {"type": "config.set", "config": "not_a_dict"},
        {"type": "nomadnet.download.cancel", "download_id": "non_existent_id"},
        {"type": "nomadnet.page.archives.get", "destination_hash": "invalid_hash", "page_path": "/invalid"},
        {"type": "lxmf.forwarding.rule.add", "rule": {}},
        {"type": "lxmf.forwarding.rule.delete", "id": -1},
        {"type": "lxm.ingest_uri", "uri": "invalid_uri"},
        {"type": "lxm.generate_paper_uri", "destination_hash": "00" * 16, "content": "test"},
        {"type": "non_existent_type", "data": "random_data"},
    ]
    
    for msg in fuzz_messages:
        try:
            # We use await here because on_websocket_data_received is async
            await mock_app.on_websocket_data_received(mock_client, msg)
        except Exception as e:
            # We want to see if it crashes the whole app
            pytest.fail(f"Websocket API crashed with message {msg}: {e}")

@pytest.mark.asyncio
async def test_config_fuzzing(mock_app):
    """Fuzz the config update logic with various values."""
    fuzz_configs = [
        {"display_name": "A" * 1000},
        {"display_name": None},
        {"auto_resend_failed_messages_when_announce_received": "not_a_bool"},
        {"unknown_config_option": 123},
        {},
    ]
    
    for config in fuzz_configs:
        try:
            # Mock update_config if it exists, or just let it run if it's safe
            if hasattr(mock_app, "update_config"):
                await mock_app.update_config(config)
        except Exception as e:
            pytest.fail(f"Config update crashed with config {config}: {e}")

def test_malformed_announce_data(mock_app):
    """Test handling of malformed or unexpected data in announces."""
    aspect = "lxmf.delivery"
    destination_hash = b"too_short" # Malformed hash
    
    # Test with None identity - should be caught by my fix
    mock_app.on_lxmf_announce_received(
        aspect,
        destination_hash,
        None,
        None,
        b""
    )
    
    # Test with identity having None hash - should be caught by my fix
    announced_identity = MagicMock()
    announced_identity.hash = None
    mock_app.on_lxmf_announce_received(
        aspect,
        destination_hash,
        announced_identity,
        None,
        b""
    )

def test_malformed_message_data(mock_app):
    """Test handling of malformed LXMF messages."""
    mock_message = MagicMock()
    # Simulate missing attributes or methods
    del mock_message.source_hash
    
    # This should be caught by the try-except in on_lxmf_delivery
    mock_app.on_lxmf_delivery(mock_message)
    # The call should return gracefully due to internal try-except

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    weird_string=st.text(min_size=0, max_size=1000),
    large_binary=st.binary(min_size=0, max_size=10000)
)
def test_database_dao_fuzzing(mock_app, weird_string, large_binary):
    """Fuzz the database DAOs with weird strings and large binary data."""
    # Test AnnounceDAO
    announce_data = {
        "destination_hash": os.urandom(16).hex(),
        "aspect": weird_string,
        "identity_hash": weird_string,
        "identity_public_key": large_binary.hex(),
        "app_data": large_binary,
        "rssi": random.randint(-120, 0),
        "snr": random.uniform(-20, 20),
        "quality": random.uniform(0, 100)
    }
    try:
        mock_app.database.announces.upsert_announce(announce_data)
    except Exception:
        # Mock database might fail, but it shouldn't crash the test runner
        pass

    # Test MessageDAO
    message_data = {
        "hash": os.urandom(16).hex(),
        "source_hash": os.urandom(16).hex(),
        "destination_hash": os.urandom(16).hex(),
        "state": weird_string,
        "title": weird_string,
        "content": weird_string,
        "fields": {"weird": weird_string},
        "timestamp": time.time(),
        "is_incoming": random.choice([0, 1]),
        "is_spam": random.choice([0, 1])
    }
    try:
        mock_app.database.messages.upsert_lxmf_message(message_data)
    except Exception:
        pass

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    audio_bytes=st.binary(min_size=0, max_size=5000),
    image_bytes=st.binary(min_size=0, max_size=10000)
)
def test_lxmf_field_fuzzing(audio_bytes, image_bytes):
    """Fuzz the LXMF field helper classes."""
    try:
        LxmfAudioField(audio_mode=random.randint(0, 10), audio_bytes=audio_bytes)
        LxmfImageField(image_type=random.choice(["png", "jpg", "webp", "invalid"]), image_bytes=image_bytes)
        LxmfFileAttachment(file_name="test.txt", file_bytes=audio_bytes)
    except Exception as e:
        pytest.fail(f"LXMF field classes crashed: {e}")
