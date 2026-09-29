from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from lxmfy.storage import Attachment, AttachmentType, deserialize_value, serialize_value


class TestStoragePropertyBased:
    """Property-based tests for storage serialization."""

    # Strategy for nested JSON-like data with bytes and datetime
    @st.composite
    def serializable_strategy(draw):
        """Generates data that LXMFy storage should be able to serialize."""
        return draw(
            st.recursive(
                st.one_of(
                    st.none(),
                    st.booleans(),
                    st.integers(),
                    st.floats(allow_nan=False, allow_infinity=False),
                    st.text(),
                    st.binary(),
                    st.datetimes(
                        max_value=datetime(2100, 1, 1),
                        min_value=datetime(1970, 1, 1),
                    ),
                ),
                lambda children: st.one_of(
                    st.lists(children),
                    st.dictionaries(st.text(), children),
                ),
            ),
        )

    @given(data=serializable_strategy())
    def test_serialization_roundtrip(self, data):
        """Test that serialize/deserialize is a lossless roundtrip for supported types."""
        serialized = serialize_value(data)
        deserialized = deserialize_value(serialized)

        # Datetime might lose microsecond precision depending on isoformat, but fromisoformat handles it
        # Actually, LXMFy uses isoformat() which is good.
        assert deserialized == data

    @given(
        type=st.sampled_from(list(AttachmentType)),
        name=st.text(min_size=1),
        data=st.binary(),
        format=st.text(),
    )
    def test_attachment_roundtrip(self, type, name, data, format):
        """Test Attachment serialization roundtrip."""
        att = Attachment(type=type, name=name, data=data, format=format)
        serialized = serialize_value(att)
        deserialized = deserialize_value(serialized)

        assert isinstance(deserialized, Attachment)
        assert deserialized.type == att.type
        assert deserialized.name == att.name
        assert deserialized.data == att.data
        assert deserialized.format == att.format
