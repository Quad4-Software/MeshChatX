import unittest
from unittest.mock import MagicMock, patch, mock_open
from meshchatx.src.backend.translator_handler import TranslatorHandler


class TestTranslatorHandler(unittest.TestCase):
    def setUp(self):
        self.handler = TranslatorHandler(enabled=True)

    @patch("requests.get")
    def test_get_supported_languages(self, mock_get):
        self.handler.has_requests = True
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = [
            {"code": "en", "name": "English"},
            {"code": "de", "name": "German"},
        ]

        langs = self.handler.get_supported_languages()
        self.assertEqual(len(langs), 2)
        self.assertEqual(langs[0]["code"], "en")

    @patch("requests.post")
    def test_translate_text_libretranslate(self, mock_post):
        self.handler.has_requests = True
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.json.return_value = {
            "translatedText": "Hallo",
            "detectedLanguage": {"language": "en"},
        }

        result = self.handler.translate_text("Hello", "en", "de")
        self.assertEqual(result["translated_text"], "Hallo")
        self.assertEqual(result["source"], "libretranslate")


if __name__ == "__main__":
    unittest.main()
