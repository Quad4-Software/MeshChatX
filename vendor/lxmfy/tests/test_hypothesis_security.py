from unittest.mock import MagicMock

import pytest
import RNS
from hypothesis import given
from hypothesis import strategies as st

from lxmfy import BotConfig, LXMFBot


def test_identity_pinning_collision_resilience(test_config_dir):
    """Verify that identity pinning resists key collisions for the same hash."""
    # 1. Setup bot with pinning and isolated storage
    import uuid

    storage_path = str(test_config_dir / f"pin_test_{uuid.uuid4().hex}")
    config = BotConfig(
        identity_pinning_enabled=True,
        test_mode=True,
        storage_path=storage_path,
        config_path=storage_path,
    )
    bot = LXMFBot(**config.__dict__)

    # 2. First owner seen for a hash
    sender_hash = "abc123def456"
    owner_identity = RNS.Identity()

    # Simulate first message verification (pins the identity)
    bot.signature_manager.verify_message_signature(
        MagicMock(),
        b"valid_sig",
        sender_hash,
        sender_identity=owner_identity,
    )

    # Verify it was pinned
    pinned_key = bot.storage.get(f"pin:{sender_hash}")
    assert pinned_key == owner_identity.get_public_key()

    # 3. Attacker with DIFFERENT key but same hash (simulated)
    attacker_identity = RNS.Identity()
    assert attacker_identity.get_public_key() != owner_identity.get_public_key()

    # Try to verify with attacker key for the same hash
    # Our pinning layer should reject it
    is_valid = bot.signature_manager.verify_message_signature(
        MagicMock(),
        b"attacker_sig",
        sender_hash,
        sender_identity=attacker_identity,
    )

    assert is_valid is False, (
        "Pinning failed to reject a different key for the same hash!"
    )


@given(st.binary(min_size=64, max_size=64))
def test_signature_malleability_hypothesis(mutated_sig):
    """Test that mutated signatures are never accepted."""
    config = BotConfig(signature_verification_enabled=True, test_mode=True)
    bot = LXMFBot(**config.__dict__)

    sender_hash = "test_sender"
    identity = RNS.Identity()

    # Any random mutation of a signature should fail validation
    # (Assuming the canonical message data is held constant)
    is_valid = bot.signature_manager.verify_message_signature(
        MagicMock(),
        mutated_sig,
        sender_hash,
        sender_identity=identity,
    )

    # Valid validation is statistically impossible with random bytes
    assert is_valid is False


@pytest.fixture(scope="module")
def trained_nlp():
    """Shared trained NLP instance for fuzzing."""
    from lxmfy.nlp import IntentClassifier

    nlp = IntentClassifier(threshold=0.5)
    nlp.add_intent("test", ["hello world", "how are you"], train=True)
    return nlp


@given(st.text(min_size=1, max_size=500))
def test_intent_classification_fuzzing(trained_nlp, input_text):
    """Fuzz the intent classifier with arbitrary strings."""
    # Should never crash regardless of input
    try:
        intent, score = trained_nlp.predict(input_text)
        assert 0.0 <= score <= 1.0
    except Exception as e:
        pytest.fail(
            f"Intent classifier crashed on input: {input_text!r} with error: {e}",
        )
