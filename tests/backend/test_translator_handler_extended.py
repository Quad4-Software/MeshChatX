# SPDX-License-Identifier: 0BSD

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.src.backend.translator_handler import (
    TranslatorHandler,
    _normalize_optional_libretranslate_api_key,
)


def test_translator_handler_init():
    handler = TranslatorHandler(
        libretranslate_url="http://127.0.0.1:5000",
        translator_argos_enabled=True,
        translator_libretranslate_enabled=True,
    )
    assert handler.libretranslate_url == "http://127.0.0.1:5000"
    assert handler.translator_argos_enabled is True


def test_translator_handler_init_optional_api_key_stripped():
    handler = TranslatorHandler(libretranslate_api_key=" trim ")
    assert handler.libretranslate_api_key == "trim"


def test_get_supported_languages_no_backends():
    handler = TranslatorHandler()
    handler.has_requests = False
    handler.has_argos = False
    handler.has_argos_lib = False
    handler.has_argos_cli = False
    assert handler.get_supported_languages() == []


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_get_supported_languages_libretranslate(mock_session_cls):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value=[
            {"code": "en", "name": "English"},
            {"code": "fr", "name": "French"},
        ],
    )
    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_cls.return_value = mock_session

    handler = TranslatorHandler()
    handler.has_argos = False
    handler.has_argos_lib = False
    handler.has_argos_cli = False
    handler.has_requests = True
    langs = handler.get_supported_languages()
    assert len(langs) == 2
    assert langs[0]["code"] == "en"
    assert langs[0]["source"] == "libretranslate"


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_translate_libretranslate(mock_session_cls):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"translatedText": "Bonjour"})
    mock_post = MagicMock()
    mock_post.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_post)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_cls.return_value = mock_session

    handler = TranslatorHandler(translator_libretranslate_enabled=True)
    handler.has_requests = True
    result = handler.translate_text("Hello", source_lang="en", target_lang="fr")
    assert result["translated_text"] == "Bonjour"


@patch("subprocess.run")
def test_translate_argos_cli(mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "Hola"
    mock_run.return_value = mock_result

    handler = TranslatorHandler(
        translator_argos_enabled=True, translator_libretranslate_enabled=False
    )
    handler.has_argos_cli = True
    handler.has_argos = True
    handler.has_requests = False  # Force CLI
    handler._argos_cli_executable = "/usr/bin/argos-translate"

    with patch("shutil.which", return_value="/usr/bin/argos-translate"):
        result = handler.translate_text(
            "Hello",
            source_lang="en",
            target_lang="es",
            use_argos=True,
        )
        assert result["translated_text"] == "Hola"


def test_detect_language_simple():
    TranslatorHandler()
    # _detect_language is private


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_detect_language_libretranslate(mock_session_cls):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "translatedText": "Bonjour",
            "detectedLanguage": {"language": "en", "confidence": 0.99},
        },
    )
    mock_post = MagicMock()
    mock_post.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_post)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_cls.return_value = mock_session

    handler = TranslatorHandler(translator_libretranslate_enabled=True)
    handler.has_requests = True
    result = handler.translate_text("Hello world", source_lang="auto", target_lang="fr")
    assert result["source_lang"] == "en"


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_libretranslate_post_disallows_redirects(mock_session_cls):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "translatedText": "y",
            "detectedLanguage": {"language": "en"},
        },
    )
    mock_post_ctx = MagicMock()
    mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_post_ctx)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_cls.return_value = mock_session

    handler = TranslatorHandler(translator_libretranslate_enabled=True)
    handler.has_requests = True
    handler.translate_text("Hello", source_lang="en", target_lang="fr", use_argos=False)

    assert mock_session.post.call_args.kwargs.get("allow_redirects") is False


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_libretranslate_get_languages_disallows_redirects(mock_session_cls):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[{"code": "en", "name": "English"}])
    mock_get_ctx = MagicMock()
    mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get_ctx)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_cls.return_value = mock_session

    handler = TranslatorHandler()
    handler.has_argos = False
    handler.has_argos_lib = False
    handler.has_argos_cli = False
    handler.has_requests = True
    handler.get_supported_languages()

    assert mock_session.get.call_args.kwargs.get("allow_redirects") is False


def test_translator_handler_errors():
    handler = TranslatorHandler(
        translator_argos_enabled=False,
        translator_libretranslate_enabled=False,
    )
    with pytest.raises(RuntimeError, match="Translator is disabled"):
        handler.translate_text("Hello", "en", "fr")

    handler.translator_argos_enabled = True
    handler.translator_libretranslate_enabled = True
    with pytest.raises(ValueError, match="Text cannot be empty"):
        handler.translate_text("", "en", "fr")


def test_language_code_to_name():
    from meshchatx.src.backend.translator_handler import LANGUAGE_CODE_TO_NAME

    assert LANGUAGE_CODE_TO_NAME["en"] == "English"
    assert LANGUAGE_CODE_TO_NAME["de"] == "German"


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_get_supported_languages_skips_link_local_lit_stored_url(mock_session_cls):
    handler = TranslatorHandler(
        libretranslate_url="http://169.254.169.254/",
        translator_libretranslate_enabled=True,
    )
    handler.has_requests = True
    handler.has_argos = False
    handler.has_argos_lib = False
    handler.has_argos_cli = False
    assert handler.get_supported_languages() == []
    mock_session_cls.assert_not_called()


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_translate_text_accepts_remote_libre_url(mock_session_cls):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"translatedText": "Hallo"})
    mock_post = MagicMock()
    mock_post.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_post)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_cls.return_value = mock_session

    handler = TranslatorHandler(
        libretranslate_url="http://example.com:5000/",
        translator_libretranslate_enabled=True,
        translator_argos_enabled=False,
    )
    handler.has_requests = True
    result = handler.translate_text("Hello", "en", "de", use_argos=False)
    assert result["translated_text"] == "Hallo"
    called_url = mock_session.post.call_args.args[0]
    assert called_url.startswith("http://example.com:5000")


def test_get_translator_languages_response_explicit_bad_override_raises():
    handler = TranslatorHandler(
        libretranslate_url="http://127.0.0.1:5000",
        translator_libretranslate_enabled=True,
    )
    handler.has_requests = True
    with pytest.raises(ValueError, match="IPv4 link-local"):
        handler.get_translator_languages_response(
            libretranslate_url="http://169.254.169.254:5000",
        )


def test_normalize_optional_libretranslate_api_key():
    assert _normalize_optional_libretranslate_api_key(None) is None
    assert _normalize_optional_libretranslate_api_key("  ") is None
    assert _normalize_optional_libretranslate_api_key(" xyz ") == "xyz"
    with pytest.raises(ValueError):
        _normalize_optional_libretranslate_api_key("k" * 513)


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_get_supported_languages_sends_api_key_for_languages_when_set(mock_session_cls):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[{"code": "en", "name": "English"}])
    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_cls.return_value = mock_session

    handler = TranslatorHandler(
        translator_libretranslate_enabled=True,
        libretranslate_api_key="srv-key",
    )
    handler.has_requests = True
    handler.has_argos = False
    handler.has_argos_lib = False
    handler.has_argos_cli = False
    handler.get_supported_languages()

    kw = mock_session.get.call_args.kwargs
    assert kw.get("params") == {"api_key": "srv-key"}


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_translate_sends_optional_api_key_in_json_body(mock_session_cls):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "translatedText": "Bonjour",
            "detectedLanguage": {"language": "en"},
        },
    )
    mock_post_ctx = MagicMock()
    mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_post_ctx)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_cls.return_value = mock_session

    handler = TranslatorHandler(
        translator_libretranslate_enabled=True,
        libretranslate_api_key="abc123",
        translator_argos_enabled=False,
    )
    handler.has_requests = True
    handler.translate_text("Hello", "en", "fr", use_argos=False)

    body = mock_session.post.call_args.kwargs.get("json")
    assert body.get("api_key") == "abc123"


@patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
def test_translate_explicit_api_key_overrides_handler_default(mock_session_cls):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"translatedText": "Hi"})
    mock_post_ctx = MagicMock()
    mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_post_ctx)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_cls.return_value = mock_session

    handler = TranslatorHandler(
        translator_libretranslate_enabled=True,
        libretranslate_api_key="stored",
        translator_argos_enabled=False,
    )
    handler.has_requests = True
    handler.translate_text(
        "Hello",
        "en",
        "de",
        use_argos=False,
        libretranslate_api_key=" one-off ",
    )
    body = mock_session.post.call_args.kwargs.get("json")
    assert body.get("api_key") == "one-off"
