# SPDX-License-Identifier: 0BSD

"""Oracle tests for bugs confirmed in the coordinated bug hunt.

Each test encodes the invariant, not the trigger input, so a patch that
only silences the reported case still fails here.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.http.errors import http_error_from_exception


@pytest.fixture(autouse=True)
def reset_database_provider():
    DatabaseProvider._instance = None
    yield
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
    DatabaseProvider._instance = None


@pytest.fixture
def temp_dir():
    import shutil

    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


class TestProviderTransactionSafety:
    def test_retryable_error_inside_transaction_is_not_dropped(self, temp_dir):
        """A retryable error inside BEGIN must not drop the connection.

        Dropping rolls back earlier statements and the retried statement
        would commit alone on a fresh autocommit connection.
        """
        db = Database(os.path.join(temp_dir, "t.db"))
        db.initialize()
        provider = db.provider
        provider.execute("CREATE TABLE IF NOT EXISTS t_probe (v INTEGER)")
        provider.begin()
        provider.execute("INSERT INTO t_probe (v) VALUES (1)")
        conn = provider.connection

        def boom():
            raise sqlite3.OperationalError("database is locked")

        with pytest.raises(sqlite3.OperationalError):
            provider._call_with_reconnect(boom)
        # Same connection, transaction still open for caller rollback.
        assert provider.connection is conn
        provider.rollback()
        row = provider.fetchone("SELECT COUNT(*) AS c FROM t_probe")
        assert row["c"] == 0

    def test_close_all_rolls_back_open_transaction(self, temp_dir):
        """Closing a connection must not commit a half-finished transaction."""
        db = Database(os.path.join(temp_dir, "t.db"))
        db.initialize()
        provider = db.provider
        provider.execute("CREATE TABLE IF NOT EXISTS t_probe (v INTEGER)")
        provider.begin()
        provider.execute("INSERT INTO t_probe (v) VALUES (1)")
        provider.close_all()
        provider2 = DatabaseProvider(os.path.join(temp_dir, "t.db"))
        row = provider2.fetchone("SELECT COUNT(*) AS c FROM t_probe")
        assert row["c"] == 0

    def test_autocommit_retry_still_recovers(self, temp_dir):
        """Outside a transaction, retryable errors still drop and retry."""
        db = Database(os.path.join(temp_dir, "t.db"))
        db.initialize()
        provider = db.provider
        provider.execute("CREATE TABLE IF NOT EXISTS t_probe (v INTEGER)")
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise sqlite3.OperationalError("database is locked")
            return "ok"

        assert provider._call_with_reconnect(flaky) == "ok"
        assert len(calls) == 2


class TestErrorMapping:
    def test_retryable_sqlite_maps_to_503(self):
        exc = sqlite3.OperationalError("database is locked")
        resp = http_error_from_exception(exc, fallback_status=500)
        assert resp.status == 503

    def test_non_retryable_sqlite_uses_fallback(self):
        exc = sqlite3.IntegrityError("constraint failed")
        resp = http_error_from_exception(exc, fallback_status=500)
        assert resp.status == 500


class TestFolderAndPin:
    def _db(self, temp_dir):
        db = Database(os.path.join(temp_dir, "t.db"))
        db.initialize()
        return db

    def test_delete_folder_removes_assignments(self, temp_dir):
        """FK pragma is off, so delete_folder must clear child rows itself."""
        db = self._db(temp_dir)
        db.messages.provider.execute(
            "INSERT INTO lxmf_folders (name, created_at, updated_at)"
            " VALUES ('f', '2020', '2020')",
        )
        folder = db.messages.provider.fetchone(
            "SELECT id FROM lxmf_folders WHERE name = 'f'",
        )
        db.messages.move_conversation_to_folder("peer1", folder["id"])
        db.messages.delete_folder(folder["id"])
        assert db.messages.get_conversation_folder("peer1") is None

    def test_toggle_peer_pin_roundtrips(self, temp_dir):
        db = self._db(temp_dir)
        assert db.messages.toggle_peer_pin("peer1") is True
        assert db.messages.is_peer_pinned("peer1") is True
        assert db.messages.toggle_peer_pin("peer1") is False
        assert db.messages.is_peer_pinned("peer1") is False


class TestPluginRemoveJail:
    def _manager(self, tmp_path):
        from meshchatx.src.backend.plugin_manager import PluginManager

        return PluginManager(str(tmp_path))

    def test_remove_rejects_traversal(self, tmp_path):
        manager = self._manager(tmp_path)
        decoy = os.path.join(tmp_path, "decoy_dir")
        os.makedirs(decoy)
        with pytest.raises(KeyError):
            manager.remove("../decoy_dir")
        assert os.path.isdir(decoy)

    def test_remove_rejects_parent_selector(self, tmp_path):
        manager = self._manager(tmp_path)
        with pytest.raises(KeyError):
            manager.remove("..")
        assert os.path.isdir(manager.installed_dir)

    def test_remove_missing_plugin_is_404_keyerror(self, tmp_path):
        manager = self._manager(tmp_path)
        with pytest.raises(KeyError):
            manager.remove("com.example.absent")

    def test_remove_nested_path_inside_jail_rejected(self, tmp_path):
        manager = self._manager(tmp_path)
        nested = os.path.join(manager.installed_dir, "legit", "inner")
        os.makedirs(nested)
        with pytest.raises(KeyError):
            manager.remove(os.path.join("legit", "inner"))
        assert os.path.isdir(nested)

    def test_disabled_plugin_assets_not_served(self, tmp_path):
        from meshchatx.src.backend.plugin_manager import PluginSecurityError

        manager = self._manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        manager.disable(plugin_id)
        with pytest.raises(PluginSecurityError):
            manager.asset_path(plugin_id, "plugin.json")

    def test_minimal_wasm_exports_alloc(self):
        import wasmtime

        from meshchatx.src.backend.plugin_manager import MINIMAL_PLUGIN_WAT

        engine = wasmtime.Engine()
        module = wasmtime.Module(engine, wasmtime.wat2wasm(MINIMAL_PLUGIN_WAT))
        store = wasmtime.Store(engine)
        linker = wasmtime.Linker(engine)
        linker.define_func(
            "host",
            "log",
            wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i32()], []),
            lambda caller, ptr, length: None,
        )
        instance = linker.instantiate(store, module)
        exports = instance.exports(store)
        assert "alloc" in exports
        assert exports["alloc"](store, 64) == 1024


class TestAsyncUtilsPendingBuffer:
    def test_pending_coroutines_drain_once_loop_arrives(self):
        import asyncio
        import time

        from meshchatx.src.backend.async_utils import AsyncUtils

        AsyncUtils.main_loop = None
        AsyncUtils._pending_coroutines.clear()
        AsyncUtils._pending_futures.clear()
        seen = []

        async def mark():
            seen.append(True)

        try:
            for _ in range(3):
                AsyncUtils.run_async(mark())

            loop = asyncio.new_event_loop()
            ready = threading.Event()

            def runner():
                AsyncUtils.set_main_loop(loop)
                ready.set()
                loop.run_forever()

            thread = threading.Thread(target=runner, daemon=True)
            thread.start()
            assert ready.wait(2)
            deadline = time.time() + 3
            while len(seen) < 3 and time.time() < deadline:
                time.sleep(0.05)
            loop.call_soon_threadsafe(loop.stop)
            thread.join(timeout=2)
            assert seen == [True, True, True]
        finally:
            AsyncUtils.main_loop = None
            AsyncUtils._pending_coroutines.clear()
            AsyncUtils._pending_futures.clear()


class TestAnnounceAppDataCap:
    def test_oversized_app_data_not_stored(self, temp_dir):
        from meshchatx.src.backend.announce_manager import (
            MAX_ANNOUNCE_APP_DATA_BYTES,
            AnnounceManager,
        )

        db = Database(os.path.join(temp_dir, "t.db"))
        db.initialize()

        class FakeIdentity:
            hash = b"\x01" * 16

            def get_public_key(self):
                return b"\x02" * 32

        manager = AnnounceManager(db)
        dest = b"\x03" * 16
        big = bytearray(MAX_ANNOUNCE_APP_DATA_BYTES + 1)
        manager.upsert_announce(
            None,
            FakeIdentity(),
            dest,
            "lxmf.delivery",
            big,
            None,
        )
        row = db.provider.fetchone(
            "SELECT app_data FROM announces WHERE destination_hash = ?",
            (dest.hex(),),
        )
        assert row is not None
        assert row["app_data"] is None

        manager.upsert_announce(
            None,
            FakeIdentity(),
            dest,
            "lxmf.delivery",
            b"small",
            None,
        )
        row = db.provider.fetchone(
            "SELECT app_data FROM announces WHERE destination_hash = ?",
            (dest.hex(),),
        )
        import base64

        assert row["app_data"] == base64.b64encode(b"small").decode("utf-8")


class TestSnapshotDeleteSymlink:
    @pytest.mark.skipif(os.name == "nt", reason="posix symlink semantics")
    def test_delete_removes_link_not_target(self, temp_dir):
        db = Database(os.path.join(temp_dir, "t.db"))
        db.initialize()
        snap_dir = os.path.join(temp_dir, "snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        real = os.path.join(snap_dir, "real.zip")
        with open(real, "wb") as handle:
            handle.write(b"zip-data")
        link = os.path.join(snap_dir, "link.zip")
        os.symlink(real, link)

        assert db.delete_snapshot_or_backup(temp_dir, "link.zip") is True
        assert not os.path.lexists(link)
        assert os.path.isfile(real)
        with open(real, "rb") as handle:
            assert handle.read() == b"zip-data"


class TestUploadStagingNoFollow:
    @pytest.mark.skipif(os.name == "nt", reason="posix symlink semantics")
    @pytest.mark.asyncio
    async def test_symlinked_staging_path_is_rejected(self, temp_dir):
        """A symlink swapped in after staging must not redirect the write."""
        import tempfile

        from meshchatx.src.backend.http.uploads import write_field_to_path

        canary = os.path.join(temp_dir, "canary.txt")
        with open(canary, "w", encoding="utf-8") as handle:
            handle.write("canary")

        fd, staging = tempfile.mkstemp(dir=temp_dir)
        os.close(fd)
        os.unlink(staging)
        os.symlink(canary, staging)

        class FakeField:
            async def read_chunk(self, _size):
                if getattr(self, "_done", False):
                    return b""
                self._done = True
                return b"payload"

        with pytest.raises(OSError):
            await write_field_to_path(FakeField(), staging, 1024)
        with open(canary, encoding="utf-8") as handle:
            assert handle.read() == "canary"

    @pytest.mark.asyncio
    async def test_normal_staging_write_still_works(self, temp_dir):
        import tempfile

        from meshchatx.src.backend.http.uploads import write_field_to_path

        fd, staging = tempfile.mkstemp(dir=temp_dir)
        os.close(fd)

        chunks = [b"aa", b"bb", b""]

        class FakeField:
            async def read_chunk(self, _size):
                return chunks.pop(0)

        written = await write_field_to_path(FakeField(), staging, 1024)
        assert written == 4
        with open(staging, "rb") as handle:
            assert handle.read() == b"aabb"


class TestUploadBasenameDrivePrefix:
    def test_drive_relative_names_rejected(self):
        from meshchatx.src.path_utils import safe_basename

        assert safe_basename("C:foo") is None
        assert safe_basename("C:") is None
        assert safe_basename("a:b.txt") is None
        assert safe_basename("plain.txt") == "plain.txt"
        assert safe_basename("file:name.txt") == "file:name.txt"


class TestDocsVersionSymlink:
    @pytest.mark.skipif(os.name == "nt", reason="posix symlink semantics")
    def test_symlinked_version_dir_not_listed_or_switchable(self, temp_dir):
        from meshchatx.src.backend.docs_manager import DocsManager

        outside = os.path.join(temp_dir, "outside")
        os.makedirs(outside)
        with open(os.path.join(outside, "secret.md"), "w") as handle:
            handle.write("secret")

        manager = DocsManager(None, temp_dir, storage_dir=temp_dir, populate=False)
        os.symlink(outside, os.path.join(manager.versions_dir, "evil"))

        assert "evil" not in manager.get_available_versions()
        assert manager.switch_version("evil") is False
        assert manager.delete_version("evil") is False
        # The planted outside dir is never removed by docs operations.
        assert os.path.isfile(os.path.join(outside, "secret.md"))


class TestReticulumRecoverGuard:
    @pytest.mark.asyncio
    async def test_recover_returns_503_while_setup_thread_alive(self, temp_dir):
        from meshchatx.meshchat import ReticulumMeshChat

        identity = MagicMock()
        identity.hash = b"h" * 16
        identity.hexhash = identity.hash.hex()
        with (
            patch("meshchatx.meshchat.AsyncUtils.ensure_background_loop"),
            patch.object(ReticulumMeshChat, "setup_identity"),
        ):
            app = ReticulumMeshChat(
                identity=identity,
                storage_dir=temp_dir,
                reticulum_config_dir=temp_dir,
                defer_network_setup=True,
            )

        alive = threading.Event()

        def fake_worker():
            alive.wait(5)

        app._network_setup_thread = threading.Thread(target=fake_worker, daemon=True)
        app._network_setup_thread.start()

        routes = web.RouteTableDef()
        middlewares = app._define_routes(routes)
        aio_app = web.Application(middlewares=list(middlewares))
        aio_app.add_routes(routes)

        try:
            async with TestClient(TestServer(aio_app)) as client:
                csrf = await client.get("/api/v1/auth/csrf")
                token = None
                if csrf.status == 200:
                    body = await csrf.json()
                    token = body.get("csrfToken") or body.get("csrf_token")
                headers = {"X-CSRF-Token": token} if token else {}
                resp = await client.post(
                    "/api/v1/reticulum/recover",
                    json={},
                    headers=headers,
                )
                assert resp.status == 503
        finally:
            alive.set()
            app._network_setup_thread.join(timeout=2)
