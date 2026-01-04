import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from meshchatx.src.backend.voicemail_manager import VoicemailManager


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_deps():
    with (
        patch("meshchatx.src.backend.voicemail_manager.shutil.which") as mock_which,
        patch("meshchatx.src.backend.voicemail_manager.subprocess.run") as mock_run,
        patch("meshchatx.src.backend.voicemail_manager.Pipeline") as mock_pipeline,
        patch("meshchatx.src.backend.voicemail_manager.OpusFileSink") as mock_sink,
        patch("meshchatx.src.backend.voicemail_manager.OpusFileSource") as mock_source,
        patch("RNS.log"),
    ):
        # Mock finding espeak and ffmpeg
        mock_which.side_effect = lambda x: f"/usr/bin/{x}"
        yield {
            "which": mock_which,
            "run": mock_run,
            "Pipeline": mock_pipeline,
            "OpusFileSink": mock_sink,
            "OpusFileSource": mock_source,
        }


def test_voicemail_manager_init(mock_deps, temp_dir):
    mock_db = MagicMock()
    mock_config = MagicMock()
    mock_tel = MagicMock()

    vm = VoicemailManager(mock_db, mock_config, mock_tel, temp_dir)

    assert vm.storage_dir == os.path.join(temp_dir, "voicemails")
    assert vm.has_espeak is True
    assert vm.has_ffmpeg is True
    assert os.path.exists(vm.greetings_dir)
    assert os.path.exists(vm.recordings_dir)


def test_generate_greeting(mock_deps, temp_dir):
    mock_db = MagicMock()
    mock_config = MagicMock()
    mock_tel = MagicMock()

    # Setup config mocks
    mock_config.voicemail_tts_speed.get.return_value = 175
    mock_config.voicemail_tts_pitch.get.return_value = 50
    mock_config.voicemail_tts_voice.get.return_value = "en"
    mock_config.voicemail_tts_word_gap.get.return_value = 10

    vm = VoicemailManager(mock_db, mock_config, mock_tel, temp_dir)

    with patch("os.path.exists", return_value=True), patch("os.remove"):
        vm.generate_greeting("Hello world")

    # Should have run espeak and ffmpeg
    assert mock_deps["run"].call_count == 2


def test_start_recording_currently_disabled(mock_deps, temp_dir):
    mock_db = MagicMock()
    mock_config = MagicMock()
    mock_tel = MagicMock()
    vm = VoicemailManager(mock_db, mock_config, mock_tel, temp_dir)

    mock_link = MagicMock()
    mock_remote_id = MagicMock()
    mock_remote_id.hash = b"remote_hash"
    mock_link.get_remote_identity.return_value = mock_remote_id

    vm.start_recording(mock_link)

    # It's currently disabled in code, so it should stay False
    assert vm.is_recording is False


def test_stop_recording(mock_deps, temp_dir):
    mock_db = MagicMock()
    mock_config = MagicMock()
    mock_tel = MagicMock()
    vm = VoicemailManager(mock_db, mock_config, mock_tel, temp_dir)

    vm.is_recording = True
    mock_pipeline_inst = MagicMock()
    vm.recording_pipeline = mock_pipeline_inst
    vm.recording_filename = "test.opus"

    mock_remote_id = MagicMock()
    # Use a mock for hash so we can mock its hex() method
    mock_hash = MagicMock()
    mock_hash.hex.return_value = "72656d6f7465"
    mock_remote_id.hash = mock_hash
    vm.recording_remote_identity = mock_remote_id
    vm.recording_start_time = 100

    vm.get_name_for_identity_hash = MagicMock(return_value="Test User")

    with patch("time.time", return_value=110):
        vm.stop_recording()

    assert vm.is_recording is False
    mock_pipeline_inst.stop.assert_called()
    mock_db.voicemails.add_voicemail.assert_called()


def test_start_voicemail_session(mock_deps, temp_dir):
    mock_db = MagicMock()
    mock_config = MagicMock()
    mock_tel_manager = MagicMock()
    mock_tel = MagicMock()
    mock_tel_manager.telephone = mock_tel

    vm = VoicemailManager(mock_db, mock_config, mock_tel_manager, temp_dir)

    mock_caller = MagicMock()
    mock_caller.hash = b"caller"

    mock_tel.answer.return_value = True
    mock_tel.audio_input = MagicMock()

    # Mocking threading.Thread to run the job synchronously for testing
    with patch("threading.Thread") as mock_thread, patch("time.sleep"):
        vm.start_voicemail_session(mock_caller)

        # Verify answer was called
        mock_tel.answer.assert_called_with(mock_caller)
        # Verify mic was stopped
        mock_tel.audio_input.stop.assert_called()

        # Get the job function and run it
        job_func = mock_thread.call_args[1]["target"]

        # We need to setup more mocks for the job to run without crashing
        mock_tel.active_call = MagicMock()
        mock_tel.active_call.audio_source = MagicMock()

        with patch.object(vm, "start_recording") as mock_start_rec:
            # Run the job
            job_func()
            mock_start_rec.assert_called()
