"""Smoke tests for LXMFy."""

from lxmfy import BotConfig, LXMFBot


def test_bot_initialization(test_config_dir):
    """Verify that the bot can be initialized with basic config."""
    config = BotConfig(
        name="SmokeBot",
        storage_path=str(test_config_dir / "smoke_storage"),
        test_mode=True,
    )
    bot = LXMFBot(**config.__dict__)
    assert bot.config.name == "SmokeBot"
    assert bot.storage is not None
    assert bot.transport is not None


def test_cog_loading(test_config_dir):
    """Verify that cogs can be enabled and disabled."""
    config = BotConfig(
        name="CogBot",
        storage_path=str(test_config_dir / "cog_storage"),
        test_mode=True,
        cogs_enabled=True,
    )
    bot = LXMFBot(**config.__dict__)
    assert bot.config.cogs_enabled is True


def test_nlp_smoke():
    """Verify that the NLP engine basic prediction works."""
    from lxmfy.nlp import IntentClassifier

    nlp = IntentClassifier(threshold=0.1)
    nlp.add_intent("test", ["this is a test"])
    intent, score = nlp.predict("this is a test")
    assert intent == "test"
    assert score > 0.1


def test_storage_smoke(test_config_dir):
    """Verify basic storage operations."""
    from lxmfy.storage import Storage, JSONStorage

    storage_path = test_config_dir / "storage_smoke"
    storage = Storage(JSONStorage(str(storage_path)))
    storage.set("test_key", "test_value")
    assert storage.get("test_key") == "test_value"
    storage.delete("test_key")
    assert storage.get("test_key") is None
