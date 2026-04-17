# SPDX-License-Identifier: 0BSD

import json
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import LXMF
import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat

PR_IDLE = LXMF.LXMRouter.PR_IDLE
PR_PATH_REQUESTED = LXMF.LXMRouter.PR_PATH_REQUESTED
PR_PATH_TIMEOUT = LXMF.LXMRouter.PR_PATH_TIMEOUT
PR_RECEIVING = LXMF.LXMRouter.PR_RECEIVING
PR_COMPLETE = LXMF.LXMRouter.PR_COMPLETE
PR_FAILED = LXMF.LXMRouter.PR_FAILED


class FakePropagationRouter:
    PR_IDLE = PR_IDLE
    PR_PATH_REQUESTED = PR_PATH_REQUESTED
    PR_COMPLETE = PR_COMPLETE
    PR_FAILED = PR_FAILED

    def __init__(self, local_hash: bytes):
        self.outbound_propagation_node = None
        self.propagation_destination = SimpleNamespace(
            hash=local_hash,
            hexhash=local_hash.hex(),
        )
        self.propagation_transfer_state = self.PR_IDLE
        self.propagation_transfer_progress = 0.0
        self.propagation_transfer_last_result = 0
        self.request_messages_calls = 0
        self.propagation_node = False

    def set_outbound_propagation_node(self, destination_hash: bytes):
        self.outbound_propagation_node = destination_hash

    def get_outbound_propagation_node(self):
        return self.outbound_propagation_node

    def request_messages_from_propagation_node(self, _identity):
        self.request_messages_calls += 1
        if self.outbound_propagation_node is None:
            self.propagation_transfer_state = self.PR_FAILED
            self.propagation_transfer_progress = 0.0
            return

        if RNS.Transport.has_path(self.outbound_propagation_node):
            self.propagation_transfer_state = self.PR_COMPLETE
            self.propagation_transfer_progress = 1.0
            self.propagation_transfer_last_result = 3
            return

        RNS.Transport.request_path(self.outbound_propagation_node)
        self.propagation_transfer_state = self.PR_PATH_REQUESTED
        self.propagation_transfer_progress = 0.0


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def integration_app(temp_dir):
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("meshchatx.src.backend.meshchat_utils.LXMRouter") as mock_utils_router,
    ):
        mock_rns.return_value.transport_enabled.return_value = False
        mock_utils_router.PR_IDLE = PR_IDLE
        mock_utils_router.PR_PATH_REQUESTED = PR_PATH_REQUESTED
        mock_utils_router.PR_PATH_TIMEOUT = PR_PATH_TIMEOUT
        mock_utils_router.PR_RECEIVING = PR_RECEIVING
        mock_utils_router.PR_COMPLETE = PR_COMPLETE
        mock_utils_router.PR_FAILED = PR_FAILED

        app = ReticulumMeshChat(
            identity=RNS.Identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        fake_router = FakePropagationRouter(local_hash=b"\x11" * 16)
        app.current_context.message_router = fake_router

        with patch.object(
            app,
            "send_config_to_websocket_clients",
            return_value=None,
        ):
            yield app, fake_router


def _route_handler(app, path, method="GET"):
    return next(r.handler for r in app.get_routes() if r.path == path and r.method == method)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_remote_propagation_sync_transitions_path_requested_to_complete(integration_app):
    app, fake_router = integration_app
    remote_hash = b"\x22" * 16
    fake_router.set_outbound_propagation_node(remote_hash)

    known_paths = set()
    request_count = {}

    def has_path(destination_hash):
        return bytes(destination_hash) in known_paths

    def request_path(destination_hash):
        key = bytes(destination_hash)
        request_count[key] = request_count.get(key, 0) + 1
        if request_count[key] >= 2:
            known_paths.add(key)

    sync_handler = _route_handler(app, "/api/v1/lxmf/propagation-node/sync")
    status_handler = _route_handler(app, "/api/v1/lxmf/propagation-node/status")

    with (
        patch("meshchatx.meshchat.RNS.Transport.has_path", side_effect=has_path),
        patch("meshchatx.meshchat.RNS.Transport.request_path", side_effect=request_path),
    ):
        first_sync = await sync_handler(None)
        assert first_sync.status == 200

        first_status = json.loads((await status_handler(None)).body)["propagation_node_status"]
        assert first_status["state"] == "path_requested"

        second_sync = await sync_handler(None)
        assert second_sync.status == 200

        second_status = json.loads((await status_handler(None)).body)["propagation_node_status"]
        assert second_status["state"] == "complete"
        assert second_status["progress"] == 100.0
        assert fake_router.request_messages_calls >= 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_local_preferred_propagation_sync_completes_without_remote_lookup(integration_app):
    app, fake_router = integration_app
    local_hash = fake_router.propagation_destination.hash
    fake_router.set_outbound_propagation_node(local_hash)

    sync_handler = _route_handler(app, "/api/v1/lxmf/propagation-node/sync")
    status_handler = _route_handler(app, "/api/v1/lxmf/propagation-node/status")

    with (
        patch("meshchatx.meshchat.RNS.Transport.has_path", return_value=False),
        patch("meshchatx.meshchat.RNS.Transport.request_path"),
    ):
        response = await sync_handler(None)
        assert response.status == 200

        status_data = json.loads((await status_handler(None)).body)["propagation_node_status"]
        assert status_data["state"] == "complete"
        assert status_data["progress"] == 100.0
        assert fake_router.request_messages_calls == 0
