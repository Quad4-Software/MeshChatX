# SPDX-License-Identifier: 0BSD
"""Oracle tests for identity hotswap serialization, delete eviction, and LXMF GET consistency."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns():
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"initial_hash_32_bytes_long_01234"
            self.hexhash = self.hash.hex()

    with ExitStack() as stack:
        patches = [
            patch("RNS.Reticulum"),
            patch("RNS.Transport"),
            patch("RNS.Identity", MockIdentityClass),
            patch("threading.Thread"),
            patch("meshchatx.src.backend.identity_context.core.Database"),
            patch("meshchatx.src.backend.identity_context.core.ConfigManager"),
            patch("meshchatx.src.backend.identity_context.core.MessageHandler"),
            patch("meshchatx.src.backend.identity_context.core.AnnounceManager"),
            patch("meshchatx.src.backend.identity_context.core.ArchiverManager"),
            patch("meshchatx.src.backend.identity_context.core.MapManager"),
            patch("meshchatx.src.backend.identity_context.core.DocsManager"),
            patch("meshchatx.src.backend.identity_context.core.NomadNetworkManager"),
            patch("meshchatx.src.backend.identity_context.core.TelephoneManager"),
            patch("meshchatx.src.backend.identity_context.core.VoicemailManager"),
            patch("meshchatx.src.backend.identity_context.core.RingtoneManager"),
            patch("meshchatx.src.backend.identity_context.core.RNCPHandler"),
            patch("meshchatx.src.backend.identity_context.core.RNStatusHandler"),
            patch("meshchatx.src.backend.identity_context.core.RNProbeHandler"),
            patch("meshchatx.src.backend.identity_context.core.TranslatorHandler"),
            patch(
                "meshchatx.src.backend.identity_context.core.CommunityInterfacesManager"
            ),
            patch("LXMF.LXMRouter"),
            patch("meshchatx.meshchat.IdentityContext"),
        ]
        mocks = {}
        for p in patches:
            attr_name = (
                p.attribute if hasattr(p, "attribute") else p.target.split(".")[-1]
            )
            mocks[attr_name] = stack.enter_context(p)

        mock_id_instance = MockIdentityClass()
        mock_id_instance.get_private_key = MagicMock(
            return_value=b"initial_private_key",
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "from_file", return_value=mock_id_instance),
        )
        yield {
            "Identity": MockIdentityClass,
            "id_instance": mock_id_instance,
            "IdentityContext": mocks["IdentityContext"],
        }


def _write_identity_tree(storage_dir: str, identity_hash: str, key: bytes) -> None:
    identity_dir = os.path.join(storage_dir, "identities", identity_hash)
    os.makedirs(identity_dir, exist_ok=True)
    with open(os.path.join(identity_dir, "identity"), "wb") as f:
        f.write(key)


@pytest.mark.asyncio
async def test_oracle_concurrent_hotswap_serializes_critical_section(
    mock_rns,
    temp_dir,
):
    """Second hotswap must not enter until the first finishes (lock held across sleep)."""
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )
    app.websocket_broadcast = AsyncMock()

    hash_a = "aa" * 16
    hash_b = "bb" * 16
    _write_identity_tree(temp_dir, hash_a, b"key_a")
    _write_identity_tree(temp_dir, hash_b, b"key_b")

    id_a = MagicMock()
    id_a.hash = bytes.fromhex(hash_a)
    id_b = MagicMock()
    id_b.hash = bytes.fromhex(hash_b)

    def from_file(path):
        if hash_a in path:
            return id_a
        if hash_b in path:
            return id_b
        return mock_rns["id_instance"]

    mock_rns["Identity"].from_file.side_effect = from_file

    ctx_a = MagicMock()
    ctx_a.config.display_name.get.return_value = "A"
    ctx_a.identity_hash = hash_a
    ctx_b = MagicMock()
    ctx_b.config.display_name.get.return_value = "B"
    ctx_b.identity_hash = hash_b

    def setup_side_effect(identity):
        if identity.hash.hex() == hash_a:
            app.current_context = ctx_a
        else:
            app.current_context = ctx_b

    app.teardown_identity = MagicMock()
    app.setup_identity = MagicMock(side_effect=setup_side_effect)
    first_in_sleep = asyncio.Event()
    release_first = asyncio.Event()

    async def gated_sleep(delay):
        if delay == 2:
            first_in_sleep.set()
            await release_first.wait()

    task_b_started = asyncio.Event()

    async def run_b():
        task_b_started.set()
        return await app.hotswap_identity(hash_b)

    with patch("meshchatx.meshchat.asyncio.sleep", side_effect=gated_sleep):
        task_a = asyncio.create_task(app.hotswap_identity(hash_a))
        await asyncio.wait_for(first_in_sleep.wait(), timeout=2)
        task_b = asyncio.create_task(run_b())
        await asyncio.wait_for(task_b_started.wait(), timeout=2)
        await asyncio.sleep(0.02)
        assert not task_b.done()
        release_first.set()
        results = await asyncio.gather(task_a, task_b)

    assert results == [True, True]
    assert app.teardown_identity.call_count == 2


@pytest.mark.asyncio
async def test_oracle_hotswap_broadcast_requires_reauth_when_auth_enabled(
    mock_rns,
    temp_dir,
):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
        auth_enabled=True,
    )
    app.websocket_broadcast = AsyncMock()
    app.teardown_identity = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.config.display_name.get.return_value = "User"
    mock_ctx.config.auth_enabled.get.return_value = True
    app.setup_identity = MagicMock(
        side_effect=lambda _id: setattr(app, "current_context", mock_ctx),
    )

    new_hash = "ee" * 16
    _write_identity_tree(temp_dir, new_hash, b"key")
    new_id = MagicMock()
    new_id.hash = bytes.fromhex(new_hash)
    mock_rns["Identity"].from_file.return_value = new_id

    with patch("meshchatx.meshchat.asyncio.sleep", new=AsyncMock()):
        await app.hotswap_identity(new_hash)

    payload = json.loads(app.websocket_broadcast.call_args[0][0])
    assert payload["type"] == "identity_switched"
    assert payload["requires_reauth"] is True


@pytest.mark.asyncio
async def test_oracle_hotswap_broadcast_no_reauth_when_auth_disabled(
    mock_rns,
    temp_dir,
):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
        auth_enabled=False,
    )
    app.websocket_broadcast = AsyncMock()
    app.teardown_identity = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.config.display_name.get.return_value = "User"
    mock_ctx.config.auth_enabled.get.return_value = False
    app.setup_identity = MagicMock(
        side_effect=lambda _id: setattr(app, "current_context", mock_ctx),
    )

    new_hash = "ff" * 16
    _write_identity_tree(temp_dir, new_hash, b"key")
    new_id = MagicMock()
    new_id.hash = bytes.fromhex(new_hash)
    mock_rns["Identity"].from_file.return_value = new_id

    with patch("meshchatx.meshchat.asyncio.sleep", new=AsyncMock()):
        await app.hotswap_identity(new_hash)

    payload = json.loads(app.websocket_broadcast.call_args[0][0])
    assert payload.get("requires_reauth") is False

    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )
    stale_hash = "cc" * 16
    current_hash = mock_rns["id_instance"].hash.hex()
    stale_ctx = MagicMock()
    stale_ctx.identity_hash = stale_hash
    app.contexts[stale_hash] = stale_ctx
    app.current_context = MagicMock()
    app.current_context.identity_hash = current_hash

    identity_dir = os.path.join(temp_dir, "identities", stale_hash)
    os.makedirs(identity_dir)
    with open(os.path.join(identity_dir, "identity"), "wb") as f:
        f.write(b"stale")

    assert app.delete_identity(stale_hash) is True
    stale_ctx.teardown.assert_called_once()
    assert stale_hash not in app.contexts
    assert not os.path.isdir(identity_dir)


def test_oracle_setup_identity_drops_context_when_storage_dir_removed(
    mock_rns,
    temp_dir,
):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )
    orphan_hash = "dd" * 16
    orphan_ctx = MagicMock()
    orphan_ctx.running = False
    app.contexts[orphan_hash] = orphan_ctx

    new_id = MagicMock()
    new_id.hash = bytes.fromhex(orphan_hash)
    mock_rns["IdentityContext"].return_value = MagicMock()

    app.setup_identity(new_id)

    orphan_ctx.teardown.assert_called_once()
    mock_rns["IdentityContext"].assert_called()


@pytest.mark.asyncio
async def test_oracle_propagation_nodes_reads_only_ctx_database(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )
    handler = None
    for route in app.get_routes():
        if route.path == "/api/v1/lxmf/propagation-nodes" and route.method == "GET":
            handler = route.handler
            break
    assert handler is not None

    ctx = app.current_context
    assert ctx is not None
    ctx.running = True
    marker = "oracle-marker-identity"
    ctx.database.announces.get_announces.return_value = [
        {
            "identity_hash": marker,
            "destination_hash": "ee" * 16,
            "app_data": None,
            "created_at": "2020-01-01",
            "updated_at": "2020-01-01",
        },
    ]
    ctx.database.announces.get_filtered_announces.return_value = []

    wrong_db = MagicMock()
    wrong_db.announces.get_announces.return_value = [
        {
            "identity_hash": "wrong-wrong-wrong-wrong-wrong-wrong",
            "destination_hash": "ff" * 16,
            "app_data": None,
            "created_at": "2020-01-01",
            "updated_at": "2020-01-01",
        },
    ]

    router = ctx.message_router
    router.propagation_destination = MagicMock(hexhash=None, hash=None)

    with patch.object(type(app), "database", property(lambda self: wrong_db)):
        request = MagicMock()
        request.query = {}
        response = await handler(request)

    assert response.status == 200
    data = json.loads(response.body)
    nodes = data["lxmf_propagation_nodes"]
    assert len(nodes) == 1
    assert nodes[0]["identity_hash"] == marker
    wrong_db.announces.get_announces.assert_not_called()
    ctx.database.announces.get_announces.assert_called_once()
