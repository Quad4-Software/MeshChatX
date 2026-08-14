# SPDX-License-Identifier: 0BSD

"""New backend clearnet fetches must be listed here and gated by privacy mode.

Do not add a file to KNOWN_CLEARNET_FETCH_FILES until it calls
ensure_outbound_http_allowed, http_url_guard, or _require_outbound_http
(or is the RNS HTTPInterface, which is mesh transport, not app clearnet).
"""

from pathlib import Path

BACKEND_ROOT = Path("meshchatx/src/backend")

FETCH_MARKERS = (
    "aiohttp.ClientSession",
    "httpx.Client(",
    "httpx.AsyncClient(",
    "urllib.request.urlopen",
    "urllib.request.Request(",
)

KNOWN_CLEARNET_FETCH_FILES = frozenset(
    {
        "data/interfaces/HTTPInterface.py",
        "map_manager.py",
        "repository_server_manager.py",
        "translator_handler.py",
    },
)

MESH_TRANSPORT_FETCH_FILES = frozenset(
    {
        "data/interfaces/HTTPInterface.py",
    },
)

PRIVACY_GATE_MARKERS = (
    "ensure_outbound_http_allowed",
    "http_url_guard",
    "_require_outbound_http",
    "OutboundHttpBlockedError",
)


def _rel(path: Path) -> str:
    return str(path.relative_to(BACKEND_ROOT)).replace("\\", "/")


def test_new_backend_clearnet_fetches_are_allowlisted():
    found: set[str] = set()
    for path in BACKEND_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in FETCH_MARKERS):
            found.add(_rel(path))
    assert found == set(KNOWN_CLEARNET_FETCH_FILES), (
        "New backend httpx/urllib/aiohttp client usage must call "
        "ensure_outbound_http_allowed or http_url_guard, then be added to "
        "KNOWN_CLEARNET_FETCH_FILES. Extra: "
        f"{sorted(found - KNOWN_CLEARNET_FETCH_FILES)}. Missing from disk: "
        f"{sorted(KNOWN_CLEARNET_FETCH_FILES - found)}"
    )


def test_allowlisted_app_fetches_mention_a_privacy_gate():
    for rel in sorted(KNOWN_CLEARNET_FETCH_FILES - MESH_TRANSPORT_FETCH_FILES):
        text = (BACKEND_ROOT / rel).read_text(encoding="utf-8")
        if any(marker in text for marker in PRIVACY_GATE_MARKERS):
            continue
        # Route-gated helpers: the HTTP route must still call the gate.
        assert rel in {
            "map_manager.py",
            "repository_server_manager.py",
            "translator_handler.py",
        }, f"{rel} opens a clearnet socket without a privacy-mode or URL guard"
