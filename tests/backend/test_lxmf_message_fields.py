from meshchatx.src.backend.lxmf_message_fields import (
    LxmfAudioField,
    LxmfFileAttachment,
    LxmfFileAttachmentsField,
    LxmfImageField,
)


def test_lxmf_audio_field():
    audio = LxmfAudioField(1, b"audio_data")
    assert audio.audio_mode == 1
    assert audio.audio_bytes == b"audio_data"


def test_lxmf_image_field():
    image = LxmfImageField("png", b"image_data")
    assert image.image_type == "png"
    assert image.image_bytes == b"image_data"


def test_lxmf_file_attachment():
    file = LxmfFileAttachment("test.txt", b"file_data")
    assert file.file_name == "test.txt"
    assert file.file_bytes == b"file_data"


def test_lxmf_file_attachments_field():
    file1 = LxmfFileAttachment("1.txt", b"data1")
    file2 = LxmfFileAttachment("2.txt", b"data2")
    field = LxmfFileAttachmentsField([file1, file2])
    assert len(field.file_attachments) == 2
    assert field.file_attachments[0].file_name == "1.txt"
    assert field.file_attachments[1].file_name == "2.txt"
