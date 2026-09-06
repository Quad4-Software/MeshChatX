# SPDX-License-Identifier: 0BSD

"""Oracle: demo mode blocks HTTP mutations outside the allowlist."""

from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.demo_mode import (
    DEMO_HTTP_MUTATION_ALLOWLIST,
    DEMO_READONLY_CODE,
    demo_http_mutation_allowed,
)
from tests.backend.demo_http_support import build_test_aio_app


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/lxmf-messages/send"),
        ("POST", "/api/v1/identities/create"),
        ("DELETE", "/api/v1/lxmf-messages/aa"),
        ("PATCH", "/api/v1/server/security"),
        ("POST", "/api/v1/lxmf/propagation-node/sync"),
        ("POST", "/api/v1/lxmf/propagation-node/stop-sync"),
    ],
)
@pytest.mark.asyncio
async def test_demo_mode_blocks_disallowed_mutations(mock_app, method, path):
    mock_app.demo_mode = True
    mock_app.current_context.running = True
    mock_app.config.auth_enabled.set(False)
    aio_app = build_test_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        response = await client.request(method, path, json={})
        assert response.status == 403
        body = await response.json()
        assert body.get("code") == DEMO_READONLY_CODE


@pytest.mark.asyncio
async def test_demo_mode_status_includes_flags(mock_app):
    mock_app.demo_mode = True
    mock_app.current_context.running = True
    mock_app._network_ready = True
    payload = mock_app._startup_status_payload()
    assert payload["demo_mode"] is True


@given(
    suffix=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=0,
        max_size=24,
    ),
)
@settings(max_examples=40, deadline=None)
def test_demo_http_mutation_fuzz_rejects_unknown_paths(suffix):
    path = f"/api/v1/lxmf-messages/send{suffix}"
    if path in DEMO_HTTP_MUTATION_ALLOWLIST:
        return
    assert demo_http_mutation_allowed("POST", path) is False


def test_allowlist_is_explicit_set():
    assert "/api/v1/auth/login" in DEMO_HTTP_MUTATION_ALLOWLIST
    assert "/api/v1/lxmf-messages/send" not in DEMO_HTTP_MUTATION_ALLOWLIST
