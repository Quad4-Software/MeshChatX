# SPDX-License-Identifier: 0BSD

import base64
import json
import os
import shutil
import tempfile
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
        self,
        mock_schema,
        mock_provider,
        mock_rns_identity,
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
        self,
        mock_schema,
        mock_provider,
        mock_rns_identity,
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
    @patch("meshchatx.src.backend.identity_manager.DatabaseProvider")
    @patch("meshchatx.src.backend.identity_manager.DatabaseSchema")
    def test_restore_identity_from_base32_with_display_name(
        self,
        mock_schema,
        mock_provider,
        mock_rns_identity,
    ):
        mock_id_instance = MagicMock()
        mock_id_instance.hash = b"test_hash_32_bytes_long_01234567"
        mock_id_instance.get_private_key.return_value = b"test_private_key"
        mock_rns_identity.from_bytes.return_value = mock_id_instance

        identity_bytes = b"some_identity_bytes"
        base32_value = base64.b32encode(identity_bytes).decode("utf-8")
        result = self.identity_manager.restore_identity_from_base32(
            base32_value,
            display_name="Imported Name",
        )

        self.assertEqual(result["display_name"], "Imported Name")

    @patch("RNS.Identity")
    @patch("meshchatx.src.backend.identity_manager.DatabaseProvider")
    @patch("meshchatx.src.backend.identity_manager.DatabaseSchema")
    def test_restore_identity_from_base32_blank_display_name_uses_default(
        self,
        mock_schema,
        mock_provider,
        mock_rns_identity,
    ):
        mock_id_instance = MagicMock()
        mock_id_instance.hash = b"test_hash_32_bytes_long_01234567"
        mock_id_instance.get_private_key.return_value = b"test_private_key"
        mock_rns_identity.from_bytes.return_value = mock_id_instance

        identity_bytes = b"some_identity_bytes"
        base32_value = base64.b32encode(identity_bytes).decode("utf-8")
        result = self.identity_manager.restore_identity_from_base32(
            base32_value,
            display_name="   ",
        )

        self.assertEqual(result["display_name"], "Restored Identity")

    @patch("RNS.Identity")
    def test_restore_identity_invalid_bytes(self, mock_rns_identity):
        mock_rns_identity.from_bytes.return_value = None
        with self.assertRaises(ValueError) as cm:
            self.identity_manager.restore_identity_from_bytes(b"invalid")
        self.assertIn("Could not load identity from bytes", str(cm.exception))

    def test_restore_identity_empty_bytes(self):
        with self.assertRaises(ValueError) as cm:
            self.identity_manager.restore_identity_from_bytes(b"")
        self.assertIn("empty", str(cm.exception).lower())

    def test_restore_identity_too_large(self):
        with self.assertRaises(ValueError) as cm:
            self.identity_manager.restore_identity_from_bytes(b"x" * 70000)
        self.assertIn("too large", str(cm.exception).lower())

    @patch("RNS.Identity")
    def test_restore_identity_invalid_base32(self, mock_rns_identity):
        with self.assertRaises(ValueError) as cm:
            self.identity_manager.restore_identity_from_base32("invalid-base32-!!!")
        self.assertIn("Invalid base32 identity", str(cm.exception))

    @patch("RNS.Identity")
    @patch("meshchatx.src.backend.identity_manager.DatabaseProvider")
    @patch("meshchatx.src.backend.identity_manager.DatabaseSchema")
    def test_restore_identity_base32_strips_whitespace(
        self,
        mock_schema,
        mock_provider,
        mock_rns_identity,
    ):
        mock_id_instance = MagicMock()
        mock_id_instance.hash = b"test_hash_32_bytes_long_01234567"
        mock_id_instance.get_private_key.return_value = b"test_private_key"
        mock_rns_identity.from_bytes.return_value = mock_id_instance

        identity_bytes = b"some_identity_bytes"
        base32_value = base64.b32encode(identity_bytes).decode("utf-8")
        spaced = " ".join(
            base32_value[i : i + 4] for i in range(0, len(base32_value), 4)
        )
        result = self.identity_manager.restore_identity_from_base32(spaced)
        self.assertEqual(result["hash"], mock_id_instance.hash.hex())
        mock_rns_identity.from_bytes.assert_called_with(identity_bytes)

    @patch("RNS.Identity")
    @patch("meshchatx.src.backend.identity_manager.DatabaseProvider")
    @patch("meshchatx.src.backend.identity_manager.DatabaseSchema")
    def test_reimport_preserves_existing_metadata(
        self,
        mock_schema,
        mock_provider,
        mock_rns_identity,
    ):
        mock_id_instance = MagicMock()
        mock_id_instance.hash = b"test_hash_32_bytes_long_01234567"
        mock_id_instance.get_private_key.return_value = b"test_private_key"
        mock_rns_identity.from_bytes.return_value = mock_id_instance

        identity_hash = mock_id_instance.hash.hex()
        identity_dir = os.path.join(self.temp_dir, "identities", identity_hash)
        os.makedirs(identity_dir, exist_ok=True)
        metadata_path = os.path.join(identity_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "display_name": "Old Name",
                    "icon_name": "account",
                    "icon_foreground_colour": "#fff",
                    "icon_background_colour": "#000",
                    "lxmf_address": "aabbcc",
                },
                f,
            )

        result = self.identity_manager.restore_identity_from_bytes(
            b"some_identity_bytes",
            display_name="New Name",
        )
        self.assertEqual(result["display_name"], "New Name")
        with open(metadata_path) as f:
            saved = json.load(f)
        self.assertEqual(saved["icon_name"], "account")
        self.assertEqual(saved["lxmf_address"], "aabbcc")
        self.assertEqual(saved["display_name"], "New Name")


if __name__ == "__main__":
    unittest.main()
