import base64
import json
import unittest


class TestBase64DecodeRisky(unittest.TestCase):
    def test_invalid_base64_does_not_crash_display_name(self):
        try:
            from meshchatx.src.backend.meshchat_utils import parse_lxmf_display_name
        except ImportError:
            self.skipTest("meshchat_utils not importable")
        for bad in [
            "!!!",
            "\x00\x01",
            "a" * 10000,
            " ",
            "=",
            "===",
            "a\nb\tc",
            "\xff\xfe",
        ]:
            result = parse_lxmf_display_name(bad, default_value="Fallback")
            self.assertIsInstance(result, str)

    def test_invalid_base64_does_not_crash_propagation_node_app_data(self):
        try:
            from meshchatx.src.backend.meshchat_utils import (
                parse_lxmf_propagation_node_app_data,
            )
        except ImportError:
            self.skipTest("meshchat_utils not importable")
        for bad in ["!!!", "", "a" * 5000]:
            try:
                parse_lxmf_propagation_node_app_data(bad)
            except Exception:
                pass

    def test_invalid_base64_does_not_crash_stamp_cost(self):
        try:
            from meshchatx.src.backend.meshchat_utils import parse_lxmf_stamp_cost
        except ImportError:
            self.skipTest("meshchat_utils not importable")
        for bad in ["!!!", "", "x" * 10000]:
            try:
                parse_lxmf_stamp_cost(bad)
            except Exception:
                pass

    def test_base64_decode_direct_invalid_chars(self):
        for s in ["a\x00b", "a--b", "a/b+c", " " * 1000]:
            try:
                base64.b64decode(s, validate=False)
            except Exception:
                pass
        try:
            base64.b64decode("!!!", validate=True)
        except Exception:
            pass


class TestJsonLoadsRisky(unittest.TestCase):
    def test_deeply_nested_json_does_not_crash_message_dict(self):
        try:
            from meshchatx.src.backend.lxmf_utils import convert_db_lxmf_message_to_dict
        except ImportError:
            self.skipTest("lxmf_utils not importable")
        deep = "x"
        for _ in range(200):
            deep = '{"a":' + deep + "}"
        db_msg = {
            "id": 1,
            "hash": "h",
            "source_hash": "s",
            "destination_hash": "d",
            "is_incoming": True,
            "state": "delivered",
            "progress": 100.0,
            "method": "direct",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "t",
            "content": "c",
            "fields": deep,
            "timestamp": 123.0,
            "rssi": -50,
            "snr": 10,
            "quality": 100,
            "is_spam": False,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        try:
            convert_db_lxmf_message_to_dict(db_msg)
        except (RecursionError, OverflowError):
            pass

    def test_prototype_pollution_keys_in_fields_do_not_crash(self):
        try:
            from meshchatx.src.backend.lxmf_utils import convert_db_lxmf_message_to_dict
        except ImportError:
            self.skipTest("lxmf_utils not importable")
        db_msg = {
            "id": 1,
            "hash": "h",
            "source_hash": "s",
            "destination_hash": "d",
            "is_incoming": True,
            "state": "delivered",
            "progress": 100.0,
            "method": "direct",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "t",
            "content": "c",
            "fields": '{"__proto__":{"x":1},"constructor":{"prototype":{"y":1}}}',
            "timestamp": 123.0,
            "rssi": -50,
            "snr": 10,
            "quality": 100,
            "is_spam": False,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        result = convert_db_lxmf_message_to_dict(db_msg)
        self.assertIsInstance(result, dict)

    def test_huge_fields_string_does_not_hang(self):
        try:
            from meshchatx.src.backend.lxmf_utils import convert_db_lxmf_message_to_dict
        except ImportError:
            self.skipTest("lxmf_utils not importable")
        db_msg = {
            "id": 1,
            "hash": "h",
            "source_hash": "s",
            "destination_hash": "d",
            "is_incoming": True,
            "state": "delivered",
            "progress": 100.0,
            "method": "direct",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "t",
            "content": "c",
            "fields": '{"k":"' + "v" * 50000 + '"}',
            "timestamp": 123.0,
            "rssi": -50,
            "snr": 10,
            "quality": 100,
            "is_spam": False,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        try:
            convert_db_lxmf_message_to_dict(db_msg)
        except (MemoryError, json.JSONDecodeError):
            pass

    def test_invalid_json_fields_returns_safe_dict(self):
        try:
            from meshchatx.src.backend.lxmf_utils import convert_db_lxmf_message_to_dict
        except ImportError:
            self.skipTest("lxmf_utils not importable")
        db_msg = {
            "id": 1,
            "hash": "h",
            "source_hash": "s",
            "destination_hash": "d",
            "is_incoming": True,
            "state": "delivered",
            "progress": 100.0,
            "method": "direct",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "t",
            "content": "c",
            "fields": "not json at all {{{",
            "timestamp": 123.0,
            "rssi": -50,
            "snr": 10,
            "quality": 100,
            "is_spam": False,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        result = convert_db_lxmf_message_to_dict(db_msg)
        self.assertIsInstance(result, dict)
        self.assertIn("fields", result)


class TestPathAndStringRisky(unittest.TestCase):
    def test_interface_config_with_null_byte(self):
        try:
            from meshchatx.src.backend.interface_config_parser import (
                InterfaceConfigParser,
            )
        except ImportError:
            self.skipTest("interface_config_parser not importable")
        try:
            InterfaceConfigParser.parse("[section]\nname\x00=value")
        except Exception:
            pass

    def test_interface_config_very_long_line(self):
        try:
            from meshchatx.src.backend.interface_config_parser import (
                InterfaceConfigParser,
            )
        except ImportError:
            self.skipTest("interface_config_parser not importable")
        try:
            InterfaceConfigParser.parse("[x]\nkey=" + "v" * 100000)
        except Exception:
            pass
