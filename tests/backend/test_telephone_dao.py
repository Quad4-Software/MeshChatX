# SPDX-License-Identifier: 0BSD

import os
import tempfile

import pytest

from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema
from meshchatx.src.backend.database.telephone import TelephoneDAO


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_call_recordings_dao(temp_db):
    provider = DatabaseProvider(temp_db)
    schema = DatabaseSchema(provider)
    schema.initialize()
    dao = TelephoneDAO(provider)

    # Test adding a recording
    dao.add_call_recording(
        remote_identity_hash="test_hash",
        remote_identity_name="Test Name",
        filename_rx="rx.opus",
        filename_tx="tx.opus",
        duration_seconds=10,
        timestamp=123456789.0,
    )

    # Test getting recordings
    recordings = dao.get_call_recordings()
    assert len(recordings) == 1
    assert recordings[0]["remote_identity_name"] == "Test Name"
    assert recordings[0]["filename_rx"] == "rx.opus"

    # Test searching
    recordings = dao.get_call_recordings(search="Test")
    assert len(recordings) == 1
    recordings = dao.get_call_recordings(search="NonExistent")
    assert len(recordings) == 0

    # Test getting single recording
    recording_id = recordings[0]["id"] if recordings else 1  # get id from first test
    # Re-fetch because list was empty in previous assertion
    recordings = dao.get_call_recordings()
    recording_id = recordings[0]["id"]
    recording = dao.get_call_recording(recording_id)
    assert recording["id"] == recording_id

    # Test deleting
    dao.delete_call_recording(recording_id)
    recordings = dao.get_call_recordings()
    assert len(recordings) == 0

    provider.close()
