# SPDX-License-Identifier: 0BSD

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.page_node import normalize_page_filename


@pytest.fixture
def node_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mock_rns():
    with patch("meshchatx.src.backend.page_node.RNS") as mock:
        mock_identity = MagicMock()
        mock_identity.hash = b"\x01" * 16
        mock_identity.get_public_key.return_value = b"\x02" * 64

        mock_destination = MagicMock()
        mock_destination.hash = b"\x03" * 16

        mock.Identity.return_value = mock_identity
        mock.Identity.from_file.return_value = mock_identity
        mock.Destination.return_value = mock_destination
        mock.Destination.IN = 1
        mock.Destination.SINGLE = 0
        mock.Destination.ALLOW_ALL = 0xFF
        mock.Transport = MagicMock()
        mock.vendor = MagicMock()
        mock.vendor.platformutils = MagicMock()
        mock.vendor.platformutils.is_windows.return_value = False

        yield mock, mock_identity, mock_destination


def _make_node(node_dir, mock_rns):
    from meshchatx.src.backend.page_node import PageNode

    _, mock_identity, _ = mock_rns
    return PageNode(
        node_id="test-node-1",
        name="Test Node",
        base_dir=node_dir,
        identity=mock_identity,
    )


class TestPageNodeSetup:
    def test_setup_creates_directories(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert os.path.isdir(node.pages_dir)
        assert os.path.isdir(node.files_dir)
        assert node.running is True

    def test_setup_returns_destination_hash_hex(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        result = node.setup()
        assert isinstance(result, str)
        assert len(result) == 32

    def test_setup_creates_identity_when_none(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        rns_mock, _, _ = mock_rns
        node = PageNode(
            node_id="test-node-2",
            name="No Identity Node",
            base_dir=node_dir,
        )
        node.setup()
        rns_mock.Identity.assert_called()

    def test_setup_loads_identity_from_file(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        rns_mock, mock_identity, _ = mock_rns
        identity_path = os.path.join(node_dir, "identity")
        with open(identity_path, "w") as f:
            f.write("fake")

        node = PageNode(
            node_id="test-node-3",
            name="File Identity Node",
            base_dir=node_dir,
        )
        node.setup()
        rns_mock.Identity.from_file.assert_called_with(identity_path)

    def test_setup_registers_link_callback(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        _, _, mock_dest = mock_rns
        mock_dest.set_link_established_callback.assert_called_once()

    def test_setup_calls_ensure_local_path(self, node_dir, mock_rns):
        rns_mock, _, _ = mock_rns
        node = _make_node(node_dir, mock_rns)
        node.setup()
        rns_mock.Identity.remember.assert_called()


class TestPageNodeTeardown:
    def test_teardown_sets_running_false(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.teardown()
        assert node.running is False
        assert node.destination is None

    def test_teardown_deregisters_handlers(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_page("test.mu", "content")
        node.add_file("test.txt", b"data")
        _, _, mock_dest = mock_rns
        node.teardown()
        assert mock_dest.deregister_request_handler.call_count >= 2

    def test_teardown_clears_active_links(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        mock_link = MagicMock()
        node.active_links.append(mock_link)
        node.teardown()
        assert len(node.active_links) == 0
        mock_link.teardown.assert_called_once()


class TestPageNodeAnnounce:
    def test_announce_calls_destination_announce(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        _, _, mock_dest = mock_rns
        mock_dest.announce.reset_mock()
        node.announce()
        mock_dest.announce.assert_called_once()

    def test_announce_skips_when_not_running(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.announce()
        _, _, mock_dest = mock_rns
        mock_dest.announce.assert_not_called()

    def test_announce_passes_name_as_app_data(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        _, _, mock_dest = mock_rns
        node.announce()
        call_kwargs = mock_dest.announce.call_args
        assert call_kwargs[1]["app_data"] == b"Test Node"

    def test_setup_announces_immediately_when_enabled(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        _, _, mock_dest = mock_rns
        node.setup()
        mock_dest.announce.assert_called_once()

    def test_setup_skips_announce_when_disabled(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        _, mock_identity, _ = mock_rns
        node = PageNode(
            node_id="test-node-disabled",
            name="Disabled Node",
            base_dir=node_dir,
            identity=mock_identity,
            announce_enabled=False,
        )
        _, _, mock_dest = mock_rns
        node.setup()
        mock_dest.announce.assert_not_called()

    def test_announce_records_last_announced_at(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        assert node.last_announced_at is None
        node.setup()
        assert node.last_announced_at is not None

    def test_announce_does_not_update_last_announced_at_when_not_running(
        self, node_dir, mock_rns
    ):
        node = _make_node(node_dir, mock_rns)
        node.announce()
        assert node.last_announced_at is None

    def test_announce_invokes_on_announce_callback(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        _, mock_identity, _ = mock_rns
        calls = []
        node = PageNode(
            node_id="test-node-cb",
            name="Callback Node",
            base_dir=node_dir,
            identity=mock_identity,
            on_announce=calls.append,
        )
        node.setup()
        assert calls == [node]

    def test_announce_callback_exceptions_are_suppressed(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        _, mock_identity, _ = mock_rns

        def boom(_node):
            raise RuntimeError("boom")

        node = PageNode(
            node_id="test-node-cb-boom",
            name="Boom Node",
            base_dir=node_dir,
            identity=mock_identity,
            on_announce=boom,
        )
        node.setup()  # must not raise
        assert node.running is True

    def test_teardown_cancels_announce_timer(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node._announce_timer is not None
        node.teardown()
        assert node._announce_timer is None


class TestPageNodeAnnounceInterval:
    def test_normalize_defaults_when_none(self):
        from meshchatx.src.backend.page_node import (
            DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
            normalize_announce_interval_seconds,
        )

        assert (
            normalize_announce_interval_seconds(None)
            == DEFAULT_ANNOUNCE_INTERVAL_SECONDS
        )

    def test_normalize_zero_or_negative_disables(self):
        from meshchatx.src.backend.page_node import normalize_announce_interval_seconds

        assert normalize_announce_interval_seconds(0) == 0
        assert normalize_announce_interval_seconds(-30) == 0

    def test_normalize_clamps_to_min_and_max(self):
        from meshchatx.src.backend.page_node import (
            MAX_ANNOUNCE_INTERVAL_SECONDS,
            MIN_ANNOUNCE_INTERVAL_SECONDS,
            normalize_announce_interval_seconds,
        )

        assert normalize_announce_interval_seconds(1) == MIN_ANNOUNCE_INTERVAL_SECONDS
        assert (
            normalize_announce_interval_seconds(999999) == MAX_ANNOUNCE_INTERVAL_SECONDS
        )

    def test_normalize_invalid_type_returns_default(self):
        from meshchatx.src.backend.page_node import (
            DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
            normalize_announce_interval_seconds,
        )

        assert (
            normalize_announce_interval_seconds("not-a-number")
            == DEFAULT_ANNOUNCE_INTERVAL_SECONDS
        )

    def test_node_defaults_to_default_interval(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        from meshchatx.src.backend.page_node import DEFAULT_ANNOUNCE_INTERVAL_SECONDS

        assert node.announce_interval_seconds == DEFAULT_ANNOUNCE_INTERVAL_SECONDS
        assert node.announce_enabled is True

    def test_node_clamps_custom_interval_on_construction(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        _, mock_identity, _ = mock_rns
        node = PageNode(
            node_id="test-node-clamp",
            name="Clamp Node",
            base_dir=node_dir,
            identity=mock_identity,
            announce_interval_seconds=5,
        )
        assert node.announce_interval_seconds == 60

    def test_setup_starts_announce_timer_when_enabled(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node._announce_timer is not None

    def test_setup_skips_timer_when_disabled(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        _, mock_identity, _ = mock_rns
        node = PageNode(
            node_id="test-node-no-timer",
            name="No Timer Node",
            base_dir=node_dir,
            identity=mock_identity,
            announce_enabled=False,
        )
        node.setup()
        assert node._announce_timer is None

    def test_setup_skips_timer_when_interval_zero(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        _, mock_identity, _ = mock_rns
        node = PageNode(
            node_id="test-node-zero-interval",
            name="Zero Interval Node",
            base_dir=node_dir,
            identity=mock_identity,
            announce_interval_seconds=0,
        )
        node.setup()
        assert node._announce_timer is None

    def test_announce_timer_fire_reannounces_and_reschedules(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        _, _, mock_dest = mock_rns
        mock_dest.announce.reset_mock()
        node._announce_timer_fire()
        mock_dest.announce.assert_called_once()
        assert node._announce_timer is not None

    def test_announce_timer_fire_noop_when_disabled_meanwhile(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        _, _, mock_dest = mock_rns
        node.announce_enabled = False
        mock_dest.announce.reset_mock()
        node._announce_timer_fire()
        mock_dest.announce.assert_not_called()
        assert node._announce_timer is None

    def test_set_announce_settings_updates_enabled_and_interval(
        self, node_dir, mock_rns
    ):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.set_announce_settings(announce_enabled=True, announce_interval_seconds=120)
        assert node.announce_enabled is True
        assert node.announce_interval_seconds == 120
        assert node._announce_timer is not None

    def test_set_announce_settings_disable_cancels_timer(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.set_announce_settings(announce_enabled=False)
        assert node.announce_enabled is False
        assert node._announce_timer is None

    def test_set_announce_settings_interval_zero_cancels_timer(
        self, node_dir, mock_rns
    ):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.set_announce_settings(announce_interval_seconds=0)
        assert node.announce_interval_seconds == 0
        assert node._announce_timer is None

    def test_set_announce_settings_partial_update_keeps_other_field(
        self, node_dir, mock_rns
    ):
        node = _make_node(node_dir, mock_rns)
        node.set_announce_settings(announce_interval_seconds=300)
        assert node.announce_enabled is True
        assert node.announce_interval_seconds == 300


class TestPageNodePages:
    def test_add_page_writes_file(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        name = node.add_page("hello", "Hello World")
        assert name == "hello.mu"
        path = os.path.join(node.pages_dir, "hello.mu")
        assert os.path.isfile(path)
        with open(path, "rb") as f:
            assert f.read() == b"Hello World"

    def test_add_page_appends_mu_extension(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node.add_page("test", "x") == "test.mu"

    def test_add_page_preserves_mu_extension(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node.add_page("test.mu", "x") == "test.mu"

    def test_add_page_accepts_md_txt_html(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node.add_page("notes.md", "# x") == "notes.md"
        assert node.add_page("readme.txt", "plain") == "readme.txt"
        assert node.add_page("static.html", "<p>a</p>") == "static.html"
        assert os.path.isfile(os.path.join(node.pages_dir, "notes.md"))
        assert "/page/notes.md" in node._registered_page_paths

    def test_add_page_rejects_unknown_extension(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        with pytest.raises(ValueError):
            node.add_page("bad.exe", "x")

    def test_remove_page_invalid_extension_returns_false(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node.remove_page("bad.exe") is False

    def test_get_page_content_invalid_extension_returns_none(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node.get_page_content("bad.exe") is None

    def test_setup_skips_unlisted_page_files(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        os.makedirs(node.pages_dir, exist_ok=True)
        with open(os.path.join(node.pages_dir, "junk.exe"), "wb") as f:
            f.write(b"x")
        node.setup()
        assert "/page/junk.exe" not in node._registered_page_paths

    def test_add_page_registers_handler(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        _, _, mock_dest = mock_rns
        node.add_page("index.mu", "content")
        mock_dest.register_request_handler.assert_called()
        assert "/page/index.mu" in node._registered_page_paths

    def test_remove_page_deletes_file(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_page("deleteme.mu", "gone")
        assert node.remove_page("deleteme.mu") is True
        assert not os.path.isfile(os.path.join(node.pages_dir, "deleteme.mu"))

    def test_remove_nonexistent_page_returns_false(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node.remove_page("nope.mu") is False

    def test_list_pages(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_page("b.mu", "b")
        node.add_page("a.mu", "a")
        pages = node.list_pages()
        assert pages == [
            {"name": "a.mu", "executable": False},
            {"name": "b.mu", "executable": False},
        ]

    def test_get_page_content(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_page("index.mu", "Hello Mesh")
        content = node.get_page_content("index.mu")
        assert content == "Hello Mesh"

    def test_get_page_content_nonexistent(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node.get_page_content("nope.mu") is None


class TestPageNodeFiles:
    def test_add_file_writes_binary(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        name = node.add_file("doc.pdf", b"\x00\x01\x02")
        assert name == "doc.pdf"
        path = os.path.join(node.files_dir, "doc.pdf")
        with open(path, "rb") as f:
            assert f.read() == b"\x00\x01\x02"

    def test_add_file_writes_bytearray(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        name = node.add_file("upload.bin", bytearray(b"\xde\xad\xbe\xef"))
        assert name == "upload.bin"
        path = os.path.join(node.files_dir, "upload.bin")
        with open(path, "rb") as f:
            assert f.read() == b"\xde\xad\xbe\xef"

    def test_add_file_registers_handler(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_file("info.txt", b"data")
        assert "/file/info.txt" in node._registered_file_paths

    def test_remove_file(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_file("rm.bin", b"\xff")
        assert node.remove_file("rm.bin") is True
        assert not os.path.isfile(os.path.join(node.files_dir, "rm.bin"))

    def test_remove_nonexistent_file(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node.remove_file("nope.bin") is False

    def test_list_files(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_file("b.txt", b"bb")
        node.add_file("a.txt", b"a")
        files = node.list_files()
        assert len(files) == 2
        assert files[0]["name"] == "a.txt"
        assert files[1]["name"] == "b.txt"
        assert files[0]["size"] == 1
        assert files[1]["size"] == 2


class TestPageNodeResponders:
    def test_page_responder_returns_content(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_page("index.mu", "page content")
        responder = node._make_page_responder("index.mu")
        result = responder("/page/index.mu", None, "req1", "link1", None, 0)
        assert result == b"page content"

    def test_page_responder_records_remote_identity(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_page("index.mu", "x")
        rid = MagicMock()
        rid.hash = bytes.fromhex("ef" * 16)
        responder = node._make_page_responder("index.mu")
        responder("/page/index.mu", None, "req1", "link1", rid, 0)
        assert node.get_status()["unique_connections"] == 1

    def test_page_responder_missing_returns_none(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        responder = node._make_page_responder("missing.mu")
        result = responder("/page/missing.mu", None, "req1", "link1", None, 0)
        assert result is None

    def test_file_responder_returns_list(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_file("data.bin", b"\x01\x02\x03")
        responder = node._make_file_responder("data.bin")
        result = responder("/file/data.bin", None, "req1", "link1", None, 0)
        assert isinstance(result, list)
        assert len(result) == 2
        file_handle = result[0]
        metadata = result[1]
        assert file_handle.read() == b"\x01\x02\x03"
        assert metadata["name"] == b"data.bin"
        file_handle.close()

    def test_file_responder_increments_stats(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_file("f.txt", b"hello")
        responder = node._make_file_responder("f.txt")
        assert node._stats["files_served"] == 0
        responder("/file/f.txt", None, "r", "l", None, 0)
        assert node._stats["files_served"] == 1
        result = responder("/file/f.txt", None, "r", "l", None, 0)
        result[0].close()
        assert node._stats["files_served"] == 2


class TestPageNodeConfig:
    def test_save_and_load_config(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.save_config()
        from meshchatx.src.backend.page_node import PageNode

        config = PageNode.load_config(node_dir)
        assert config is not None
        assert config["node_id"] == "test-node-1"
        assert config["name"] == "Test Node"

    def test_load_config_missing(self, node_dir):
        from meshchatx.src.backend.page_node import PageNode

        assert PageNode.load_config(node_dir) is None

    def test_save_config_persists_announce_settings(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        node = _make_node(node_dir, mock_rns)
        node.set_announce_settings(
            announce_enabled=False, announce_interval_seconds=120
        )
        node.save_config()

        config = PageNode.load_config(node_dir)
        assert config["announce_enabled"] is False
        assert config["announce_interval_seconds"] == 120

    def test_save_config_defaults_announce_settings(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import (
            DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
            PageNode,
        )

        node = _make_node(node_dir, mock_rns)
        node.save_config()

        config = PageNode.load_config(node_dir)
        assert config["announce_enabled"] is True
        assert config["announce_interval_seconds"] == DEFAULT_ANNOUNCE_INTERVAL_SECONDS

    def test_save_config_persists_executable_pages_enabled(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        node = _make_node(node_dir, mock_rns)
        node.set_executable_pages_enabled(True)
        node.save_config()

        config = PageNode.load_config(node_dir)
        assert config["executable_pages_enabled"] is True


class TestPageNodeStatus:
    def test_get_status(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_page("index.mu", "hi")
        status = node.get_status()
        assert status["node_id"] == "test-node-1"
        assert status["name"] == "Test Node"
        assert status["running"] is True
        assert status["destination_hash"] is not None
        assert "index.mu" in [p["name"] for p in status["pages"]]
        assert isinstance(status["stats"], dict)
        assert status["unique_connections"] == 0
        assert status["uptime_seconds"] >= 0

    def test_get_status_includes_announce_fields(self, node_dir, mock_rns):
        from meshchatx.src.backend.page_node import DEFAULT_ANNOUNCE_INTERVAL_SECONDS

        node = _make_node(node_dir, mock_rns)
        status = node.get_status()
        assert status["announce_enabled"] is True
        assert status["announce_interval_seconds"] == DEFAULT_ANNOUNCE_INTERVAL_SECONDS
        assert status["last_announced_at"] is None

        node.setup()
        status = node.get_status()
        assert status["last_announced_at"] is not None

    def test_get_destination_hash_when_not_running(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        assert node.get_destination_hash() is None


class TestPageNodeLinkCallbacks:
    def test_link_established_callback(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        mock_link = MagicMock()
        mock_link.get_remote_identity.return_value = None
        node._link_established(mock_link)
        assert mock_link in node.active_links
        assert node._stats["links_established"] == 1
        mock_link.set_link_closed_callback.assert_called_once()

    def test_link_established_records_remote_identity(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        mock_link = MagicMock()
        rid = MagicMock()
        rid.hash = bytes.fromhex("cd" * 16)
        mock_link.get_remote_identity.return_value = rid
        node._link_established(mock_link)
        assert node.get_status()["unique_connections"] == 1

    def test_link_closed_callback(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        mock_link = MagicMock()
        node.active_links.append(mock_link)
        node._link_closed(mock_link)
        assert mock_link not in node.active_links

    def test_link_closed_callback_ignores_unknown(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node._link_closed(MagicMock())
        assert len(node.active_links) == 0


class TestNormalizePageFilename:
    def test_accepts_allowed_extensions(self):
        assert normalize_page_filename("a.mu") == "a.mu"
        assert normalize_page_filename("b.md") == "b.md"
        assert normalize_page_filename("c.txt") == "c.txt"
        assert normalize_page_filename("d.html") == "d.html"
        assert normalize_page_filename("x") == "x.mu"

    def test_rejects_bad_extension(self):
        with pytest.raises(ValueError):
            normalize_page_filename("x.exe")


class TestPageNodeEdgeCases:
    def test_add_page_before_running(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        assert not os.path.isdir(node.pages_dir)
        name = node.add_page("offline.mu", "data")
        assert name == "offline.mu"
        assert os.path.isfile(os.path.join(node.pages_dir, "offline.mu"))
        assert "/page/offline.mu" not in node._registered_page_paths

    def test_add_file_before_running(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        assert not os.path.isdir(node.files_dir)
        name = node.add_file("offline.txt", b"data")
        assert name == "offline.txt"
        assert os.path.isfile(os.path.join(node.files_dir, "offline.txt"))
        assert "/file/offline.txt" not in node._registered_file_paths

    def test_setup_registers_existing_pages(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        os.makedirs(node.pages_dir, exist_ok=True)
        with open(os.path.join(node.pages_dir, "pre.mu"), "w") as f:
            f.write("existing")
        node.setup()
        assert "/page/pre.mu" in node._registered_page_paths

    def test_setup_registers_existing_files(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        os.makedirs(node.files_dir, exist_ok=True)
        with open(os.path.join(node.files_dir, "pre.txt"), "wb") as f:
            f.write(b"existing")
        node.setup()
        assert "/file/pre.txt" in node._registered_file_paths

    def test_list_files_registers_manually_added_files(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        with open(os.path.join(node.files_dir, "dropped.bin"), "wb") as f:
            f.write(b"dropped")
        assert "/file/dropped.bin" not in node._registered_file_paths
        node.list_files()
        assert "/file/dropped.bin" in node._registered_file_paths

    def test_path_traversal_blocked(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        name = node.add_page("../../etc/passwd", "malicious")
        assert name == "passwd.mu"
        assert not os.path.exists(os.path.join(node_dir, "..", "etc"))

    @pytest.mark.skipif(os.name == "nt", reason="symlink jail oracle is POSIX")
    def test_file_symlink_out_is_not_readable_or_overwritten(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        bait_dir = os.path.join(os.path.dirname(node_dir), "outside-jail")
        os.makedirs(bait_dir, exist_ok=True)
        bait = os.path.join(bait_dir, "secret.bin")
        with open(bait, "wb") as f:
            f.write(b"keep-me")
        link_name = os.path.join(node.files_dir, "escape.bin")
        os.symlink(bait, link_name)

        assert node.read_hosted_file("escape.bin") is None
        assert node.list_files() == []
        assert node.remove_file("escape.bin") is False
        with pytest.raises(ValueError, match="invalid file name"):
            node.add_file("escape.bin", b"overwrite")
        with open(bait, "rb") as f:
            assert f.read() == b"keep-me"
        responder = node._make_file_responder("escape.bin")
        assert responder("/file/escape.bin", None, None, None, None, None) is None

    @pytest.mark.skipif(os.name == "nt", reason="symlink jail oracle is POSIX")
    def test_page_symlink_out_is_not_readable_or_overwritten(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        bait_dir = os.path.join(os.path.dirname(node_dir), "outside-jail")
        os.makedirs(bait_dir, exist_ok=True)
        bait = os.path.join(bait_dir, "secret.mu")
        with open(bait, "w", encoding="utf-8") as f:
            f.write("keep-me")
        bait_mode = os.stat(bait).st_mode
        os.symlink(bait, os.path.join(node.pages_dir, "escape.mu"))

        assert node.get_page_content("escape.mu") is None
        assert node.serve_page_content("escape.mu") is None
        assert node.list_pages() == []
        assert node.remove_page("escape.mu") is False
        with pytest.raises(ValueError, match="invalid page name"):
            node.add_page("escape.mu", "overwrite")
        with pytest.raises(ValueError, match="page not found"):
            node.set_page_executable("escape.mu", True)
        with open(bait, encoding="utf-8") as f:
            assert f.read() == "keep-me"
        assert os.stat(bait).st_mode == bait_mode
        responder = node._make_page_responder("escape.mu")
        assert responder("/page/escape.mu", None, None, None, None, None) is None


class TestPageNodeExecutablePages:
    def test_executable_disabled_serves_static_even_when_chmod_x(
        self, node_dir, mock_rns
    ):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        script = "#!/usr/bin/env python3\nprint('dynamic')\n"
        node.add_page("dyn.mu", script, executable=True)
        assert node.serve_page_content("dyn.mu") == script.encode("utf-8")

    def test_executable_enabled_runs_script(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.set_executable_pages_enabled(True)
        script = "#!/usr/bin/env python3\nprint('dynamic-output')\n"
        node.add_page("dyn.mu", script, executable=True)
        result = node.serve_page_content("dyn.mu")
        assert result == b"dynamic-output\n"

    def test_executable_passes_env_vars(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.set_executable_pages_enabled(True)
        script = (
            "#!/usr/bin/env python3\n"
            "import os\n"
            "print(os.environ.get('var_name', ''), end='')\n"
            "print('|', os.environ.get('field_form', ''), end='')\n"
        )
        node.add_page("env.mu", script, executable=True)
        result = node.serve_page_content(
            "env.mu",
            data={"var_name": "alice", "field_form": "submit", "ignored": "x"},
            link_id=b"\x01" * 16,
            remote_identity=MagicMock(hash=b"\x02" * 16),
        )
        assert b"alice" in result
        assert b"submit" in result

    def test_executable_timeout_returns_error_page(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.set_executable_pages_enabled(True)
        script = "#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n"
        node.add_page("slow.mu", script, executable=True)
        result = node.serve_page_content("slow.mu")
        assert b">Page Generation Failed" in result
        assert b"timed out" in result.lower()

    def test_get_page_content_never_executes(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.set_executable_pages_enabled(True)
        script = "#!/usr/bin/env python3\nprint('dynamic')\n"
        node.add_page("dyn.mu", script, executable=True)
        assert node.get_page_content("dyn.mu") == script

    def test_windows_platform_skips_execution(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.set_executable_pages_enabled(True)
        script = "#!/usr/bin/env python3\nprint('dynamic')\n"
        node.add_page("dyn.mu", script, executable=True)
        with patch(
            "meshchatx.src.backend.page_node._is_windows_platform",
            return_value=True,
        ):
            result = node.serve_page_content("dyn.mu")
        assert result == script.encode("utf-8")

    def test_set_page_executable_round_trip(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_page("toggle.mu", "static")
        assert node.is_page_executable("toggle.mu") is False
        node.set_page_executable("toggle.mu", True)
        assert node.is_page_executable("toggle.mu") is True
        node.set_page_executable("toggle.mu", False)
        assert node.is_page_executable("toggle.mu") is False

    def test_page_responder_uses_serve_page_content(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.set_executable_pages_enabled(True)
        script = "#!/usr/bin/env python3\nprint('from-responder')\n"
        node.add_page("dyn.mu", script, executable=True)
        responder = node._make_page_responder("dyn.mu")
        result = responder(
            "/page/dyn.mu", {"var_x": "1"}, "req1", b"\xab" * 16, None, 0
        )
        assert result == b"from-responder\n"
