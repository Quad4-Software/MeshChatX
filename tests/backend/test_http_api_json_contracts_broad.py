# SPDX-License-Identifier: 0BSD

"""Broad JSON Schema contract tests for GET /api/v1 HTTP handlers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.backend.api_json_contract_schemas import assert_matches_schema
from tests.backend.http_api_contract_helpers import load_route_fixture
from tests.backend.http_api_contract_runtime import (
    HttpJsonContract,
    bootstrap_contract_app,
    invoke_json_contract,
    make_contract_app,
    make_minimal_identity,
)
from tests.backend.http_api_response_registry import (
    HTTP_JSON_GET_CONTRACTS,
    is_excluded_json_get_route,
    registered_get_paths,
)

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "http_api_routes.json"


@pytest.fixture(scope="module")
def temp_dir():
    import shutil
    import tempfile

    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture(scope="module")
def mock_rns_minimal():
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True
        yield make_minimal_identity()


@pytest.fixture(scope="module")
def contract_app(mock_rns_minimal, temp_dir):
    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("psutil.Process") as mock_process,
        patch("psutil.net_io_counters") as mock_net_io,
        patch("importlib.metadata.version", return_value="1.2.3"),
        patch("meshchatx.meshchat.LXST") as mock_lxst,
        patch("threading.Thread"),
    ):
        mock_lxst.__version__ = "1.2.3"
        mock_proc_instance = mock_process.return_value
        mock_proc_instance.memory_info.return_value.rss = 1024
        mock_proc_instance.memory_info.return_value.vms = 2048
        mock_proc_instance.net_connections.return_value = []
        mock_net_instance = mock_net_io.return_value
        mock_net_instance.bytes_sent = 0
        mock_net_instance.bytes_recv = 0
        mock_net_instance.packets_sent = 0
        mock_net_instance.packets_recv = 0
        app = bootstrap_contract_app(make_contract_app(temp_dir, mock_rns_minimal))
        yield app


def _validate_body(contract: HttpJsonContract, status: int, body) -> None:
    schemas = (contract.schema, *contract.alt_schemas)
    if status in contract.allow_statuses:
        for schema in schemas:
            try:
                assert_matches_schema(body, schema)
                return
            except Exception:
                continue
        raise AssertionError(
            f"{contract.method} {contract.path} status {status} body did not match "
            f"any allowed schema: {json.dumps(body)[:500]}",
        )
    raise AssertionError(
        f"{contract.method} {contract.path} returned unexpected status {status}: "
        f"{json.dumps(body)[:500]}",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "contract",
    HTTP_JSON_GET_CONTRACTS,
    ids=lambda c: f"{c.method} {c.path}",
)
async def test_get_json_response_matches_schema(contract_app, contract: HttpJsonContract):
    status, body = await invoke_json_contract(contract_app, contract)
    _validate_body(contract, status, body)


def test_every_json_get_route_is_registered_or_excluded():
    routes = load_route_fixture(_FIXTURE)
    get_api = [r["path"] for r in routes if r["method"] == "GET" and r["path"].startswith("/api/v1")]
    registered = registered_get_paths()
    uncovered = []
    for path in get_api:
        if path in registered:
            continue
        if is_excluded_json_get_route(path):
            continue
        uncovered.append(path)
    assert not uncovered, (
        "GET /api/v1 routes missing from HTTP JSON contract registry "
        f"(add schema or exclude): {uncovered}"
    )
