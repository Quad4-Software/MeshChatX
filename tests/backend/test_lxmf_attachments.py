# SPDX-License-Identifier: 0BSD

import json

import pytest

from meshchatx.src.backend.meshchat_utils import message_fields_have_attachments


def test_message_fields_have_attachments():
    # Empty or null fields
    assert message_fields_have_attachments(None) is False
    assert message_fields_have_attachments("") is False
    assert message_fields_have_attachments("{}") is False

    # Image attachment
    assert message_fields_have_attachments(json.dumps({"image": "base64data"})) is True

    # Audio attachment
    assert message_fields_have_attachments(json.dumps({"audio": "base64data"})) is True

    # File attachments - empty list
    assert (
        message_fields_have_attachments(json.dumps({"file_attachments": []})) is False
    )

    # File attachments - with files
    assert (
        message_fields_have_attachments(
            json.dumps({"file_attachments": [{"file_name": "test.txt"}]}),
        )
        is True
    )

    # Invalid JSON
    assert message_fields_have_attachments("invalid-json") is False


def test_message_fields_have_attachments_mixed():
    # Both image and files
    assert (
        message_fields_have_attachments(
            json.dumps(
                {"image": "img", "file_attachments": [{"file_name": "test.txt"}]},
            ),
        )
        is True
    )

    # Unrelated fields
    assert (
        message_fields_have_attachments(
            json.dumps({"title": "hello", "content": "world"}),
        )
        is False
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/home/user/Documents/secret.pdf", "secret.pdf"),
        (r"C:\Users\bob\passwords.txt", "passwords.txt"),
        ("../../etc/passwd", "passwd"),
        ("note.txt", "note.txt"),
        ("", "attachment"),
        (".", "attachment"),
        ("..", "attachment"),
    ],
)
def test_lxmf_file_attachment_name_is_basename_only(raw, expected):
    from meshchatx.src.backend.lxmf_message_fields import LxmfFileAttachment

    att = LxmfFileAttachment(raw, b"data")
    assert att.file_name == expected
    assert "/" not in att.file_name
    assert "\\" not in att.file_name
