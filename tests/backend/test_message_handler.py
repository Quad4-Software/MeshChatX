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
        self.assertEqual(self.db.provider.execute.call_count, 4)
        call_args_list = self.db.provider.execute.call_args_list
        sql0, p0 = call_args_list[0][0]
        sql1, p1 = call_args_list[1][0]
        sql2, p2 = call_args_list[2][0]
        sql3, p3 = call_args_list[3][0]
        self.assertIn("DELETE FROM lxmf_messages", sql0)
        self.assertEqual(p0, ["dest"])
        self.assertIn("DELETE FROM lxmf_conversation_read_state", sql1)
        self.assertEqual(p1, ["dest"])
        self.assertIn("DELETE FROM lxmf_conversation_folders", sql2)
        self.assertEqual(p2, ["dest"])
        self.assertIn("DELETE FROM lxmf_conversation_pins", sql3)
        self.assertEqual(p3, ["dest"])

    def test_get_conversations_includes_failed_count(self):
        self.db.provider.fetchall.return_value = [
            {
                "id": 1,
                "hash": "h1",
                "source_hash": "src",
                "destination_hash": "dst",
                "peer_hash": "peer1",
                "state": "failed",
                "progress": 0,
                "is_incoming": 0,
                "title": "",
                "content": "failed msg",
                "fields": "{}",
                "timestamp": 1234567890,
                "is_spam": 0,
                "reply_to_hash": None,
                "created_at": "2023-01-01",
                "updated_at": "2023-01-01",
                "peer_app_data": None,
                "custom_display_name": None,
                "contact_image": None,
                "icon_name": None,
                "foreground_colour": None,
                "background_colour": None,
                "last_read_at": None,
                "folder_id": None,
                "folder_name": None,
                "failed_count": 3,
                "is_contact": 0,
            }
        ]
        result = self.handler.get_conversations("local")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["failed_count"], 3)

    def test_get_conversations_with_filter_failed(self):
        self.db.provider.fetchall.return_value = []
        self.handler.get_conversations("local", filter_failed=True)
        args, _ = self.db.provider.fetchall.call_args
        self.assertIn("state = 'failed'", args[0])

    def test_search_messages(self):
        self.db.provider.fetchall.return_value = [
            {"peer_hash": "peer1", "max_ts": 1234567890}
        ]
        result = self.handler.search_messages("local", "test")
        self.assertEqual(len(result), 1)
        args, _ = self.db.provider.fetchall.call_args
        self.assertIn("LIKE", args[0])

    def test_get_conversation_messages_with_after_id(self):
        self.db.provider.fetchall.return_value = []
        self.handler.get_conversation_messages("local", "dest", after_id=5)
        args, _ = self.db.provider.fetchall.call_args
        self.assertIn("id > ?", args[0])
        self.assertIn(5, args[1])

    def test_get_conversation_messages_with_before_id(self):
        self.db.provider.fetchall.return_value = []
        self.handler.get_conversation_messages("local", "dest", before_id=10)
        args, _ = self.db.provider.fetchall.call_args
        self.assertIn("id < ?", args[0])
        self.assertIn(10, args[1])


if __name__ == "__main__":
    unittest.main()
