"""Property-based robustness tests for NLP module."""

from hypothesis import given, strategies as st
from lxmfy.nlp import IntentClassifier


class TestNLPRobustnessProperty:
    """Property-based tests for IntentClassifier."""

    @given(
        intents=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=10,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            ),
            values=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
            min_size=1,
            max_size=10,
        ),
        threshold=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_nlp_never_crashes_on_training(self, intents, threshold):
        """Verify that IntentClassifier can be trained with any input without crashing."""
        nlp = IntentClassifier(threshold=threshold)
        for name, examples in intents.items():
            nlp.add_intent(name, examples)
        nlp.train()

    @given(
        examples=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=10),
        query=st.text(max_size=500),
        threshold=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_nlp_prediction_robustness(self, examples, query, threshold):
        """Verify that prediction logic handles any query string gracefully."""
        nlp = IntentClassifier(threshold=threshold)
        nlp.add_intent("test_intent", examples)

        # Should not crash
        intent, score = nlp.predict(query)

        assert 0.0 <= score <= 1.000000000000001
        if intent is not None:
            assert intent == "test_intent"

    @given(text=st.text(max_size=1000))
    def test_tokenization_robustness(self, text):
        """Verify that internal tokenization handles all unicode characters."""
        tokens = IntentClassifier._tokenize(text)
        assert isinstance(tokens, list)
        for t in tokens:
            assert isinstance(t, str)

    @given(text=st.text(max_size=100), n=st.integers(min_value=1, max_value=10))
    def test_ngram_robustness(self, text, n):
        """Verify that n-gram generation handles all inputs and n values."""
        ngrams = IntentClassifier._get_char_ngrams(text, n=n)
        assert isinstance(ngrams, list)
        if len(text) + 2 < n:  # +2 for ^ and $
            assert len(ngrams) == 0
        else:
            for ng in ngrams:
                assert len(ng) == n
