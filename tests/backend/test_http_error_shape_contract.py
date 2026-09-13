# SPDX-License-Identifier: 0BSD

"""Contract test: HTTP error responses go through http/errors.py helpers.

Raw web.json_response({...}, status=4xx/5xx) calls in route modules
bypass the canonical {"error", "code", "message"} shape. Flag them so
new handlers adopt the helpers instead of ad-hoc payloads.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROUTES_ROOT = _REPO_ROOT / "meshchatx" / "src" / "backend" / "http"

_CALL_RE = re.compile(r"web\.json_response\s*\(")
_ERROR_KEY_RE = re.compile(r"[\"'](?:error|message)[\"']\s*:")
_ERROR_STATUS_RE = re.compile(r"status\s*=\s*(?:4\d\d|5\d\d)")


def _call_region(text: str, open_paren: int) -> str:
    """Return text of a call from its opening paren to the matching close."""
    depth = 0
    for i in range(open_paren, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren : i + 1]
    return text[open_paren:]


def _raw_error_responses() -> list[str]:
    violations: list[str] = []
    for path in sorted(_ROUTES_ROOT.rglob("*.py")):
        if path.name in ("errors.py", "db_availability.py"):
            continue
        text = path.read_text(encoding="utf-8")
        for m in _CALL_RE.finditer(text):
            region = _call_region(text, m.end() - 1)
            if _ERROR_KEY_RE.search(region) and _ERROR_STATUS_RE.search(region):
                line = text.count("\n", 0, m.start()) + 1
                violations.append(f"{path.relative_to(_REPO_ROOT)}:{line}")
    return violations


def test_route_error_responses_use_shared_helpers():
    violations = _raw_error_responses()
    assert not violations, (
        "Raw web.json_response error payloads found. Use the helpers in "
        "meshchatx.src.backend.http.errors (http_bad_request, "
        "http_forbidden, http_not_found, http_error, ...) which emit the "
        "canonical {error, code, message} shape:\n" + "\n".join(violations)
    )
