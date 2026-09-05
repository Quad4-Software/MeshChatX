# SPDX-License-Identifier: 0BSD

"""Parse Reticulum [interfaces] config text into a list of interface dicts."""

from __future__ import annotations

import logging
from typing import Any

import RNS.vendor.configobj

_log = logging.getLogger("meshchatx.interface_config")


class InterfaceConfigParser:
    """Turn INI-style interface config into a list of named dicts."""

    @staticmethod
    def parse(text: str) -> list[dict[str, Any]]:
        raw_lines = text.splitlines()
        normalized = [line.strip() for line in raw_lines]

        if "[interfaces]" not in normalized:
            raw_lines.insert(0, "[interfaces]")

        try:
            config = RNS.vendor.configobj.ConfigObj(raw_lines)
        except Exception as exc:
            _log.warning("ConfigObj parse failed, using fallback parser: %s", exc)
            return InterfaceConfigParser._fallback_parse(raw_lines)

        section = config.get("interfaces", {})
        if not section:
            return []

        result: list[dict[str, Any]] = []
        for name, body in section.items():
            if not isinstance(body, dict):
                _log.warning(
                    "Skipping invalid interface %s: expected dict, got %s",
                    name,
                    type(body),
                )
                continue
            entry = dict(body)
            entry["name"] = name
            result.append(entry)
        return result

    @staticmethod
    def _fallback_parse(lines: list[str]) -> list[dict[str, Any]]:
        """Minimal INI walker used when ConfigObj cannot parse the text."""
        interfaces: list[dict[str, Any]] = []
        iface_name: str | None = None
        iface_body: dict[str, Any] = {}
        nested_name: str | None = None
        nested_body: dict[str, Any] | None = None

        def flush_nested() -> None:
            nonlocal nested_name, nested_body
            if nested_name is not None and nested_body is not None:
                iface_body[nested_name] = nested_body
            nested_name = None
            nested_body = None

        def flush_iface() -> None:
            nonlocal iface_name, iface_body
            if iface_name is not None:
                interfaces.append(dict(iface_body))
            iface_name = None
            iface_body = {}

        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower() == "[interfaces]":
                continue

            if line.startswith("[[[") and line.endswith("]]]"):
                flush_nested()
                nested_name = line[3:-3].strip()
                nested_body = {}
                continue

            if line.startswith("[[") and line.endswith("]]"):
                flush_nested()
                flush_iface()
                iface_name = line[2:-2].strip()
                iface_body = {"name": iface_name}
                continue

            if "=" in line and iface_name is not None:
                key, value = line.split("=", 1)
                target = nested_body if nested_body is not None else iface_body
                target[key.strip()] = value.strip()

        flush_nested()
        flush_iface()
        return interfaces
