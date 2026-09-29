from unittest import mock

import RNS
from hypothesis import given
from hypothesis import strategies as st

from lxmfy.signatures import SignatureManager

FIELD_SIGNATURE = 0xFA


class TestSignaturePropertyBased:
    """Property-based tests for SignatureManager."""

    @given(
        source_hash=st.binary(min_size=0, max_size=100),
        dest_hash=st.binary(min_size=0, max_size=100),
        content=st.one_of(st.binary(min_size=0, max_size=1000), st.none()),
        title=st.one_of(st.binary(min_size=0, max_size=200), st.none()),
        timestamp=st.one_of(st.integers(min_value=0, max_value=2**32 - 1), st.none()),
        fields=st.dictionaries(
            st.integers(min_value=1, max_value=255),
            st.binary(min_size=0, max_size=100),
        ),
    )
    def test_canonicalize_roundtrip_consistency(
        self,
        source_hash,
        dest_hash,
        content,
        title,
        timestamp,
        fields,
    ):
        """Test that canonicalization is consistent and handles arbitrary data."""
        bot = mock.MagicMock()
        sig_manager = SignatureManager(bot)

        mock_message = mock.MagicMock()
        mock_message.source_hash = source_hash
        mock_message.destination_hash = dest_hash
        mock_message.content = content
        mock_message.title = title
        mock_message.timestamp = timestamp
        # Filter out FIELD_SIGNATURE if it happens to be in generated fields
        mock_message.fields = {k: v for k, v in fields.items() if k != FIELD_SIGNATURE}

        result1 = sig_manager._canonicalize_message(mock_message)
        result2 = sig_manager._canonicalize_message(mock_message)

        # Determinism check
        assert result1 == result2
        assert isinstance(result1, bytes)

    @given(
        content=st.binary(min_size=1, max_size=500),
        title=st.binary(min_size=0, max_size=100),
    )
    def test_signature_verification_property(self, content, title):
        """Test that a signed message always verifies with the correct identity."""
        bot = mock.MagicMock()
        bot.config.identity_pinning_enabled = False  # Disable for this test
        sig_manager = SignatureManager(bot)
        identity = RNS.Identity()

        mock_message = mock.MagicMock()
        mock_message.source_hash = b"source"
        mock_message.destination_hash = b"dest"
        mock_message.content = content
        mock_message.title = title
        mock_message.timestamp = 123456789
        mock_message.fields = {}

        signature = sig_manager.sign_message(mock_message, identity)
        mock_message.fields[FIELD_SIGNATURE] = signature

        sender_hash = RNS.hexrep(identity.hash, delimit=False)
        assert (
            sig_manager.verify_message_signature(
                mock_message,
                signature,
                sender_hash,
                identity,
            )
            is True
        )
