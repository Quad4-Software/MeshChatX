"""NLP module for LXMFy.

This module provides lightweight, local intent classification using mathematical
vector embeddings (TF-IDF and Cosine Similarity).
"""

import math
import re
from collections import Counter


class IntentClassifier:
    """Lightweight intent classifier using TF-IDF and Cosine Similarity."""

    def __init__(self, threshold: float = 0.5, use_char_ngrams: bool = True):
        """Initialize the IntentClassifier.

        Args:
            threshold: Minimum similarity score to consider a match.
            use_char_ngrams: Whether to use character n-grams for typo resilience.

        """
        self.intents = {}  # {intent_name: [example_vectors]}
        self.vocabulary = set()
        self.idf = {}
        self.threshold = threshold
        self.use_char_ngrams = use_char_ngrams
        self._processed_examples = {}  # {intent_name: [processed_vectors]}
        self._initialize_base_idf()

    def _initialize_base_idf(self):
        """Initialize with a small set of common English words to provide baseline intelligence."""
        # Baseline IDF values for very common words to help with weighting
        # These are used as a fallback when training data is sparse.
        self.base_idf = {
            "the": 0.1,
            "be": 0.2,
            "to": 0.2,
            "of": 0.2,
            "and": 0.2,
            "a": 0.2,
            "in": 0.3,
            "that": 0.3,
            "have": 0.3,
            "i": 0.3,
            "it": 0.3,
            "for": 0.3,
            "not": 0.4,
            "on": 0.4,
            "with": 0.4,
            "he": 0.4,
            "as": 0.4,
            "you": 0.4,
            "do": 0.4,
            "at": 0.4,
        }
        for word in self.base_idf:
            self.vocabulary.add(word)

    def add_intent(self, name: str, examples: list[str], train: bool = True):
        """Add an intent with training examples.

        Args:
            name: The name of the intent.
            examples: A list of example phrases for this intent.
            train: Whether to retrain the model immediately.

        """
        self.intents[name] = examples
        if train:
            self._train()

    def train(self):
        """Manually trigger model training."""
        self._train()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize and clean text."""
        if not text:
            return []
        # Limit text length and use a simple regex to avoid any potential backtracking
        return re.findall(r"[a-z0-9]+", text.lower()[:1000])

    @staticmethod
    def _get_char_ngrams(text: str, n: int = 3) -> list[str]:
        """Generate character n-grams for typo resilience."""
        if not text:
            return []
        text = f"^{text.strip()}$"
        if len(text) < n:
            return []
        return [text[i : i + n] for i in range(len(text) - n + 1)]

    def _get_features(self, text: str) -> list[str]:
        """Extract features (tokens and optionally n-grams) from text."""
        tokens = self._tokenize(text)
        if not tokens:
            return []

        features = list(tokens)
        if self.use_char_ngrams:
            seen_words = set()
            for word in tokens:
                if word not in seen_words and len(word) > 2:
                    # Use both bigrams and trigrams for better typo resilience
                    features.extend(self._get_char_ngrams(word, n=2))
                    features.extend(self._get_char_ngrams(word, n=3))
                    seen_words.add(word)
        return features

    def _train(self):
        """Calculate IDF and vectorize examples efficiently."""
        all_docs_features = []
        for examples in self.intents.values():
            for ex in examples:
                feats = self._get_features(ex)
                if feats:
                    all_docs_features.append(set(feats))

        num_docs = len(all_docs_features)
        if num_docs == 0:
            return

        # Pre-calculate document frequencies
        df_counts = Counter()
        for doc_set in all_docs_features:
            df_counts.update(doc_set)

        # Build IDF, incorporating base words if they are not already weighted
        self.idf = dict(self.base_idf)
        for feature, count in df_counts.items():
            # Standard IDF: log(N/df)
            # We add 1 to denominator to avoid division by zero (though count is >= 1)
            # and use log(1 + N/df) for smoother weighting
            self.idf[feature] = math.log(1 + (num_docs / count))

        self._processed_examples = {}
        for name, examples in self.intents.items():
            processed_for_intent = []
            for ex in examples:
                vector = self._vectorize(self._get_features(ex))
                if vector:
                    magnitude = math.sqrt(sum(v**2 for v in vector.values()))
                    if magnitude > 0:
                        processed_for_intent.append((vector, magnitude))
            self._processed_examples[name] = processed_for_intent

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        """Convert tokens to a TF-IDF vector (dictionary representation)."""
        if not tokens:
            return {}

        counts = Counter(tokens)
        vector = {}
        total_tokens = len(tokens)

        for token, count in counts.items():
            if token in self.idf:
                tf = count / total_tokens
                vector[token] = tf * self.idf[token]
        return vector

    @staticmethod
    def _cosine_similarity(
        v1: dict[str, float],
        mag1: float,
        v2: dict[str, float],
        mag2: float,
    ) -> float:
        """Calculate cosine similarity between two sparse vectors."""
        # Intersection of keys for sparse dot product
        if len(v1) < len(v2):
            intersection = [x for x in v1 if x in v2]
        else:
            intersection = [x for x in v2 if x in v1]

        if not intersection:
            return 0.0

        numerator = sum(v1[x] * v2[x] for x in intersection)
        denominator = mag1 * mag2

        if denominator <= 0:
            return 0.0
        return numerator / denominator

    def export_model(self) -> dict:
        """Export the trained model data for persistence.

        Returns:
            A dictionary containing the IDF and processed example vectors.

        """
        return {
            "idf": self.idf,
            "processed_examples": self._processed_examples,
            "intents": self.intents,
            "vocabulary": list(self.vocabulary),
            "threshold": self.threshold,
            "use_char_ngrams": self.use_char_ngrams,
        }

    def import_model(self, model_data: dict):
        """Import a previously exported model.

        Args:
            model_data: The dictionary returned by export_model.

        """
        self.idf = model_data.get("idf", {})
        self._processed_examples = model_data.get("processed_examples", {})
        self.intents = model_data.get("intents", {})
        self.vocabulary = set(model_data.get("vocabulary", []))
        self.threshold = model_data.get("threshold", self.threshold)
        self.use_char_ngrams = model_data.get("use_char_ngrams", self.use_char_ngrams)

    def predict(self, text: str) -> tuple[str | None, float]:
        """Predict the intent of a given text.

        Returns:
            A tuple of (intent_name, confidence_score).

        """
        tokens = self._get_features(text)
        if not tokens:
            return None, 0.0

        query_vector = self._vectorize(tokens)
        if not query_vector:
            return None, 0.0

        # Pre-calculate query magnitude once
        query_magnitude = math.sqrt(sum(v**2 for v in query_vector.values()))
        if not query_magnitude:
            return None, 0.0

        best_intent = None
        max_score = 0.0

        for name, examples in self._processed_examples.items():
            for example_vector, magnitude in examples:
                score = self._cosine_similarity(
                    query_vector,
                    query_magnitude,
                    example_vector,
                    magnitude,
                )
                if score > max_score:
                    max_score = score
                    best_intent = name

        if max_score >= self.threshold:
            return best_intent, max_score
        return None, max_score
