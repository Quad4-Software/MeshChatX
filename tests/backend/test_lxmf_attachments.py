import json

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
