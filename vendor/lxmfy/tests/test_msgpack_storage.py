"""Tests for the MsgPack storage backend."""

import json
from datetime import datetime

import pytest
import RNS.vendor.umsgpack as msgpack

from lxmfy import LXMFBot
from lxmfy.storage import MsgPackStorage, Storage


class TestMsgPackStorage:
    """Unit tests for the file-per-key MsgPack backend."""

    def test_set_get_roundtrip(self, tmp_path):
        """Values written to msgpack files read back identically."""
        store = Storage(MsgPackStorage(str(tmp_path / "data")))
        store.set("greeting", "hello")
        store.set("count", 42)
        store.set("flag", True)
        store.set("nothing", None)
        store.set("ratio", 1.5)

        assert store.get("greeting") == "hello"
        assert store.get("count") == 42
        assert store.get("flag") is True
        assert store.get("nothing") is None
        assert store.get("ratio") == 1.5

    def test_nested_structures(self, tmp_path):
        """Nested dicts and lists survive the roundtrip."""
        store = Storage(MsgPackStorage(str(tmp_path / "data")))
        payload = {
            "users": ["alice", "bob"],
            "limits": {"alice": 5, "bob": {"max": 10, "burst": True}},
            8: "integer key survives msgpack",
        }
        store.set("config", payload)

        assert store.get("config") == payload

    def test_bytes_and_datetime(self, tmp_path):
        """Facade serialization of bytes and datetime works on msgpack."""
        store = Storage(MsgPackStorage(str(tmp_path / "data")))
        payload = {
            "blob": b"\x00\xff\x10binary",
            "when": datetime(2026, 9, 25, 12, 30, 0),
            "nested": [b"\x01", datetime(2000, 1, 1)],
        }
        store.set("complex", payload)

        assert store.get("complex") == payload

    def test_on_disk_format_is_msgpack(self, tmp_path):
        """Files on disk are msgpack bytes, not JSON text."""
        store = Storage(MsgPackStorage(str(tmp_path / "data")))
        store.set("encoded", {"k": "v"})

        raw = (tmp_path / "data" / "encoded.msgpack").read_bytes()
        assert msgpack.unpackb(raw) == {"k": "v"}
        with pytest.raises((json.JSONDecodeError, UnicodeDecodeError)):
            json.loads(raw.decode("utf-8"))

    def test_persists_across_instances(self, tmp_path):
        """A fresh backend instance reads data written by another."""
        first = Storage(MsgPackStorage(str(tmp_path / "data")))
        first.set("survives", {"restart": [1, 2, 3]})

        second = Storage(MsgPackStorage(str(tmp_path / "data")))
        assert second.get("survives") == {"restart": [1, 2, 3]}

    def test_delete_exists_scan(self, tmp_path):
        """delete, exists, and prefix scan behave like the other backends."""
        backend = MsgPackStorage(str(tmp_path / "data"))
        store = Storage(backend)
        store.set("user:a", "A")
        store.set("user:b", "B")
        store.set("other", "C")

        assert store.exists("user:a")
        assert sorted(store.scan("user:")) == ["user:a", "user:b"]

        store.delete("user:a")
        assert not store.exists("user:a")
        assert store.get("user:a") is None
        assert store.scan("user:") == ["user:b"]

    def test_corrupt_file_returns_default(self, tmp_path):
        """A corrupt file falls back to the default instead of raising."""
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "broken.msgpack").write_bytes(b"\xc1\xff\xff")
        store = Storage(MsgPackStorage(str(tmp_path / "data")))

        assert store.get("broken", "fallback") == "fallback"


class TestMsgPackStorageBotWiring:
    """LXMFBot selects MsgPackStorage for storage_type="msgpack"."""

    def test_bot_uses_msgpack_backend(self, test_config_dir):
        bot = LXMFBot(
            name="MsgBot",
            storage_type="msgpack",
            storage_path=str(test_config_dir / "msgpack_data"),
            test_mode=True,
        )
        try:
            assert isinstance(bot.storage.backend, MsgPackStorage)
            bot.storage.set("wired", True)
            assert bot.storage.get("wired") is True
        finally:
            bot.cleanup()

    def test_unknown_storage_type_still_rejected(self, test_config_dir):
        with pytest.raises(ValueError, match="storage_type"):
            LXMFBot(
                name="BadBot",
                storage_type="yaml",
                storage_path=str(test_config_dir / "bad_data"),
                test_mode=True,
            )
