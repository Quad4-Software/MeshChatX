# SPDX-License-Identifier: 0BSD

import json
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.database.announces import AnnounceDAO
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema
from meshchatx.src.backend.meshchat_utils import convert_db_favourite_to_dict
from meshchatx.src.backend.nomadnet_downloader import (
    NomadnetDownloader,
    _nomadnet_links_lock,
    drop_cached_link,
    nomad_link_identity_kwargs,
    nomadnet_cached_links,
)


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns_minimal():
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


@pytest.fixture(autouse=True)
def clear_nomadnet_link_cache():
    with _nomadnet_links_lock:
        nomadnet_cached_links.clear()
        from meshchatx.src.backend.nomadnet_downloader import _nomadnet_link_last_used

        _nomadnet_link_last_used.clear()
    yield
    with _nomadnet_links_lock:
        nomadnet_cached_links.clear()
        from meshchatx.src.backend.nomadnet_downloader import _nomadnet_link_last_used

        _nomadnet_link_last_used.clear()


def _column_names(provider, table: str) -> set[str]:
    cur = provider.connection.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cur.fetchall()}
    finally:
        cur.close()


def test_schema_v58_adds_identify_on_connect_column(tmp_path):
    db_path = tmp_path / "fav.db"
    provider = DatabaseProvider(str(db_path))
    schema = DatabaseSchema(provider)
    schema.initialize()
    assert "identify_on_connect" in _column_names(provider, "favourite_destinations")
    try:
        provider.execute(
            "ALTER TABLE favourite_destinations DROP COLUMN identify_on_connect",
        )
    except Exception as exc:
        pytest.skip(f"SQLite DROP COLUMN not available: {exc}")
    provider.execute(
        "UPDATE config SET value = ? WHERE key = ?",
        ("57", "database_version"),
    )
    assert "identify_on_connect" not in _column_names(
        provider,
        "favourite_destinations",
    )
    schema.migrate(57)
    assert "identify_on_connect" in _column_names(provider, "favourite_destinations")
    assert (
        int(
            provider.fetchone(
                "SELECT value FROM config WHERE key = ?",
                ("database_version",),
            )["value"],
        )
        == DatabaseSchema.LATEST_VERSION
    )
    provider.close_all()


def test_upsert_favourite_identify_on_connect_roundtrip(tmp_path):
    db_path = tmp_path / "fav2.db"
    provider = DatabaseProvider(str(db_path))
    schema = DatabaseSchema(provider)
    schema.initialize()
    announces = AnnounceDAO(provider)
    dest = "a" * 32
    announces.upsert_favourite(dest, "Node A", "nomadnetwork.node")
    assert announces.should_identify_on_connect(dest) is False
    announces.upsert_favourite(
        dest,
        "Node A",
        "nomadnetwork.node",
        identify_on_connect=True,
    )
    assert announces.should_identify_on_connect(dest) is True
    row = announces.get_favourite_by_destination_hash(dest)
    assert convert_db_favourite_to_dict(row)["identify_on_connect"] is True
    announces.upsert_favourite(dest, "Node A Renamed", "nomadnetwork.node")
    assert announces.should_identify_on_connect(dest) is True
    provider.close_all()


def test_nomad_link_identity_kwargs_respects_private_and_favourite(tmp_path):
    db_path = tmp_path / "fav3.db"
    provider = DatabaseProvider(str(db_path))
    schema = DatabaseSchema(provider)
    schema.initialize()
    announces = AnnounceDAO(provider)
    dest = "b" * 32
    announces.upsert_favourite(
        dest,
        "Node B",
        "nomadnetwork.node",
        identify_on_connect=True,
    )
    app = MagicMock()
    app.database = MagicMock()
    app.database.announces = announces
    app.identity = MagicMock(name="identity")
    dest_bytes = bytes.fromhex(dest)
    private_kwargs = nomad_link_identity_kwargs(app, dest_bytes, private=True)
    assert private_kwargs["identify_on_connect"] is False
    assert private_kwargs["local_identity"] is None
    public_kwargs = nomad_link_identity_kwargs(app, dest_bytes, private=False)
    assert public_kwargs["identify_on_connect"] is True
    assert public_kwargs["local_identity"] is app.identity
    provider.close_all()


def test_link_established_identifies_when_flag_set():
    identity = MagicMock()
    link = MagicMock()
    link.status = RNS.Link.ACTIVE
    link.request = MagicMock(return_value=MagicMock())
    d = NomadnetDownloader(
        b"dest",
        "/page/index.mu",
        None,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        local_identity=identity,
        identify_on_connect=True,
    )
    d.link_established(link)
    link.identify.assert_called_once_with(identity)
    link.request.assert_called_once()


def test_link_established_skips_identify_when_private():
    identity = MagicMock()
    link = MagicMock()
    link.status = RNS.Link.ACTIVE
    link.request = MagicMock(return_value=MagicMock())
    d = NomadnetDownloader(
        b"dest",
        "/page/index.mu",
        None,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        private=True,
        local_identity=identity,
        identify_on_connect=True,
    )
    assert d.identify_on_connect is False
    d.link_established(link)
    link.identify.assert_not_called()


def test_drop_cached_link_tears_down():
    mock_link = MagicMock()
    mock_link.status = RNS.Link.ACTIVE
    with _nomadnet_links_lock:
        nomadnet_cached_links[b"dropme"] = mock_link
    assert drop_cached_link(b"dropme") is True
    mock_link.teardown.assert_called_once()
    assert drop_cached_link(b"dropme") is False


@pytest.mark.asyncio
async def test_favourites_identify_on_connect_api(mock_rns_minimal, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns_minimal,
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )
    handler = None
    for route in app.get_routes():
        if (
            route.path == "/api/v1/favourites/{destination_hash}/identify-on-connect"
            and route.method == "POST"
        ):
            handler = route.handler
            break
    assert handler is not None

    dest = "c" * 32
    request = MagicMock()
    request.match_info = {"destination_hash": dest}
    request.json = AsyncMock(
        return_value={
            "enabled": True,
            "display_name": "Node C",
            "aspect": "nomadnetwork.node",
        },
    )
    response = await handler(request)
    data = json.loads(response.body)
    assert data["identify_on_connect"] is True
    assert app.database.announces.should_identify_on_connect(dest) is True

    mock_link = MagicMock()
    mock_link.status = RNS.Link.ACTIVE
    with _nomadnet_links_lock:
        nomadnet_cached_links[bytes.fromhex(dest)] = mock_link

    request.json = AsyncMock(return_value={"enabled": False})
    response = await handler(request)
    data = json.loads(response.body)
    assert data["identify_on_connect"] is False
    assert data["cache_dropped"] is True
    mock_link.teardown.assert_called_once()
    assert app.database.announces.should_identify_on_connect(dest) is False


@pytest.mark.asyncio
async def test_favourites_import_persists_identify_on_connect(
    mock_rns_minimal,
    temp_dir,
):
    app = ReticulumMeshChat(
        identity=mock_rns_minimal,
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )
    handler = None
    for route in app.get_routes():
        if route.path == "/api/v1/favourites/import" and route.method == "POST":
            handler = route.handler
            break
    assert handler is not None
    dest = "d" * 32
    request = MagicMock()
    request.json = AsyncMock(
        return_value={
            "favourites": [
                {
                    "destination_hash": dest,
                    "display_name": "Node D",
                    "aspect": "nomadnetwork.node",
                    "identify_on_connect": True,
                },
            ],
        },
    )
    response = await handler(request)
    data = json.loads(response.body)
    assert data["imported"] == 1
    assert app.database.announces.should_identify_on_connect(dest) is True
