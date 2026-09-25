#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""License policy gate for distributed artifacts.

Fails on strong-copyleft / non-commercial licenses in backend (Python) or
frontend (Node) dependency trees. Warns on ambiguous or missing license
metadata so reviews catch new entries early.
"""

from __future__ import annotations

import re
import sys

from meshchatx.src.backend.licenses_collector import build_licenses_payload

# Strong copyleft / restrictive licenses not allowed in distributed builds.
# Matching is token-based on normalized license strings.
_DENY_PATTERNS = (
    "agpl",
    "affero",
    "gpl-1.0",
    "gpl-2.0",
    "gpl-3.0",
    "gnu general public license",
    "gplv",
    "sspl",
    "server side public license",
    "busl",
    "business source",
    "elastic license",
    "commons clause",
    "noncommercial",
    "non-commercial",
    "cc-by-nc",
    "cc by-nc",
    "no derivatives",
    "cc-by-nd",
)

# Licenses that are fine but worth surfacing once for awareness.
_WARN_PATTERNS = ("lgpl", "lesser general public", "mpl", "epl", "cddl")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _term_verdict(term: str) -> str | None:
    norm = _norm(term).strip("() ")
    for pat in _DENY_PATTERNS:
        if pat in norm:
            return "denied"
    for pat in _WARN_PATTERNS:
        if pat in norm:
            return "warn"
    return None


def _classify(license_name: str) -> str | None:
    norm = _norm(license_name)
    if not norm or norm in ("-", "unknown", "none"):
        return "unknown"
    # SPDX-style expressions: "A OR B" means any alternative is acceptable,
    # "A AND B" means all apply. Evaluate each OR branch; a single clean
    # branch makes the expression acceptable.
    denied = warned = clean = False
    for branch in re.split(r"\bor\b", license_name, flags=re.IGNORECASE):
        # Within a branch, every AND operand applies - deny if any is denied.
        operands = re.split(r"\band\b", branch, flags=re.IGNORECASE)
        verdicts = [_term_verdict(op) for op in operands]
        if "denied" in verdicts:
            denied = True
        elif "warn" in verdicts:
            warned = True
        else:
            clean = True
    if denied and not clean:
        return "denied"
    if warned:
        return "warn"
    return None


def main() -> int:
    payload = build_licenses_payload()
    denied: list[str] = []
    warned: list[str] = []
    unknown: list[str] = []

    for section in ("backend", "frontend"):
        for row in payload.get(section) or []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", "?"))
            version = str(row.get("version", "?"))
            license_name = str(row.get("license", "-"))
            verdict = _classify(license_name)
            entry = f"{section}:{name} {version} [{license_name}]"
            if verdict == "denied":
                denied.append(entry)
            elif verdict == "warn":
                warned.append(entry)
            elif verdict == "unknown":
                unknown.append(entry)

    for entry in warned:
        print(f"WARN copyleft-adjacent license: {entry}")
    for entry in unknown:
        print(f"WARN license metadata missing: {entry}")
    if denied:
        for entry in denied:
            print(f"DENIED license: {entry}")
        print(f"license-check: {len(denied)} denied license(s) found")
        return 1
    print(
        f"license-check: ok "
        f"({len(warned)} weak-copyleft, {len(unknown)} unknown, 0 denied)",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
