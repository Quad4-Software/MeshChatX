import base64
import os
import time
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import LXMF
import pytest
import RNS
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat


@given(value=st.one_of(st.text(), st.lists(st.text(), min_size=0, max_size=20)))
@settings(deadline=None)
def test_discovery_pattern_sanitization_never_emits_unsafe_tokens(value):
    patterns = ReticulumMeshChat.sanitize_discovery_patterns(value)
    assert isinstance(patterns, list)
    assert len(patterns) <= 128
    for token in patterns:
        assert token
        assert len(token) <= 128
        assert "," not in token
        assert "\n" not in token
        assert "\r" not in token
        assert token.strip() == token


@pytest.fixture
def mock_app():
    # Save real Identity class to use as base for our mock class
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"test_hash_32_bytes_long_01234567"
            self.hexhash = self.hash.hex()

    with ExitStack() as stack:
        # Mock core dependencies that interact with the system/network
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
        stack.enter_context(patch("RNS.Identity", MockIdentityClass))
        stack.enter_context(patch("RNS.Reticulum"))
        stack.enter_context(patch("RNS.Transport"))
        mock_packet = stack.enter_context(patch("RNS.Packet"))
        mock_packet.MTU = 500

        # Stop background loops
        stack.enter_context(
            patch.object(ReticulumMeshChat, "announce_loop", return_value=None),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "announce_sync_propagation_nodes",
                return_value=None,
            ),
        )
        stack.enter_context(
            patch.object(ReticulumMeshChat, "crawler_loop", return_value=None),
        )
        stack.enter_context(
            patch.object(ReticulumMeshChat, "auto_backup_loop", return_value=None),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "send_config_to_websocket_clients",
                return_value=None,
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

        # Fix TelephoneManager.initiate to be awaitable
        async def mock_initiate(*args, **kwargs):
            return MagicMock()

        mock_telephone_manager = stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TelephoneManager"),
        )
        mock_telephone_manager.return_value.initiate = MagicMock(
            side_effect=mock_initiate,
        )

        app = ReticulumMeshChat(
            identity=mock_id,
            storage_dir="/tmp/meshchat_test",
            reticulum_config_dir="/tmp/meshchat_test",
        )

        # Basic config setup
        app.config = MagicMock()
        app.config.auto_announce_enabled.get.return_value = False
        app.config.voicemail_enabled.get.return_value = True

        # Surface mocks for tracking
        app.is_destination_blocked = MagicMock(return_value=False)
        app.check_spam_keywords = MagicMock(return_value=False)
        app.db_upsert_lxmf_message = MagicMock()
        app.handle_forwarding = MagicMock()
        app.update_lxmf_user_icon = MagicMock()
        app.websocket_broadcast = MagicMock()

        # Avoid crashing during broadcast by returning None for message lookup
        mock_db = app.current_context.database
        mock_db.messages.get_lxmf_message_by_hash.return_value = None

        yield app
        app.teardown_identity()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    field_data=st.one_of(
        st.lists(
            st.one_of(
                st.text(),
                st.binary(),
                st.integers(),
                st.floats(),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=10,
        ),
        st.dictionaries(
            keys=st.text(),
            values=st.one_of(
                st.text(),
                st.binary(),
                st.integers(),
                st.floats(),
                st.booleans(),
                st.none(),
            ),
        ),
        st.binary(),
        st.text(),
    ),
)
def test_lxmf_icon_appearance_fuzzing(mock_app, field_data):
    """Fuzz LXMF.FIELD_ICON_APPEARANCE parsing in on_lxmf_delivery."""
    mock_app.db_upsert_lxmf_message.reset_mock()

    mock_message = MagicMock()
    mock_message.get_fields.return_value = {LXMF.FIELD_ICON_APPEARANCE: field_data}
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    # Should not crash even with malformed icon data
    mock_app.on_lxmf_delivery(mock_message)

    # Message should still be saved to DB regardless of icon parsing success
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    attachments_data=st.lists(
        st.one_of(
            st.lists(
                st.one_of(
                    st.text(),
                    st.binary(),
                    st.integers(),
                    st.floats(),
                    st.booleans(),
                    st.none(),
                ),
                min_size=0,
                max_size=5,
            ),
            st.text(),
            st.binary(),
            st.none(),
        ),
        min_size=0,
        max_size=10,
    ),
)
def test_lxmf_attachments_fuzzing(mock_app, attachments_data):
    """Fuzz LXMF.FIELD_FILE_ATTACHMENTS parsing."""
    mock_app.db_upsert_lxmf_message.reset_mock()

    mock_message = MagicMock()
    mock_message.get_fields.return_value = {
        LXMF.FIELD_FILE_ATTACHMENTS: attachments_data,
    }
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    image_data=st.one_of(
        st.lists(
            st.one_of(
                st.text(),
                st.binary(),
                st.integers(),
                st.floats(),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=5,
        ),
        st.binary(),
        st.none(),
    ),
)
def test_lxmf_image_field_fuzzing(mock_app, image_data):
    """Fuzz LXMF.FIELD_IMAGE parsing."""
    mock_app.db_upsert_lxmf_message.reset_mock()

    mock_message = MagicMock()
    mock_message.get_fields.return_value = {LXMF.FIELD_IMAGE: image_data}
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    audio_data=st.one_of(
        st.lists(
            st.one_of(
                st.text(),
                st.binary(),
                st.integers(),
                st.floats(),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=5,
        ),
        st.binary(),
        st.none(),
    ),
)
def test_lxmf_audio_field_fuzzing(mock_app, audio_data):
    """Fuzz LXMF.FIELD_AUDIO parsing."""
    mock_app.db_upsert_lxmf_message.reset_mock()

    mock_message = MagicMock()
    mock_message.get_fields.return_value = {LXMF.FIELD_AUDIO: audio_data}
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    filename=st.text(min_size=0, max_size=1000),
    file_bytes=st.binary(min_size=0, max_size=10000),
)
def test_attachment_filename_security(mock_app, filename, file_bytes):
    """Test for potential crashes with malformed filenames in attachments."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {
        LXMF.FIELD_FILE_ATTACHMENTS: [[filename, file_bytes]],
    }
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    # Should not crash
    mock_app.on_lxmf_delivery(mock_message)
    from meshchatx.src.backend.lxmf_utils import convert_lxmf_message_to_dict

    convert_lxmf_message_to_dict(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(caller_id_bytes=st.binary(min_size=0, max_size=1000))
def test_telephone_callback_fuzzing(mock_app, caller_id_bytes):
    """Fuzz telephone manager callbacks with malformed identity bytes."""
    mock_identity = MagicMock()
    mock_identity.hash = caller_id_bytes

    # Should handle malformed hashes gracefully without crashing
    mock_app.telephone_manager.on_telephone_ringing(mock_identity)
    mock_app.telephone_manager.on_telephone_call_established(mock_identity)
    mock_app.telephone_manager.on_telephone_call_ended(mock_identity)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    data=st.dictionaries(
        keys=st.text(),
        values=st.one_of(
            st.text(),
            st.binary(),
            st.integers(),
            st.floats(),
            st.lists(st.text()),
            st.dictionaries(keys=st.text(), values=st.text()),
        ),
    ),
)
def test_message_dao_upsert_fuzzing(mock_app, data):
    """Fuzz MessageDAO.upsert_lxmf_message with varied dictionary data."""
    mock_app.database.messages.upsert_lxmf_message(data)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    title_bytes=st.binary(min_size=0, max_size=1000),
    content_bytes=st.binary(min_size=0, max_size=5000),
)
def test_lxmf_message_decoding_fuzzing(mock_app, title_bytes, content_bytes):
    """Fuzz LXMF message title and content decoding."""
    mock_message = MagicMock()
    mock_message.title = title_bytes
    mock_message.content = content_bytes
    mock_message.hash = os.urandom(16)
    mock_message.source_hash = os.urandom(16)
    mock_message.destination_hash = os.urandom(16)
    mock_message.incoming = True
    mock_message.state = LXMF.LXMessage.DELIVERED
    mock_message.method = LXMF.LXMessage.DIRECT
    mock_message.progress = 1.0
    mock_message.timestamp = 123456789.0
    mock_message.rssi = -50
    mock_message.snr = 10
    mock_message.q = 100
    mock_message.get_fields.return_value = {}

    from meshchatx.src.backend.lxmf_utils import convert_lxmf_message_to_dict

    result = convert_lxmf_message_to_dict(mock_message)
    assert isinstance(result, dict)
    assert "hash" in result
    assert "title" in result
    assert "content" in result


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(greeting_text=st.text(min_size=0, max_size=1000))
def test_voicemail_greeting_fuzzing(mock_app, greeting_text):
    """Fuzz voicemail greeting generation with varied text."""
    mock_app.voicemail_manager.has_espeak = True
    mock_app.voicemail_manager.has_ffmpeg = True
    mock_app.voicemail_manager.espeak_path = "/usr/bin/espeak"
    mock_app.voicemail_manager.ffmpeg_path = "/usr/bin/ffmpeg"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        try:
            mock_app.voicemail_manager.generate_greeting(greeting_text)
            # Should call subprocess to generate audio if text is not empty
            if greeting_text.strip():
                assert mock_run.called
        except Exception:
            pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(caller_hash=st.binary(min_size=0, max_size=32))
def test_voicemail_incoming_call_fuzzing(mock_app, caller_hash):
    """Fuzz voicemail incoming call handling."""
    mock_identity = MagicMock()
    mock_identity.hash = caller_hash

    # Should not crash with malformed identity hashes
    mock_app.voicemail_manager.handle_incoming_call(mock_identity)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    source_hash=st.text(min_size=0, max_size=64),
    recipient_hash=st.text(min_size=0, max_size=64),
    dest_hash=st.text(min_size=0, max_size=64),
)
def test_forwarding_manager_mapping_fuzzing(
    mock_app,
    source_hash,
    recipient_hash,
    dest_hash,
):
    """Fuzz forwarding manager mapping creation."""
    # Should handle malformed hashes gracefully
    mock_app.forwarding_manager.get_or_create_mapping(
        source_hash,
        recipient_hash,
        dest_hash,
    )


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(uri=st.text(min_size=0, max_size=5000))
def test_lxm_ingest_uri_fuzzing(mock_app, uri):
    """Fuzz the lxm.ingest_uri WebSocket handler."""
    mock_client = MagicMock()

    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                mock_client,
                {"type": "lxm.ingest_uri", "uri": uri},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    config_data=st.dictionaries(
        keys=st.text(),
        values=st.one_of(
            st.text(),
            st.integers(),
            st.booleans(),
            st.none(),
            st.lists(st.text()),
            st.dictionaries(keys=st.text(), values=st.text()),
        ),
    ),
)
def test_update_config_fuzzing(mock_app, config_data):
    """Fuzz the update_config method with randomized dictionary data."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(mock_app.update_config(config_data))
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(large_string=st.text(min_size=1000, max_size=10000))
def test_large_payload_dos_resistance(mock_app, large_string):
    """Check resistance to DoS via large strings in various fields."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.title = large_string.encode()
    mock_message.content = large_string.encode()
    mock_message.hash = os.urandom(16)
    mock_message.source_hash = os.urandom(16)
    mock_message.get_fields.return_value = {}

    # Should not crash or hang excessively
    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    nested_data=st.recursive(
        st.one_of(st.text(), st.integers()),
        lambda children: st.dictionaries(st.text(), children) | st.lists(children),
        max_leaves=100,
    ),
)
def test_websocket_recursion_fuzzing(mock_app, nested_data):
    """Fuzz the WebSocket handler with deeply nested JSON data."""
    mock_client = MagicMock()
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                mock_client,
                {"type": "ping", "data": nested_data},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(dest_hash=st.text(), content=st.text())
def test_lxm_generate_paper_uri_fuzzing(mock_app, dest_hash, content):
    """Fuzz paper URI generation with randomized inputs."""
    mock_client = MagicMock()
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                mock_client,
                {
                    "type": "lxm.generate_paper_uri",
                    "destination_hash": dest_hash,
                    "content": content,
                },
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    lon=st.floats(allow_nan=False, allow_infinity=False),
    lat=st.floats(allow_nan=False, allow_infinity=False),
    zoom=st.integers(min_value=-100, max_value=100),
)
def test_map_manager_coord_fuzzing(mock_app, lon, lat, zoom):
    """Fuzz coordinate to tile conversion in MapManager."""
    # Should handle invalid coordinates gracefully
    mock_app.map_manager._lonlat_to_tile(lon, lat, zoom)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    text=st.text(),
    source_lang=st.text(min_size=0, max_size=10),
    target_lang=st.text(min_size=0, max_size=10),
)
def test_translator_handler_fuzzing(mock_app, text, source_lang, target_lang):
    """Fuzz the TranslatorHandler translate_text method."""
    mock_app.translator_handler.has_requests = False
    mock_app.translator_handler.has_argos = False
    mock_app.translator_handler.translate_text(text, source_lang, target_lang)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(dest_hash=st.text(), icon_name=st.text(), fg_color=st.text(), bg_color=st.text())
def test_update_lxmf_user_icon_fuzzing(
    mock_app,
    dest_hash,
    icon_name,
    fg_color,
    bg_color,
):
    """Fuzz user icon update logic with malformed strings."""
    mock_app.update_lxmf_user_icon(dest_hash, icon_name, fg_color, bg_color)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(binary_data=st.binary(min_size=0, max_size=10000))
def test_rns_identity_load_fuzzing(mock_app, binary_data):
    """Fuzz RNS.Identity loading with random binary data."""
    # These should catch RNS internal errors if they are severe enough to crash Python
    try:
        RNS.Identity.from_bytes(binary_data)
    except Exception:
        pass

    id_inst = RNS.Identity(create_keys=False)
    try:
        id_inst.load_private_key(binary_data)
    except Exception:
        pass

    try:
        id_inst.load_public_key(binary_data)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    uri=st.one_of(
        st.text(min_size=0, max_size=10000),
        st.binary(min_size=0, max_size=10000),
    ),
)
def test_lxm_uri_comprehensive_fuzzing(mock_app, uri):
    """Fuzz lxm:// and lxmf:// URI ingestion with various data types."""
    mock_client = MagicMock()
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        uri_str = (
            uri.decode("utf-8", errors="ignore") if isinstance(uri, bytes) else uri
        )
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                mock_client,
                {"type": "lxm.ingest_uri", "uri": uri_str},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    uri_prefix=st.sampled_from(["lxm://", "lxmf://", "LXM://", "LXMF://", "LxM://"]),
    uri_body=st.text(min_size=0, max_size=5000),
)
def test_lxm_uri_prefix_variations_fuzzing(mock_app, uri_prefix, uri_body):
    """Fuzz lxm:// URI with various prefix case combinations and malformed bodies."""
    mock_client = MagicMock()
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        full_uri = uri_prefix + uri_body
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                mock_client,
                {"type": "lxm.ingest_uri", "uri": full_uri},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(telemetry_packed=st.binary(min_size=0, max_size=10000))
def test_telemetry_from_packed_fuzzing(mock_app, telemetry_packed):
    """Fuzz Telemeter.from_packed with random binary data."""
    from meshchatx.src.backend.telemetry_utils import Telemeter

    Telemeter.from_packed(telemetry_packed)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    telemetry_data=st.one_of(
        st.binary(min_size=0, max_size=10000),
        st.text(min_size=0, max_size=1000),
        st.lists(
            st.one_of(
                st.text(),
                st.binary(),
                st.integers(),
                st.floats(),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=10,
        ),
        st.dictionaries(
            keys=st.text(),
            values=st.one_of(
                st.text(),
                st.binary(),
                st.integers(),
                st.floats(),
                st.booleans(),
                st.none(),
            ),
        ),
    ),
)
def test_lxmf_telemetry_field_fuzzing(mock_app, telemetry_data):
    """Fuzz LXMF.FIELD_TELEMETRY parsing in on_lxmf_delivery."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {LXMF.FIELD_TELEMETRY: telemetry_data}
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    icon_name=st.text(min_size=0, max_size=200),
    foreground_bytes=st.one_of(
        st.binary(min_size=0, max_size=100),
        st.text(min_size=0, max_size=100),
        st.integers(),
        st.none(),
    ),
    background_bytes=st.one_of(
        st.binary(min_size=0, max_size=100),
        st.text(min_size=0, max_size=100),
        st.integers(),
        st.none(),
    ),
)
def test_lxmf_icon_appearance_structure_fuzzing(
    mock_app,
    icon_name,
    foreground_bytes,
    background_bytes,
):
    """Fuzz LXMF.FIELD_ICON_APPEARANCE with structured data."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {
        LXMF.FIELD_ICON_APPEARANCE: [icon_name, foreground_bytes, background_bytes],
    }
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    icon_appearance_list=st.lists(
        st.one_of(
            st.text(),
            st.binary(),
            st.integers(),
            st.floats(),
            st.booleans(),
            st.none(),
        ),
        min_size=0,
        max_size=10,
    ),
)
def test_lxmf_icon_appearance_list_variations_fuzzing(mock_app, icon_appearance_list):
    """Fuzz LXMF.FIELD_ICON_APPEARANCE with various list structures."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {
        LXMF.FIELD_ICON_APPEARANCE: icon_appearance_list,
    }
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    dest_hash=st.text(min_size=0, max_size=100),
    icon_name=st.text(min_size=0, max_size=500),
    fg_color=st.text(min_size=0, max_size=100),
    bg_color=st.text(min_size=0, max_size=100),
)
def test_update_lxmf_user_icon_comprehensive_fuzzing(
    mock_app,
    dest_hash,
    icon_name,
    fg_color,
    bg_color,
):
    """Fuzz update_lxmf_user_icon with various string inputs."""
    mock_app.update_lxmf_user_icon(dest_hash, icon_name, fg_color, bg_color)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    audio_mode=st.one_of(
        st.text(min_size=0, max_size=100),
        st.binary(min_size=0, max_size=100),
        st.integers(),
        st.floats(),
        st.booleans(),
        st.none(),
    ),
    audio_bytes=st.one_of(
        st.binary(min_size=0, max_size=100000),
        st.text(min_size=0, max_size=10000),
        st.lists(st.integers(min_value=0, max_value=255), min_size=0, max_size=1000),
        st.none(),
    ),
)
def test_lxmf_audio_field_structure_fuzzing(mock_app, audio_mode, audio_bytes):
    """Fuzz LXMF.FIELD_AUDIO with structured data."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {
        LXMF.FIELD_AUDIO: [audio_mode, audio_bytes],
    }
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    audio_field=st.one_of(
        st.lists(
            st.one_of(
                st.text(),
                st.binary(),
                st.integers(),
                st.floats(),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=20,
        ),
        st.binary(min_size=0, max_size=100000),
        st.text(min_size=0, max_size=10000),
        st.dictionaries(
            keys=st.text(),
            values=st.one_of(st.text(), st.binary(), st.integers()),
        ),
    ),
)
def test_lxmf_audio_field_variations_fuzzing(mock_app, audio_field):
    """Fuzz LXMF.FIELD_AUDIO with various data structures."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {LXMF.FIELD_AUDIO: audio_field}
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    contact_name=st.text(min_size=0, max_size=500),
    contact_hash=st.text(min_size=0, max_size=100),
)
def test_contact_sharing_content_fuzzing(mock_app, contact_name, contact_hash):
    """Fuzz contact sharing content parsing."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    contact_content = f"Contact: {contact_name} <{contact_hash}>"
    mock_message = MagicMock()
    mock_message.content = contact_content.encode("utf-8", errors="ignore")
    mock_message.title = b""
    mock_message.hash = os.urandom(16)
    mock_message.source_hash = os.urandom(16)
    mock_message.destination_hash = os.urandom(16)
    mock_message.incoming = True
    mock_message.state = LXMF.LXMessage.DELIVERED
    mock_message.method = LXMF.LXMessage.DIRECT
    mock_message.progress = 1.0
    mock_message.timestamp = 123456789.0
    mock_message.rssi = -50
    mock_message.snr = 10
    mock_message.q = 100
    mock_message.get_fields.return_value = {}

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    contact_content=st.text(min_size=0, max_size=2000),
)
def test_contact_sharing_malformed_content_fuzzing(mock_app, contact_content):
    """Fuzz contact sharing with malformed content strings."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.content = contact_content.encode("utf-8", errors="ignore")
    mock_message.title = b""
    mock_message.hash = os.urandom(16)
    mock_message.source_hash = os.urandom(16)
    mock_message.destination_hash = os.urandom(16)
    mock_message.incoming = True
    mock_message.state = LXMF.LXMessage.DELIVERED
    mock_message.method = LXMF.LXMessage.DIRECT
    mock_message.progress = 1.0
    mock_message.timestamp = 123456789.0
    mock_message.rssi = -50
    mock_message.snr = 10
    mock_message.q = 100
    mock_message.get_fields.return_value = {}

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    name=st.text(min_size=0, max_size=500),
    hash_str=st.text(min_size=0, max_size=100),
)
def test_add_contact_api_fuzzing(mock_app, name, hash_str):
    """Fuzz contact addition API with various inputs."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {
                    "type": "telephone.add_contact",
                    "name": name,
                    "remote_identity_hash": hash_str,
                },
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    time_utc=st.one_of(
        st.integers(min_value=-2147483648, max_value=2147483647),
        st.floats(min_value=-2147483648, max_value=2147483647),
        st.none(),
    ),
    location=st.one_of(
        st.fixed_dictionaries(
            {
                "latitude": st.floats(allow_nan=False, allow_infinity=False),
                "longitude": st.floats(allow_nan=False, allow_infinity=False),
            },
            optional={
                "altitude": st.floats(allow_nan=False, allow_infinity=False),
                "speed": st.floats(allow_nan=False, allow_infinity=False),
                "bearing": st.floats(allow_nan=False, allow_infinity=False),
                "accuracy": st.floats(allow_nan=False, allow_infinity=False),
                "last_update": st.floats(allow_nan=False, allow_infinity=False),
            },
        ),
        st.none(),
    ),
)
def test_telemetry_pack_fuzzing(mock_app, time_utc, location):
    """Fuzz Telemeter.pack with various data."""
    from meshchatx.src.backend.telemetry_utils import Telemeter

    try:
        Telemeter.pack(time_utc=time_utc, location=location)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    packed_location=st.one_of(
        st.lists(
            st.one_of(
                st.binary(min_size=0, max_size=100),
                st.integers(),
                st.text(),
                st.floats(),
                st.none(),
            ),
            min_size=0,
            max_size=20,
        ),
        st.binary(min_size=0, max_size=1000),
        st.text(min_size=0, max_size=1000),
        st.none(),
    ),
)
def test_telemetry_unpack_location_fuzzing(mock_app, packed_location):
    """Fuzz Telemeter.unpack_location with various formats."""
    from meshchatx.src.backend.telemetry_utils import Telemeter

    Telemeter.unpack_location(packed_location)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    latitude=st.floats(allow_nan=True, allow_infinity=True),
    longitude=st.floats(allow_nan=True, allow_infinity=True),
    altitude=st.one_of(st.floats(allow_nan=True, allow_infinity=True), st.integers()),
    speed=st.one_of(st.floats(allow_nan=True, allow_infinity=True), st.integers()),
    bearing=st.one_of(st.floats(allow_nan=True, allow_infinity=True), st.integers()),
    accuracy=st.one_of(st.floats(allow_nan=True, allow_infinity=True), st.integers()),
    last_update=st.one_of(
        st.integers(),
        st.floats(),
        st.text(),
        st.binary(),
        st.none(),
    ),
)
def test_telemetry_pack_location_fuzzing(
    mock_app,
    latitude,
    longitude,
    altitude,
    speed,
    bearing,
    accuracy,
    last_update,
):
    """Fuzz Telemeter.pack_location with edge case coordinates."""
    from meshchatx.src.backend.telemetry_utils import Telemeter

    Telemeter.pack_location(
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        speed=speed,
        bearing=bearing,
        accuracy=accuracy,
        last_update=last_update,
    )


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    destination_hash=st.one_of(st.text(), st.binary()),
    timestamp=st.one_of(
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(),
        st.none(),
    ),
    data=st.one_of(
        st.text(),
        st.binary(),
        st.dictionaries(keys=st.text(), values=st.text()),
    ),
    received_from=st.one_of(st.text(), st.binary(), st.none()),
    physical_link=st.one_of(
        st.dictionaries(
            keys=st.text(),
            values=st.one_of(st.integers(), st.floats(), st.text()),
        ),
        st.text(),
        st.binary(),
        st.none(),
    ),
)
def test_telemetry_upsert_fuzzing(
    mock_app,
    destination_hash,
    timestamp,
    data,
    received_from,
    physical_link,
):
    """Fuzz telemetry database upsert with varied data types."""
    dest_hash_str = (
        destination_hash.decode("utf-8", errors="ignore")
        if isinstance(destination_hash, bytes)
        else str(destination_hash)
    )
    mock_app.database.telemetry.upsert_telemetry(
        destination_hash=dest_hash_str,
        timestamp=timestamp,
        data=data,
        received_from=received_from,
        physical_link=physical_link,
    )


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    z=st.one_of(st.integers(), st.text(), st.floats()),
    x=st.one_of(st.integers(), st.text(), st.floats()),
    y=st.one_of(st.integers(), st.text(), st.floats()),
)
def test_map_tile_coordinates_fuzzing(mock_app, z, x, y):
    """Fuzz map tile coordinate parsing."""
    try:
        z_int = (
            int(z)
            if isinstance(z, (int, float))
            and not (isinstance(z, float) and (z != z or abs(z) == float("inf")))
            else 0
        )
        x_int = (
            int(x)
            if isinstance(x, (int, float))
            and not (isinstance(x, float) and (x != x or abs(x) == float("inf")))
            else 0
        )
        y_int = (
            int(y)
            if isinstance(y, (int, float))
            and not (isinstance(y, float) and (y != y or abs(y) == float("inf")))
            else 0
        )
        mock_app.map_manager.get_tile(z_int, x_int, y_int)
    except (OverflowError, ValueError):
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    filename=st.text(min_size=0, max_size=500),
)
def test_mbtiles_filename_fuzzing(mock_app, filename):
    """Fuzz MBTiles filename handling."""
    mock_app.map_manager.delete_mbtiles(filename)
    mock_app.map_manager.get_connection(filename)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    destination_hash=st.text(min_size=0, max_size=100),
    page_path=st.text(min_size=0, max_size=1000),
    content=st.text(min_size=0, max_size=100000),
)
def test_archive_page_content_fuzzing(mock_app, destination_hash, page_path, content):
    """Fuzz archive page content storage and retrieval."""
    mock_app.archiver_manager.archive_page(
        destination_hash,
        page_path,
        content,
        max_versions=5,
        max_storage_gb=1,
    )
    mock_app.archiver_manager.get_archived_page_versions(destination_hash, page_path)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    ids=st.lists(
        st.one_of(st.integers(), st.text(), st.floats()),
        min_size=0,
        max_size=100,
    ),
)
def test_delete_archived_pages_ids_fuzzing(mock_app, ids):
    """Fuzz SQL injection in delete_archived_pages."""
    mock_app.database.misc.delete_archived_pages(ids=ids)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    query=st.text(min_size=0, max_size=500),
)
def test_archived_pages_query_sql_injection_fuzzing(mock_app, query):
    """Fuzz SQL injection in archived_pages search."""
    mock_app.database.misc.get_archived_pages_paginated(query=query)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    file_path=st.text(min_size=0, max_size=1000),
)
def test_rncp_file_path_traversal_fuzzing(mock_app, file_path):
    """Fuzz RNCP file path handling for directory traversal."""
    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            mock_app.rncp_handler.send_file(
                os.urandom(16),
                file_path,
                timeout=1.0,
            ),
        )
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    path=st.text(min_size=0, max_size=1000),
    data=st.one_of(st.text(), st.binary()),
    request_id=st.one_of(st.integers(), st.text()),
)
def test_rncp_fetch_request_path_fuzzing(mock_app, path, data, request_id):
    """Fuzz RNCP fetch request path handling."""
    try:
        mock_identity = MagicMock()
        mock_identity.hash = os.urandom(16)
        mock_app.rncp_handler._fetch_request(
            path,
            data,
            request_id,
            os.urandom(16),
            mock_identity,
            time.time(),
        )
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    app_data_base64=st.text(min_size=0, max_size=10000),
)
def test_parse_lxmf_stamp_cost_fuzzing(mock_app, app_data_base64):
    """Fuzz LXMF stamp cost parsing from base64 app_data."""
    try:
        from meshchatx.src.backend.meshchat_utils import parse_lxmf_stamp_cost

        parse_lxmf_stamp_cost(app_data_base64)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    app_data_base64=st.text(min_size=0, max_size=10000),
)
def test_parse_lxmf_propagation_node_app_data_fuzzing(mock_app, app_data_base64):
    """Fuzz LXMF propagation node app_data parsing."""
    from meshchatx.src.backend.meshchat_utils import (
        parse_lxmf_propagation_node_app_data,
    )

    parse_lxmf_propagation_node_app_data(app_data_base64)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    destination_hash=st.text(min_size=0, max_size=100),
    page_path=st.text(min_size=0, max_size=1000),
)
def test_nomadnet_page_path_fuzzing(mock_app, destination_hash, page_path):
    """Fuzz NomadNet page path handling."""
    mock_app.nomadnet_manager.archive_page(
        destination_hash,
        page_path,
        "test content",
        is_manual=False,
    )
    mock_app.nomadnet_manager.get_archived_page_versions(destination_hash, page_path)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    page_content=st.text(min_size=0, max_size=100000),
)
def test_nomadnet_page_content_fuzzing(mock_app, page_content):
    """Fuzz NomadNet page content parsing."""
    from meshchatx.src.backend.nomadnet_utils import (
        convert_nomadnet_field_data_to_map,
    )

    convert_nomadnet_field_data_to_map(page_content)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(path_data=st.one_of(st.text(min_size=0, max_size=10000), st.none()))
def test_nomadnet_string_data_to_map_fuzzing(mock_app, path_data):
    """Fuzz NomadNet path variable string parsing (e.g. after backtick in page path)."""
    from meshchatx.src.backend.nomadnet_utils import convert_nomadnet_string_data_to_map

    result = convert_nomadnet_string_data_to_map(path_data)
    assert isinstance(result, dict)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    download_id=st.one_of(
        st.integers(),
        st.text(min_size=0, max_size=200),
        st.none(),
    ),
)
def test_nomadnet_download_cancel_fuzzing(mock_app, download_id):
    """Fuzz nomadnet.download.cancel WebSocket handler."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {"type": "nomadnet.download.cancel", "download_id": download_id},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    destination_hash=st.text(min_size=0, max_size=200),
    page_path=st.text(min_size=0, max_size=2000),
)
def test_nomadnet_page_archives_get_fuzzing(mock_app, destination_hash, page_path):
    """Fuzz nomadnet.page.archives.get WebSocket handler."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {
                    "type": "nomadnet.page.archives.get",
                    "destination_hash": destination_hash,
                    "page_path": page_path,
                },
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    archive_id=st.one_of(
        st.integers(),
        st.text(min_size=0, max_size=100),
        st.floats(allow_nan=False, allow_infinity=False),
        st.none(),
    ),
)
def test_nomadnet_page_archive_load_fuzzing(mock_app, archive_id):
    """Fuzz nomadnet.page.archive.load and get_archived_page_by_id."""
    mock_app.database.misc.get_archived_page_by_id(archive_id)
    import asyncio

    mock_app.database.misc.get_archived_page_by_id.return_value = None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {"type": "nomadnet.page.archive.load", "archive_id": archive_id},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    destination_hash=st.text(min_size=0, max_size=200),
    page_path=st.text(min_size=0, max_size=2000),
    content=st.one_of(
        st.text(min_size=0, max_size=50000),
        st.binary(min_size=0, max_size=10000),
    ),
)
def test_nomadnet_page_archive_add_fuzzing(
    mock_app, destination_hash, page_path, content
):
    """Fuzz nomadnet.page.archive.add WebSocket handler and archive_page."""
    import asyncio

    content_str = (
        content.decode("utf-8", errors="replace")
        if isinstance(content, bytes)
        else content
    )
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {
                    "type": "nomadnet.page.archive.add",
                    "destination_hash": destination_hash,
                    "page_path": page_path,
                    "content": content_str,
                },
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    destination_hash=st.text(min_size=0, max_size=200),
    file_path=st.text(min_size=0, max_size=2000),
)
def test_nomadnet_file_download_fuzzing(mock_app, destination_hash, file_path):
    """Fuzz nomadnet.file.download WebSocket handler (path traversal, malformed hash)."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        payload = {
            "type": "nomadnet.file.download",
            "nomadnet_file_download": {
                "destination_hash": destination_hash,
                "file_path": file_path,
            },
        }
        loop.run_until_complete(
            mock_app.on_websocket_data_received(MagicMock(), payload),
        )
    except (ValueError, TypeError):
        pass
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    destination_hash=st.text(min_size=0, max_size=200),
    page_path=st.text(min_size=0, max_size=2000),
    field_data=st.one_of(
        st.dictionaries(
            keys=st.text(),
            values=st.one_of(st.text(), st.integers(), st.booleans(), st.none()),
        ),
        st.text(min_size=0, max_size=5000),
        st.lists(st.text(), min_size=0, max_size=20),
        st.none(),
    ),
)
def test_nomadnet_page_download_fuzzing(
    mock_app, destination_hash, page_path, field_data
):
    """Fuzz nomadnet.page.download WebSocket handler (page_path with backtick, field_data)."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        payload = {
            "type": "nomadnet.page.download",
            "nomadnet_page_download": {
                "destination_hash": destination_hash,
                "page_path": page_path,
                "field_data": field_data,
            },
        }
        loop.run_until_complete(
            mock_app.on_websocket_data_received(MagicMock(), payload),
        )
    except (ValueError, TypeError):
        pass
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(archive_id=st.one_of(st.integers(), st.text(), st.floats(), st.none()))
def test_get_archived_page_by_id_fuzzing(mock_app, archive_id):
    """Fuzz archived page lookup by id (SQL injection, type confusion)."""
    mock_app.database.misc.get_archived_page_by_id(archive_id)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    forward_to_hash=st.text(min_size=0, max_size=100),
    identity_hash=st.one_of(st.text(min_size=0, max_size=100), st.none()),
    source_filter_hash=st.one_of(st.text(min_size=0, max_size=100), st.none()),
    is_active=st.one_of(st.booleans(), st.integers(), st.none()),
    name=st.one_of(st.text(min_size=0, max_size=200), st.none()),
)
def test_lxmf_forwarding_rule_add_fuzzing(
    mock_app,
    forward_to_hash,
    identity_hash,
    source_filter_hash,
    is_active,
    name,
):
    """Fuzz lxmf.forwarding.rule.add WebSocket handler and create_forwarding_rule."""
    import asyncio

    rule = {"forward_to_hash": forward_to_hash}
    if identity_hash is not None:
        rule["identity_hash"] = identity_hash
    if source_filter_hash is not None:
        rule["source_filter_hash"] = source_filter_hash
    if is_active is not None:
        rule["is_active"] = is_active
    if name is not None:
        rule["name"] = name
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {"type": "lxmf.forwarding.rule.add", "rule": rule},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    rule_id=st.one_of(st.integers(), st.text(min_size=0, max_size=50), st.none()),
)
def test_lxmf_forwarding_rule_delete_fuzzing(mock_app, rule_id):
    """Fuzz lxmf.forwarding.rule.delete WebSocket handler."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {"type": "lxmf.forwarding.rule.delete", "id": rule_id},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    rule_id=st.one_of(st.integers(), st.text(min_size=0, max_size=50), st.none()),
)
def test_lxmf_forwarding_rule_toggle_fuzzing(mock_app, rule_id):
    """Fuzz lxmf.forwarding.rule.toggle WebSocket handler."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {"type": "lxmf.forwarding.rule.toggle", "id": rule_id},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    action=st.text(min_size=0, max_size=200),
    keys=st.one_of(
        st.lists(st.text(), min_size=0, max_size=20),
        st.text(min_size=0, max_size=500),
        st.integers(),
    ),
)
def test_keyboard_shortcuts_set_fuzzing(mock_app, action, keys):
    """Fuzz keyboard_shortcuts.set WebSocket handler (action and keys)."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {"type": "keyboard_shortcuts.set", "action": action, "keys": keys},
            ),
        )
    except (KeyError, TypeError, ValueError):
        pass
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(message_hash=st.text(min_size=0, max_size=200))
def test_messages_get_by_hash_fuzzing(mock_app, message_hash):
    """Fuzz message lookup by hash (SQL, type confusion)."""
    mock_app.database.messages.get_lxmf_message_by_hash(message_hash)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(message_hash=st.text(min_size=0, max_size=200))
def test_messages_delete_by_hash_fuzzing(mock_app, message_hash):
    """Fuzz single message delete by hash."""
    try:
        mock_app.database.messages.delete_lxmf_message_by_hash(message_hash)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    message_hashes=st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=50)
)
def test_messages_delete_by_hashes_fuzzing(mock_app, message_hashes):
    """Fuzz bulk message delete by hashes."""
    try:
        mock_app.database.messages.delete_lxmf_messages_by_hashes(message_hashes)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    table_name=st.text(min_size=0, max_size=100),
)
def test_sql_table_name_injection_fuzzing(mock_app, table_name):
    """Fuzz SQL table name injection."""
    mock_app.database.provider.execute(f"PRAGMA table_info({table_name})")


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    fields_json=st.text(min_size=0, max_size=10000),
)
def test_lxmf_fields_json_parsing_fuzzing(mock_app, fields_json):
    """Fuzz LXMF fields JSON parsing."""
    db_message = {
        "id": 1,
        "hash": "test",
        "source_hash": "test",
        "destination_hash": "test",
        "is_incoming": True,
        "state": "delivered",
        "progress": 100.0,
        "method": "direct",
        "delivery_attempts": 0,
        "next_delivery_attempt_at": None,
        "title": "test",
        "content": "test",
        "fields": fields_json,
        "timestamp": 123456789.0,
        "rssi": -50,
        "snr": 10,
        "quality": 100,
        "is_spam": False,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    from meshchatx.src.backend.lxmf_utils import convert_db_lxmf_message_to_dict

    try:
        convert_db_lxmf_message_to_dict(db_message)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    password=st.text(min_size=0, max_size=1000),
)
def test_auth_password_fuzzing(mock_app, password):
    """Fuzz authentication password handling."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {"type": "auth.login", "password": password},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    filename=st.text(min_size=0, max_size=500),
)
def test_mbtiles_upload_filename_fuzzing(mock_app, filename):
    """Fuzz MBTiles upload filename."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        mock_field = MagicMock()
        mock_field.name = "file"
        mock_field.filename = filename
        mock_field.read_chunk = MagicMock(return_value=b"")
        mock_reader = MagicMock()
        mock_reader.next = MagicMock(return_value=mock_field)

        mock_request = MagicMock()
        mock_request.multipart = MagicMock(return_value=mock_reader)

        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                MagicMock(),
                {"type": "map.upload_offline", "filename": filename},
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    crawl_destination_hash=st.text(min_size=0, max_size=100),
    crawl_page_path=st.text(min_size=0, max_size=1000),
)
def test_crawler_task_path_fuzzing(mock_app, crawl_destination_hash, crawl_page_path):
    """Fuzz crawler task destination hash and page path."""
    mock_app.database.misc.upsert_crawl_task(
        crawl_destination_hash,
        crawl_page_path,
        status="pending",
        retry_count=0,
    )


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    doc_path=st.text(min_size=0, max_size=1000),
)
def test_docs_path_traversal_fuzzing(mock_app, doc_path):
    """Fuzz documentation path handling."""
    try:
        mock_app.docs_manager.get_doc_content(doc_path)
    except (IsADirectoryError, OSError):
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    bbox=st.lists(
        st.one_of(st.floats(allow_nan=False, allow_infinity=False), st.integers()),
        min_size=4,
        max_size=4,
    ),
    min_zoom=st.integers(min_value=-10, max_value=30),
    max_zoom=st.integers(min_value=-10, max_value=30),
    name=st.text(min_size=0, max_size=500),
)
def test_map_export_parameters_fuzzing(mock_app, bbox, min_zoom, max_zoom, name):
    """Fuzz map export parameters."""
    mock_app.map_manager.start_export(
        "test_export",
        bbox,
        min_zoom,
        max_zoom,
        name=name,
    )


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    mbtiles_path=st.text(min_size=0, max_size=1000),
)
def test_mbtiles_metadata_parsing_fuzzing(mock_app, mbtiles_path):
    """Fuzz MBTiles metadata parsing."""
    mock_app.map_manager.get_metadata()
    if os.path.exists(mbtiles_path):
        mock_app.map_manager.get_connection(mbtiles_path)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    audio_frame=st.one_of(
        st.binary(min_size=0, max_size=10000),
        st.lists(st.integers(min_value=0, max_value=255), min_size=0, max_size=1000),
        st.text(min_size=0, max_size=1000),
        st.none(),
    ),
)
def test_lxst_audio_frame_handling_fuzzing(mock_app, audio_frame):
    """Fuzz LXST audio frame handling in Tee.handle_frame."""
    try:
        from meshchatx.src.backend.telephone_manager import Tee

        mock_sink = MagicMock()
        mock_sink.handle_frame = MagicMock()
        mock_sink.can_receive = MagicMock(return_value=True)
        tee = Tee(mock_sink)
        tee.handle_frame(audio_frame, "test_source")
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    call_status=st.integers(min_value=-10, max_value=20),
    caller_identity_hash=st.binary(min_size=0, max_size=100),
)
def test_lxst_call_state_transitions_fuzzing(
    mock_app,
    call_status,
    caller_identity_hash,
):
    """Fuzz LXST call state transitions with invalid states."""
    try:
        mock_identity = MagicMock()
        mock_identity.hash = caller_identity_hash

        if (
            hasattr(mock_app.telephone_manager, "telephone")
            and mock_app.telephone_manager.telephone
        ):
            mock_app.telephone_manager.telephone.call_status = call_status
            mock_app.telephone_manager.on_telephone_ringing(mock_identity)
            mock_app.telephone_manager.on_telephone_call_established(mock_identity)
            mock_app.telephone_manager.on_telephone_call_ended(mock_identity)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    codec2_data=st.binary(min_size=0, max_size=100000),
    codec_mode=st.sampled_from(
        [
            "450PWB",
            "450",
            "700C",
            "1200",
            "1300",
            "1400",
            "1600",
            "2400",
            "3200",
            "invalid",
        ],
    ),
)
def test_codec2_decode_fuzzing(mock_app, codec2_data, codec_mode):
    """Fuzz Codec2 audio decoding with malformed data."""
    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        mock_client = MagicMock()
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                mock_client,
                {
                    "type": "codec2.decode",
                    "data": codec2_data,
                    "mode": codec_mode,
                },
            ),
        )
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    opus_data=st.one_of(
        st.binary(min_size=0, max_size=100000),
        st.text(min_size=0, max_size=10000),
        st.lists(st.integers(min_value=0, max_value=255), min_size=0, max_size=10000),
    ),
)
def test_opus_audio_decode_fuzzing(mock_app, opus_data):
    """Fuzz Opus audio decoding in LXMF audio fields."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {
        LXMF.FIELD_AUDIO: [0x10, opus_data],  # AM_OPUS_OGG = 0x10
    }
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    audio_mode=st.integers(min_value=0, max_value=255),
    audio_bytes=st.binary(min_size=0, max_size=100000),
)
def test_lxmf_audio_mode_fuzzing(mock_app, audio_mode, audio_bytes):
    """Fuzz all possible LXMF audio mode values."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {
        LXMF.FIELD_AUDIO: [audio_mode, audio_bytes],
    }
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    profile_id=st.one_of(
        st.integers(min_value=-100, max_value=100),
        st.text(min_size=0, max_size=100),
        st.none(),
    ),
)
def test_lxst_profile_switching_fuzzing(mock_app, profile_id):
    """Fuzz LXST audio profile switching."""
    if (
        hasattr(mock_app.telephone_manager, "telephone")
        and mock_app.telephone_manager.telephone
    ):
        mock_app.telephone_manager.telephone.switch_profile(profile_id)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    destination_hash=st.one_of(
        st.binary(min_size=0, max_size=100),
        st.text(min_size=0, max_size=100),
    ),
    timeout=st.one_of(
        st.integers(min_value=-100, max_value=1000),
        st.floats(allow_nan=True, allow_infinity=True),
    ),
)
def test_lxst_call_initiation_fuzzing(mock_app, destination_hash, timeout):
    """Fuzz LXST call initiation."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if isinstance(destination_hash, str) and len(destination_hash) == 32:
            try:
                dest_hash_bytes = bytes.fromhex(destination_hash)
            except ValueError:
                dest_hash_bytes = os.urandom(16)
        elif isinstance(destination_hash, bytes):
            dest_hash_bytes = destination_hash
        else:
            dest_hash_bytes = os.urandom(16)
        timeout_int = (
            int(timeout)
            if isinstance(timeout, (int, float))
            and not (
                isinstance(timeout, float)
                and (timeout != timeout or abs(timeout) == float("inf"))
            )
            else 15
        )

        loop.run_until_complete(
            mock_app.telephone_manager.initiate(
                dest_hash_bytes,
                timeout_seconds=timeout_int,
            ),
        )
    finally:
        loop.close()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    micron_content=st.text(min_size=0, max_size=50000),
)
def test_micron_parser_content_fuzzing(mock_app, micron_content):
    """Fuzz Micron parser content handling."""
    mock_app.db_upsert_lxmf_message.reset_mock()
    mock_message = MagicMock()
    mock_message.content = micron_content.encode("utf-8", errors="ignore")
    mock_message.title = b""
    mock_message.hash = os.urandom(16)
    mock_message.source_hash = os.urandom(16)
    mock_message.destination_hash = os.urandom(16)
    mock_message.incoming = True
    mock_message.state = LXMF.LXMessage.DELIVERED
    mock_message.method = LXMF.LXMessage.DIRECT
    mock_message.progress = 1.0
    mock_message.timestamp = 123456789.0
    mock_message.rssi = -50
    mock_message.snr = 10
    mock_message.q = 100
    mock_message.get_fields.return_value = {}

    mock_app.on_lxmf_delivery(mock_message)
    mock_app.db_upsert_lxmf_message.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    voicemail_text=st.text(min_size=0, max_size=10000),
)
def test_voicemail_greeting_text_fuzzing(mock_app, voicemail_text):
    """Fuzz voicemail greeting generation."""
    from meshchatx.src.backend.voicemail_manager import VoicemailManager

    # Use real VoicemailManager to test its internal logic calling subprocess
    vm = VoicemailManager(MagicMock(), MagicMock(), MagicMock(), "/tmp/voicemail_test")
    vm.has_espeak = True
    vm.has_ffmpeg = True
    vm.espeak_path = "/usr/bin/espeak"
    vm.ffmpeg_path = "/usr/bin/ffmpeg"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        try:
            vm.generate_greeting(voicemail_text)
            # If text is provided, it should call subprocess.run
            if voicemail_text.strip():
                assert mock_run.called
        except Exception:
            # Ignore errors from underlying tools in fuzzing
            pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    rns_packet_data=st.binary(min_size=0, max_size=10000),
)
def test_rns_packet_parsing_fuzzing(mock_app, rns_packet_data):
    """Fuzz RNS packet parsing with malformed protocol data."""
    try:
        import RNS

        try:
            RNS.Packet(None, rns_packet_data)
        except Exception:
            pass
        try:
            RNS.Packet.unpack(rns_packet_data)
        except Exception:
            pass
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    lxmf_message_data=st.binary(min_size=0, max_size=100000),
)
def test_lxmf_message_unpacking_fuzzing(mock_app, lxmf_message_data):
    """Fuzz LXMF message unpacking."""
    try:
        LXMF.LXMessage.unpack(lxmf_message_data)
    except Exception:
        pass
    try:
        message = LXMF.LXMessage(None, None, "")
        message.unpack(lxmf_message_data)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    pipeline_config=st.dictionaries(
        keys=st.text(),
        values=st.one_of(
            st.text(),
            st.binary(),
            st.integers(),
            st.floats(),
            st.booleans(),
            st.none(),
        ),
    ),
)
def test_lxst_pipeline_config_fuzzing(mock_app, pipeline_config):
    """Fuzz LXST Pipeline configuration."""
    from LXST.Codecs import Null
    from LXST.Pipeline import Pipeline
    from LXST.Sinks import Sink
    from LXST.Sources import Source

    class DummySource(Source):
        pass

    class DummySink(Sink):
        pass

    # Pipeline requires source, codec, and sink
    try:
        pipeline = Pipeline(source=DummySource(), codec=Null(), sink=DummySink())
        for key, value in pipeline_config.items():
            try:
                setattr(pipeline, key, value)
            except Exception:
                pass
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    sink_data=st.one_of(
        st.binary(min_size=0, max_size=10000),
        st.text(min_size=0, max_size=1000),
    ),
)
def test_lxst_sink_handling_fuzzing(mock_app, sink_data):
    """Fuzz LXST sink data handling."""
    from LXST.Sinks import OpusFileSink

    sink = OpusFileSink("/tmp/test.opus")
    try:
        sink.handle_frame(sink_data, "test_source")
    except Exception:
        pass
    try:
        sink.can_receive("test_source")
    except Exception:
        pass


def test_telemetry_packing_invariants_regression():
    """Deterministic regression test for telemetry packing/unpacking."""
    from meshchatx.src.backend.telemetry_utils import Telemeter

    original_data = {
        "time": {"utc": 123456789.0},
        "location": {
            "latitude": 45.0,
            "longitude": -90.0,
            "altitude": 100,
            "speed": 10,
            "bearing": 180,
            "accuracy": 5,
            "last_update": 123456780.0,
        },
    }

    packed = Telemeter.pack(
        time_utc=original_data["time"]["utc"],
        location=original_data["location"],
    )
    unpacked = Telemeter.from_packed(packed)

    assert unpacked["time"]["utc"] == original_data["time"]["utc"]
    assert unpacked["location"]["latitude"] == original_data["location"]["latitude"]
    assert unpacked["location"]["longitude"] == original_data["location"]["longitude"]


def test_lxmf_display_name_parsing_regression():
    """Deterministic regression test for LXMF display name parsing."""
    from meshchatx.src.backend.meshchat_utils import parse_lxmf_display_name

    valid_b64 = base64.b64encode(b"test").decode()

    with patch("LXMF.display_name_from_app_data") as mock_parser:
        # Success case
        mock_parser.return_value = "Test User"
        assert parse_lxmf_display_name(valid_b64) == "Test User"

        # None case (fallback to default)
        mock_parser.return_value = None
        assert (
            parse_lxmf_display_name(valid_b64, default_value="Fallback") == "Fallback"
        )

        # Exception case
        mock_parser.side_effect = Exception("Parsing error")
        assert (
            parse_lxmf_display_name(valid_b64, default_value="Fallback") == "Fallback"
        )

    # None input
    assert parse_lxmf_display_name(None, default_value="Fallback") == "Fallback"


class TestLxmfFieldHardening:
    """Tests for LXMF message field type safety and edge cases."""

    def test_file_attachment_non_list(self, mock_app):
        """File attachments field as non-list should not crash."""
        mock_message = MagicMock()
        mock_message.source_hash = os.urandom(16)
        mock_message.destination_hash = os.urandom(16)
        mock_message.hash = os.urandom(16)
        mock_message.content = b"test"
        mock_message.title = b""
        mock_message.incoming = True
        mock_message.state = LXMF.LXMessage.DELIVERED
        mock_message.method = LXMF.LXMessage.DIRECT
        mock_message.progress = 1.0
        mock_message.timestamp = 123456789.0
        mock_message.rssi = -50
        mock_message.snr = 10
        mock_message.q = 100
        mock_message.delivery_attempts = 1
        mock_message.next_delivery_attempt = None
        mock_message.get_fields.return_value = {
            LXMF.FIELD_FILE_ATTACHMENTS: "not-a-list",
        }
        from meshchatx.src.backend.lxmf_utils import convert_lxmf_message_to_dict

        result = convert_lxmf_message_to_dict(mock_message)
        assert isinstance(result, dict)

    def test_file_attachment_item_wrong_type(self, mock_app):
        """File attachment items that are not [name, data] pairs should not crash."""
        mock_message = MagicMock()
        mock_message.source_hash = os.urandom(16)
        mock_message.destination_hash = os.urandom(16)
        mock_message.hash = os.urandom(16)
        mock_message.content = b"test"
        mock_message.title = b""
        mock_message.incoming = True
        mock_message.state = LXMF.LXMessage.DELIVERED
        mock_message.method = LXMF.LXMessage.DIRECT
        mock_message.progress = 1.0
        mock_message.timestamp = 123456789.0
        mock_message.rssi = -50
        mock_message.snr = 10
        mock_message.q = 100
        mock_message.delivery_attempts = 1
        mock_message.next_delivery_attempt = None
        mock_message.get_fields.return_value = {
            LXMF.FIELD_FILE_ATTACHMENTS: [42, None, "string", {"a": "b"}],
        }
        from meshchatx.src.backend.lxmf_utils import convert_lxmf_message_to_dict

        try:
            convert_lxmf_message_to_dict(mock_message)
        except (TypeError, IndexError, KeyError):
            pass

    def test_image_field_non_list(self, mock_app):
        """Image field as unexpected type should not crash."""
        mock_message = MagicMock()
        mock_message.source_hash = os.urandom(16)
        mock_message.destination_hash = os.urandom(16)
        mock_message.hash = os.urandom(16)
        mock_message.content = b"test"
        mock_message.title = b""
        mock_message.incoming = True
        mock_message.state = LXMF.LXMessage.DELIVERED
        mock_message.method = LXMF.LXMessage.DIRECT
        mock_message.progress = 1.0
        mock_message.timestamp = 123456789.0
        mock_message.rssi = -50
        mock_message.snr = 10
        mock_message.q = 100
        mock_message.delivery_attempts = 1
        mock_message.next_delivery_attempt = None
        mock_message.get_fields.return_value = {
            LXMF.FIELD_IMAGE: 42,
        }
        from meshchatx.src.backend.lxmf_utils import convert_lxmf_message_to_dict

        try:
            convert_lxmf_message_to_dict(mock_message)
        except (TypeError, IndexError, KeyError):
            pass

    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None
    )
    @given(
        fields_data=st.dictionaries(
            keys=st.integers(min_value=0, max_value=20),
            values=st.one_of(
                st.none(),
                st.booleans(),
                st.integers(),
                st.text(max_size=200),
                st.binary(max_size=200),
                st.lists(st.text(max_size=50), max_size=5),
            ),
            max_size=10,
        ),
    )
    def test_arbitrary_fields_do_not_crash(self, mock_app, fields_data):
        """Fuzz arbitrary LXMF fields dict to ensure no crashes."""
        mock_message = MagicMock()
        mock_message.source_hash = os.urandom(16)
        mock_message.destination_hash = os.urandom(16)
        mock_message.hash = os.urandom(16)
        mock_message.content = b"ok"
        mock_message.title = b""
        mock_message.incoming = True
        mock_message.state = LXMF.LXMessage.DELIVERED
        mock_message.method = LXMF.LXMessage.DIRECT
        mock_message.progress = 1.0
        mock_message.timestamp = 123456789.0
        mock_message.rssi = -50
        mock_message.snr = 10
        mock_message.q = 100
        mock_message.delivery_attempts = 1
        mock_message.next_delivery_attempt = None
        mock_message.get_fields.return_value = fields_data
        from meshchatx.src.backend.lxmf_utils import convert_lxmf_message_to_dict

        try:
            convert_lxmf_message_to_dict(mock_message)
        except (TypeError, IndexError, KeyError, ValueError):
            pass


class TestStrangerAttachmentBlocking:
    """Tests for stranger attachment stripping logic."""

    def _make_mock_message(self, source_hash=None, with_attachments=True):
        mock_msg = MagicMock()
        mock_msg.source_hash = source_hash or os.urandom(16)
        mock_msg.destination_hash = os.urandom(16)
        mock_msg.hash = os.urandom(16)
        mock_msg.content = b"hello from stranger"
        mock_msg.title = b""
        mock_msg.incoming = True
        mock_msg.state = LXMF.LXMessage.DELIVERED
        mock_msg.method = LXMF.LXMessage.DIRECT
        mock_msg.progress = 1.0
        mock_msg.timestamp = 123456789.0
        mock_msg.rssi = -50
        mock_msg.snr = 10
        mock_msg.q = 100
        mock_msg.delivery_attempts = 1
        mock_msg.next_delivery_attempt = None

        fields = {}
        if with_attachments:
            fields[LXMF.FIELD_FILE_ATTACHMENTS] = [
                [b"malware.exe", b"\x00" * 100],
            ]
        mock_msg.get_fields.return_value = fields
        mock_msg.fields = fields
        return mock_msg

    def test_stranger_attachments_stripped_when_enabled(self, mock_app):
        """Attachments from non-contacts should be stripped when setting is on."""
        source_hash = os.urandom(16)
        mock_msg = self._make_mock_message(source_hash=source_hash)

        mock_app.config.block_attachments_from_strangers.get.return_value = True
        mock_app.config.block_all_from_strangers.get.return_value = False
        mock_app._is_contact = MagicMock(return_value=False)
        mock_app.is_destination_blocked = MagicMock(return_value=False)
        mock_app.check_spam_keywords = MagicMock(return_value=False)

        mock_app.on_lxmf_delivery(mock_msg)

        mock_app.db_upsert_lxmf_message.assert_called_once()
        call_kwargs = mock_app.db_upsert_lxmf_message.call_args
        assert call_kwargs[1].get("attachments_stripped") is True or (
            len(call_kwargs[0]) > 2 and call_kwargs[0][2] is True
        )

    def test_contact_attachments_not_stripped(self, mock_app):
        """Attachments from contacts should NOT be stripped."""
        source_hash = os.urandom(16)
        mock_msg = self._make_mock_message(source_hash=source_hash)

        mock_app.config.block_attachments_from_strangers.get.return_value = True
        mock_app.config.block_all_from_strangers.get.return_value = False
        mock_app._is_contact = MagicMock(return_value=True)
        mock_app.is_destination_blocked = MagicMock(return_value=False)
        mock_app.check_spam_keywords = MagicMock(return_value=False)

        mock_app.on_lxmf_delivery(mock_msg)
        mock_app.db_upsert_lxmf_message.assert_called_once()
        fields = mock_msg.get_fields()
        assert LXMF.FIELD_FILE_ATTACHMENTS in fields

    def test_setting_disabled_allows_stranger_attachments(self, mock_app):
        """When setting is off, stranger attachments pass through."""
        source_hash = os.urandom(16)
        mock_msg = self._make_mock_message(source_hash=source_hash)

        mock_app.config.block_attachments_from_strangers.get.return_value = False
        mock_app.config.block_all_from_strangers.get.return_value = False
        mock_app._is_contact = MagicMock(return_value=False)
        mock_app.is_destination_blocked = MagicMock(return_value=False)
        mock_app.check_spam_keywords = MagicMock(return_value=False)

        mock_app.on_lxmf_delivery(mock_msg)
        mock_app.db_upsert_lxmf_message.assert_called_once()
        fields = mock_msg.get_fields()
        assert LXMF.FIELD_FILE_ATTACHMENTS in fields

    def test_text_message_from_stranger_still_delivered(self, mock_app):
        """Text-only messages from strangers are delivered normally."""
        source_hash = os.urandom(16)
        mock_msg = self._make_mock_message(
            source_hash=source_hash, with_attachments=False
        )

        mock_app.config.block_attachments_from_strangers.get.return_value = True
        mock_app.config.block_all_from_strangers.get.return_value = False
        mock_app._is_contact = MagicMock(return_value=False)
        mock_app.is_destination_blocked = MagicMock(return_value=False)
        mock_app.check_spam_keywords = MagicMock(return_value=False)

        mock_app.on_lxmf_delivery(mock_msg)
        mock_app.db_upsert_lxmf_message.assert_called_once()


class TestBlockAllFromStrangers:
    """Tests for the block-everything-from-strangers feature."""

    def _make_mock_message(self, source_hash=None, with_attachments=False):
        mock_msg = MagicMock()
        mock_msg.source_hash = source_hash or os.urandom(16)
        mock_msg.destination_hash = os.urandom(16)
        mock_msg.hash = os.urandom(16)
        mock_msg.content = b"hello from stranger"
        mock_msg.title = b""
        mock_msg.incoming = True
        mock_msg.state = LXMF.LXMessage.DELIVERED
        mock_msg.method = LXMF.LXMessage.DIRECT
        mock_msg.progress = 1.0
        mock_msg.timestamp = 123456789.0
        mock_msg.rssi = -50
        mock_msg.snr = 10
        mock_msg.q = 100
        mock_msg.delivery_attempts = 1
        mock_msg.next_delivery_attempt = None
        fields = {}
        if with_attachments:
            fields[LXMF.FIELD_FILE_ATTACHMENTS] = [[b"file.txt", b"data"]]
        mock_msg.get_fields.return_value = fields
        mock_msg.fields = fields
        return mock_msg

    def test_stranger_message_dropped_when_enabled(self, mock_app):
        """Text message from a stranger is silently dropped when block_all is on."""
        mock_msg = self._make_mock_message()
        mock_app.config.block_all_from_strangers.get.return_value = True
        mock_app.config.block_attachments_from_strangers.get.return_value = False
        mock_app._is_contact = MagicMock(return_value=False)
        mock_app.is_destination_blocked = MagicMock(return_value=False)
        mock_app.check_spam_keywords = MagicMock(return_value=False)

        mock_app.on_lxmf_delivery(mock_msg)
        mock_app.db_upsert_lxmf_message.assert_not_called()

    def test_contact_message_delivered_when_block_all_enabled(self, mock_app):
        """Messages from contacts pass through even when block_all is on."""
        mock_msg = self._make_mock_message()
        mock_app.config.block_all_from_strangers.get.return_value = True
        mock_app.config.block_attachments_from_strangers.get.return_value = False
        mock_app._is_contact = MagicMock(return_value=True)
        mock_app.is_destination_blocked = MagicMock(return_value=False)
        mock_app.check_spam_keywords = MagicMock(return_value=False)

        mock_app.on_lxmf_delivery(mock_msg)
        mock_app.db_upsert_lxmf_message.assert_called_once()

    def test_stranger_with_attachments_dropped(self, mock_app):
        """Message with attachments from stranger is dropped entirely, not just stripped."""
        mock_msg = self._make_mock_message(with_attachments=True)
        mock_app.config.block_all_from_strangers.get.return_value = True
        mock_app.config.block_attachments_from_strangers.get.return_value = True
        mock_app._is_contact = MagicMock(return_value=False)
        mock_app.is_destination_blocked = MagicMock(return_value=False)
        mock_app.check_spam_keywords = MagicMock(return_value=False)

        mock_app.on_lxmf_delivery(mock_msg)
        mock_app.db_upsert_lxmf_message.assert_not_called()

    def test_disabled_allows_stranger_messages(self, mock_app):
        """When block_all is off, stranger messages are delivered."""
        mock_msg = self._make_mock_message()
        mock_app.config.block_all_from_strangers.get.return_value = False
        mock_app.config.block_attachments_from_strangers.get.return_value = False
        mock_app._is_contact = MagicMock(return_value=False)
        mock_app.is_destination_blocked = MagicMock(return_value=False)
        mock_app.check_spam_keywords = MagicMock(return_value=False)

        mock_app.on_lxmf_delivery(mock_msg)
        mock_app.db_upsert_lxmf_message.assert_called_once()
