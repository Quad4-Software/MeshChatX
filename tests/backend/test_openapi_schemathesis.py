# SPDX-License-Identifier: 0BSD

"""Optional Schemathesis live run against MESHCHAT_OPENAPI_BASE_URL.

Skip unless MESHCHAT_OPENAPI_LIVE=1. Point at a running MeshChatX UI HTTP bind
(for example http://127.0.0.1:8000). Does not invent mesh traffic.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("schemathesis")

import schemathesis

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OPENAPI = _REPO_ROOT / "openapi" / "meshchatx-ui-core.yaml"

_LIVE = os.environ.get("MESHCHAT_OPENAPI_LIVE") == "1"
_BASE = (os.environ.get("MESHCHAT_OPENAPI_BASE_URL") or "http://127.0.0.1:8000").rstrip(
    "/"
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _LIVE,
        reason="Set MESHCHAT_OPENAPI_LIVE=1 and MESHCHAT_OPENAPI_BASE_URL to fuzz",
    ),
]


@pytest.fixture
def api_schema():
    return schemathesis.openapi.from_path(str(_OPENAPI))


schema = schemathesis.pytest.from_fixture("api_schema")


@schema.parametrize()
def test_openapi_core_schemathesis(case):
    # Auth mutators need a real password and CSRF cookie. Limit generation to
    # safe GETs unless MESHCHAT_OPENAPI_MUTATE=1.
    if (
        case.method.upper() != "GET"
        and os.environ.get("MESHCHAT_OPENAPI_MUTATE") != "1"
    ):
        pytest.skip("mutating OpenAPI cases require MESHCHAT_OPENAPI_MUTATE=1")
    response = case.call(base_url=_BASE)
    case.validate_response(response)
