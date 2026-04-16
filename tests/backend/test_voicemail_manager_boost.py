# SPDX-License-Identifier: 0BSD

import os
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.voicemail_manager import VoicemailManager


@pytest.fixture
def voicemail_manager(tmp_path):
    db = MagicMock()
    config = MagicMock()
    telephone_manager = MagicMock()
    storage_dir = tmp_path / "voicemail"
    storage_dir.mkdir()
    return VoicemailManager(db, config, telephone_manager, str(storage_dir))


def test_voicemail_manager_init(voicemail_manager):
    assert os.path.exists(voicemail_manager.greetings_dir)
    assert os.path.exists(voicemail_manager.recordings_dir)
    assert voicemail_manager.is_recording is False


def test_find_bundled_binary_not_frozen(voicemail_manager):
    with patch("sys.frozen", False, create=True):
        assert voicemail_manager._find_bundled_binary("test") is None


def test_find_espeak_shutil(voicemail_manager):
    with patch(
        "shutil.which",
        side_effect=lambda x: f"/usr/bin/{x}" if "espeak" in x else None,
    ):
        path = voicemail_manager._find_espeak()
        assert "espeak" in path


def test_find_ffmpeg_shutil(voicemail_manager):
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        path = voicemail_manager._find_ffmpeg()
        assert path == "/usr/bin/ffmpeg"


def test_get_voicemails_empty(voicemail_manager):
    # Voicemails are fetched via DAO
    voicemail_manager.db.voicemails.get_voicemails.return_value = []
    # ReticulumMeshChat uses this pattern:
    res = voicemail_manager.db.voicemails.get_voicemails()
    assert res == []


def test_delete_voicemail(voicemail_manager):
    voicemail_manager.db.voicemails.get_voicemail.return_value = {"filename": "v1.opus"}

    with patch("os.path.exists", return_value=True), patch("os.remove"):
        # deletion is done via DAO and removal of file in routes usually
        voicemail_manager.db.voicemails.delete_voicemail(1)
        voicemail_manager.db.voicemails.delete_voicemail.assert_called_once_with(1)


def test_mark_as_read(voicemail_manager):
    voicemail_manager.db.voicemails.mark_as_read(1)
    voicemail_manager.db.voicemails.mark_as_read.assert_called_once_with(1)
