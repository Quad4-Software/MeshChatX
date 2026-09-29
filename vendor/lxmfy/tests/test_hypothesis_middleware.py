from hypothesis import given
from hypothesis import strategies as st

from lxmfy.middleware import MessageTracker


class TestMiddlewarePropertyBased:
    """Property-based tests for middleware utilities."""

    @given(
        hashes=st.lists(st.text(min_size=1), min_size=1, max_size=200),
        max_size=st.integers(min_value=10, max_value=50),
    )
    def test_message_tracker_pruning(self, hashes, max_size):
        """Test that MessageTracker correctly prunes old hashes and tracks new ones."""
        tracker = MessageTracker(max_size=max_size)

        for h in hashes:
            tracker.is_processed(h)

        assert len(tracker.processed_set) <= max_size

        # Last added items should generally be in the set
        last_item = hashes[-1]
        assert last_item in tracker.processed_set

    @given(h=st.text(min_size=1))
    def test_message_tracker_idempotence(self, h):
        """Test that the first call returns False and subsequent calls return True."""
        tracker = MessageTracker()
        assert tracker.is_processed(h) is False
        assert tracker.is_processed(h) is True
        assert tracker.is_processed(h) is True
