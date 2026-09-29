import pytest
from hypothesis import given
from hypothesis import strategies as st

from lxmfy.attachments import Attachment, AttachmentType, pack_attachment


class TestAttachmentFuzzing:
    """Fuzz testing for attachment binary parsing and packing."""

    @given(
        type=st.sampled_from(list(AttachmentType)),
        name=st.text(min_size=0, max_size=255),
        data=st.binary(min_size=0, max_size=10000),
        format=st.text(min_size=0, max_size=50),
    )
    def test_pack_attachment_robustness(self, type, name, data, format):
        """Test that packing an attachment with any binary data never crashes."""
        att = Attachment(type=type, name=name, data=data, format=format)
        try:
            fields = pack_attachment(att)
            assert isinstance(fields, dict)
            # Ensure keys are integers for LXMF compatibility
            assert all(isinstance(k, int) for k in fields.keys())
        except Exception as e:
            pytest.fail(f"pack_attachment crashed with {type}, {name}: {e}")
