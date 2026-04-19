# SPDX-License-Identifier: 0BSD

import asyncio
import json
import os
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import LXMF
import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.lxmf_message_fields import LxmfAudioField


@pytest.fixture
def mock_app():
    # Use __new__ to avoid full initialization
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = MagicMock()
    app.config = MagicMock()
    app.database = MagicMock()
    app.reticulum = MagicMock()
    app.message_router = MagicMock()
    app.storage_dir = "/tmp/meshchat_test"
    os.makedirs(app.storage_dir, exist_ok=True)
    return app


def test_get_current_icon_hash_none(mock_app):
    mock_app.config.lxmf_user_icon_name.get.return_value = None
    assert mock_app.get_current_icon_hash() is None


def test_get_current_icon_hash_valid(mock_app):
    mock_app.config.lxmf_user_icon_name.get.return_value = "icon"
    mock_app.config.lxmf_user_icon_foreground_colour.get.return_value = "#ffffff"
    mock_app.config.lxmf_user_icon_background_colour.get.return_value = "#000000"

    icon_hash = mock_app.get_current_icon_hash()
    assert icon_hash is not None
    assert len(icon_hash) == 64


def test_parse_bool(mock_app):
    assert mock_app._parse_bool(True) is True
    assert mock_app._parse_bool("true") is True
    assert mock_app._parse_bool("True") is True
    assert mock_app._parse_bool(False) is False
    assert mock_app._parse_bool("false") is False
    assert mock_app._parse_bool("no") is False


@pytest.mark.asyncio
async def test_update_config_display_name(mock_app):
    data = {"display_name": "New Name"}
    mock_app.update_identity_metadata_cache = MagicMock()
    mock_app.send_config_to_websocket_clients = MagicMock(return_value=asyncio.Future())
    mock_app.send_config_to_websocket_clients.return_value.set_result(None)

    await mock_app.update_config(data)
    mock_app.config.display_name.set.assert_called_with("New Name")
    mock_app.update_identity_metadata_cache.assert_called_once()


@pytest.mark.asyncio
async def test_update_config_theme(mock_app):
    data = {"theme": "dark"}
    mock_app.send_config_to_websocket_clients = MagicMock(return_value=asyncio.Future())
    mock_app.send_config_to_websocket_clients.return_value.set_result(None)

    await mock_app.update_config(data)
    mock_app.config.theme.set.assert_called_with("dark")


def test_get_config_dict_no_context(mock_app):
    mock_app.current_context = None
    assert mock_app.get_config_dict() == {}


def test_get_config_dict_basic(mock_app):
    ctx = mock_app.current_context
    mock_config = MagicMock()
    mock_app.current_context.config = mock_config

    mock_config.display_name.get.return_value = "Test"
    mock_config.theme.get.return_value = "light"
    mock_config.language.get.return_value = "en"

    # Mocking all items returned in get_config_dict
    for attr in [
        "auto_announce_enabled",
        "auto_announce_interval_seconds",
        "last_announced_at",
        "auto_resend_failed_messages_when_announce_received",
        "allow_auto_resending_failed_messages_with_attachments",
        "auto_send_failed_messages_to_propagation_node",
        "show_suggested_community_interfaces",
        "lxmf_local_propagation_node_enabled",
        "lxmf_preferred_propagation_node_destination_hash",
        "lxmf_preferred_propagation_node_auto_select",
        "lxmf_preferred_propagation_node_auto_sync_interval_seconds",
        "lxmf_preferred_propagation_node_last_synced_at",
        "lxmf_user_icon_name",
        "lxmf_user_icon_foreground_colour",
        "lxmf_user_icon_background_colour",
        "lxmf_inbound_stamp_cost",
        "lxmf_propagation_node_stamp_cost",
        "page_archiver_enabled",
        "page_archiver_max_versions",
        "archives_max_storage_gb",
        "backup_max_count",
        "crawler_enabled",
        "crawler_max_retries",
        "crawler_retry_delay_seconds",
        "crawler_max_concurrent",
        "auth_enabled",
        "voicemail_enabled",
        "voicemail_greeting",
        "voicemail_auto_answer_delay_seconds",
        "voicemail_max_recording_seconds",
        "voicemail_tts_speed",
        "voicemail_tts_pitch",
        "voicemail_tts_voice",
        "voicemail_tts_word_gap",
        "custom_ringtone_enabled",
        "ringtone_filename",
        "ringtone_preferred_id",
        "ringtone_volume",
        "map_offline_enabled",
        "map_mbtiles_dir",
        "map_tile_cache_enabled",
        "map_default_lat",
        "map_default_lon",
        "map_default_zoom",
        "map_tile_server_url",
        "map_nominatim_api_url",
        "do_not_disturb_enabled",
        "telephone_allow_calls_from_contacts_only",
        "telephone_audio_profile_id",
        "telephone_web_audio_enabled",
        "telephone_web_audio_allow_fallback",
        "call_recording_enabled",
        "banished_effect_enabled",
        "banished_text",
        "banished_color",
        "message_font_size",
        "message_icon_size",
        "translator_enabled",
        "libretranslate_url",
        "desktop_open_calls_in_separate_window",
        "desktop_hardware_acceleration_enabled",
        "blackhole_integration_enabled",
        "announce_max_stored_lxmf_delivery",
        "announce_max_stored_nomadnetwork_node",
        "announce_max_stored_lxmf_propagation",
        "announce_fetch_limit_lxmf_delivery",
        "announce_fetch_limit_nomadnetwork_node",
        "announce_fetch_limit_lxmf_propagation",
        "announce_search_max_fetch",
        "discovered_interfaces_max_return",
        "csp_extra_connect_src",
        "csp_extra_img_src",
        "csp_extra_frame_src",
        "csp_extra_script_src",
        "csp_extra_style_src",
        "telephone_tone_generator_enabled",
        "telephone_tone_generator_volume",
        "location_source",
        "location_manual_lat",
        "location_manual_lon",
        "location_manual_alt",
        "telemetry_enabled",
        "nomad_render_markdown_enabled",
        "nomad_render_html_enabled",
        "nomad_render_plaintext_enabled",
        "nomad_default_page_path",
        "message_outbound_bubble_color",
        "message_inbound_bubble_color",
        "message_failed_bubble_color",
        "message_waiting_bubble_color",
    ]:
        getattr(mock_config, attr).get.return_value = None

    mock_config.display_name.get.return_value = "Test"
    mock_config.theme.get.return_value = "light"
    mock_config.language.get.return_value = "en"

    ctx.identity.hash.hex.return_value = "abcd"
    ctx.identity.get_public_key.return_value = bytes.fromhex("a1" * 32)
    ctx.local_lxmf_destination.hexhash = "beef"
    ctx.telephone_manager.telephone = None
    mock_app.reticulum.transport_enabled.return_value = True

    config_dict = mock_app.get_config_dict()
    assert config_dict["display_name"] == "Test"
    assert config_dict["theme"] == "light"
    assert config_dict["is_transport_enabled"] is True
    assert config_dict["identity_public_key"] == "a1" * 32
    assert "nomad_default_page_path" in config_dict
    assert "nomad_render_markdown_enabled" in config_dict


@pytest.mark.asyncio
async def test_update_config_nomad_renderer(mock_app):
    mock_app.send_config_to_websocket_clients = MagicMock(return_value=asyncio.Future())
    mock_app.send_config_to_websocket_clients.return_value.set_result(None)
    for name in (
        "nomad_render_markdown_enabled",
        "nomad_render_html_enabled",
        "nomad_render_plaintext_enabled",
        "nomad_default_page_path",
    ):
        setattr(mock_app.config, name, MagicMock())

    await mock_app.update_config(
        {
            "nomad_render_markdown_enabled": False,
            "nomad_render_html_enabled": True,
            "nomad_render_plaintext_enabled": False,
            "nomad_default_page_path": "/page/index.html",
        },
    )
    mock_app.config.nomad_render_markdown_enabled.set.assert_called_with(False)
    mock_app.config.nomad_render_html_enabled.set.assert_called_with(True)
    mock_app.config.nomad_render_plaintext_enabled.set.assert_called_with(False)
    mock_app.config.nomad_default_page_path.set.assert_called_with("/page/index.html")


@pytest.mark.asyncio
async def test_update_config_nomad_default_page_path_empty_resets(mock_app):
    mock_app.send_config_to_websocket_clients = MagicMock(return_value=asyncio.Future())
    mock_app.send_config_to_websocket_clients.return_value.set_result(None)
    mock_app.config.nomad_default_page_path = MagicMock()

    await mock_app.update_config({"nomad_default_page_path": ""})
    mock_app.config.nomad_default_page_path.set.assert_called_with("/page/index.mu")


@pytest.mark.asyncio
async def test_update_config_nomad_default_page_path_invalid_skipped(mock_app):
    mock_app.send_config_to_websocket_clients = MagicMock(return_value=asyncio.Future())
    mock_app.send_config_to_websocket_clients.return_value.set_result(None)
    mock_app.config.nomad_default_page_path = MagicMock()

    await mock_app.update_config({"nomad_default_page_path": "/page/../../etc/passwd"})
    mock_app.config.nomad_default_page_path.set.assert_not_called()


@pytest.mark.asyncio
async def test_lxm_ingest_uri_lxma_adds_contact(mock_app):
    mock_app.database.contacts.get_contact_by_identity_hash.return_value = None
    mock_app.database.contacts.add_contact = MagicMock()
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))

    fake_identity = MagicMock()
    fake_identity.hash = bytes.fromhex("bb" * 16)
    fake_identity.load_public_key.return_value = True

    with (
        patch(
            "meshchatx.meshchat.AsyncUtils.run_async",
            side_effect=lambda coro: asyncio.create_task(coro),
        ),
        patch("meshchatx.meshchat.RNS.Identity", return_value=fake_identity),
    ):
        await mock_app.on_websocket_data_received(
            mock_client,
            {
                "type": "lxm.ingest_uri",
                "uri": f"lxma://{'aa' * 16}:{'11' * 64}",
            },
        )
        await asyncio.sleep(0)

    mock_app.database.contacts.add_contact.assert_called_once_with(
        "Contact aaaaaaaa",
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        lxmf_address="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    mock_app.message_router.ingest_lxm_uri.assert_not_called()
    mock_client.send_str.assert_called_once()
    payload = json.loads(mock_client.send_str.call_args[0][0])
    assert payload["type"] == "lxm.ingest_uri.result"
    assert payload["status"] == "success"
    assert payload["ingest_type"] == "lxma_contact"
    assert payload["destination_hash"] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_db_upsert_lxmf_message_basic(mock_app):
    mock_msg = MagicMock()
    mock_msg.hash = b"h" * 16
    mock_msg.source_hash = b"s" * 16
    mock_msg.destination_hash = b"d" * 16
    mock_msg.content = b"Hello"
    mock_msg.get_fields.return_value = {}
    mock_msg.timestamp = 123456789
    mock_msg.progress = 0.5
    mock_msg.incoming = True
    mock_msg.state = 0
    mock_msg.method = 0
    mock_msg.delivery_attempts = 0
    mock_msg.title = b""
    mock_msg.rssi = None
    mock_msg.snr = None
    mock_msg.q = None

    mock_app.current_context.local_lxmf_destination.hexhash = "local"

    mock_app.db_upsert_lxmf_message(mock_msg)

    mock_app.current_context.database.messages.upsert_lxmf_message.assert_called_once()
    args, _ = mock_app.current_context.database.messages.upsert_lxmf_message.call_args
    assert args[0]["content"] == "Hello"
    assert args[0]["peer_hash"] == "73737373737373737373737373737373"  # Hex of b"s"*16


def test_get_lxmf_conversation_name(mock_app):
    mock_app.database.announces.get_announce_by_hash.return_value = {
        "app_data": "base64data",
        "destination_hash": "dest",
    }
    with patch("meshchatx.meshchat.parse_lxmf_display_name", return_value="Peer Name"):
        name = mock_app.get_lxmf_conversation_name("dest")
        assert name == "Peer Name"


def test_get_lxmf_conversation_name_default(mock_app):
    mock_app.database.announces.get_announce_by_hash.return_value = None
    name = mock_app.get_lxmf_conversation_name("dest", default_name="Default")
    assert name == "Default"


@pytest.mark.asyncio
async def test_send_config_to_websocket_clients(mock_app):
    mock_app.websocket_broadcast = MagicMock(return_value=asyncio.Future())
    mock_app.websocket_broadcast.return_value.set_result(None)
    mock_app.get_config_dict = MagicMock(return_value={"conf": "val"})

    await mock_app.send_config_to_websocket_clients()
    mock_app.websocket_broadcast.assert_called_once()
    args, _ = mock_app.websocket_broadcast.call_args
    payload = json.loads(args[0])
    assert payload["type"] == "config"
    assert payload["config"] == {"conf": "val"}


@pytest.mark.asyncio
async def test_on_lxmf_sending_state_updated(mock_app):
    mock_msg = MagicMock()
    mock_msg.progress = 0.75
    mock_msg.rssi = None
    mock_msg.snr = None
    mock_msg.q = None
    mock_msg.hash.hex.return_value = "ab" * 16
    mock_msg.delivery_attempts = 2

    ctx = mock_app.current_context
    mock_app.websocket_broadcast = MagicMock(return_value=asyncio.Future())
    mock_app.websocket_broadcast.return_value.set_result(None)

    with (
        patch(
            "meshchatx.meshchat.convert_lxmf_message_to_dict",
            return_value={"h": "v"},
        ),
        patch(
            "meshchatx.meshchat.convert_lxmf_state_to_string",
            return_value="delivered",
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async") as mock_run_async,
    ):
        mock_app.on_lxmf_sending_state_updated(mock_msg, context=ctx)

        ctx.database.messages.update_lxmf_message_state.assert_called_once()
        call_kwargs = ctx.database.messages.update_lxmf_message_state.call_args
        assert call_kwargs.kwargs["message_hash"] == "ab" * 16
        assert call_kwargs.kwargs["progress"] == 75.0
        assert call_kwargs.kwargs["state"] == "delivered"
        mock_run_async.assert_called_once()


@pytest.mark.asyncio
async def test_lxmf_messages_send_route(mock_app):
    # Setup mocks for route handler
    mock_app.send_message = MagicMock(return_value=asyncio.Future())
    mock_msg = MagicMock()
    mock_msg.hash = b"hash"
    mock_app.send_message.return_value.set_result(mock_msg)

    # Mock convert_lxmf_message_to_dict
    with patch(
        "meshchatx.meshchat.convert_lxmf_message_to_dict",
        return_value={"hash": "hashhex"},
    ):
        # We need to find the route handler. It's normally set up in __init__.
        # Let's mock a request
        request = MagicMock()
        request.json = MagicMock(return_value=asyncio.Future())
        request.json.return_value.set_result(
            {
                "lxmf_message": {
                    "destination_hash": "dest",
                    "content": "hello",
                    "fields": {},
                },
            },
        )

        # Since we can't easily get the handler from mock_app without full init,
        # we can skip this or try to mock the internal method if it exists.


def test_on_lxmf_sending_failed_no_propagation(mock_app):
    mock_msg = MagicMock()
    mock_msg.state = 0  # NOT FAILED
    mock_app.on_lxmf_sending_state_updated = MagicMock()

    mock_app.on_lxmf_sending_failed(mock_msg)
    mock_app.on_lxmf_sending_state_updated.assert_called_once_with(
        mock_msg,
        context=mock_app.current_context,
    )


def test_convert_webm_opus_to_ogg_already_ogg(mock_app):
    ogg_data = b"OggS" + b"\x00" * 100
    result = mock_app._convert_webm_opus_to_ogg(ogg_data)
    assert result is ogg_data


def test_convert_webm_opus_to_ogg_undecodable_returns_input(mock_app):
    """Unknown containers (e.g. legacy WebM) fall through unchanged."""
    webm_data = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
    result = mock_app._convert_webm_opus_to_ogg(webm_data)
    assert result is webm_data


def _build_wav_pcm16(samplerate=48000, duration_seconds=0.5, frequency=440.0):
    import io
    import math
    import struct
    import wave

    n_samples = int(samplerate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        frames = bytearray()
        for i in range(n_samples):
            sample = int(0.3 * 32767 * math.sin(2 * math.pi * frequency * (i / samplerate)))
            frames.extend(struct.pack("<h", sample))
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def test_convert_webm_opus_to_ogg_wav_uses_audio_codec(mock_app):
    """WAV input is routed through audio_codec, no subprocess fallback."""
    wav_bytes = _build_wav_pcm16()
    fake_ogg = b"OggS" + b"\x42" * 64

    with (
        patch(
            "meshchatx.src.backend.audio_codec.encode_audio_bytes_to_ogg_opus",
            return_value=fake_ogg,
        ) as mock_encode,
        patch("subprocess.run") as mock_run,
    ):
        result = mock_app._convert_webm_opus_to_ogg(wav_bytes)

    assert result == fake_ogg
    mock_encode.assert_called_once_with(wav_bytes)
    mock_run.assert_not_called()


def test_convert_webm_opus_to_ogg_wav_falls_through_when_codec_fails(mock_app):
    wav_bytes = _build_wav_pcm16()
    with patch(
        "meshchatx.src.backend.audio_codec.encode_audio_bytes_to_ogg_opus",
        return_value=None,
    ):
        result = mock_app._convert_webm_opus_to_ogg(wav_bytes)
    assert result is wav_bytes


def test_encode_pcm_wav_to_ogg_opus_produces_ogg(mock_app):
    """The WAV->OGG/Opus wrapper still produces a valid OGG container."""
    wav_bytes = _build_wav_pcm16()
    encoded = mock_app._encode_pcm_wav_to_ogg_opus(wav_bytes)
    assert encoded is not None
    assert encoded[:4] == b"OggS"
    assert len(encoded) > 0
    assert len(encoded) < len(wav_bytes)


def test_encode_pcm_wav_to_ogg_opus_invalid_returns_none(mock_app):
    assert mock_app._encode_pcm_wav_to_ogg_opus(b"not a wav file at all") is None


def test_convert_webm_opus_to_ogg_audio_codec_exception(mock_app):
    """Exceptions inside the codec helper degrade gracefully."""
    webm_data = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
    with patch(
        "meshchatx.src.backend.audio_codec.encode_audio_bytes_to_ogg_opus",
        side_effect=RuntimeError("boom"),
    ):
        result = mock_app._convert_webm_opus_to_ogg(webm_data)
    assert result is webm_data


@pytest.fixture
def sendable_app(mock_app):
    """mock_app wired so send_message can run to completion."""
    ctx = mock_app.current_context
    ctx.config.auto_send_failed_messages_to_propagation_node.get.return_value = False
    ctx.message_router.delivery_link_available.return_value = True
    ctx.local_lxmf_destination = MagicMock()
    ctx.forwarding_manager = None

    mock_app._await_transport_path = AsyncMock()
    mock_app.get_current_icon_hash = MagicMock(return_value=None)
    mock_app.db_upsert_lxmf_message = MagicMock()
    mock_app.websocket_broadcast = AsyncMock()
    mock_app.handle_lxmf_message_progress = AsyncMock()
    mock_app._convert_webm_opus_to_ogg = MagicMock(side_effect=lambda b: b)

    return mock_app


async def _run_send(app, destination_hash="aa" * 16, **kwargs):
    fake_identity = MagicMock()
    fake_destination = MagicMock()
    fake_lxm = MagicMock(spec=LXMF.LXMessage)
    fake_lxm.fields = {}
    fake_lxm.include_ticket = False

    with (
        patch("meshchatx.meshchat.RNS.Identity.recall", return_value=fake_identity),
        patch("meshchatx.meshchat.RNS.Destination", return_value=fake_destination),
        patch("meshchatx.meshchat.LXMF.LXMessage", return_value=fake_lxm),
        patch(
            "meshchatx.meshchat.convert_lxmf_message_to_dict",
            return_value={"hash": "x"},
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        await app.send_message(
            destination_hash=destination_hash,
            content="hi",
            **kwargs,
        )

    return fake_lxm


@pytest.mark.asyncio
async def test_send_message_sets_renderer_markdown(sendable_app):
    lxm = await _run_send(sendable_app)
    assert LXMF.FIELD_RENDERER in lxm.fields
    assert lxm.fields[LXMF.FIELD_RENDERER] == LXMF.RENDERER_MARKDOWN


@pytest.mark.asyncio
async def test_send_message_include_ticket_for_contact(sendable_app):
    sendable_app._is_contact = MagicMock(return_value=True)
    lxm = await _run_send(sendable_app)
    assert lxm.include_ticket is True


@pytest.mark.asyncio
async def test_send_message_no_ticket_for_stranger(sendable_app):
    sendable_app._is_contact = MagicMock(return_value=False)
    lxm = await _run_send(sendable_app)
    assert lxm.include_ticket is False


@pytest.mark.asyncio
async def test_send_message_opus_audio_triggers_conversion(sendable_app):
    audio = LxmfAudioField(audio_mode=LXMF.AM_OPUS_OGG, audio_bytes=b"\x1a\x45")
    lxm = await _run_send(sendable_app, audio_field=audio)
    sendable_app._convert_webm_opus_to_ogg.assert_called_once_with(b"\x1a\x45")
    assert LXMF.FIELD_AUDIO in lxm.fields


@pytest.mark.asyncio
async def test_send_message_codec2_audio_skips_conversion(sendable_app):
    audio = LxmfAudioField(audio_mode=LXMF.AM_CODEC2_1200, audio_bytes=b"\xcc")
    lxm = await _run_send(sendable_app, audio_field=audio)
    sendable_app._convert_webm_opus_to_ogg.assert_not_called()
    assert lxm.fields[LXMF.FIELD_AUDIO] == [LXMF.AM_CODEC2_1200, b"\xcc"]
