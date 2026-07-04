# SPDX-License-Identifier: 0BSD

"""Shared runtime helpers for HTTP JSON response contract tests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import RNS

from meshchatx.meshchat import ReticulumMeshChat


@dataclass(frozen=True)
class HttpJsonContract:
    method: str
    path: str
    schema: dict
    match_info: dict[str, str] = field(default_factory=dict)
    query: dict[str, str] = field(default_factory=dict)
    allow_statuses: tuple[int, ...] = (200,)
    alt_schemas: tuple[dict, ...] = ()


class _Query:
    def __init__(self, data: dict[str, str] | None = None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


def make_contract_app(temp_dir: str, mock_identity: MagicMock) -> ReticulumMeshChat:
    return ReticulumMeshChat(
        identity=mock_identity,
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )


def make_minimal_identity() -> MagicMock:
    mock_id = MagicMock(spec=RNS.Identity)
    mock_id.hash = b"test_hash_32_bytes_long_01234567"
    mock_id.hexhash = mock_id.hash.hex()
    key = b"public_key_bytes_32_chars_long!!"
    mock_id.get_private_key.return_value = key
    mock_id.get_public_key.return_value = key
    return mock_id


def bootstrap_contract_app(app: ReticulumMeshChat) -> ReticulumMeshChat:
    ctx = app.current_context
    if ctx is None:
        return app
    lxmf_dest = MagicMock()
    lxmf_dest.hexhash = "cc" * 16
    ctx.local_lxmf_destination = lxmf_dest
    if getattr(app, "message_router", None) is not None:
        prop = MagicMock()
        prop.hexhash = "dd" * 16
        app.message_router.propagation_destination = prop
    if getattr(ctx, "telephone_manager", None) is not None:
        telephone = getattr(ctx.telephone_manager, "telephone", None)
        if telephone is not None:
            dest = MagicMock()
            dest.hexhash = "ee" * 16
            telephone.destination = dest
    return app


def find_route_handler(app: ReticulumMeshChat, path: str, method: str):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def build_request(
    *,
    match_info: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
) -> MagicMock:
    request = MagicMock()
    request.match_info = match_info or {}
    request.query = _Query(query)
    return request


async def invoke_json_contract(
    app: ReticulumMeshChat,
    contract: HttpJsonContract,
) -> tuple[int, Any]:
    handler = find_route_handler(app, contract.path, contract.method)
    if handler is None:
        raise AssertionError(
            f"No handler for {contract.method} {contract.path}",
        )
    request = build_request(
        match_info=contract.match_info,
        query=contract.query,
    )
    if contract.method in {"POST", "PATCH", "PUT", "DELETE"}:
        request.json = AsyncMock(return_value={})
    response = await handler(request)
    status = response.status
    body = json.loads(response.body)
    return status, body
