# SPDX-License-Identifier: 0BSD

"""Plugin permission catalog, grant normalization, and network endpoint scanning."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import urlparse

KNOWN_HOOKS = frozenset(
    {
        "announce.received",
        "rns.link.event",
    },
)

KNOWN_MANAGERS = frozenset(
    {
        "destinationPath.read",
        "debugLog.read",
        "bugReport.status",
        "bugReport.listCollectors",
        "bugReport.listReports",
        "bugReport.deleteReport",
        "bugReport.clearReports",
        "bugReport.preview",
        "bugReport.send",
        "bugReport.startCollector",
        "bugReport.stopCollector",
        "bugReport.announce",
        "bugReport.setCollectorName",
        "bugReport.listIssues",
        "bugReport.getIssue",
        "bugReport.recordLocal",
        "bugReport.setIssueStatus",
        "bugReport.listPendingSends",
        "bugReport.enqueueSend",
        "bugReport.cancelPendingSend",
        "rnsLink.open",
        "rnsLink.identify",
        "rnsLink.request",
        "rnsLink.send",
        "rnsLink.close",
    },
)

KNOWN_STORAGE = frozenset({"isolated", "none"})
KNOWN_NETWORK = frozenset({"none", "fetch"})
KNOWN_UI = frozenset({"none", "sandboxed-html"})

_URL_IN_TEXT_RE = re.compile(r"""https?://[^\s"'<>\\)]+""")
_SCHEME_HOST_RE = re.compile(
    r"https?://([a-z0-9][-a-z0-9.]*(?:\.[a-z0-9][-a-z0-9.]*)+)",
    re.IGNORECASE,
)
_SCAN_EXTENSIONS = frozenset(
    {".js", ".mjs", ".json", ".wasm", ".ts", ".go", ".wat", ".html", ".htm"}
)
_LOOPBACK_OR_UNSPECIFIED_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
    },
)


def permission_id_for_hook(hook: str) -> str:
    return f"hooks:{hook}"


def permission_id_for_manager(manager: str) -> str:
    return f"managers:{manager}"


def permission_id_for_storage(storage: str) -> str:
    return f"storage:{storage}"


def permission_id_for_network(network: str) -> str:
    return f"network:{network}"


def permission_id_for_ui(ui: str) -> str:
    return f"ui:{ui}"


def normalize_network_mode(value: Any) -> str:
    if value is None or value == "" or value == "none":
        return "none"
    if value in ("fetch", "http", "https", "outbound"):
        return "fetch"
    if isinstance(value, str):
        return "fetch"
    return "none"


def normalize_ui_modes(value: Any) -> list[str]:
    if value is None or value == "" or value == "none":
        return []
    if value == "sandboxed-html":
        return ["sandboxed-html"]
    if isinstance(value, list):
        modes: list[str] = []
        for item in value:
            if item == "sandboxed-html":
                modes.append("sandboxed-html")
        return modes
    return []


def declared_permission_ids(manifest: dict[str, Any]) -> list[str]:
    permissions = manifest.get("permissions") or {}
    if not isinstance(permissions, dict):
        return []
    ids: list[str] = []
    for hook in permissions.get("hooks") or []:
        if isinstance(hook, str) and hook.strip():
            ids.append(permission_id_for_hook(hook.strip()))
    for manager in permissions.get("managers") or []:
        if isinstance(manager, str) and manager.strip():
            ids.append(permission_id_for_manager(manager.strip()))
    storage = permissions.get("storage") or "none"
    if isinstance(storage, str) and storage not in ("", "none"):
        ids.append(permission_id_for_storage(storage.strip()))
    network = normalize_network_mode(permissions.get("network"))
    if network != "none":
        ids.append(permission_id_for_network(network))
    for ui_mode in normalize_ui_modes(permissions.get("ui")):
        ids.append(permission_id_for_ui(ui_mode))
    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in ids:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def validate_declared_permissions(manifest: dict[str, Any]) -> None:
    permissions = manifest.get("permissions") or {}
    if permissions and not isinstance(permissions, dict):
        raise ValueError("permissions must be an object")
    if not isinstance(permissions, dict):
        return
    for hook in permissions.get("hooks") or []:
        if not isinstance(hook, str) or hook not in KNOWN_HOOKS:
            raise ValueError(f"unknown hook permission: {hook!r}")
    for manager in permissions.get("managers") or []:
        if not isinstance(manager, str) or manager not in KNOWN_MANAGERS:
            raise ValueError(f"unknown manager permission: {manager!r}")
    storage = permissions.get("storage", "none")
    if storage is not None and storage not in KNOWN_STORAGE:
        raise ValueError(f"unknown storage permission: {storage!r}")
    network = permissions.get("network", "none")
    if network is not None and normalize_network_mode(network) not in KNOWN_NETWORK:
        raise ValueError(f"unknown network permission: {network!r}")
    ui = permissions.get("ui", "none")
    if ui is not None and ui != "none":
        modes = normalize_ui_modes(ui)
        if not modes and ui not in KNOWN_UI:
            raise ValueError(f"unknown ui permission: {ui!r}")
        for mode in modes:
            if mode not in KNOWN_UI:
                raise ValueError(f"unknown ui permission: {mode!r}")
    network_block = manifest.get("network")
    if network_block is not None:
        if not isinstance(network_block, dict):
            raise ValueError("network must be an object")
        endpoints = network_block.get("endpoints")
        if endpoints is not None and not isinstance(endpoints, list):
            raise ValueError("network.endpoints must be an array")


def normalize_granted_permissions(
    declared: list[str],
    granted: list[str] | None,
) -> list[str]:
    declared_set = set(declared)
    if granted is None:
        return list(declared)
    selected: list[str] = []
    seen: set[str] = set()
    for item in granted:
        if not isinstance(item, str):
            continue
        if item not in declared_set or item in seen:
            continue
        seen.add(item)
        selected.append(item)
    return selected


def granted_allows_hook(granted: list[str] | None, hook: str) -> bool:
    if granted is None:
        return True
    return permission_id_for_hook(hook) in granted


def granted_allows_manager(granted: list[str] | None, manager: str) -> bool:
    if granted is None:
        return True
    return permission_id_for_manager(manager) in granted


def granted_allows_network_fetch(granted: list[str] | None) -> bool:
    if granted is None:
        return True
    return permission_id_for_network("fetch") in granted


def granted_allows_storage(granted: list[str] | None) -> bool:
    if granted is None:
        return True
    return permission_id_for_storage("isolated") in granted


def _normalize_endpoint(value: str) -> str:
    return value.strip().rstrip(".,;)]}\"'")


def _is_http_url(value: str) -> bool:
    lower = value.lower()
    return lower.startswith("http://") or lower.startswith("https://")


def _hostname_is_loopback_or_unspecified(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.strip().lower().strip("[]")
    return host in _LOOPBACK_OR_UNSPECIFIED_HOSTS


def _is_external_http_url(value: str) -> bool:
    if not _is_http_url(value):
        return False
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
    except (ValueError, UnicodeError):
        return True
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return True
    if _hostname_is_loopback_or_unspecified(hostname):
        return False
    return True


def _should_scan_network_file(path: str) -> bool:
    _, ext = os.path.splitext(path.lower())
    return ext in _SCAN_EXTENSIONS


def extract_urls_from_text(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _URL_IN_TEXT_RE.findall(text):
        endpoint = _normalize_endpoint(match)
        if not endpoint or not _is_external_http_url(endpoint):
            continue
        if endpoint in seen:
            continue
        seen.add(endpoint)
        out.append(endpoint)
    return out


def _host_root(endpoint: str) -> str | None:
    match = _SCHEME_HOST_RE.search(endpoint)
    if not match:
        return None
    return f"https://{match.group(1).lower()}/"


def collect_network_endpoints(manifest: dict[str, Any], plugin_dir: str) -> list[str]:
    seen: set[str] = set()
    manifest_endpoints: list[str] = []
    scanned: list[str] = []

    def add(value: str, *, require_http: bool, declared: bool) -> None:
        value = _normalize_endpoint(value)
        if not value:
            return
        if require_http and not _is_http_url(value):
            return
        if require_http and not _is_external_http_url(value):
            return
        if value in seen:
            return
        seen.add(value)
        if declared:
            manifest_endpoints.append(value)
        else:
            scanned.append(value)

    network = manifest.get("network") or {}
    if isinstance(network, dict):
        for endpoint in network.get("endpoints") or []:
            if not isinstance(endpoint, str):
                continue
            urls = extract_urls_from_text(endpoint)
            if not urls:
                add(endpoint, require_http=False, declared=True)
                continue
            for url in urls:
                add(url, require_http=False, declared=True)

    if plugin_dir and os.path.isdir(plugin_dir):
        for root, _dirs, files in os.walk(plugin_dir):
            for name in files:
                path = os.path.join(root, name)
                if not _should_scan_network_file(path):
                    continue
                try:
                    with open(path, "rb") as handle:
                        data = handle.read(2_000_000)
                except OSError:
                    continue
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                for url in extract_urls_from_text(text):
                    add(url, require_http=True, declared=False)

    for endpoint in list(manifest_endpoints) + list(scanned):
        root = _host_root(endpoint)
        if root:
            add(root, require_http=True, declared=False)

    scanned.sort()
    return manifest_endpoints + scanned


def requires_network_fetch(manifest: dict[str, Any], endpoints: list[str]) -> bool:
    permissions = manifest.get("permissions") or {}
    network = normalize_network_mode(
        permissions.get("network") if isinstance(permissions, dict) else None,
    )
    if network == "fetch":
        return True
    return bool(endpoints)


def permission_label_key(permission_id: str) -> str:
    return f"plugins.permissions.{permission_id.replace(':', '.')}"


def serialize_granted(granted: list[str] | None) -> str:
    return json.dumps(list(granted or []), separators=(",", ":"))


def deserialize_granted(raw: str | None) -> list[str] | None:
    if raw is None or raw == "":
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    return [item for item in data if isinstance(item, str)]
