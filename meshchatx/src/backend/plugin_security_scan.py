# SPDX-License-Identifier: 0BSD

"""Heuristic security assessment for plugin packages and Sideband scripts."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from meshchatx.src.backend.plugin_permissions import (
    collect_network_endpoints,
    declared_permission_ids,
    extract_urls_from_text,
    normalize_network_mode,
    requires_network_fetch,
)
from meshchatx.src.backend.plugin_signature import SignatureInfo

_JS_EVAL_RE = re.compile(r"\beval\s*\(")
_JS_FUNCTION_CTOR_RE = re.compile(r"\bnew\s+Function\s*\(")
_JS_ATOB_RE = re.compile(r"\batob\s*\(")
_JS_DOC_WRITE_RE = re.compile(r"\bdocument\.write\s*\(")
_PY_EVAL_RE = re.compile(r"\beval\s*\(")
_PY_EXEC_RE = re.compile(r"\bexec\s*\(")
_PY_SUBPROCESS_RE = re.compile(r"\bsubprocess\b")
_PY_SOCKET_RE = re.compile(r"\bsocket\b")
_PY_REQUESTS_RE = re.compile(r"\brequests\b|\burllib\.request\b")
_SCAN_EXTENSIONS = frozenset(
    {".js", ".mjs", ".json", ".wasm", ".ts", ".go", ".py", ".wat"}
)


@dataclass
class SecurityFinding:
    id: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "severity": self.severity, "message": self.message}


@dataclass
class SecurityAssessment:
    risk_level: str = "low"
    score: int = 0
    findings: list[SecurityFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "score": self.score,
            "findings": [item.to_dict() for item in self.findings],
        }


def assess_plugin(
    manifest: dict[str, Any],
    directory: str = "",
    embedded: dict[str, bytes] | None = None,
    signature: SignatureInfo | None = None,
) -> SecurityAssessment:
    signature = signature or SignatureInfo()
    findings: list[SecurityFinding] = []
    score = 0

    def add(finding_id: str, severity: str, message: str, points: int) -> None:
        nonlocal score
        findings.append(
            SecurityFinding(id=finding_id, severity=severity, message=message)
        )
        score += points

    if not str(manifest.get("id") or "").strip():
        add("missing-id", "high", "plugin manifest is missing an id", 40)
    if signature.present and not signature.valid:
        add(
            "invalid-signature",
            "high",
            "plugin signature is present but invalid",
            50,
        )

    declared = declared_permission_ids(manifest)
    network_mode = normalize_network_mode(
        (manifest.get("permissions") or {}).get("network")
    )
    endpoints = collect_network_endpoints(manifest, directory) if directory else []
    if embedded:
        for _path, data in embedded.items():
            for url in extract_urls_from_text(data.decode("utf-8", errors="ignore")):
                if url not in endpoints:
                    endpoints.append(url)

    if network_mode == "fetch" and not signature.valid:
        add(
            "unsigned-network",
            "warn",
            "unsigned plugin requests outbound network access",
            20,
        )
    if len(declared) >= 6:
        add("many-permissions", "warn", "plugin requests many permissions", 10)
    if len(endpoints) > 15:
        add(
            "many-endpoints",
            "warn",
            "plugin references many external network endpoints",
            10,
        )
    if network_mode == "fetch":
        declared_endpoints: set[str] = set()
        network = manifest.get("network") or {}
        if isinstance(network, dict):
            for endpoint in network.get("endpoints") or []:
                if isinstance(endpoint, str):
                    declared_endpoints.add(endpoint.strip())
                    declared_endpoints.update(extract_urls_from_text(endpoint))
        if any(
            (ep.startswith("http://") or ep.startswith("https://"))
            and ep not in declared_endpoints
            for ep in endpoints
        ):
            add(
                "undeclared-network",
                "warn",
                "plugin code references network endpoints not declared in the manifest",
                15,
            )

    for pattern in _scan_suspicious_code(directory, embedded):
        add(pattern[0], pattern[1], pattern[2], pattern[3])

    if requires_network_fetch(manifest, endpoints) and not declared:
        add(
            "implicit-network",
            "warn",
            "plugin appears to use network endpoints without declared permissions",
            10,
        )

    risk = "low"
    if score >= 50:
        risk = "high"
    elif score >= 20:
        risk = "medium"
    return SecurityAssessment(risk_level=risk, score=score, findings=findings)


def assess_sideband_script(
    path: str,
    source: str | bytes,
    signature: SignatureInfo | None = None,
) -> SecurityAssessment:
    signature = signature or SignatureInfo()
    if isinstance(source, bytes):
        text = source.decode("utf-8", errors="ignore")
    else:
        text = source
    findings: list[SecurityFinding] = []
    score = 0

    def add(finding_id: str, severity: str, message: str, points: int) -> None:
        nonlocal score
        findings.append(
            SecurityFinding(id=finding_id, severity=severity, message=message)
        )
        score += points

    add(
        "sideband-full-access",
        "high",
        "Sideband plugins run in-process with full host access",
        40,
    )
    if signature.present and not signature.valid:
        add(
            "invalid-signature",
            "high",
            f"Sideband script signature is invalid for {os.path.basename(path)}",
            50,
        )
    if _PY_EVAL_RE.search(text):
        add("py-eval", "high", "Sideband script uses eval()", 25)
    if _PY_EXEC_RE.search(text):
        add("py-exec", "high", "Sideband script uses exec()", 25)
    if _PY_SUBPROCESS_RE.search(text):
        add("py-subprocess", "warn", "Sideband script references subprocess", 15)
    if _PY_SOCKET_RE.search(text):
        add("py-socket", "warn", "Sideband script references socket", 15)
    if _PY_REQUESTS_RE.search(text):
        add(
            "py-network",
            "warn",
            "Sideband script references outbound HTTP libraries",
            15,
        )

    risk = "low"
    if score >= 50:
        risk = "high"
    elif score >= 20:
        risk = "medium"
    return SecurityAssessment(risk_level=risk, score=score, findings=findings)


def _scan_suspicious_code(
    directory: str,
    embedded: dict[str, bytes] | None,
) -> list[tuple[str, str, str, int]]:
    seen: set[str] = set()
    out: list[tuple[str, str, str, int]] = []

    def record(finding_id: str, severity: str, message: str, points: int) -> None:
        if finding_id in seen:
            return
        seen.add(finding_id)
        out.append((finding_id, severity, message, points))

    def scan_text(path: str, text: str) -> None:
        lower_path = path.lower()
        if lower_path.endswith(".py"):
            if _PY_EVAL_RE.search(text):
                record("py-eval", "high", "plugin Python uses eval()", 25)
            if _PY_EXEC_RE.search(text):
                record("py-exec", "high", "plugin Python uses exec()", 25)
            if _PY_SUBPROCESS_RE.search(text):
                record(
                    "py-subprocess", "warn", "plugin Python references subprocess", 15
                )
            if _PY_SOCKET_RE.search(text):
                record("py-socket", "warn", "plugin Python references socket", 15)
            return
        if _JS_EVAL_RE.search(text):
            record("js-eval", "high", "plugin JavaScript uses eval()", 25)
        if _JS_FUNCTION_CTOR_RE.search(text):
            record(
                "js-function-ctor",
                "warn",
                "plugin JavaScript uses the Function constructor",
                15,
            )
        if _JS_ATOB_RE.search(text):
            record(
                "js-atob",
                "warn",
                "plugin JavaScript uses atob() which may decode obfuscated payloads",
                10,
            )
        if _JS_DOC_WRITE_RE.search(text):
            record(
                "js-document-write",
                "warn",
                "plugin JavaScript uses document.write()",
                10,
            )

    if embedded:
        for path, data in embedded.items():
            scan_text(path, data.decode("utf-8", errors="ignore"))
    if directory and os.path.isdir(directory):
        for root, _dirs, files in os.walk(directory):
            for name in files:
                path = os.path.join(root, name)
                _, ext = os.path.splitext(name.lower())
                if ext not in _SCAN_EXTENSIONS:
                    continue
                try:
                    with open(path, "rb") as handle:
                        data = handle.read(2_000_000)
                except OSError:
                    continue
                scan_text(path, data.decode("utf-8", errors="ignore"))
    return out
