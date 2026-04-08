import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from meshchatx.src.backend.translator_handler import TranslatorHandler


def _mock_session_for_languages():
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value=[
            {"code": "en", "name": "English"},
            {"code": "de", "name": "German"},
        ],
    )
    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    return mock_session


class TestTranslatorHandler(unittest.TestCase):
    def setUp(self):
        self.handler = TranslatorHandler(enabled=True)

    @patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
    def test_get_supported_languages(self, mock_session_cls):
        self.handler.has_requests = True
        mock_session_cls.return_value = _mock_session_for_languages()

        langs = self.handler.get_supported_languages()
        self.assertEqual(len(langs), 2)
        self.assertEqual(langs[0]["code"], "en")

    @patch("meshchatx.src.backend.translator_handler.aiohttp.ClientSession")
    def test_translate_text_libretranslate(self, mock_session_cls):
        self.handler.has_requests = True
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "translatedText": "Hallo",
                "detectedLanguage": {"language": "en"},
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

        result = self.handler.translate_text("Hello", "en", "de")
        self.assertEqual(result["translated_text"], "Hallo")
        self.assertEqual(result["source"], "libretranslate")


if __name__ == "__main__":
    unittest.main()
