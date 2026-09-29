from lxmfy.nlp import IntentClassifier


def test_intent_classification_robustness():
    """Test that the NLP engine can handle common typos and variations."""
    nlp = IntentClassifier(threshold=0.35, use_char_ngrams=True)
    nlp.add_intent(
        "help",
        ["how do i use this", "show me commands", "help me please", "what can you do"],
    )

    # Test cases for typos
    typo_cases = [
        ("h3lp", "help"),
        ("hlp", "help"),
        ("show commands", "help"),
        ("what can u do", "help"),
        ("how use this", "help"),
    ]

    for input_text, expected_intent in typo_cases:
        intent, score = nlp.predict(input_text)
        assert intent == expected_intent, (
            f"Failed to match '{input_text}' to '{expected_intent}' (score: {score})"
        )


def test_intent_classification_accuracy():
    """Generate a confusion matrix report for the NLP engine."""
    nlp = IntentClassifier(threshold=0.3, use_char_ngrams=True)

    intents = {
        "greeting": ["hello", "hi there", "greetings", "good morning"],
        "help": ["how do i use this", "show me commands", "help me please"],
        "status": ["what is your status", "are you online", "is everything okay"],
        "shutdown": ["turn off", "stop running", "shutdown bot"],
    }

    for name, examples in intents.items():
        nlp.add_intent(name, examples)

    report = []
    report.append("\n" + "=" * 50)
    report.append("NLP CONFUSION MATRIX REPORT")
    report.append("=" * 50)
    report.append(f"{'Actual Intent':<15} | {'Predicted Intent':<15} | {'Score':<6}")
    report.append("-" * 45)

    total_tests = 0
    correct_matches = 0

    for actual_name, examples in intents.items():
        for example in examples:
            total_tests += 1
            predicted_name, score = nlp.predict(example)
            report.append(
                f"{actual_name:<15} | {predicted_name!s:<15} | {score:.4f}",
            )
            if predicted_name == actual_name:
                correct_matches += 1

    accuracy = (correct_matches / total_tests) * 100 if total_tests > 0 else 0
    report.append("-" * 45)
    report.append(f"Total Accuracy: {accuracy:.2f}% ({correct_matches}/{total_tests})")
    report.append("=" * 50 + "\n")

    # Print report to stdout when running with -s
    print("\n".join(report))

    assert accuracy > 90, "NLP classification accuracy is too low"


def test_intent_classification_discrimination():
    """Test that unrelated text does not trigger intents."""
    nlp = IntentClassifier(threshold=0.5, use_char_ngrams=True)
    nlp.add_intent("help", ["how do i use this", "show me commands", "help me please"])

    unrelated_texts = [
        "the weather is nice today",
        "i like to eat pizza",
        "quantum physics is complex",
        "1234567890",
    ]

    for text in unrelated_texts:
        intent, score = nlp.predict(text)
        assert intent is None, (
            f"False positive triggered for '{text}' (intent: {intent}, score: {score})"
        )
