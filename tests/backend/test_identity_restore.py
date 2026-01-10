import os
import shutil
import tempfile
import base64
import unittest
from unittest.mock import MagicMock, patch
from meshchatx.src.backend.identity_manager import IdentityManager


class TestIdentityRestore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.identity_manager = IdentityManager(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch("RNS.Identity")
    @patch("meshchatx.src.backend.identity_manager.DatabaseProvider")
    @patch("meshchatx.src.backend.identity_manager.DatabaseSchema")
    def test_restore_identity_from_bytes(
        self, mock_schema, mock_provider, mock_rns_identity
    ):
        # Setup mock identity
        mock_id_instance = MagicMock()
        mock_id_instance.hash = b"test_hash_32_bytes_long_01234567"
        mock_id_instance.get_private_key.return_value = b"test_private_key"
        mock_rns_identity.from_bytes.return_value = mock_id_instance

        identity_bytes = b"some_identity_bytes"
        result = self.identity_manager.restore_identity_from_bytes(identity_bytes)

        identity_hash = mock_id_instance.hash.hex()
        self.assertEqual(result["hash"], identity_hash)
        self.assertEqual(result["display_name"], "Restored Identity")

        # Verify files were created
        identity_dir = os.path.join(self.temp_dir, "identities", identity_hash)
        self.assertTrue(os.path.exists(identity_dir))
        self.assertTrue(os.path.exists(os.path.join(identity_dir, "identity")))
        self.assertTrue(os.path.exists(os.path.join(identity_dir, "metadata.json")))

        # Verify private key was written
        with open(os.path.join(identity_dir, "identity"), "rb") as f:
            self.assertEqual(f.read(), b"test_private_key")

    @patch("RNS.Identity")
    @patch("meshchatx.src.backend.identity_manager.DatabaseProvider")
    @patch("meshchatx.src.backend.identity_manager.DatabaseSchema")
    def test_restore_identity_from_base32(
        self, mock_schema, mock_provider, mock_rns_identity
    ):
        # Setup mock identity
        mock_id_instance = MagicMock()
        mock_id_instance.hash = b"test_hash_32_bytes_long_01234567"
        mock_id_instance.get_private_key.return_value = b"test_private_key"
        mock_rns_identity.from_bytes.return_value = mock_id_instance

        identity_bytes = b"some_identity_bytes"
        base32_value = base64.b32encode(identity_bytes).decode("utf-8")

        result = self.identity_manager.restore_identity_from_base32(base32_value)

        identity_hash = mock_id_instance.hash.hex()
        self.assertEqual(result["hash"], identity_hash)

        # Verify from_bytes was called with the decoded bytes
        mock_rns_identity.from_bytes.assert_called_with(identity_bytes)

    @patch("RNS.Identity")
    def test_restore_identity_invalid_bytes(self, mock_rns_identity):
        mock_rns_identity.from_bytes.return_value = None
        with self.assertRaises(ValueError) as cm:
            self.identity_manager.restore_identity_from_bytes(b"invalid")
        self.assertIn("Could not load identity from bytes", str(cm.exception))

    @patch("RNS.Identity")
    def test_restore_identity_invalid_base32(self, mock_rns_identity):
        with self.assertRaises(ValueError) as cm:
            self.identity_manager.restore_identity_from_base32("invalid-base32-!!!")
        self.assertIn("Invalid base32 identity", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
