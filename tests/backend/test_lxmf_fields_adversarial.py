# SPDX-License-Identifier: 0BSD
"""Adversarial attachment names for lxmf_message_fields."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.lxmf_message_fields import LxmfFileAttachment


class TestAttachmentNameSafety:
    @given(name=st.text(max_size=120))
    @settings(max_examples=150, deadline=2000)
    def test_attachment_never_raises_on_name(self, name):
        LxmfFileAttachment(file_name=name, file_bytes=b"x")

    @given(name=st.text(alphabet="ab/.\\:_~x0- ", max_size=80))
    @settings(max_examples=150, deadline=2000)
    def test_sanitized_name_is_basename(self, name):
        att = LxmfFileAttachment(file_name=name, file_bytes=b"x")
        assert "/" not in att.file_name
        assert "\\" not in att.file_name
        assert att.file_name not in ("", ".", "..")

    @pytest.mark.parametrize(
        "name",
        [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "/abs/path/file",
            "\\\\server\\share",
            ".",
            "..",
            "",
            None,
            123,
        ],
    )
    def test_traversal_names_neutralized(self, name):
        att = LxmfFileAttachment(file_name=name, file_bytes=b"x")
        assert "/" not in att.file_name
        assert "\\" not in att.file_name
        assert att.file_name not in ("", ".", "..")

    def test_null_bytes_not_published(self):
        # A null byte in the published name can truncate filename handling on
        # peer platforms and in zip/archive tooling.
        att = LxmfFileAttachment(file_name="a\x00b.txt", file_bytes=b"x")
        assert "\x00" not in att.file_name


class TestFieldData:
    @given(data=st.binary(max_size=64))
    @settings(max_examples=60, deadline=2000)
    def test_arbitrary_binary_attachment_data(self, data):
        att = LxmfFileAttachment(file_name="f.bin", file_bytes=data)
        assert att.file_bytes == data
