# SPDX-License-Identifier: 0BSD

import json
from pathlib import Path
from typing import Any

_BUNDLED = Path(__file__).resolve().parent / "data" / "community_interfaces.json"


class CommunityInterfacesManager:
    """Load suggested interface presets from bundled data or public/community_interfaces.json."""

    def __init__(self, public_override_path: str | None = None):
        self._public_override_path = public_override_path
        self.interfaces = self._load_raw()

    def _candidate_paths(self) -> list[Path]:
        paths: list[Path] = []
        if self._public_override_path:
            paths.append(Path(self._public_override_path))
        paths.append(_BUNDLED)
        return paths

    def _load_raw(self) -> list[dict[str, Any]]:
        for path in self._candidate_paths():
            if not path.is_file():
                continue
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            raw = doc.get("interfaces", doc) if isinstance(doc, dict) else doc
            if not isinstance(raw, list):
                continue
            normalized = [self._normalize_entry(x) for x in raw if isinstance(x, dict)]
            if normalized:
                return normalized
        return []

    @staticmethod
    def _normalize_entry(item: dict[str, Any]) -> dict[str, Any]:
        out = dict(item)
        iface_type = out.get("type")
        if iface_type == "BackboneInterface":
            remote = (out.get("remote") or out.get("target_host") or "").strip()
            if remote:
                out["remote"] = remote
                out["target_host"] = remote
            tp = out.get("target_port")
            if tp is not None and tp != "":
                out["target_port"] = int(tp)
        elif iface_type == "I2PInterface":
            peers = out.get("i2p_peers") or []
            if isinstance(peers, list) and peers:
                cleaned = [str(p).strip() for p in peers if str(p).strip()]
                out["i2p_peers"] = cleaned
                if cleaned:
                    out["target_host"] = cleaned[0]
            if "target_port" not in out:
                out["target_port"] = None
        elif iface_type == "TCPClientInterface":
            th = (out.get("target_host") or "").strip()
            if th:
                out["target_host"] = th
            tp = out.get("target_port")
            if tp is not None and tp != "":
                out["target_port"] = int(tp)
        return out

    async def get_interfaces(self) -> list[dict[str, Any]]:
        return [{**iface, "online": None, "last_check": 0} for iface in self.interfaces]
