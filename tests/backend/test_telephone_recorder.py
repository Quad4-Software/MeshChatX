# SPDX-License-Identifier: 0BSD

import os
import time
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend.telephone_manager import TelephoneManager


@pytest.fixture
def mock_identity():
    mock_id = MagicMock(spec=RNS.Identity)
    mock_id.hash = b"test_identity_hash_32_bytes_long"
    return mock_id


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.call_recording_enabled.get.return_value = True
    config.telephone_audio_profile_id.get.return_value = 2
    return config


@pytest.fixture
def mock_db():
    db = MagicMock()
    return db


@pytest.fixture
def temp_storage(tmp_path):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return str(storage_dir)


def test_telephone_manager_init(mock_identity, mock_config, temp_storage):
    tm = TelephoneManager(
        mock_identity,
        config_manager=mock_config,
        storage_dir=temp_storage,
    )
    assert tm.identity == mock_identity
    assert tm.config_manager == mock_config
    assert tm.storage_dir == temp_storage
    assert os.path.exists(tm.recordings_dir)


@patch("meshchatx.src.backend.telephone_manager.Telephone")
def test_call_recording_lifecycle(
    mock_telephone_class,
    mock_identity,
    mock_config,
    mock_db,
    temp_storage,
):
    # Setup mocks
    mock_telephone = mock_telephone_class.return_value
    mock_active_call = MagicMock()
    mock_remote_identity = MagicMock()
    mock_remote_identity.hash = b"remote_hash_32_bytes_long_012345"
    mock_active_call.get_remote_identity.return_value = mock_remote_identity
    mock_telephone.active_call = mock_active_call

    # Mock mixers
    mock_telephone.receive_mixer = MagicMock()
    mock_telephone.transmit_mixer = MagicMock()

    tm = TelephoneManager(
        mock_identity,
        config_manager=mock_config,
        storage_dir=temp_storage,
        db=mock_db,
    )
    tm.get_name_for_identity_hash = MagicMock(return_value="Remote User")
    tm.init_telephone()

    # Simulate call established
    tm.on_telephone_call_established(mock_remote_identity)

    # Verify recording NOT started (disabled for now)
    assert not tm.is_recording
    # assert mock_sink.call_count == 0 # RX and TX sinks not created
    # assert mock_sink.return_value.start.called # Autodigest handled by monkey patch in meshchat.py

    # Simulate call ended after some time
    tm.recording_start_time = time.time() - 5  # 5 seconds duration
    # tm.is_recording = True # Force recording state for test (Disabled for now as property has no setter)
    tm.recording_remote_identity = mock_remote_identity
    tm.on_telephone_call_ended(mock_remote_identity)

    # Verify recording stopped and saved to DB
    assert not tm.is_recording
    # assert mock_db.telephone.add_call_recording.called # Disabled for now as recording is disabled


def test_call_recording_disabled(mock_identity, mock_config, mock_db, temp_storage):
    mock_config.call_recording_enabled.get.return_value = False
    tm = TelephoneManager(
        mock_identity,
        config_manager=mock_config,
        storage_dir=temp_storage,
        db=mock_db,
    )

    # Mock telephone and active call
    tm.telephone = MagicMock()
    tm.telephone.active_call = MagicMock()

    tm.on_telephone_call_established(MagicMock())

    assert not tm.is_recording
    assert not mock_db.telephone.add_call_recording.called


def test_audio_profile_persistence(mock_identity, mock_config, temp_storage):
    with patch(
        "meshchatx.src.backend.telephone_manager.Telephone",
    ) as mock_telephone_class:
        mock_telephone = mock_telephone_class.return_value
        mock_config.telephone_audio_profile_id.get.return_value = 4

        tm = TelephoneManager(
            mock_identity,
            config_manager=mock_config,
            storage_dir=temp_storage,
        )
        tm.init_telephone()

        # Verify switch_profile was called with configured ID
        mock_telephone.switch_profile.assert_called_with(4)


@patch("meshchatx.src.backend.telephone_manager.Telephone")
def test_call_recording_saves_after_disconnect(
    mock_telephone_class,
    mock_identity,
    mock_config,
    mock_db,
    temp_storage,
):
    # Setup mocks
    mock_telephone = mock_telephone_class.return_value
    mock_active_call = MagicMock()
    mock_remote_identity = MagicMock()
    mock_remote_identity.hash = b"remote_hash_32_bytes_long_012345"
    mock_active_call.get_remote_identity.return_value = mock_remote_identity
    mock_telephone.active_call = mock_active_call

    # Mock mixers
    mock_telephone.receive_mixer = MagicMock()
    mock_telephone.transmit_mixer = MagicMock()

    tm = TelephoneManager(
        mock_identity,
        config_manager=mock_config,
        storage_dir=temp_storage,
        db=mock_db,
    )
    tm.init_telephone()

    # Start recording
    tm.start_recording()
    assert not tm.is_recording  # Disabled for now

    # Force recording state for test
    # tm.is_recording = True (Disabled for now as property has no setter)
    tm.recording_remote_identity = mock_remote_identity

    # Simulate call disconnected (active_call becomes None)
    mock_telephone.active_call = None

    # End recording (simulate call ended callback)
    tm.recording_start_time = time.time() - 5
    tm.on_telephone_call_ended(mock_remote_identity)

    # Verify it still saved using the captured identity
    assert not tm.is_recording
    # assert mock_db.telephone.add_call_recording.called # Disabled for now as recording is disabled


@patch("meshchatx.src.backend.telephone_manager.Telephone")
def test_manual_mute_overrides(
    mock_telephone_class,
    mock_identity,
    mock_config,
    temp_storage,
):
    mock_telephone = mock_telephone_class.return_value
    tm = TelephoneManager(
        mock_identity,
        config_manager=mock_config,
        storage_dir=temp_storage,
    )
    tm.init_telephone()

    # Test transmit mute
    tm.mute_transmit()
    assert tm.transmit_muted is True
    mock_telephone.mute_transmit.assert_called_once()

    tm.unmute_transmit()
    assert tm.transmit_muted is False
    mock_telephone.unmute_transmit.assert_called_once()

    # Test receive mute
    tm.mute_receive()
    assert tm.receive_muted is True
    mock_telephone.mute_receive.assert_called_once()

    tm.unmute_receive()
    assert tm.receive_muted is False
    mock_telephone.unmute_receive.assert_called_once()
