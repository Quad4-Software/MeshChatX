from unittest.mock import MagicMock

from lxmfy import BotConfig, LXMFBot


def test_intent_classification_basic():
    """Test the NLP intent classification engine."""
    config = BotConfig(nlp_enabled=True, nlp_threshold=0.4, test_mode=True)
    bot = LXMFBot(**config.__dict__)

    # Register an intent
    @bot.intent(
        "help",
        examples=[
            "how do i use this",
            "show me commands",
            "help me please",
            "what can you do",
        ],
    )
    def help_intent(msg):
        msg.reply("I am here to help!")

    # Test exact match (token based)
    intent, score = bot.nlp.predict("help")
    assert intent == "help"
    assert score > 0.5

    # Test semantic similarity (subset of words)
    intent, score = bot.nlp.predict("how use this")
    assert intent == "help"
    assert score > 0.3

    # Test no match
    intent, score = bot.nlp.predict("completely unrelated text")
    assert intent is None


def test_intent_routing_message_flow():
    """Test that the bot correctly routes messages to intent handlers."""
    config = BotConfig(
        nlp_enabled=True,
        nlp_threshold=0.4,
        test_mode=True,
        command_prefix="/",
    )
    bot = LXMFBot(**config.__dict__)

    intent_called = False

    @bot.intent("greet", examples=["hello bot", "hi there", "greetings", "hi bot"])
    def greet_intent(msg):
        nonlocal intent_called
        intent_called = True
        msg.reply("Hello human!")

    # Mock message
    msg = MagicMock()
    msg.content = b"hi bot"  # Should match 'hi there' or 'hello bot'
    msg.hash = b"mock_hash"

    # Process message
    bot._process_message(msg, "test_sender")

    assert intent_called is True
