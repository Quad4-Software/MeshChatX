# SPDX-License-Identifier: 0BSD

"""Adversarial oracles from the 2026-08-15 exploratory hunt.

Each test names an invariant, then checks the code matches it. Failures are
confirmed bugs, not crash-only fuzz.
"""

from __future__ import annotations

import os
import zipfile
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.docs_manager import DocsManager
from meshchatx.src.backend.plugin_guard import PluginSecurityError
from meshchatx.src.backend.plugin_manager import PluginManager
from meshchatx.src.backend.repository_server_manager import RepositoryServerManager
from meshchatx.src.backend.rncp_handler import RNCPHandler
from meshchatx.src.backend.rns_filesync_handler import RnsFilesyncHandler
from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCManager
from meshchatx.src.backend.rrc.server import RRCHubServer, _Session

HUB_HASH = bytes(range(16))


class FakeIdentity:
    def __init__(self, hash_bytes):
        self.hash = hash_bytes


class FakeLink:
    def __init__(self, identity, on_close=None):
        self._identity = identity
        self._on_close = on_close

    def get_remote_identity(self):
        return self._identity

    def teardown(self):
        if self._on_close is not None:
            self._on_close(self)


class FakeRrcManager:
    def __init__(self):
        self.identity = FakeIdentity(b"\x22" * 16)
        self.history_per_room_cap = 0
        self.filter_loaded_history = False

    def get_nickname(self):
        return None

    def get_name_for_identity_hash(self, _h):
        return None

    def save(self):
        return None

    def _notify_change(self, hub=None):
        return None

    def _notify_messages(self, hub, msg):
        return None

    def set_active(self, hub, room):
        return None

    def active_room_for(self, hub):
        return None

    def _on_welcome(self, hub):
        return None

    def find_local_server(self, _h):
        return None

    def is_bad_key_error(self, text):
        return RRCManager.is_bad_key_error(text)

    def forget_room_key(self, hub, room):
        return 0


def _rncp(tmp_path):
    storage = tmp_path / "id"
    storage.mkdir()
    return RNCPHandler(MagicMock(), MagicMock(), str(storage)), storage


def test_oracle_rncp_send_refuses_ssl_and_database(tmp_path):
    """RNCP send must not exfiltrate TLS keys or the identity database."""
    handler, storage = _rncp(tmp_path)
    ssl_dir = storage / "ssl"
    ssl_dir.mkdir()
    key = ssl_dir / "key.pem"
    key.write_text("PRIVATE", encoding="utf-8")
    db = storage / "database.db"
    db.write_bytes(b"sqlite")
    allowed = storage / "filesync" / "sync"
    allowed.mkdir(parents=True)
    ok = allowed / "note.txt"
    ok.write_text("hi", encoding="utf-8")

    with pytest.raises(PermissionError):
        handler._resolve_send_path(str(key))
    with pytest.raises(PermissionError):
        handler._resolve_send_path(str(db))
    with pytest.raises(PermissionError):
        handler._resolve_send_path("ssl/key.pem")
    with pytest.raises(PermissionError):
        handler._resolve_send_path("database.db")
    assert handler._resolve_send_path(str(ok)) == str(ok.resolve())


def test_oracle_rncp_fetch_save_refuses_ssl_and_storage_root(tmp_path):
    """RNCP fetch must not land downloads in ssl/ or on the identity root."""
    handler, storage = _rncp(tmp_path)
    ssl_dir = storage / "ssl"
    ssl_dir.mkdir()
    bait = ssl_dir / "key.pem"
    bait.write_text("keep", encoding="utf-8")

    with pytest.raises(PermissionError):
        handler._resolve_fetch_save_dir("ssl")
    with pytest.raises(PermissionError):
        handler._resolve_fetch_save_dir(str(ssl_dir))
    with pytest.raises(PermissionError):
        handler._resolve_fetch_save_dir(".")
    with pytest.raises(PermissionError):
        handler._resolve_fetch_save_dir(str(storage))

    dest = handler._resolve_fetch_save_dir("rncp/downloads")
    assert dest.startswith(str(storage.resolve()) + os.sep)
    assert os.path.basename(os.path.dirname(dest)) == "rncp"
    assert bait.read_text(encoding="utf-8") == "keep"


def test_oracle_docs_zip_absolute_and_dotdot_leave_bait(tmp_path):
    """Docs zip members that escape the extract tree must not overwrite bait."""
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    config = MagicMock()
    dm = DocsManager(
        config,
        str(public_dir),
        storage_dir=str(storage_dir),
        populate=False,
    )

    outside = tmp_path / "OUTSIDE"
    outside.mkdir()
    bait = outside / "secret.txt"
    bait.write_text("safe", encoding="utf-8")

    zip_path = tmp_path / "slip.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("goodroot/docs/index.md", "# ok\n")
        archive.writestr("../OUTSIDE/secret.txt", "pwned")
        info = zipfile.ZipInfo(filename=str(bait))
        archive.writestr(info, "pwned-abs")
        archive.writestr("/tmp/meshchatx-docs-slip.txt", "pwned-unix")

    try:
        dm._extract_docs(str(zip_path), "slip")
    except Exception:
        pass

    assert bait.read_text(encoding="utf-8") == "safe"


def test_oracle_dispatch_hook_skips_when_plugins_disabled(tmp_path):
    """MESHCHAT_DISABLE_PLUGINS / plugins_enabled=False must skip hook exec."""
    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        (
            '{"id":"com.example.hooks","version":"1.0.0","apiVersion":1,'
            '"name":"Hooks","backend":{"entry":"backend/main.py","type":"python"},'
            '"permissions":{"hooks":["announce.received"],"storage":"isolated"}}'
        ),
        encoding="utf-8",
    )
    backend = source / "backend"
    backend.mkdir()
    (backend / "main.py").write_text(
        "def on_hook(hook, payload, host):\n    host.storage_set('last_hook', hook)\n",
        encoding="utf-8",
    )

    class EnabledApp:
        reticulum = object()
        rnpath_handler = None
        plugins_enabled = True

    manager = PluginManager(str(tmp_path / "storage"), app=EnabledApp())
    installed = manager.install_from_directory(
        str(source),
        granted_permissions=["hooks:announce.received", "storage:isolated"],
    )
    plugin_id = installed["id"]
    manager.enable(plugin_id)
    manager.app.plugins_enabled = False
    manager.dispatch_hook(plugin_id, "announce.received", {"x": 1})
    assert manager.storage_get(plugin_id, "last_hook") is None


def test_oracle_python_runtime_purges_nested_pycache(tmp_path):
    """Integrity ignores __pycache__, so load must purge nested bytecode too."""
    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        (
            '{"id":"com.example.nested-cache","version":"1.0.0","apiVersion":1,'
            '"name":"Nested Cache","backend":{"entry":"backend/main.py","type":"python"},'
            '"permissions":{"storage":"isolated"}}'
        ),
        encoding="utf-8",
    )
    backend = source / "backend"
    pkg = backend / "pkg"
    pkg.mkdir(parents=True)
    (backend / "main.py").write_text(
        "def invoke(method, args, host=None):\n    return {'ok': True}\n",
        encoding="utf-8",
    )
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mod.py").write_text("VALUE = 'clean'\n", encoding="utf-8")

    class FakeApp:
        reticulum = object()
        rnpath_handler = None
        plugins_enabled = True

    manager = PluginManager(str(tmp_path / "storage"), app=FakeApp())
    manager.install_from_directory(
        str(source),
        granted_permissions=["storage:isolated"],
    )
    nested = (
        tmp_path
        / "storage"
        / "plugins"
        / "installed"
        / "com.example.nested-cache"
        / "backend"
        / "pkg"
        / "__pycache__"
    )
    nested.mkdir(parents=True, exist_ok=True)
    planted = nested / "mod.cpython-314.pyc"
    planted.write_bytes(b"not-real-bytecode")
    manager.enable("com.example.nested-cache")
    assert not planted.exists()
    assert not nested.exists()


@pytest.mark.skipif(os.name == "nt", reason="symlink follow-on-open is a POSIX case")
def test_oracle_repository_upload_refuses_symlink_dest(tmp_path):
    """Upload must not write through a pre-created symlink in uploads/."""
    outside = tmp_path / "OUTSIDE"
    outside.mkdir()
    bait = outside / "secret.whl"
    bait.write_bytes(b"keep")
    mgr = RepositoryServerManager(str(tmp_path / "identity"))
    dest = os.path.join(mgr.uploads_dir, "foo.whl")
    os.symlink(str(bait), dest)
    ok, err = mgr.save_upload("foo.whl", b"pwned")
    assert ok is False
    assert err is not None
    assert bait.read_bytes() == b"keep"


def test_oracle_kline_error_without_room_drops_all_client_rooms(tmp_path):
    """Global kline ERROR has no room field. Client must still leave every room."""
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
    )
    hub = manager.add_hub(HUB_HASH, name="Client")
    hub.rooms.add("lobby")
    hub.rooms.add("ops")
    hub.messages["lobby"] = []
    hub.messages["ops"] = []
    hub.members["lobby"] = {b"\x11" * 16}
    hub._handle_error(
        proto.make_envelope(
            proto.T_ERROR,
            src=HUB_HASH,
            body="banned (kline)",
        ),
    )
    assert "lobby" not in hub.rooms
    assert "ops" not in hub.rooms
    assert "lobby" not in hub.messages
    assert "ops" not in hub.messages


def test_oracle_kline_teardown_fans_parted_to_remaining_members():
    """Kline teardown must notify remaining members the same way kick does."""
    server = RRCHubServer(FakeRrcManager(), FakeIdentity(HUB_HASH), name="Oracle Hub")
    sent = []

    def capture(link, payload):
        sent.append((link, proto.decode(payload)))

    server._send_payload = capture

    def add_session(peer_hash, nick):
        link = FakeLink(FakeIdentity(peer_hash), on_close=server._on_close)
        sess = _Session()
        sess.peer = peer_hash
        sess.nick = nick
        sess.welcomed = True
        server._sessions[link] = sess
        return link, sess

    link_op, sess_op = add_session(b"\xaa" * 16, "op")
    link_victim, sess_victim = add_session(b"\xbb" * 16, "victim")
    for link, sess, room in (
        (link_op, sess_op, "lobby"),
        (link_victim, sess_victim, "lobby"),
    ):
        outgoing = []
        server._route(
            link,
            sess,
            proto.make_envelope(proto.T_JOIN, src=sess.peer, room=room),
            outgoing,
        )
    assert link_victim in server._room_members.get("lobby", set())

    outgoing = []
    server._disconnect_banned(sess_victim.peer, outgoing, "banned (kline)")
    parted = [
        env
        for lnk, env in sent
        if lnk is link_op and env.get(proto.K_T) == proto.T_PARTED
    ]
    assert parted, "remaining members must see PARTED after kline teardown"
    assert link_victim not in server._room_members.get("lobby", set())
    assert link_victim not in server._sessions


def test_oracle_filesync_refuses_page_nodes_sync_root(tmp_path):
    """Mesh Server node dirs hold a nested identity key. FileSync must not share them."""
    storage = tmp_path / "id"
    node_dir = storage / "page_nodes" / "node1"
    node_dir.mkdir(parents=True)
    (node_dir / "identity").write_bytes(b"page-node-private-key")
    handler = RnsFilesyncHandler(
        MagicMock(),
        type("Ident", (), {"hash": b"\x33" * 16})(),
        str(storage),
    )
    assert handler._resolve_sync_directory(str(storage / "page_nodes")) is None
    assert handler._resolve_sync_directory(str(node_dir)) is None
    assert handler._resolve_sync_directory(str(node_dir / "identity")) is None
    ok = storage / "filesync" / "sync"
    ok.mkdir(parents=True, exist_ok=True)
    assert handler._resolve_sync_directory(str(ok)) == str(ok.resolve())


def test_oracle_rncp_shared_root_refuses_session_secret_and_sibling_identity(
    tmp_path,
):
    """Production RNCPHandler uses app.storage_dir, not the identity folder.

    Reserved tops must be relative to that shared root. identities/ and
    session_secret sit next to identities/<hash>/, not inside it.
    """
    shared = tmp_path / "storage"
    ident_a = shared / "identities" / ("a" * 32)
    ident_b = shared / "identities" / ("b" * 32)
    ident_a.mkdir(parents=True)
    ident_b.mkdir(parents=True)
    (ident_a / "identity").write_bytes(b"key-a")
    (ident_b / "identity").write_bytes(b"key-b")
    db_b = ident_b / "database.db"
    db_b.write_bytes(b"sqlite-b")
    ssl_b = ident_b / "ssl"
    ssl_b.mkdir()
    key_b = ssl_b / "key.pem"
    key_b.write_text("PRIVATE", encoding="utf-8")
    secret = shared / "session_secret"
    secret.write_text("cookie-hmac-key", encoding="utf-8")
    security = shared / "app_security.json"
    security.write_text("{}", encoding="utf-8")
    allowed = shared / "rncp_received"
    allowed.mkdir()
    ok = allowed / "note.txt"
    ok.write_text("hi", encoding="utf-8")

    handler = RNCPHandler(MagicMock(), MagicMock(), str(shared))
    with pytest.raises(PermissionError):
        handler._resolve_send_path(str(secret))
    with pytest.raises(PermissionError):
        handler._resolve_send_path(str(security))
    with pytest.raises(PermissionError):
        handler._resolve_send_path(str(db_b))
    with pytest.raises(PermissionError):
        handler._resolve_send_path(str(key_b))
    with pytest.raises(PermissionError):
        handler._resolve_fetch_save_dir(str(ident_b))
    with pytest.raises(PermissionError):
        handler._resolve_fetch_save_dir("identities")
    assert handler._resolve_send_path(str(ok)) == str(ok.resolve())
    assert handler._safe_received_filename("identity") == "downloaded_file"
    assert handler._safe_received_filename("session_secret") == "downloaded_file"


@pytest.mark.skipif(os.name == "nt", reason="symlink follow-on-copy is a POSIX case")
def test_oracle_plugin_install_does_not_copy_symlink_target(tmp_path):
    """Install must not follow source-tree file symlinks into host identity bytes."""
    bait_dir = tmp_path / "OUTSIDE"
    bait_dir.mkdir()
    bait = bait_dir / "identity"
    bait.write_bytes(b"HOST-PRIVATE-KEY")
    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        (
            '{"id":"com.example.symlink","version":"1.0.0","apiVersion":1,'
            '"name":"Symlink","frontend":{"entry":"frontend/main.js","type":"js"}}'
        ),
        encoding="utf-8",
    )
    frontend = source / "frontend"
    frontend.mkdir()
    (frontend / "main.js").write_text(
        "export async function activate() {}",
        encoding="utf-8",
    )
    os.symlink(str(bait), str(source / "stolen"))

    manager = PluginManager(str(tmp_path / "storage"))
    with pytest.raises(PluginSecurityError):
        manager.install_from_directory(str(source))
    installed = (
        tmp_path
        / "storage"
        / "plugins"
        / "installed"
        / "com.example.symlink"
        / "stolen"
    )
    assert not installed.is_file() or installed.read_bytes() != b"HOST-PRIVATE-KEY"
    assert bait.read_bytes() == b"HOST-PRIVATE-KEY"


def test_oracle_rncp_refuses_page_nodes_send_and_fetch_save(tmp_path):
    """RNCP must not send or land downloads on Mesh Server identity trees."""
    storage = tmp_path / "id"
    node_dir = storage / "page_nodes" / "node1"
    node_dir.mkdir(parents=True)
    key = node_dir / "identity"
    key.write_bytes(b"page-node-private-key")
    page = node_dir / "pages"
    page.mkdir()
    page_file = page / "index.mu"
    page_file.write_text("Hello\n", encoding="utf-8")
    handler = RNCPHandler(MagicMock(), MagicMock(), str(storage))
    with pytest.raises(PermissionError):
        handler._resolve_send_path(str(key))
    with pytest.raises(PermissionError):
        handler._resolve_send_path(str(page_file))
    with pytest.raises(PermissionError):
        handler._resolve_fetch_save_dir(str(node_dir))
    with pytest.raises(PermissionError):
        handler._resolve_fetch_save_dir("page_nodes")
