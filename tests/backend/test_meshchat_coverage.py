# SPDX-License-Identifier: 0BSD

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import LXMF
import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.lxmf_message_fields import LxmfAudioField
from meshchatx.src.backend.reticulum_pathfinding import OutboundPathOutcome


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
async def test_update_config_libretranslate_api_key(mock_app):
    mock_app.send_config_to_websocket_clients = MagicMock(return_value=asyncio.Future())
    mock_app.send_config_to_websocket_clients.return_value.set_result(None)
    mock_app.config.libretranslate_api_key = MagicMock()
    mock_app.translator_handler = MagicMock()
    await mock_app.update_config({"libretranslate_api_key": " sek "})
    mock_app.config.libretranslate_api_key.set.assert_called_once_with("sek")
    assert mock_app.translator_handler.libretranslate_api_key == "sek"


@pytest.mark.asyncio
async def test_update_config_libretranslate_api_key_empty_clears(mock_app):
    mock_app.send_config_to_websocket_clients = MagicMock(return_value=asyncio.Future())
    mock_app.send_config_to_websocket_clients.return_value.set_result(None)
    mock_app.config.libretranslate_api_key = MagicMock()
    mock_app.translator_handler = MagicMock()
    await mock_app.update_config({"libretranslate_api_key": ""})
    mock_app.config.libretranslate_api_key.set.assert_called_once_with(None)
    assert mock_app.translator_handler.libretranslate_api_key is None


@pytest.mark.asyncio
async def test_update_config_libretranslate_api_key_length_limit(mock_app):
    mock_app.send_config_to_websocket_clients = MagicMock(return_value=asyncio.Future())
    mock_app.send_config_to_websocket_clients.return_value.set_result(None)
    mock_app.config.libretranslate_api_key = MagicMock()
    mock_app.translator_handler = MagicMock()
    with pytest.raises(ValueError):
        await mock_app.update_config({"libretranslate_api_key": "z" * 513})


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

    peer = RNS.Identity()
    dest = RNS.Destination.hash(peer, "lxmf", "delivery").hex()
    uri = f"lxma://{dest}:{peer.get_public_key().hex()}"

    mock_app.config.auth_enabled.get.return_value = False

    with (
        patch(
            "meshchatx.meshchat.AsyncUtils.run_async",
            side_effect=lambda coro: asyncio.create_task(coro),
        ),
        patch("meshchatx.meshchat.RNS.Identity.remember") as remember_mock,
    ):
        await mock_app.on_websocket_data_received(
            mock_client,
            {
                "type": "lxm.ingest_uri",
                "uri": uri,
            },
        )
        await asyncio.sleep(0)

    mock_app.database.contacts.add_contact.assert_called_once_with(
        f"Contact {dest[:8]}",
        peer.hash.hex(),
        lxmf_address=dest,
    )
    remember_mock.assert_called_once()
    mock_app.message_router.ingest_lxm_uri.assert_not_called()
    mock_client.send_str.assert_called_once()
    payload = json.loads(mock_client.send_str.call_args[0][0])
    assert payload["type"] == "lxm.ingest_uri.result"
    assert payload["status"] == "success"
    assert payload["ingest_type"] == "lxma_contact"
    assert payload["destination_hash"] == dest


@pytest.mark.asyncio
async def test_lxm_ingest_uri_lxma_accepts_128_hex_public_key(mock_app):
    """64-byte RNS public keys must load from full material, not only the first 32 bytes."""
    mock_app.database.contacts.get_contact_by_identity_hash.return_value = None
    mock_app.database.contacts.add_contact = MagicMock()
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))

    peer = RNS.Identity()
    dest = RNS.Destination.hash(peer, "lxmf", "delivery").hex()
    pub = peer.get_public_key()
    assert len(pub) == 64
    mock_app.config.auth_enabled.get.return_value = False

    with (
        patch(
            "meshchatx.meshchat.AsyncUtils.run_async",
            side_effect=lambda coro: asyncio.create_task(coro),
        ),
        patch("meshchatx.meshchat.RNS.Identity.remember"),
    ):
        await mock_app.on_websocket_data_received(
            mock_client,
            {
                "type": "lxm.ingest_uri",
                "uri": f"lxma://{dest}:{pub.hex()}",
            },
        )
        await asyncio.sleep(0)

    mock_app.database.contacts.add_contact.assert_called_once()
    payload = json.loads(mock_client.send_str.call_args[0][0])
    assert payload["status"] == "success"
    assert payload["ingest_type"] == "lxma_contact"
    assert payload["destination_hash"] == dest
    kwargs = mock_app.database.contacts.add_contact.call_args
    assert kwargs.kwargs["lxmf_address"] == dest
    assert kwargs.args[1] == peer.hash.hex()


def test_identity_from_public_key_bytes_accepts_real_rns_none_return():
    """Regression for issue #21: RNS load_public_key returns None on success."""
    import RNS

    from meshchatx.meshchat import ReticulumMeshChat

    source = RNS.Identity()
    pub = source.get_public_key()
    loaded = ReticulumMeshChat._identity_from_public_key_bytes(pub)
    assert loaded is not None
    assert loaded.hash == source.hash
    assert ReticulumMeshChat._identity_from_public_key_bytes(b"\x00" * 8) is None


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
        patch(
            "meshchatx.meshchat.convert_lxmf_method_to_string",
            return_value="direct",
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async") as mock_run_async,
    ):
        mock_app.on_lxmf_sending_state_updated(mock_msg, context=ctx)

        ctx.database.messages.update_lxmf_message_state.assert_called_once()
        call_kwargs = ctx.database.messages.update_lxmf_message_state.call_args
        assert call_kwargs.kwargs["message_hash"] == "ab" * 16
        assert call_kwargs.kwargs["progress"] == 75.0
        assert call_kwargs.kwargs["state"] == "delivered"
        assert call_kwargs.kwargs["method"] == "direct"
        mock_run_async.assert_called_once()


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
            sample = int(
                0.3 * 32767 * math.sin(2 * math.pi * frequency * (i / samplerate)),
            )
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

    mock_app._await_transport_path = AsyncMock(
        return_value=OutboundPathOutcome(True, "reused_valid_path", False),
    )
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

    app.recall_identity = MagicMock(return_value=fake_identity)
    with (
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
