import unittest
from unittest.mock import MagicMock

from meshchatx.src.backend.database.announces import AnnounceDAO
from meshchatx.src.backend.database.messages import MessageDAO
from meshchatx.src.backend.database.misc import MiscDAO


class TestMaintenance(unittest.TestCase):
    def setUp(self):
        self.provider = MagicMock()
        self.messages_dao = MessageDAO(self.provider)
        self.announces_dao = AnnounceDAO(self.provider)
        self.misc_dao = MiscDAO(self.provider)

    def test_delete_all_lxmf_messages(self):
        self.messages_dao.delete_all_lxmf_messages()
        self.assertEqual(self.provider.execute.call_count, 2)
        calls = self.provider.execute.call_args_list
        self.assertIn("DELETE FROM lxmf_messages", calls[0][0][0])
        self.assertIn("DELETE FROM lxmf_conversation_read_state", calls[1][0][0])

    def test_delete_all_announces(self):
        # Test without aspect
        self.announces_dao.delete_all_announces()
        self.provider.execute.assert_called_with("DELETE FROM announces")

        # Test with aspect
        self.announces_dao.delete_all_announces(aspect="test_aspect")
        self.provider.execute.assert_called_with(
            "DELETE FROM announces WHERE aspect = ?",
            ("test_aspect",),
        )

    def test_delete_all_favourites(self):
        # Test without aspect
        self.announces_dao.delete_all_favourites()
        self.provider.execute.assert_called_with("DELETE FROM favourite_destinations")

        # Test with aspect
        self.announces_dao.delete_all_favourites(aspect="test_aspect")
        self.provider.execute.assert_called_with(
            "DELETE FROM favourite_destinations WHERE aspect = ?",
            ("test_aspect",),
        )

    def test_delete_archived_pages(self):
        self.misc_dao.delete_archived_pages()
        self.provider.execute.assert_called_with("DELETE FROM archived_pages")

    def test_delete_all_user_icons(self):
        self.misc_dao.delete_all_user_icons()
        self.provider.execute.assert_called_with("DELETE FROM lxmf_user_icons")

    def test_upsert_lxmf_message(self):
        msg_data = {
            "hash": "test_hash",
            "source_hash": "source",
            "destination_hash": "dest",
            "peer_hash": "peer",
            "content": "hello",
        }
        self.messages_dao.upsert_lxmf_message(msg_data)
        self.provider.execute.assert_called()
        args, _ = self.provider.execute.call_args
        self.assertIn("INSERT INTO lxmf_messages", args[0])
        self.assertIn("ON CONFLICT(hash) DO UPDATE SET", args[0])


if __name__ == "__main__":
    unittest.main()
