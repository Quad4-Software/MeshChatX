import os
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.telephone_manager import Tee, TelephoneManager


@pytest.fixture
def mock_identity():
    return MagicMock()


@pytest.fixture
def tel_manager(mock_identity, tmp_path):
    storage_dir = tmp_path / "tel"
    storage_dir.mkdir()
    return TelephoneManager(mock_identity, storage_dir=str(storage_dir))


def test_tee_basic():
    sink = MagicMock()
    tee = Tee(sink)
    assert sink in tee.sinks

    tee.handle_frame(b"frame", "source")
    sink.handle_frame.assert_called_with(b"frame", "source")


def test_tel_manager_init(tel_manager, mock_identity):
    assert tel_manager.identity == mock_identity
    assert os.path.exists(tel_manager.recordings_dir)


@patch("meshchatx.src.backend.telephone_manager.Telephone")
def test_init_telephone(mock_tel_class, tel_manager):
    tel_manager.init_telephone()
    assert tel_manager.telephone is not None
    mock_tel_class.assert_called_once()


@patch("meshchatx.src.backend.telephone_manager.Telephone")
def test_init_telephone_applies_config_audio_profile(mock_tel_class, mock_identity, tmp_path):
    storage_dir = tmp_path / "tel"
    storage_dir.mkdir()
    cfg = MagicMock()
    cfg.telephone_audio_profile_id.get.return_value = 96
    tm = TelephoneManager(mock_identity, config_manager=cfg, storage_dir=str(storage_dir))
    tm.init_telephone()
    mock_tel_class.return_value.switch_profile.assert_called_with(96)


def test_is_recording_false(tel_manager):
    assert tel_manager.is_recording is False


def test_set_callbacks(tel_manager):
    def cb1():
        return None

    def cb2():
        return None

    def cb3():
        return None

    tel_manager.set_callbacks(ringing=cb1, established=cb2, ended=cb3)
    assert tel_manager.on_ringing_callback == cb1
    assert tel_manager.on_established_callback == cb2
    assert tel_manager.on_ended_callback == cb3
