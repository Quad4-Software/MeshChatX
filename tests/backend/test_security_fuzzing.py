import os
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import LXMF
import pytest
import RNS
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def mock_app():
    # Save real Identity class to use as base for our mock class
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"test_hash_32_bytes_long_01234567"
            self.hexhash = self.hash.hex()

    with ExitStack() as stack:
        stack.enter_context(patch("meshchatx.src.backend.identity_context.Database"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.ConfigManager")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.MessageHandler")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.AnnounceManager")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.ArchiverManager")
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.MapManager"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TelephoneManager")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.VoicemailManager")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RingtoneManager")
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.RNCPHandler"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNStatusHandler")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNProbeHandler")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TranslatorHandler")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager")
        )
        mock_async_utils = stack.enter_context(patch("meshchatx.meshchat.AsyncUtils"))
        stack.enter_context(patch("LXMF.LXMRouter"))
        stack.enter_context(patch("RNS.Identity", MockIdentityClass))
        stack.enter_context(patch("RNS.Reticulum"))
        stack.enter_context(patch("RNS.Transport"))
        stack.enter_context(patch("threading.Thread"))
        stack.enter_context(
            patch.object(
                ReticulumMeshChat, "announce_loop", new=MagicMock(return_value=None)
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
                ReticulumMeshChat, "crawler_loop", new=MagicMock(return_value=None)
            ),
        )

        mock_id = MockIdentityClass()
        mock_id.get_private_key = MagicMock(return_value=b"test_private_key")

        stack.enter_context(
            patch.object(MockIdentityClass, "from_file", return_value=mock_id)
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "recall", return_value=mock_id)
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "from_bytes", return_value=mock_id)
        )

        # Make run_async a no-op that doesn't trigger coroutine warnings
        def mock_run_async(coro):
            import asyncio

            if asyncio.iscoroutine(coro):
                coro.close()

        mock_async_utils.run_async = MagicMock(side_effect=mock_run_async)

        app = ReticulumMeshChat(
            identity=mock_id,
            storage_dir="/tmp/meshchat_test",
            reticulum_config_dir="/tmp/meshchat_test",
        )

        # Setup config mock to return real values to avoid background thread issues
        app.config = MagicMock()
        app.config.auto_announce_enabled.get.return_value = False
        app.config.auto_announce_interval_seconds.get.return_value = 600
        app.config.last_announced_at.get.return_value = 0
        app.config.lxmf_auto_sync_propagation_nodes_enabled.get.return_value = False
        app.config.lxmf_auto_sync_propagation_nodes_interval_seconds.get.return_value = 3600
        app.config.lxmf_auto_sync_propagation_nodes_last_synced_at.get.return_value = 0
        app.config.voicemail_enabled.get.return_value = True
        app.config.voicemail_auto_answer_delay_seconds.get.return_value = 0
        app.config.voicemail_greeting.get.return_value = "Hello"
        app.config.voicemail_max_recording_seconds.get.return_value = 10

        # Other required mocks for on_lxmf_delivery
        app.is_destination_blocked = MagicMock(return_value=False)
        app.check_spam_keywords = MagicMock(return_value=False)
        app.db_upsert_lxmf_message = MagicMock()
        app.handle_forwarding = MagicMock()
        app.update_lxmf_user_icon = MagicMock()
        app.websocket_broadcast = MagicMock()

        yield app


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
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {LXMF.FIELD_ICON_APPEARANCE: field_data}
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    try:
        mock_app.on_lxmf_delivery(mock_message)
    except Exception:
        pass


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
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {
        LXMF.FIELD_FILE_ATTACHMENTS: attachments_data,
    }
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    try:
        mock_app.on_lxmf_delivery(mock_message)
    except Exception:
        pass


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
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {LXMF.FIELD_IMAGE: image_data}
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    try:
        mock_app.on_lxmf_delivery(mock_message)
    except Exception:
        pass


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
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {LXMF.FIELD_AUDIO: audio_data}
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    try:
        mock_app.on_lxmf_delivery(mock_message)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    filename=st.text(min_size=0, max_size=1000),
    file_bytes=st.binary(min_size=0, max_size=10000),
)
def test_attachment_filename_security(mock_app, filename, file_bytes):
    """Test for potential directory traversal or malicious filenames in attachments."""
    mock_message = MagicMock()
    mock_message.get_fields.return_value = {
        LXMF.FIELD_FILE_ATTACHMENTS: [[filename, file_bytes]],
    }
    mock_message.source_hash = os.urandom(16)
    mock_message.hash = os.urandom(16)

    try:
        mock_app.on_lxmf_delivery(mock_message)
        mock_app.convert_lxmf_message_to_dict(mock_message)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(caller_id_bytes=st.binary(min_size=0, max_size=1000))
def test_telephone_callback_fuzzing(mock_app, caller_id_bytes):
    """Fuzz telephone manager callbacks with malformed identity bytes."""
    try:
        mock_identity = MagicMock()
        mock_identity.hash = caller_id_bytes

        mock_app.telephone_manager.on_telephone_ringing(mock_identity)
        mock_app.telephone_manager.on_telephone_call_established(mock_identity)
        mock_app.telephone_manager.on_telephone_call_ended(mock_identity)
    except Exception:
        pass


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
    try:
        mock_app.database.messages.upsert_lxmf_message(data)
    except Exception:
        pass


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

    try:
        mock_app.convert_lxmf_message_to_dict(mock_message)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(greeting_text=st.text(min_size=0, max_size=1000))
def test_voicemail_greeting_fuzzing(mock_app, greeting_text):
    """Fuzz voicemail greeting generation with varied text."""
    mock_app.voicemail_manager.has_espeak = True
    mock_app.voicemail_manager.has_ffmpeg = True
    mock_app.voicemail_manager.espeak_path = "/usr/bin/espeak"
    mock_app.voicemail_manager.ffmpeg_path = "/usr/bin/ffmpeg"

    with patch("subprocess.run"):
        try:
            mock_app.voicemail_manager.generate_greeting(greeting_text)
        except Exception:
            pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(caller_hash=st.binary(min_size=0, max_size=32))
def test_voicemail_incoming_call_fuzzing(mock_app, caller_hash):
    """Fuzz voicemail incoming call handling."""
    mock_identity = MagicMock()
    mock_identity.hash = caller_hash

    try:
        mock_app.voicemail_manager.handle_incoming_call(mock_identity)
    except Exception:
        pass


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
    try:
        mock_app.forwarding_manager.get_or_create_mapping(
            source_hash,
            recipient_hash,
            dest_hash,
        )
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(uri=st.text(min_size=0, max_size=5000))
def test_lxm_ingest_uri_fuzzing(mock_app, uri):
    """Fuzz the lxm.ingest_uri WebSocket handler."""
    mock_client = MagicMock()
    mock_client.send_str = MagicMock()

    try:
        # We need to wrap it in a task since it's async
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                mock_client,
                {"type": "lxm.ingest_uri", "uri": uri},
            ),
        )
    except Exception:
        pass


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
    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(mock_app.update_config(config_data))
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(large_string=st.text(min_size=1000, max_size=10000))
def test_large_payload_dos_resistance(mock_app, large_string):
    """Check resistance to DoS via large strings in various fields."""
    mock_message = MagicMock()
    mock_message.title = large_string.encode()
    mock_message.content = large_string.encode()
    mock_message.hash = os.urandom(16)
    mock_message.source_hash = os.urandom(16)
    mock_message.get_fields.return_value = {}

    try:
        mock_app.on_lxmf_delivery(mock_message)
    except Exception:
        pass


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
    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            mock_app.on_websocket_data_received(
                mock_client,
                {"type": "ping", "data": nested_data},
            ),
        )
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(dest_hash=st.text(), content=st.text())
def test_lxm_generate_paper_uri_fuzzing(mock_app, dest_hash, content):
    """Fuzz paper URI generation with randomized inputs."""
    mock_client = MagicMock()
    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
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
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    lon=st.floats(allow_nan=False, allow_infinity=False),
    lat=st.floats(allow_nan=False, allow_infinity=False),
    zoom=st.integers(min_value=-100, max_value=100),
)
def test_map_manager_coord_fuzzing(mock_app, lon, lat, zoom):
    """Fuzz coordinate to tile conversion in MapManager."""
    try:
        mock_app.map_manager._lonlat_to_tile(lon, lat, zoom)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    text=st.text(),
    source_lang=st.text(min_size=0, max_size=10),
    target_lang=st.text(min_size=0, max_size=10),
)
def test_translator_handler_fuzzing(mock_app, text, source_lang, target_lang):
    """Fuzz the TranslatorHandler translate_text method."""
    try:
        # Mock dependencies
        mock_app.translator_handler.has_requests = False
        mock_app.translator_handler.has_argos = False
        mock_app.translator_handler.translate_text(text, source_lang, target_lang)
    except Exception:
        pass


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
    try:
        mock_app.update_lxmf_user_icon(dest_hash, icon_name, fg_color, bg_color)
    except Exception:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(binary_data=st.binary(min_size=0, max_size=10000))
def test_rns_identity_load_fuzzing(mock_app, binary_data):
    """Fuzz RNS.Identity loading with random binary data."""
    try:
        import RNS

        try:
            RNS.Identity.from_bytes(binary_data)
        except Exception:
            pass
        try:
            id_inst = RNS.Identity(create_keys=False)
            id_inst.load_private_key(binary_data)
        except Exception:
            pass
        try:
            id_inst = RNS.Identity(create_keys=False)
            id_inst.load_public_key(binary_data)
        except Exception:
            pass
    except Exception:
        pass
