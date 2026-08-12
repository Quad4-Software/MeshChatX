# SPDX-License-Identifier: 0BSD

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def storage_dir():
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


def _make_manager(storage_dir):
    from meshchatx.src.backend.page_node_manager import PageNodeManager

    return PageNodeManager(storage_dir)


class TestPageNodeManagerCreate:
    def test_create_node(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("My Server")
        assert node.name == "My Server"
        assert node.node_id in mgr.nodes
        assert os.path.isdir(node.base_dir)

    def test_add_page_without_starting(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Publish Target")
        saved_name = node.add_page("index", "hello mesh")
        assert saved_name == "index.mu"
        assert node.list_pages() == [{"name": "index.mu", "executable": False}]
        assert node.running is False

    def test_create_node_with_custom_id(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Custom", node_id="custom-123")
        assert node.node_id == "custom-123"

    def test_create_node_saves_config(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Saved")
        config_path = os.path.join(node.base_dir, "config.json")
        assert os.path.isfile(config_path)


class TestPageNodeManagerDelete:
    def test_delete_node(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("ToDelete")
        node_id = node.node_id
        base_dir = node.base_dir
        assert mgr.delete_node(node_id) is True
        assert node_id not in mgr.nodes
        assert not os.path.exists(base_dir)

    def test_delete_running_node_stops_first(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Running")
        mgr.start_node(node.node_id)
        assert node.running is True
        mgr.delete_node(node.node_id)
        assert node.running is False

    def test_delete_nonexistent_returns_false(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        assert mgr.delete_node("nonexistent") is False


class TestPageNodeManagerStartStop:
    def test_start_node(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("StartMe")
        dest_hash = mgr.start_node(node.node_id)
        assert node.running is True
        assert dest_hash is not None

    def test_start_already_running(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("AlreadyRunning")
        mgr.start_node(node.node_id)
        result = mgr.start_node(node.node_id)
        assert result is not None

    def test_start_nonexistent_raises(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        with pytest.raises(KeyError):
            mgr.start_node("nope")

    def test_stop_node(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("StopMe")
        mgr.start_node(node.node_id)
        mgr.stop_node(node.node_id)
        assert node.running is False

    def test_stop_nonexistent_raises(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        with pytest.raises(KeyError):
            mgr.stop_node("nope")

    def test_start_all(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        mgr.create_node("A", node_id="a")
        mgr.create_node("B", node_id="b")
        mgr.start_all()
        for node in mgr.nodes.values():
            assert node.running is True

    def test_stop_all(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        mgr.create_node("A", node_id="a")
        mgr.create_node("B", node_id="b")
        mgr.start_all()
        mgr.stop_all()
        for node in mgr.nodes.values():
            assert node.running is False


class TestPageNodeManagerAnnounce:
    def test_announce_node(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Announcer")
        mgr.start_node(node.node_id)
        _, _, mock_dest = mock_rns
        mgr.announce_node(node.node_id)
        mock_dest.announce.assert_called()

    def test_announce_nonexistent_raises(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        with pytest.raises(KeyError):
            mgr.announce_node("nope")

    def test_announce_all(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        mgr.create_node("A", node_id="a")
        mgr.create_node("B", node_id="b")
        mgr.start_all()
        _, _, mock_dest = mock_rns
        mgr.announce_all()
        assert mock_dest.announce.call_count >= 2


class TestPageNodeManagerAnnounceSettings:
    def test_create_node_with_custom_announce_settings(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node(
            "Custom", announce_enabled=False, announce_interval_seconds=120
        )
        assert node.announce_enabled is False
        assert node.announce_interval_seconds == 120

    def test_create_node_defaults_announce_enabled(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Defaults")
        assert node.announce_enabled is True

    def test_create_node_with_executable_pages_enabled(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Dynamic", executable_pages_enabled=True)
        assert node.executable_pages_enabled is True

    def test_set_executable_pages_enabled_persists(self, storage_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Dynamic")
        mgr.set_executable_pages_enabled(node.node_id, True)
        config = PageNode.load_config(node.base_dir)
        assert config["executable_pages_enabled"] is True

    def test_set_announce_settings_updates_node(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Settable")
        mgr.set_announce_settings(
            node.node_id, announce_enabled=False, announce_interval_seconds=300
        )
        assert node.announce_enabled is False
        assert node.announce_interval_seconds == 300

    def test_set_announce_settings_persists_to_disk(self, storage_dir, mock_rns):
        from meshchatx.src.backend.page_node import PageNode

        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Persisted", node_id="persist-announce")
        mgr.set_announce_settings(node.node_id, announce_enabled=False)

        config = PageNode.load_config(node.base_dir)
        assert config["announce_enabled"] is False

    def test_set_announce_settings_nonexistent_raises(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        with pytest.raises(KeyError):
            mgr.set_announce_settings("nope", announce_enabled=False)

    def test_load_nodes_restores_announce_settings(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Reloaded", node_id="reload-1")
        mgr.set_announce_settings(
            node.node_id, announce_enabled=False, announce_interval_seconds=200
        )

        mgr2 = _make_manager(storage_dir)
        mgr2.load_nodes()
        reloaded = mgr2.nodes["reload-1"]
        assert reloaded.announce_enabled is False
        assert reloaded.announce_interval_seconds == 200

    def test_on_announce_callback_wired_through_manager(self, storage_dir, mock_rns):
        calls = []
        mgr = _make_manager(storage_dir)
        mgr.on_announce = calls.append
        node = mgr.create_node("Callback")
        mgr.start_node(node.node_id)
        assert calls == [node]

    def test_on_announce_callback_wired_for_loaded_nodes(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("ToReload", node_id="reload-cb")
        node.save_config()

        calls = []
        mgr2 = _make_manager(storage_dir)
        mgr2.on_announce = calls.append
        mgr2.load_nodes()
        mgr2.start_node("reload-cb")
        assert calls == [mgr2.nodes["reload-cb"]]


class TestPageNodeManagerRename:
    def test_rename_node(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("OldName")
        mgr.rename_node(node.node_id, "NewName")
        assert node.name == "NewName"

    def test_rename_nonexistent_raises(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        with pytest.raises(KeyError):
            mgr.rename_node("nope", "Ignored")


class TestPageNodeManagerGetAndList:
    def test_get_node(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("FindMe")
        assert mgr.get_node(node.node_id) is node

    def test_get_node_missing(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        assert mgr.get_node("nope") is None

    def test_list_nodes(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        mgr.create_node("A", node_id="a")
        mgr.create_node("B", node_id="b")
        result = mgr.list_nodes()
        assert len(result) == 2
        ids = {n["node_id"] for n in result}
        assert ids == {"a", "b"}


class TestPageNodeManagerLoad:
    def test_load_nodes_from_disk(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Persisted", node_id="persist-1")
        node.save_config()

        mgr2 = _make_manager(storage_dir)
        mgr2.load_nodes()
        assert "persist-1" in mgr2.nodes
        assert mgr2.nodes["persist-1"].name == "Persisted"

    def test_load_nodes_skips_bad_dirs(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        bad_dir = os.path.join(mgr.storage_dir, "bad-node")
        os.makedirs(bad_dir, exist_ok=True)
        mgr.load_nodes()
        assert "bad-node" not in mgr.nodes

    def test_load_nodes_skips_already_loaded(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        node = mgr.create_node("Already", node_id="already-1")
        node.save_config()
        mgr.load_nodes()
        assert len(mgr.nodes) == 1


class TestPageNodeManagerTeardown:
    def test_teardown_stops_and_clears(self, storage_dir, mock_rns):
        mgr = _make_manager(storage_dir)
        mgr.create_node("A", node_id="a")
        mgr.create_node("B", node_id="b")
        mgr.start_all()
        mgr.teardown()
        assert len(mgr.nodes) == 0
