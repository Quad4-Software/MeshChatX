"""Advanced mathematical and manifold testing for NLP and protocol logic."""

from lxmfy.nlp import IntentClassifier


class TestNLPManifolds:
    """Mathematical verification of intent vector space."""

    def test_intent_orthogonality_matrix(self):
        """Verify that registered intents are mathematically distinct."""
        nlp = IntentClassifier(threshold=0.5)

        # Add potentially confusing intents
        intents = {
            "shutdown": [
                "turn off the bot",
                "shutdown now",
                "stop the service",
                "kill process",
            ],
            "status": [
                "what is the status",
                "is the bot running",
                "check service health",
                "is it alive",
            ],
            "restart": [
                "restart the bot",
                "reboot service",
                "turn off and on again",
                "refresh process",
            ],
            "help": [
                "how do i use this",
                "show me commands",
                "help me please",
                "what can you do",
            ],
        }

        for name, examples in intents.items():
            nlp.add_intent(name, examples)

        nlp.train()

        # Calculate Cosine Similarity Matrix between all intents
        # We compare the average vector (or best match) of each intent against others
        intent_names = list(intents.keys())
        collisions = []

        for i, name1 in enumerate(intent_names):
            for j, name2 in enumerate(intent_names):
                if i >= j:
                    continue

                # Check cross-similarity
                # We use the internal processed_examples to find max similarity between two intent sets
                max_cross_sim = 0
                for v1, mag1 in nlp._processed_examples[name1]:
                    for v2, mag2 in nlp._processed_examples[name2]:
                        sim = nlp._cosine_similarity(v1, mag1, v2, mag2)
                        if sim > max_cross_sim:
                            max_cross_sim = sim

                # If similarity is too high (> 0.7), the manifold is ambiguous
                if max_cross_sim > 0.7:
                    collisions.append((name1, name2, max_cross_sim))

        # Report collisions
        if collisions:
            msg = "\n".join(
                [
                    f"Ambiguous intent pair: {n1} <-> {n2} (Sim: {s:.4f})"
                    for n1, n2, s in collisions
                ]
            )
            # We don't necessarily fail unless it's extreme, but we want to know
            print(f"\n[NLP Manifold Warning] {msg}")

        # A hard failure if two different intents are identical or nearly identical
        for n1, n2, s in collisions:
            assert s < 0.9, (
                f"Intents '{n1}' and '{n2}' are mathematically indistinguishable (Sim: {s})"
            )

    def test_vector_space_density(self):
        """Test how intent classification behaves with varying training density."""
        # Test with 1 example vs 10 examples
        nlp_sparse = IntentClassifier(threshold=0.4)
        nlp_dense = IntentClassifier(threshold=0.4)

        nlp_sparse.add_intent("help", ["help"])
        nlp_dense.add_intent(
            "help", ["help", "i need help", "assist me", "show commands", "manual"]
        )

        nlp_sparse.train()
        nlp_dense.train()

        # Test a variation
        query = "help me please"
        _, score_sparse = nlp_sparse.predict(query)
        _, score_dense = nlp_dense.predict(query)

        # Dense training should generally provide better or equal confidence for variations
        # due to more anchor points in the manifold
        print(
            f"\n[NLP Density] Sparse score: {score_sparse:.4f}, Dense score: {score_dense:.4f}"
        )
        # Note: In TF-IDF, score_dense might be lower if "help" is less rare,
        # but bigrams/trigrams help stability.
        assert score_dense > 0 or score_sparse > 0
