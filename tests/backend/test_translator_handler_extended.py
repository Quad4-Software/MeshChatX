import pytest
from unittest.mock import MagicMock, patch
from meshchatx.src.backend.translator_handler import TranslatorHandler


def test_translator_handler_init():
    handler = TranslatorHandler(libretranslate_url="http://test:5000", enabled=True)
    assert handler.libretranslate_url == "http://test:5000"
    assert handler.enabled is True


def test_get_supported_languages_disabled():
    handler = TranslatorHandler(enabled=False)
    assert handler.get_supported_languages() == []


@patch("requests.get")
def test_get_supported_languages_libretranslate(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"code": "en", "name": "English"},
        {"code": "fr", "name": "French"},
    ]
    mock_get.return_value = mock_response

    handler = TranslatorHandler(enabled=True)
    langs = handler.get_supported_languages()
    assert len(langs) == 2
    assert langs[0]["code"] == "en"
    assert langs[0]["source"] == "libretranslate"


@patch("requests.post")
def test_translate_libretranslate(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"translatedText": "Bonjour"}
    mock_post.return_value = mock_response

    handler = TranslatorHandler(enabled=True)
    result = handler.translate_text("Hello", source_lang="en", target_lang="fr")
    assert result["translated_text"] == "Bonjour"


@patch("subprocess.run")
def test_translate_argos_cli(mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "Hola"
    mock_run.return_value = mock_result

    handler = TranslatorHandler(enabled=True)
    handler.has_argos_cli = True
    handler.has_argos = True
    handler.has_requests = False  # Force CLI

    with patch("shutil.which", return_value="/usr/bin/argos-translate"):
        result = handler.translate_text(
            "Hello", source_lang="en", target_lang="es", use_argos=True
        )
        assert result["translated_text"] == "Hola"


def test_detect_language_simple():
    TranslatorHandler(enabled=True)
    # _detect_language is private
    pass


@patch("requests.post")
def test_detect_language_libretranslate(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "translatedText": "Bonjour",
        "detectedLanguage": {"language": "en", "confidence": 0.99},
    }
    mock_post.return_value = mock_response

    handler = TranslatorHandler(enabled=True)
    # detect_language is actually done during translate_text in libretranslate
    result = handler.translate_text("Hello world", source_lang="auto", target_lang="fr")
    assert result["source_lang"] == "en"


def test_translator_handler_errors():
    handler = TranslatorHandler(enabled=False)
    with pytest.raises(RuntimeError, match="Translator is disabled"):
        handler.translate_text("Hello", "en", "fr")

    handler.enabled = True
    with pytest.raises(ValueError, match="Text cannot be empty"):
        handler.translate_text("", "en", "fr")


def test_language_code_to_name():
    from meshchatx.src.backend.translator_handler import LANGUAGE_CODE_TO_NAME

    assert LANGUAGE_CODE_TO_NAME["en"] == "English"
    assert LANGUAGE_CODE_TO_NAME["de"] == "German"
