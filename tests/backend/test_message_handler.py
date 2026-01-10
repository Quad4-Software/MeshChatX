import unittest
from unittest.mock import MagicMock

from meshchatx.src.backend.message_handler import MessageHandler


class TestMessageHandler(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.handler = MessageHandler(self.db)

    def test_get_conversation_messages(self):
        self.db.provider.fetchall.return_value = [{"id": 1, "content": "test"}]

        messages = self.handler.get_conversation_messages("local", "dest", limit=50)

        self.assertEqual(len(messages), 1)
        self.db.provider.fetchall.assert_called()
        args, kwargs = self.db.provider.fetchall.call_args
        self.assertIn("peer_hash = ?", args[0])
        self.assertIn("dest", args[1])

    def test_delete_conversation(self):
        self.handler.delete_conversation("local", "dest")
        self.assertEqual(self.db.provider.execute.call_count, 2)
        call_args_list = self.db.provider.execute.call_args_list
        first_call_args, _ = call_args_list[0]
        second_call_args, _ = call_args_list[1]
        self.assertIn("DELETE FROM lxmf_messages", first_call_args[0])
        self.assertIn("dest", first_call_args[1])
        self.assertIn("DELETE FROM lxmf_conversation_folders", second_call_args[0])
        self.assertIn("dest", second_call_args[1])


if __name__ == "__main__":
    unittest.main()
