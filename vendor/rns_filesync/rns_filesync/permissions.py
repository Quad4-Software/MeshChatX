"""rngit-style access control for FileSync.

Rules use permission:target (for example r:all, w:<hash>).
When ACL enforcement is active, access is denied by default.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterable

from rns_filesync.constants import VALID_PERMISSIONS

TGT_ALL = "all"
TGT_NONE = "none"

PERM_MAP = {
    "r": ("read",),
    "read": ("read",),
    "w": ("write",),
    "write": ("write",),
    "d": ("delete",),
    "delete": ("delete",),
    "rw": ("read", "write"),
    "readwrite": ("read", "write"),
    "rwd": ("read", "write", "delete"),
    "adm": ("read", "write", "delete"),
    "admin": ("read", "write", "delete"),
}

TGT_ALL_ALIASES = frozenset({"all", "a", "everyone", "*"})
TGT_NONE_ALIASES = frozenset({"none", "n", "nobody"})


def _normalize_hash(value: bytes | str) -> str:
    if isinstance(value, bytes):
        return value.hex()
    return value.lower().replace(":", "").strip()


class PermissionStore:
    """Thread-safe ACL using rngit-style permission:target rules."""

    def __init__(
        self,
        entries: dict[str, list[str]] | None = None,
        *,
        enforce: bool | None = None,
    ):
        self._lock = threading.RLock()
        self._aliases: dict[str, str] = {}
        self._blocked: set[str] = set()
        # permission -> set of targets (hash hex, ALL, NONE)
        self._rules: dict[str, set[str]] = {
            "read": set(),
            "write": set(),
            "delete": set(),
        }
        self._admin: set[str] = set()
        self._enforce = False if enforce is None else bool(enforce)
        if entries:
            for identity_hash, perms in entries.items():
                self.grant(identity_hash, perms)
            if enforce is None:
                self._enforce = True

    @property
    def enabled(self) -> bool:
        """True when ACL enforcement is active (deny by default)."""
        with self._lock:
            return self._enforce

    def set_alias(self, name: str, identity_hash: str) -> None:
        with self._lock:
            self._aliases[name.strip().lower()] = _normalize_hash(identity_hash)

    def set_aliases(self, aliases: dict[str, str]) -> None:
        for name, identity_hash in aliases.items():
            self.set_alias(str(name), str(identity_hash))

    def block(self, identity_hash: str | bytes) -> None:
        with self._lock:
            self._blocked.add(_normalize_hash(identity_hash))

    def set_blocked(self, hashes: Iterable[str | bytes]) -> None:
        for value in hashes:
            self.block(value)

    def _resolve_target(self, target: str) -> str | None:
        target = target.strip()
        if not target:
            return None
        lower = target.lower()
        if lower in self._aliases:
            return self._aliases[lower]
        if lower in TGT_ALL_ALIASES:
            return TGT_ALL
        if lower in TGT_NONE_ALIASES:
            return TGT_NONE
        cleaned = _normalize_hash(target)
        if len(cleaned) == 32:
            try:
                bytes.fromhex(cleaned)
            except ValueError:
                return None
            return cleaned
        return None

    def parse_rule(self, rule: str) -> tuple[tuple[str, ...], str] | None:
        """Parse perm:target into permission names and resolved target."""
        rule = rule.strip()
        if not rule or rule.startswith("#"):
            return None
        if ":" not in rule:
            return None
        perm_s, target_s = rule.split(":", 1)
        perms = PERM_MAP.get(perm_s.strip().lower())
        if not perms:
            return None
        with self._lock:
            target = self._resolve_target(target_s)
        if target is None:
            return None
        return perms, target

    def add_rule(self, rule: str) -> bool:
        parsed = self.parse_rule(rule)
        if not parsed:
            return False
        perms, target = parsed
        perm_key = rule.split(":", 1)[0].strip().lower()
        with self._lock:
            self._enforce = True
            if perm_key in ("adm", "admin"):
                self._admin.add(target)
            for perm in perms:
                self._rules[perm].add(target)
        return True

    def add_rules(self, rules: Iterable[str]) -> int:
        loaded = 0
        for rule in rules:
            if self.add_rule(rule):
                loaded += 1
        return loaded

    def grant(self, identity_hash: str, perms: Iterable[str]) -> list[str]:
        """Legacy helper: grant named permissions to one identity hash."""
        valid = []
        for perm in perms:
            p = str(perm).strip().lower()
            if p in VALID_PERMISSIONS and p not in valid:
                valid.append(p)
        if not valid:
            return []
        key = _normalize_hash(identity_hash)
        if key in TGT_ALL_ALIASES or key == "*":
            key = TGT_ALL
        with self._lock:
            self._enforce = True
            for perm in valid:
                self._rules[perm].add(key)
        return valid

    def set_permissions(self, identity_hash: str, perms: Iterable[str]) -> list[str]:
        return self.grant(identity_hash, perms)

    def load_allowed_text(self, text: str) -> int:
        loaded = 0
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                for part in [p.strip() for p in line.split(",") if p.strip()]:
                    if self.add_rule(part):
                        loaded += 1
            elif self._load_legacy_line(line):
                loaded += 1
        return loaded

    def _load_legacy_line(self, line: str) -> bool:
        parts = line.split()
        if len(parts) < 2:
            return False
        identity_hash = parts[0]
        perms = [p.strip() for p in parts[1].split(",")]
        return bool(self.grant(identity_hash, perms))

    def load_file(self, path: str) -> int:
        if not os.path.isfile(path):
            return 0
        if os.access(path, os.X_OK):
            # Executable .allowed: run and parse stdout (rngit behavior).
            import subprocess

            try:
                result = subprocess.run(
                    [path],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                return self.load_allowed_text(result.stdout or "")
            except Exception:
                return 0
        with open(path, encoding="utf-8") as handle:
            return self.load_allowed_text(handle.read())

    def load_access_value(self, value: str | list | None) -> int:
        if value is None:
            return 0
        if isinstance(value, list):
            text = ", ".join(str(v) for v in value)
        else:
            text = str(value)
        return self.load_allowed_text(text)

    def check(self, identity_hash: bytes | str, permission: str) -> bool:
        permission = permission.lower()
        if permission not in VALID_PERMISSIONS:
            return False
        key = _normalize_hash(identity_hash)
        with self._lock:
            if key in self._blocked:
                return False
            if not self._enforce:
                return True
            targets = self._rules.get(permission, set())
            if TGT_NONE in targets:
                return False
            if TGT_ALL in targets or key in targets:
                return True
            if TGT_ALL in self._admin or key in self._admin:
                return True
            return False

    def can_connect(self, identity_hash: bytes | str) -> bool:
        key = _normalize_hash(identity_hash)
        with self._lock:
            if key in self._blocked:
                return False
            if not self._enforce:
                return True
            if TGT_ALL in self._admin or key in self._admin:
                return True
            for targets in self._rules.values():
                if TGT_NONE in targets:
                    continue
                if TGT_ALL in targets or key in targets:
                    return True
            return False

    def get(self, identity_hash: bytes | str) -> list[str]:
        return [p for p in ("read", "write", "delete") if self.check(identity_hash, p)]

    def as_dict(self) -> dict[str, list[str]]:
        with self._lock:
            return {perm: sorted(targets) for perm, targets in self._rules.items()}
