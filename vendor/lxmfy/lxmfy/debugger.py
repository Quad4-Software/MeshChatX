"""Message send/receive debugger for LXMFy.

Diagnoses why a bot cannot send or peers cannot receive.
Produces privacy-friendly reports that can be saved and shared.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .__version__ import __version__ as LXMFY_VERSION
from .colors import (
    print_check,
    print_dim,
    print_error,
    print_header,
    print_info,
    print_kv,
    print_section,
    print_success,
    print_warning,
)
from .reticulum_config import (
    discover_user_reticulum_config_dir,
    is_isolated_reticulum_dir,
    resolve_reticulum_config_dir,
)

logger = logging.getLogger(__name__)

HASH_LEN_BYTES = 16


@dataclass
class CheckResult:
    """One diagnostic check result."""

    name: str
    status: str
    detail: str = ""
    hint: str | None = None
    category: str = "general"

    @property
    def ok(self) -> bool:
        return self.status in {"ok", "info"}


@dataclass
class DestinationProbe:
    """Path/identity probe for a destination hash."""

    destination: str
    valid_hash: bool
    identity_known: bool = False
    has_path: bool = False
    hops: int | None = None
    next_hop: str | None = None
    path_requested: bool = False
    path_waited: bool = False
    path_found_after_wait: bool = False
    app_data: str | None = None
    notes: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self, *, privacy: bool = True) -> dict[str, Any]:
        data = {
            "destination": self.destination,
            "valid_hash": self.valid_hash,
            "identity_known": self.identity_known,
            "has_path": self.has_path,
            "hops": self.hops,
            "next_hop": self.next_hop,
            "path_requested": self.path_requested,
            "path_waited": self.path_waited,
            "path_found_after_wait": self.path_found_after_wait,
            "app_data": self.app_data,
            "notes": list(self.notes),
            "hints": list(self.hints),
            "timeline": list(self.timeline),
        }
        if privacy:
            data["destination"] = redact_hash(self.destination)
            if self.next_hop:
                data["next_hop"] = redact_hash(self.next_hop)
            if self.app_data:
                data["app_data"] = redact_display_name(self.app_data)
        return data


@dataclass
class DoctorReport:
    """Full connectivity doctor report."""

    checks: list[CheckResult] = field(default_factory=list)
    probe: DestinationProbe | None = None
    tips: list[str] = field(default_factory=list)
    reticulum_config_dir: str | None = None
    bot_hash: str | None = None
    generated_at: str = ""
    lxmfy_version: str = ""
    privacy: bool = True
    send_blockers: list[str] = field(default_factory=list)
    receive_blockers: list[str] = field(default_factory=list)
    verdict: str = "unknown"
    next_steps: list[str] = field(default_factory=list)
    compare: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        redacted_dir = (
            redact_path(self.reticulum_config_dir)
            if self.privacy and self.reticulum_config_dir
            else self.reticulum_config_dir
        )
        checks_out = []
        for c in self.checks:
            item = _check_to_dict(c)
            if self.privacy:
                item["detail"] = redact_sensitive_text(str(item.get("detail") or ""))
                if item.get("hint"):
                    item["hint"] = redact_sensitive_text(str(item["hint"]))
            checks_out.append(item)
        return {
            "generated_at": self.generated_at,
            "lxmfy_version": self.lxmfy_version,
            "privacy": self.privacy,
            "reticulum_config_dir": redacted_dir,
            "bot_hash": redact_hash(self.bot_hash) if self.privacy else self.bot_hash,
            "checks": checks_out,
            "probe": self.probe.to_dict(privacy=self.privacy) if self.probe else None,
            "send_blockers": self.send_blockers,
            "receive_blockers": self.receive_blockers,
            "verdict": self.verdict,
            "next_steps": list(self.next_steps),
            "compare": self.compare,
            "tips": self.tips,
            "ok": all(c.status != "fail" for c in self.checks),
            "warnings": sum(1 for c in self.checks if c.status == "warn"),
            "failures": sum(1 for c in self.checks if c.status == "fail"),
        }


CATEGORY_ORDER = [
    "environment",
    "instance",
    "disk",
    "network",
    "announce",
    "send",
    "receive",
    "destination",
    "general",
]

CATEGORY_TITLES = {
    "environment": "Environment / OS",
    "instance": "Shared Instance vs Owned",
    "disk": "Disk Permissions",
    "network": "Network / Interfaces",
    "announce": "Announce",
    "send": "Send Pipeline",
    "receive": "Receive Readiness",
    "destination": "Destination Probe",
    "general": "Other",
}

COMMON_TIPS = [
    "Can't send: destination Identity unknown means the peer has not announced "
    "(or you have no path). Ask them to announce, or wait after request_path.",
    "Can't send: has_path=False with identity known usually means your interfaces "
    "are up but there is no route. Check shared Reticulum / transport peers.",
    "Can't receive: peers need your LXMF delivery hash and a path to you. "
    "Confirm announce_enabled and that you announced after interfaces came online.",
    "Digest rejected / AuthenticationError: bot is colliding with NomadNet/Columba "
    "on the shared RNS instance. Use the discovered user Reticulum config, or an "
    "isolated config with share_instance=No.",
    "Public TCP/backbone entrypoints: keep opportunistic_sending=True (default). "
    "DIRECT (link-based) delivery often fails through those gateways.",
    "Propagation fallback without a prop node will fail. Set propagation_node, "
    "enable autopeer_propagation, or disable propagation_fallback_enabled.",
    "Share the saved report file (lxmfy-debug-*.txt or .json). It is privacy "
    "redacted by default (home paths and full hashes truncated).",
]


STATUS_RANK = {"fail": 0, "warn": 1, "info": 2, "ok": 3}


def sort_checks_by_severity(checks: list[CheckResult]) -> list[CheckResult]:
    """Sort checks fail-first within their existing relative order."""
    return sorted(
        checks,
        key=lambda c: (
            STATUS_RANK.get(c.status, 9),
            CATEGORY_ORDER.index(c.category) if c.category in CATEGORY_ORDER else 99,
        ),
    )


def build_verdict(
    checks: list[CheckResult],
    *,
    send_blockers: list[str],
    receive_blockers: list[str],
    probe: DestinationProbe | None = None,
) -> tuple[str, list[str]]:
    """Derive a short verdict and concrete next steps from checks."""
    fails = [c for c in checks if c.status == "fail"]
    warns = [c for c in checks if c.status == "warn"]
    by_name = {c.name: c for c in checks}
    steps: list[str] = []

    if send_blockers and receive_blockers:
        verdict = "cannot_send_or_receive"
    elif send_blockers:
        verdict = "cannot_send"
    elif receive_blockers:
        verdict = "cannot_receive"
    elif probe and probe.valid_hash and not probe.identity_known:
        verdict = "cannot_send"
        steps.append(
            "Peer identity unknown. Ask them to announce, then: "
            "lxmfy debug probe <hash> --request-path --wait 30",
        )
    elif probe and probe.valid_hash and not probe.has_path:
        verdict = "path_missing"
        steps.append(
            "No path to peer. Ensure shared transport / interfaces, then "
            "request path and wait.",
        )
    elif warns and not fails:
        verdict = "likely_ok_with_warnings"
    elif not fails:
        verdict = "likely_ok"
    else:
        verdict = "issues_detected"

    # Concrete steps from specific failures
    if (
        by_name.get("interfaces_online")
        and by_name["interfaces_online"].status == "fail"
    ):
        steps.append(
            "Bring at least one Reticulum interface online before debugging send/receive.",
        )
    if by_name.get("instance_mode") and by_name["instance_mode"].status == "fail":
        steps.append(
            "Set share_instance=No on isolated bot configs (digest rejection with NomadNet/Columba).",
        )
    if by_name.get("announce_enabled") and by_name["announce_enabled"].status == "fail":
        steps.append(
            "Enable announce_enabled so peers can discover your delivery hash.",
        )
    client = by_name.get("shared_instance_role")
    if client and client.status == "warn":
        steps.append(
            "You are a LocalClientInterface client of another RNS process. "
            "Check that host process (NomadNet/rnsd) has working radios/TCP.",
        )
    if (
        by_name.get("propagation_fallback")
        and by_name["propagation_fallback"].status == "warn"
    ):
        steps.append(
            "Configure propagation_node or enable autopeer_propagation, or disable propagation_fallback.",
        )
    if (
        by_name.get("opportunistic_sending")
        and by_name["opportunistic_sending"].status == "warn"
    ):
        steps.append(
            "Set opportunistic_sending=True for public TCP/backbone entrypoints.",
        )
    if by_name.get("identity_known") and by_name["identity_known"].status == "fail":
        steps.append(
            "lxmfy debug probe <hash> --request-path --wait 30 after the peer announces.",
        )
    if by_name.get("has_path") and by_name["has_path"].status == "fail":
        steps.append(
            "Fix routing/path: shared network + online interfaces + peer announce.",
        )

    # De-dupe while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for s in steps:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    if not uniq and verdict == "likely_ok":
        uniq.append(
            "No hard blockers found. If messaging still fails, run: lxmfy debug probe <peer> --request-path --wait 30",
        )
    return verdict, uniq[:6]


def _usernames() -> list[str]:
    names: list[str] = []
    for key in ("USER", "USERNAME", "LOGNAME"):
        val = os.environ.get(key)
        if val and len(val) > 1:
            names.append(val)
    try:
        import getpass

        gp = getpass.getuser()
        if gp and len(gp) > 1:
            names.append(gp)
    except Exception:
        logger.debug("getuser probe failed", exc_info=True)
    return sorted(set(names), key=len, reverse=True)


def redact_path(path: str | None) -> str:
    """Replace home directory prefixes and usernames for shareable reports."""
    if not path:
        return ""
    text = str(path)
    for home in _home_prefixes():
        if text.startswith(home):
            text = "~" + text[len(home) :]
            break
    for user in _usernames():
        text = text.replace(f"/{user}/", "/<user>/")
        text = text.replace(f"\\{user}\\", "\\<user>\\")
        if text.endswith(f"/{user}"):
            text = text[: -len(user)] + "<user>"
        if text.endswith(f"\\{user}"):
            text = text[: -len(user)] + "<user>"
    return text


def _home_prefixes() -> list[str]:
    homes: list[str] = []
    expanded = os.path.expanduser("~")
    if expanded and expanded != "~":
        homes.append(expanded)
    for key in ("HOME", "USERPROFILE"):
        env_home = os.environ.get(key)
        if env_home:
            homes.append(env_home)
    return sorted(set(homes), key=len, reverse=True)


def redact_hash(value: str | None, *, keep: int = 8) -> str:
    """Truncate a hex hash for privacy-friendly sharing."""
    if not value:
        return ""
    cleaned = normalize_destination_hex(value)
    if len(cleaned) <= keep + 4:
        return cleaned
    return f"{cleaned[:keep]}…{cleaned[-4:]}"


def redact_display_name(value: str) -> str:
    """Replace display names with length-only placeholder."""
    if not value:
        return ""
    return f"<display_name len={len(value)}>"


def redact_sensitive_text(text: str | None) -> str:
    """Redact home paths and long hex hashes inside free-form detail text."""
    if text is None:
        return ""
    out = str(text)
    for home in _home_prefixes():
        out = out.replace(home, "~")
    for user in _usernames():
        out = out.replace(f"/{user}/", "/<user>/")
        out = out.replace(f"\\{user}\\", "\\<user>\\")
    import re

    def _sub(match: re.Match[str]) -> str:
        h = match.group(0)
        if len(h) >= 32:
            return redact_hash(h)
        return h

    return re.sub(r"\b[0-9a-fA-F]{32,}\b", _sub, out)


def _check_to_dict(check: CheckResult) -> dict[str, Any]:
    return {
        "name": check.name,
        "status": check.status,
        "detail": check.detail,
        "hint": check.hint,
        "category": check.category,
    }


def normalize_destination_hex(destination: str) -> str:
    """Normalize a destination hash string (strip separators, lowercase)."""
    return (
        destination.strip().lower().replace(":", "").replace("-", "").removeprefix("0x")
    )


def parse_destination_hash(destination: str) -> bytes | None:
    """Parse a hex destination hash to bytes, or None if invalid."""
    cleaned = normalize_destination_hex(destination)
    try:
        raw = bytes.fromhex(cleaned)
    except ValueError:
        return None
    expected = _hash_len()
    if len(raw) != expected:
        return None
    return raw


def _hash_len() -> int:
    try:
        import RNS

        return RNS.Reticulum.TRUNCATED_HASHLENGTH // 8
    except Exception:
        return HASH_LEN_BYTES


def _package_version(name: str) -> str:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return "unknown"


def _probe_dir_access(path: str) -> dict[str, Any]:
    """Check existence and read/write access for a directory."""
    info: dict[str, Any] = {
        "path": path,
        "exists": os.path.isdir(path),
        "readable": False,
        "writable": False,
        "can_create_file": False,
        "error": None,
    }
    try:
        if not info["exists"]:
            parent = os.path.dirname(path) or "."
            info["readable"] = os.access(parent, os.R_OK)
            info["writable"] = os.access(parent, os.W_OK)
            return info
        info["readable"] = os.access(path, os.R_OK)
        info["writable"] = os.access(path, os.W_OK)
        if info["writable"]:
            fd, tmp = tempfile.mkstemp(prefix=".lxmfy_dbg_", dir=path)
            os.close(fd)
            os.unlink(tmp)
            info["can_create_file"] = True
    except OSError as e:
        info["error"] = str(e)
        info["can_create_file"] = False
    return info


def _probe_file_access(path: str) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": path,
        "exists": os.path.isfile(path),
        "readable": False,
        "writable": False,
        "error": None,
    }
    try:
        if info["exists"]:
            info["readable"] = os.access(path, os.R_OK)
            info["writable"] = os.access(path, os.W_OK)
        else:
            parent = os.path.dirname(path) or "."
            info["writable"] = os.access(parent, os.W_OK)
    except OSError as e:
        info["error"] = str(e)
    return info


class Debugger:
    """Diagnose LXMF send/receive connectivity problems."""

    def __init__(
        self,
        *,
        reticulum_config_dir: str | None = None,
        config_path: str | None = None,
        bot: Any | None = None,
        privacy: bool = True,
    ):
        """Create a debugger.

        Args:
            reticulum_config_dir: Explicit Reticulum config directory.
            config_path: Bot config directory (identity, announce state).
            bot: Optional running LXMFBot instance to introspect.
            privacy: Redact paths/hashes in reports (default True).

        """
        self.bot = bot
        self.privacy = privacy
        self.config_path = os.path.abspath(
            config_path
            or (getattr(bot, "config_path", None) if bot else None)
            or os.path.join(os.getcwd(), "config"),
        )
        if bot and getattr(bot, "reticulum_config_dir", None):
            self.reticulum_config_dir = os.path.abspath(bot.reticulum_config_dir)
        elif reticulum_config_dir:
            self.reticulum_config_dir = os.path.abspath(
                os.path.expanduser(reticulum_config_dir),
            )
        else:
            self.reticulum_config_dir = resolve_reticulum_config_dir(
                None,
                self.config_path,
            )
        self._reticulum_ready = False
        self._storage_path = self._resolve_storage_path()

    def _resolve_storage_path(self) -> str:
        if self.bot and getattr(self.bot, "config", None):
            return os.path.abspath(
                os.path.expanduser(self.bot.config.storage_path),
            )
        return os.path.abspath(os.path.join(os.getcwd(), "data"))

    def ensure_reticulum(self, loglevel: int | None = None) -> bool:
        """Initialize Reticulum if needed."""
        if self._reticulum_ready:
            return True
        if self.bot and not getattr(self.bot.config, "test_mode", False):
            try:
                import RNS

                if RNS.Reticulum.get_instance() is not None:
                    self._reticulum_ready = True
                    return True
            except Exception:
                logger.debug("shared Reticulum probe failed", exc_info=True)

        try:
            import RNS

            level = loglevel if loglevel is not None else RNS.LOG_ERROR
            try:
                RNS.Reticulum(
                    configdir=self.reticulum_config_dir,
                    loglevel=level,
                )
            except OSError as e:
                if "reinitialise" not in str(e).lower():
                    raise
            self._reticulum_ready = True
            return True
        except Exception:
            logger.exception("Failed to initialize Reticulum")
            return False

    def check_environment(self) -> list[CheckResult]:
        """OS, Python, and package versions."""
        results: list[CheckResult] = []
        os_detail = f"{platform.system()} {platform.release()} ({platform.machine()})"
        results.append(
            CheckResult(
                name="os",
                status="ok",
                detail=os_detail,
                category="environment",
            ),
        )
        results.append(
            CheckResult(
                name="python",
                status="ok",
                detail=platform.python_version(),
                category="environment",
            ),
        )
        results.append(
            CheckResult(
                name="lxmfy",
                status="ok",
                detail=LXMFY_VERSION,
                category="environment",
            ),
        )
        rns_ver = _package_version("rns")
        lxmf_ver = _package_version("lxmf")
        results.append(
            CheckResult(
                name="rns",
                status="ok" if rns_ver != "unknown" else "warn",
                detail=rns_ver,
                category="environment",
            ),
        )
        results.append(
            CheckResult(
                name="lxmf",
                status="ok" if lxmf_ver != "unknown" else "warn",
                detail=lxmf_ver,
                category="environment",
            ),
        )
        results.append(
            CheckResult(
                name="cwd",
                status="info",
                detail=redact_path(os.getcwd()) if self.privacy else os.getcwd(),
                category="environment",
            ),
        )
        return results

    def check_instance(self) -> list[CheckResult]:
        """Shared RNS instance vs owned/isolated bot config."""
        results: list[CheckResult] = []
        discovered = discover_user_reticulum_config_dir()
        config_file = os.path.join(self.reticulum_config_dir, "config")
        exists = os.path.isfile(config_file)
        isolated = is_isolated_reticulum_dir(
            self.reticulum_config_dir,
            self.config_path,
        )
        share = _read_share_instance(config_file) if exists else None

        results.append(
            CheckResult(
                name="reticulum_config",
                status="ok" if exists else "fail",
                detail=redact_path(self.reticulum_config_dir)
                if self.privacy
                else self.reticulum_config_dir,
                hint=None
                if exists
                else "No config file found. Point --config / "
                "LXMFY_RETICULUM_CONFIG_DIR at a valid RNS config.",
                category="instance",
            ),
        )

        if discovered:
            same = os.path.abspath(discovered) == os.path.abspath(
                self.reticulum_config_dir,
            )
            results.append(
                CheckResult(
                    name="user_reticulum_config",
                    status="ok" if same else "info",
                    detail=(
                        (redact_path(discovered) if self.privacy else discovered)
                        + (" (selected)" if same else " (not selected)")
                    ),
                    category="instance",
                ),
            )
        else:
            results.append(
                CheckResult(
                    name="user_reticulum_config",
                    status="warn",
                    detail="none discovered",
                    hint="No ~/.reticulum / ~/.config/reticulum / "
                    "/etc/reticulum config. Bot may be isolated.",
                    category="instance",
                ),
            )

        # Clear owned vs shared labeling
        runtime_shared = None
        if self.ensure_reticulum():
            try:
                import RNS

                runtime_shared = bool(
                    getattr(RNS.Transport, "is_shared_instance", False),
                )
            except Exception:
                runtime_shared = None

        if isolated:
            if share in {None, "yes", "true", "1"}:
                mode = "owned_misconfigured"
                status = "fail"
                detail = (
                    f"owned/isolated config but share_instance="
                    f"{share or 'unset (defaults to Yes)'}"
                )
                hint = (
                    "Isolated bot configs must set share_instance=No or they "
                    "collide with NomadNet/Columba (digest sent was rejected)."
                )
            else:
                mode = "owned"
                status = "ok"
                detail = f"owned/isolated, share_instance={share or 'No'}"
                hint = None
        else:
            mode = "shared"
            status = "ok"
            detail = f"shared/user config, share_instance={share or 'default'}"
            hint = None

        results.append(
            CheckResult(
                name="instance_mode",
                status=status,
                detail=f"{mode}: {detail}",
                hint=hint,
                category="instance",
            ),
        )

        if runtime_shared is not None:
            results.append(
                CheckResult(
                    name="runtime_shared_instance",
                    status="info",
                    detail="yes (joined shared RNS)"
                    if runtime_shared
                    else "no (own process/instance)",
                    category="instance",
                ),
            )

        return results

    def check_disk_permissions(self) -> list[CheckResult]:
        """Verify config, storage, and Reticulum dirs are usable."""
        results: list[CheckResult] = []
        targets = [
            ("config_path", self.config_path, True),
            ("reticulum_config_dir", self.reticulum_config_dir, True),
            ("storage_path", self._storage_path, True),
        ]
        for name, path, need_write in targets:
            info = _probe_dir_access(path)
            show = redact_path(path) if self.privacy else path
            if not info["exists"]:
                parent_ok = info["writable"]
                results.append(
                    CheckResult(
                        name=name,
                        status="warn" if parent_ok else "fail",
                        detail=f"missing ({show}), parent_writable={parent_ok}",
                        hint=(
                            "Directory will be created on bot start if parent "
                            "is writable."
                            if parent_ok
                            else "Cannot create directory. Fix ownership/permissions."
                        ),
                        category="disk",
                    ),
                )
                continue

            if need_write and not info["can_create_file"]:
                results.append(
                    CheckResult(
                        name=name,
                        status="fail",
                        detail=(
                            f"{show} exists but not writable "
                            f"({info.get('error') or 'permission denied'})"
                        ),
                        hint="Fix directory ownership/permissions so the bot "
                        "can write identity, announce throttle, and queues.",
                        category="disk",
                    ),
                )
            else:
                results.append(
                    CheckResult(
                        name=name,
                        status="ok",
                        detail=(
                            f"{show} readable={info['readable']} "
                            f"writable={info['writable']}"
                        ),
                        category="disk",
                    ),
                )

        identity = os.path.join(self.config_path, "identity")
        id_info = _probe_file_access(identity)
        show_id = redact_path(identity) if self.privacy else identity
        if id_info["exists"]:
            results.append(
                CheckResult(
                    name="identity_file",
                    status="ok" if id_info["readable"] else "fail",
                    detail=(
                        f"present readable={id_info['readable']} "
                        f"writable={id_info['writable']}"
                    ),
                    hint=None
                    if id_info["readable"]
                    else f"Cannot read identity at {show_id}",
                    category="disk",
                ),
            )
        else:
            results.append(
                CheckResult(
                    name="identity_file",
                    status="info",
                    detail="absent (created on first bot run)",
                    category="disk",
                ),
            )

        announce_file = os.path.join(self.config_path, "announce")
        ann_info = _probe_file_access(announce_file)
        if ann_info["exists"] and not ann_info["writable"]:
            results.append(
                CheckResult(
                    name="announce_file",
                    status="fail",
                    detail="exists but not writable",
                    hint="Announce throttle file must be writable or announces "
                    "will fail after the first send.",
                    category="disk",
                ),
            )
        elif ann_info["exists"]:
            results.append(
                CheckResult(
                    name="announce_file",
                    status="ok",
                    detail="present and writable",
                    category="disk",
                ),
            )

        if self.bot and hasattr(self.bot, "get_landlock_status"):
            try:
                ll = self.bot.get_landlock_status()
                active = bool(ll.get("active"))
                results.append(
                    CheckResult(
                        name="landlock",
                        status="info" if active else "ok",
                        detail=(
                            f"active={active} supported={ll.get('supported')} "
                            f"enabled={ll.get('config_enabled')}"
                        ),
                        hint=(
                            "Landlock sandbox is active. Unexpected write paths "
                            "outside config/storage/reticulum will fail."
                            if active
                            else None
                        ),
                        category="disk",
                    ),
                )
            except Exception as e:
                results.append(
                    CheckResult(
                        name="landlock",
                        status="warn",
                        detail=str(e),
                        category="disk",
                    ),
                )

        return results

    def check_interfaces(self) -> list[CheckResult]:
        """Report Reticulum interface status (no hostnames/IPs)."""
        results: list[CheckResult] = []
        if not self.ensure_reticulum():
            return [
                CheckResult(
                    name="interfaces",
                    status="fail",
                    detail="Reticulum not initialized",
                    hint="Fix reticulum config and try again.",
                    category="network",
                ),
            ]

        try:
            import RNS

            interfaces = list(getattr(RNS.Transport, "interfaces", []) or [])
            if not interfaces:
                results.append(
                    CheckResult(
                        name="interfaces",
                        status="fail",
                        detail="no interfaces loaded",
                        hint="Add at least one enabled interface under "
                        "[interfaces] in your Reticulum config.",
                        category="network",
                    ),
                )
                return results

            online = 0
            type_counts: dict[str, list[bool]] = {}
            for iface in interfaces:
                name = str(getattr(iface, "name", type(iface).__name__))
                # Avoid leaking host/IP from interface names when possible
                safe_name = name
                if (
                    self.privacy
                    and any(ch.isdigit() for ch in name)
                    and ("." in name or ":" in name)
                ):
                    safe_name = f"iface_{len(type_counts)}"
                online_flag = bool(getattr(iface, "online", False))
                if online_flag:
                    online += 1
                itype = type(iface).__name__
                type_counts.setdefault(itype, []).append(online_flag)
                results.append(
                    CheckResult(
                        name=f"interface:{safe_name}",
                        status="ok" if online_flag else "warn",
                        detail=f"{itype} online={online_flag}",
                        hint=None
                        if online_flag
                        else "Interface offline. Check remote reachability "
                        "and that the interface is enabled.",
                        category="network",
                    ),
                )

            if online == 0:
                results.append(
                    CheckResult(
                        name="interfaces_online",
                        status="fail",
                        detail=f"0/{len(interfaces)} online",
                        hint="No online interfaces. The bot cannot send or "
                        "receive until at least one interface connects.",
                        category="network",
                    ),
                )
            else:
                results.append(
                    CheckResult(
                        name="interfaces_online",
                        status="ok",
                        detail=f"{online}/{len(interfaces)} online",
                        category="network",
                    ),
                )

            summary = ", ".join(
                f"{t}={sum(1 for x in flags if x)}/{len(flags)}"
                for t, flags in sorted(type_counts.items())
            )
            results.append(
                CheckResult(
                    name="interface_types",
                    status="info",
                    detail=summary,
                    category="network",
                ),
            )

            # Client-only shared instance is a common false "all green"
            only_local_client = (
                len(type_counts) == 1 and "LocalClientInterface" in type_counts
            )
            shared = bool(getattr(RNS.Transport, "is_shared_instance", False))
            if only_local_client or shared:
                results.append(
                    CheckResult(
                        name="shared_instance_role",
                        status="warn" if only_local_client else "info",
                        detail=(
                            "RNS client via LocalClientInterface only"
                            if only_local_client
                            else "joined shared RNS instance"
                        ),
                        hint=(
                            "Radios/TCP live in the host RNS process "
                            "(NomadNet, rnsd, Columba). If that host cannot "
                            "reach the mesh, this bot cannot either."
                            if only_local_client
                            else None
                        ),
                        category="network",
                    ),
                )
        except Exception as e:
            results.append(
                CheckResult(
                    name="interfaces",
                    status="fail",
                    detail=str(e),
                    category="network",
                ),
            )
        return results

    def check_announce(self, *, try_announce: bool = False) -> list[CheckResult]:
        """Announce configuration and optional live announce test."""
        results: list[CheckResult] = []
        enabled = True
        interval = 600
        if self.bot:
            enabled = bool(self.bot.config.announce_enabled)
            interval = int(self.bot.config.announce or 0)

        results.append(
            CheckResult(
                name="announce_enabled",
                status="ok" if enabled else "fail",
                detail=str(enabled),
                hint=None
                if enabled
                else "Peers cannot discover you. Set announce_enabled=True.",
                category="announce",
            ),
        )
        results.append(
            CheckResult(
                name="announce_interval",
                status="ok" if interval >= 300 or interval == 0 else "warn",
                detail=f"{interval}s",
                hint="Intervals under 300s can spam the network."
                if 0 < interval < 300
                else None,
                category="announce",
            ),
        )

        announce_path = os.path.join(self.config_path, "announce")
        if os.path.isfile(announce_path):
            try:
                with open(announce_path, encoding="utf-8") as f:
                    next_at = int(f.readline().strip() or "0")
                remaining = next_at - int(time.time())
                if remaining > 0:
                    detail = f"throttle active, next in ~{remaining}s"
                    status = "ok"
                else:
                    detail = "throttle elapsed (announce due)"
                    status = "info"
                results.append(
                    CheckResult(
                        name="announce_throttle",
                        status=status,
                        detail=detail,
                        category="announce",
                    ),
                )
            except Exception as e:
                results.append(
                    CheckResult(
                        name="announce_throttle",
                        status="warn",
                        detail=f"unreadable: {e}",
                        category="announce",
                    ),
                )
        else:
            results.append(
                CheckResult(
                    name="announce_throttle",
                    status="info",
                    detail="no throttle file yet (bot has not announced)",
                    hint="If the bot never announced, peers will not learn "
                    "your delivery hash.",
                    category="announce",
                ),
            )

        if try_announce:
            if not self.bot:
                results.append(
                    CheckResult(
                        name="announce_test",
                        status="warn",
                        detail="skipped (no live bot)",
                        hint="Run debugger against a running bot, or start "
                        "the bot so announce_now can be called.",
                        category="announce",
                    ),
                )
            elif not enabled:
                results.append(
                    CheckResult(
                        name="announce_test",
                        status="fail",
                        detail="skipped (announce_enabled=False)",
                        category="announce",
                    ),
                )
            elif not getattr(self.bot, "local", None):
                results.append(
                    CheckResult(
                        name="announce_test",
                        status="fail",
                        detail="no local LXMF destination (test_mode?)",
                        category="announce",
                    ),
                )
            else:
                try:
                    self.bot.announce_now(force=True)
                    results.append(
                        CheckResult(
                            name="announce_test",
                            status="ok",
                            detail="announce_now(force=True) completed",
                            category="announce",
                        ),
                    )
                except Exception as e:
                    results.append(
                        CheckResult(
                            name="announce_test",
                            status="fail",
                            detail=str(e),
                            hint="Announce failed. Check interfaces online and "
                            "disk write access to the announce throttle file.",
                            category="announce",
                        ),
                    )
        else:
            results.append(
                CheckResult(
                    name="announce_test",
                    status="info",
                    detail="not run (pass --announce-test to try live announce)",
                    category="announce",
                ),
            )

        return results

    def check_delivery_config(self) -> list[CheckResult]:
        """Report effective delivery knobs (bot config or framework defaults)."""
        from .config import BotConfig

        cfg = self.bot.config if self.bot else BotConfig()
        results: list[CheckResult] = []
        source = "live_bot" if self.bot else "defaults"
        results.append(
            CheckResult(
                name="delivery_config_source",
                status="info",
                detail=source,
                category="send",
            ),
        )
        results.append(
            CheckResult(
                name="opportunistic_sending",
                status="ok" if cfg.opportunistic_sending else "warn",
                detail=str(cfg.opportunistic_sending),
                hint=None
                if cfg.opportunistic_sending
                else "DIRECT often fails on public TCP/backbone. Prefer "
                "opportunistic_sending=True.",
                category="send",
            ),
        )
        results.append(
            CheckResult(
                name="direct_delivery_retries",
                status="info",
                detail=str(cfg.direct_delivery_retries),
                category="send",
            ),
        )
        has_prop = bool(
            cfg.propagation_node
            or cfg.autopeer_propagation
            or cfg.enable_propagation_node,
        )
        if cfg.propagation_fallback_enabled and not has_prop:
            results.append(
                CheckResult(
                    name="propagation_fallback",
                    status="warn",
                    detail="enabled but no prop node / autopeer",
                    hint="Configure propagation_node, enable "
                    "autopeer_propagation, or disable "
                    "propagation_fallback_enabled.",
                    category="send",
                ),
            )
        else:
            results.append(
                CheckResult(
                    name="propagation_fallback",
                    status="ok",
                    detail=(
                        f"enabled={cfg.propagation_fallback_enabled} "
                        f"has_source={has_prop}"
                    ),
                    category="send",
                ),
            )
        results.append(
            CheckResult(
                name="default_delivery_method",
                status="ok",
                detail=("OPPORTUNISTIC" if cfg.opportunistic_sending else "DIRECT"),
                category="send",
            ),
        )
        results.append(
            CheckResult(
                name="message_persistence",
                status="ok" if cfg.message_persistence_enabled else "warn",
                detail=str(cfg.message_persistence_enabled),
                hint=(
                    "Disabled: crash mid-send loses queued outbound messages."
                    if not cfg.message_persistence_enabled
                    else None
                ),
                category="send",
            ),
        )
        results.append(
            CheckResult(
                name="announce_enabled_config",
                status="ok" if cfg.announce_enabled else "fail",
                detail=str(cfg.announce_enabled),
                category="announce",
            ),
        )
        return results

    def check_storage_history(self) -> list[CheckResult]:
        """Read delivery_attempts / persisted_queue from disk without a live bot."""
        results: list[CheckResult] = []
        storage_dir = self._storage_path
        attempts_path = os.path.join(storage_dir, "delivery_attempts.json")
        queue_path = os.path.join(storage_dir, "persisted_queue.json")

        if self.bot and getattr(self.bot, "storage", None) is not None:
            try:
                attempts = self.bot.storage.get("delivery_attempts", {}) or {}
                persisted = self.bot.storage.get("persisted_queue", []) or []
                return self._format_storage_history(attempts, persisted, "live_storage")
            except Exception as e:
                results.append(
                    CheckResult(
                        name="storage_history",
                        status="warn",
                        detail=f"live storage read failed: {e}",
                        category="send",
                    ),
                )

        attempts: dict = {}
        persisted: list = []
        if os.path.isfile(attempts_path):
            try:
                with open(attempts_path, encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    attempts = raw
                else:
                    results.append(
                        CheckResult(
                            name="delivery_attempts_file",
                            status="warn",
                            detail="unexpected JSON type",
                            category="send",
                        ),
                    )
            except Exception as e:
                results.append(
                    CheckResult(
                        name="delivery_attempts_file",
                        status="warn",
                        detail=f"unreadable: {e}",
                        category="send",
                    ),
                )
        if os.path.isfile(queue_path):
            try:
                with open(queue_path, encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, list):
                    persisted = raw
                else:
                    results.append(
                        CheckResult(
                            name="persisted_queue_file",
                            status="warn",
                            detail="unexpected JSON type",
                            category="send",
                        ),
                    )
            except Exception as e:
                results.append(
                    CheckResult(
                        name="persisted_queue_file",
                        status="warn",
                        detail=f"unreadable: {e}",
                        category="send",
                    ),
                )

        if not os.path.isdir(storage_dir):
            results.append(
                CheckResult(
                    name="storage_history",
                    status="info",
                    detail="storage dir missing (bot may never have run here)",
                    category="send",
                ),
            )
            return results

        results.extend(
            self._format_storage_history(attempts, persisted, "disk"),
        )
        return results

    def _format_storage_history(
        self,
        attempts: dict,
        persisted: list,
        source: str,
    ) -> list[CheckResult]:
        results: list[CheckResult] = []
        if attempts:
            hot = sorted(
                attempts.items(),
                key=lambda kv: (
                    int(kv[1]) if str(kv[1]).isdigit() or isinstance(kv[1], int) else 0
                ),
                reverse=True,
            )[:8]
            parts = []
            for dest, n in hot:
                label = redact_hash(str(dest)) if self.privacy else str(dest)[:12]
                parts.append(f"{label}={n}")
            results.append(
                CheckResult(
                    name="delivery_attempts",
                    status="warn",
                    detail=f"{source}: " + ", ".join(parts),
                    hint="Non-zero attempts mean recent delivery failures.",
                    category="send",
                ),
            )
        else:
            results.append(
                CheckResult(
                    name="delivery_attempts",
                    status="ok",
                    detail=f"{source}: none recorded",
                    category="send",
                ),
            )

        results.append(
            CheckResult(
                name="persisted_queue",
                status="warn" if persisted else "ok",
                detail=f"{source}: {len(persisted)} message(s)",
                hint=(
                    "Messages waiting from prior runs / crash recovery."
                    if persisted
                    else None
                ),
                category="send",
            ),
        )
        return results

    def check_delivery_timeline(self, limit: int = 10) -> list[CheckResult]:
        """Render recent delivery events from the live bot or disk."""
        events: list = []
        source = "none"
        if self.bot and getattr(self.bot, "delivery", None) is not None:
            try:
                events = self.bot.delivery.recent(limit)
                source = "live"
            except Exception:
                logger.debug("live delivery read failed", exc_info=True)
        if not events:
            events_path = os.path.join(self._storage_path, "delivery_events.json")
            if os.path.isfile(events_path):
                try:
                    with open(events_path, encoding="utf-8") as f:
                        raw = json.load(f)
                    if isinstance(raw, list):
                        events = [e for e in raw if isinstance(e, dict)][-limit:]
                        source = "disk"
                except Exception as e:
                    return [
                        CheckResult(
                            name="delivery_timeline",
                            status="warn",
                            detail=f"delivery_events.json unreadable: {e}",
                            category="send",
                        ),
                    ]
        if not events:
            return [
                CheckResult(
                    name="delivery_timeline",
                    status="info",
                    detail="no delivery events recorded yet",
                    category="send",
                ),
            ]

        counts: dict[str, int] = {}
        for event in events:
            stage = str(event.get("stage", "?"))
            counts[stage] = counts.get(stage, 0) + 1
        summary = ", ".join(f"{s}={n}" for s, n in sorted(counts.items()))
        last = events[-1]
        last_line = (
            f"last: {last.get('stage', '?')} "
            f"{str(last.get('destination') or '?')[:16]}"
            + (f" ({last.get('reason')})" if last.get("reason") else "")
        )
        status = "warn" if counts.get("failed") or counts.get("dropped") else "info"
        return [
            CheckResult(
                name="delivery_timeline",
                status=status,
                detail=f"{source}: {summary}. {last_line}",
                hint=(
                    "Recent delivery failures or drops in the stream."
                    if status == "warn"
                    else None
                ),
                category="send",
            ),
        ]

    def check_send_pipeline(self) -> list[CheckResult]:
        """Internal reasons messages would or would not leave the bot."""
        results: list[CheckResult] = []
        results.extend(self.check_delivery_config())
        results.extend(self.check_storage_history())

        if not self.bot:
            results.append(
                CheckResult(
                    name="bot_runtime",
                    status="info",
                    detail="no live bot attached (config-only doctor)",
                    hint="Queue/retry live state needs a running bot. "
                    "Storage history above is read from disk when present.",
                    category="send",
                ),
            )
            results.append(
                CheckResult(
                    name="send_prerequisites",
                    status="info",
                    detail=(
                        "send() requires: valid 32-hex dest, Identity.recall, "
                        "online interface, free outbound queue slot"
                    ),
                    category="send",
                ),
            )
            return results

        cfg = self.bot.config
        results.append(
            CheckResult(
                name="test_mode",
                status="fail" if cfg.test_mode else "ok",
                detail=str(cfg.test_mode),
                hint="test_mode skips real RNS/LXMF delivery."
                if cfg.test_mode
                else None,
                category="send",
            ),
        )

        outbound = None
        peer_count = 0
        if hasattr(self.bot, "get_propagation_node_status"):
            try:
                prop = self.bot.get_propagation_node_status()
                outbound = prop.get("current_outbound_node")
                peer_count = len(prop.get("discovered_peers") or [])
            except Exception:
                logger.debug("propagation status probe failed", exc_info=True)

        if outbound:
            results.append(
                CheckResult(
                    name="outbound_propagation_node",
                    status="ok",
                    detail=redact_hash(outbound) if self.privacy else outbound,
                    category="send",
                ),
            )
        results.append(
            CheckResult(
                name="discovered_prop_peers",
                status="info",
                detail=str(peer_count),
                category="send",
            ),
        )

        queue = getattr(self.bot, "queue", None)
        if queue is not None:
            qsize = queue.qsize()
            maxsize = getattr(queue, "maxsize", 0) or 0
            full = bool(maxsize and qsize >= maxsize)
            results.append(
                CheckResult(
                    name="outbound_queue",
                    status="fail" if full else "ok",
                    detail=f"{qsize}/{maxsize}",
                    hint="Queue full: new sends drop oldest or fail." if full else None,
                    category="send",
                ),
            )

        router = getattr(self.bot, "router", None)
        local = getattr(self.bot, "local", None)
        results.append(
            CheckResult(
                name="lxmf_router",
                status="ok" if router and local else "fail",
                detail="ready" if router and local else "not ready",
                hint=(
                    "Router/local delivery identity missing. Bot cannot "
                    "send or receive on the mesh."
                    if not (router and local)
                    else None
                ),
                category="send",
            ),
        )

        stamp = cfg.stamp_cost
        results.append(
            CheckResult(
                name="inbound_stamp_cost",
                status="info",
                detail=str(stamp),
                hint=(
                    "Applies to inbound delivery only. "
                    "Outbound stamp cost comes from peer announces "
                    "unless send(stamp_cost=...) overrides it."
                ),
                category="send",
            ),
        )
        results.append(
            CheckResult(
                name="include_tickets",
                status="ok" if getattr(cfg, "include_tickets", True) else "warn",
                detail=str(getattr(cfg, "include_tickets", True)),
                hint=(
                    None
                    if getattr(cfg, "include_tickets", True)
                    else "Peers that require stamps may not be able to reply quickly."
                ),
                category="send",
            ),
        )
        if cfg.require_stamps:
            results.append(
                CheckResult(
                    name="require_stamps",
                    status="info",
                    detail="True (inbound unsigned/invalid stamps rejected)",
                    category="receive",
                ),
            )

        if router is not None:
            deferred = getattr(router, "pending_deferred_stamps", None) or {}
            lxmf_outbound = getattr(router, "pending_outbound", None) or []
            results.append(
                CheckResult(
                    name="deferred_stamps",
                    status="warn" if deferred else "ok",
                    detail=f"{len(deferred)} pending",
                    hint=(
                        "Outbound messages are waiting on stamp generation. "
                        "High peer stamp costs delay replies."
                        if deferred
                        else None
                    ),
                    category="send",
                ),
            )
            results.append(
                CheckResult(
                    name="pending_outbound",
                    status="info",
                    detail=f"{len(lxmf_outbound)} in LXMF outbound queue",
                    category="send",
                ),
            )

        return results

    def check_bot_identity(self) -> list[CheckResult]:
        """Report bot delivery destination if available."""
        results: list[CheckResult] = []
        bot_hash = self._bot_hash()
        if bot_hash:
            detail = redact_hash(bot_hash) if self.privacy else bot_hash
            results.append(
                CheckResult(
                    name="bot_delivery_hash",
                    status="ok",
                    detail=detail,
                    category="receive",
                ),
            )
        else:
            identity_file = os.path.join(self.config_path, "identity")
            if os.path.isfile(identity_file):
                try:
                    import RNS

                    # Compute hash only. Do NOT construct Destination(IN, ...)
                    # here: that registers lxmf/delivery on Transport and breaks
                    # a later bot start in the same process
                    # ("Attempt to register an already registered destination").
                    identity = RNS.Identity.from_file(identity_file)
                    dest_hash = RNS.Destination.hash(identity, "lxmf", "delivery")
                    h = RNS.hexrep(dest_hash, delimit=False)
                    detail = redact_hash(h) if self.privacy else h
                    results.append(
                        CheckResult(
                            name="bot_delivery_hash",
                            status="ok",
                            detail=detail + " (from identity file)",
                            category="receive",
                        ),
                    )
                except Exception as e:
                    results.append(
                        CheckResult(
                            name="bot_delivery_hash",
                            status="warn",
                            detail=f"failed to load identity: {e}",
                            category="receive",
                        ),
                    )
            else:
                results.append(
                    CheckResult(
                        name="bot_delivery_hash",
                        status="info",
                        detail="no bot identity yet",
                        hint="Pass --config at a bot config dir, or run with "
                        "a live bot.",
                        category="receive",
                    ),
                )

        if self.bot:
            sig = self.bot.config.signature_verification_enabled
            req = self.bot.config.require_message_signatures
            results.append(
                CheckResult(
                    name="signature_policy",
                    status="info",
                    detail=f"verification={sig} require={req}",
                    hint=(
                        "require_message_signatures=True rejects unsigned inbound."
                        if req
                        else None
                    ),
                    category="receive",
                ),
            )

        return results

    def probe_destination(
        self,
        destination: str,
        *,
        request_path: bool = False,
        wait: float = 0.0,
    ) -> DestinationProbe:
        """Probe path and identity knowledge for a destination."""
        cleaned = normalize_destination_hex(destination)
        dest_bytes = parse_destination_hash(cleaned)
        probe = DestinationProbe(
            destination=cleaned or destination,
            valid_hash=dest_bytes is not None,
        )

        if dest_bytes is None:
            probe.notes.append("Invalid destination hash")
            probe.hints.append(
                f"Hash must be {_hash_len() * 2} hex characters ({_hash_len()} bytes).",
            )
            return probe

        if not self.ensure_reticulum():
            probe.notes.append("Reticulum not initialized")
            probe.hints.append("Fix Reticulum config and retry.")
            return probe

        import RNS

        t0 = time.monotonic()
        probe.timeline.append({"t": 0.0, "event": "probe_start"})

        identity = RNS.Identity.recall(dest_bytes)
        probe.identity_known = identity is not None
        probe.timeline.append(
            {
                "t": round(time.monotonic() - t0, 3),
                "event": "identity_recalled"
                if probe.identity_known
                else "identity_unknown",
            },
        )
        probe.has_path = bool(RNS.Transport.has_path(dest_bytes))
        probe.timeline.append(
            {
                "t": round(time.monotonic() - t0, 3),
                "event": "path_present" if probe.has_path else "path_missing",
            },
        )

        if probe.has_path:
            try:
                hops = RNS.Transport.hops_to(dest_bytes)
                probe.hops = int(hops) if hops is not None else None
            except Exception:
                probe.hops = None
            try:
                nh = RNS.Transport.next_hop(dest_bytes)
                if nh:
                    probe.next_hop = RNS.hexrep(nh, delimit=False)
            except Exception:
                logger.debug("next_hop probe failed", exc_info=True)

        try:
            app_data = RNS.Identity.recall_app_data(dest_bytes)
            if app_data:
                if isinstance(app_data, bytes):
                    probe.app_data = app_data.decode("utf-8", errors="replace")
                else:
                    probe.app_data = str(app_data)
        except Exception:
            logger.debug("app_data probe failed", exc_info=True)

        if not probe.identity_known:
            probe.notes.append("Identity not recalled")
            probe.hints.append(
                "LXMFy send() returns False until Identity.recall succeeds. "
                "Peer must announce on a network you share.",
            )
        if not probe.has_path:
            probe.notes.append("No path known")
            probe.hints.append(
                "No route to destination. Ensure interfaces are online and "
                "you share a transport path with the peer.",
            )

        if request_path and (not probe.has_path or not probe.identity_known):
            try:
                RNS.Transport.request_path(dest_bytes)
                probe.path_requested = True
                probe.notes.append("Path requested")
                probe.timeline.append(
                    {
                        "t": round(time.monotonic() - t0, 3),
                        "event": "path_requested",
                    },
                )
            except Exception as e:
                probe.notes.append(f"Path request failed: {e}")
                probe.timeline.append(
                    {
                        "t": round(time.monotonic() - t0, 3),
                        "event": f"path_request_failed:{e}",
                    },
                )

            if wait and wait > 0:
                probe.path_waited = True
                deadline = time.time() + wait
                while time.time() < deadline:
                    if RNS.Transport.has_path(dest_bytes):
                        probe.has_path = True
                        probe.path_found_after_wait = True
                        elapsed = round(time.monotonic() - t0, 3)
                        identity = RNS.Identity.recall(dest_bytes)
                        probe.identity_known = identity is not None
                        try:
                            hops = RNS.Transport.hops_to(dest_bytes)
                            probe.hops = int(hops) if hops is not None else None
                        except Exception:
                            logger.debug("hops_to probe failed", exc_info=True)
                        probe.notes.append(
                            f"Path became available after {elapsed}s",
                        )
                        probe.timeline.append(
                            {"t": elapsed, "event": "path_found"},
                        )
                        if probe.identity_known:
                            probe.timeline.append(
                                {
                                    "t": elapsed,
                                    "event": "identity_recalled_after_path",
                                },
                            )
                        break
                    time.sleep(0.25)
                else:
                    elapsed = round(time.monotonic() - t0, 3)
                    probe.notes.append(
                        f"No path within {wait}s after request (waited {elapsed}s)",
                    )
                    probe.timeline.append(
                        {"t": elapsed, "event": "path_timeout"},
                    )
                    probe.hints.append(
                        "Path request timed out. Peer may be offline, on a "
                        "disjoint network, or not announcing.",
                    )

        if probe.identity_known and probe.has_path:
            probe.hints.append(
                "Identity and path look good. If send still fails, check "
                "delivery retries, opportunistic vs DIRECT, and propagation.",
            )
        elif probe.identity_known and not probe.has_path:
            probe.hints.append(
                "Identity known but no path. Request path and wait.",
            )

        return probe

    def diagnose_send(
        self,
        destination: str,
        *,
        probe: DestinationProbe | None = None,
    ) -> list[CheckResult]:
        """Explain why sending to a destination may fail."""
        if probe is None:
            probe = self.probe_destination(destination)
        results: list[CheckResult] = []
        dest_show = (
            redact_hash(probe.destination) if self.privacy else probe.destination
        )

        results.append(
            CheckResult(
                name="destination_hash",
                status="ok" if probe.valid_hash else "fail",
                detail=dest_show,
                hint=None if probe.valid_hash else f"Need {_hash_len() * 2} hex chars.",
                category="destination",
            ),
        )
        if not probe.valid_hash:
            return results

        results.append(
            CheckResult(
                name="identity_known",
                status="ok" if probe.identity_known else "fail",
                detail=str(probe.identity_known),
                hint=None
                if probe.identity_known
                else "send() aborts when Identity.recall fails. "
                "Use: lxmfy debug probe <hash> --request-path --wait 30",
                category="destination",
            ),
        )
        results.append(
            CheckResult(
                name="has_path",
                status="ok" if probe.has_path else "fail",
                detail=(f"True (hops={probe.hops})" if probe.has_path else "False"),
                hint=None
                if probe.has_path
                else "No route. Bring interfaces online and ensure a shared "
                "Reticulum transport path.",
                category="destination",
            ),
        )
        if probe.next_hop:
            nh = redact_hash(probe.next_hop) if self.privacy else probe.next_hop
            results.append(
                CheckResult(
                    name="next_hop",
                    status="info",
                    detail=nh,
                    category="destination",
                ),
            )
        if probe.app_data:
            ad = redact_display_name(probe.app_data) if self.privacy else probe.app_data
            results.append(
                CheckResult(
                    name="announce_app_data",
                    status="info",
                    detail=ad,
                    category="destination",
                ),
            )

        # Would send() accept this right now?
        can_queue = probe.valid_hash and probe.identity_known
        results.append(
            CheckResult(
                name="send_would_queue",
                status="ok" if can_queue else "fail",
                detail=str(can_queue),
                hint=None
                if can_queue
                else "LXMFy will not enqueue: identity unknown or bad hash.",
                category="destination",
            ),
        )

        if probe.valid_hash:
            try:
                import RNS

                dest_bytes = parse_destination_hash(probe.destination)
                ratchet_id = (
                    RNS.Identity.current_ratchet_id(dest_bytes)
                    if dest_bytes is not None
                    else None
                )
                results.append(
                    CheckResult(
                        name="peer_ratchet",
                        status="ok" if ratchet_id else "warn",
                        detail=(
                            RNS.hexrep(ratchet_id, delimit=False)
                            if ratchet_id
                            else "unknown"
                        ),
                        hint=(
                            None
                            if ratchet_id
                            else "No announced ratchet yet. Opportunistic sends "
                            "use static identity encryption until an announce arrives."
                        ),
                        category="destination",
                    ),
                )
                if self.bot and getattr(self.bot, "router", None):
                    peer_stamp = self.bot.router.get_outbound_stamp_cost(dest_bytes)
                    ticket = self.bot.router.get_outbound_ticket(dest_bytes)
                    results.append(
                        CheckResult(
                            name="peer_stamp_cost",
                            status="info",
                            detail=str(peer_stamp),
                            hint=(
                                "Peer requires stamps. Replies wait on stamp "
                                "generation unless an outbound ticket is available."
                                if peer_stamp
                                else None
                            ),
                            category="destination",
                        ),
                    )
                    results.append(
                        CheckResult(
                            name="outbound_ticket",
                            status="ok" if ticket or not peer_stamp else "warn",
                            detail="present" if ticket else "none",
                            hint=(
                                None
                                if ticket or not peer_stamp
                                else "No ticket from this peer. Stamp generation "
                                "may delay or fail replies to stamp-requiring clients."
                            ),
                            category="destination",
                        ),
                    )
            except Exception as e:
                results.append(
                    CheckResult(
                        name="peer_stamp_ratchet",
                        status="warn",
                        detail=f"check failed: {e}",
                        category="destination",
                    ),
                )

        if self.bot:
            attempts = (getattr(self.bot, "delivery_attempts", None) or {}).get(
                normalize_destination_hex(destination),
                0,
            )
            max_retries = getattr(self.bot.config, "direct_delivery_retries", 3)
            results.append(
                CheckResult(
                    name="delivery_attempts_for_dest",
                    status="warn" if attempts else "ok",
                    detail=f"{attempts}/{max_retries}",
                    hint=(
                        "At or past retries, LXMFy switches to PROPAGATED "
                        "if fallback is enabled."
                        if attempts >= max_retries
                        else None
                    ),
                    category="destination",
                ),
            )
            if attempts >= max_retries and self.bot.config.propagation_fallback_enabled:
                results.append(
                    CheckResult(
                        name="method_for_dest",
                        status="info",
                        detail="PROPAGATED (retry limit reached)",
                        category="destination",
                    ),
                )
            elif self.bot.config.opportunistic_sending:
                results.append(
                    CheckResult(
                        name="method_for_dest",
                        status="info",
                        detail="OPPORTUNISTIC",
                        category="destination",
                    ),
                )
            else:
                results.append(
                    CheckResult(
                        name="method_for_dest",
                        status="info",
                        detail="DIRECT",
                        category="destination",
                    ),
                )

        return results

    def diagnose_receive(self) -> list[CheckResult]:
        """Explain why peers may not be able to reach this bot."""
        results = self.check_bot_identity()
        results.extend(self.check_interfaces())
        results.extend(self.check_announce())

        bot_hash = self._bot_hash()
        if bot_hash and self.ensure_reticulum():
            try:
                import RNS

                dest = bytes.fromhex(bot_hash)
                has = RNS.Transport.has_path(dest)
                results.append(
                    CheckResult(
                        name="local_path_to_self",
                        status="info",
                        detail=str(has),
                        hint="Peers need a path to your delivery hash. "
                        "Announce after interfaces are online.",
                        category="receive",
                    ),
                )
            except Exception:
                logger.debug("local path probe failed", exc_info=True)

        results.append(
            CheckResult(
                name="receive_tip",
                status="info",
                detail="Share your LXMF delivery hash with peers",
                hint="Printed at startup as 'LXMF Router ready to receive on: …'",
                category="receive",
            ),
        )
        return results

    def _collect_blockers(
        self,
        checks: list[CheckResult],
    ) -> tuple[list[str], list[str]]:
        send_keys = {
            "interfaces",
            "interfaces_online",
            "lxmf_router",
            "outbound_queue",
            "test_mode",
            "identity_known",
            "has_path",
            "destination_hash",
            "send_would_queue",
            "share_instance",
            "instance_mode",
            "config_path",
            "reticulum_config_dir",
            "storage_path",
            "reticulum_config",
        }
        recv_keys = {
            "interfaces",
            "interfaces_online",
            "announce_enabled",
            "announce_test",
            "announce_file",
            "lxmf_router",
            "bot_delivery_hash",
            "identity_file",
            "instance_mode",
        }
        send_blockers: list[str] = []
        recv_blockers: list[str] = []
        for c in checks:
            if c.status != "fail":
                continue
            line = f"{c.name}: {c.detail}"
            base = c.name.split(":", 1)[0]
            if (
                c.name in send_keys
                or base in send_keys
                or c.category
                in {
                    "send",
                    "destination",
                    "network",
                    "disk",
                    "instance",
                }
            ):
                send_blockers.append(line)
            if (
                c.name in recv_keys
                or base in recv_keys
                or c.category
                in {
                    "receive",
                    "announce",
                    "network",
                    "disk",
                    "instance",
                }
            ):
                recv_blockers.append(line)
        return send_blockers, recv_blockers

    def run_doctor(
        self,
        destination: str | None = None,
        *,
        request_path: bool = False,
        wait: float = 0.0,
        try_announce: bool = False,
    ) -> DoctorReport:
        """Run a full connectivity doctor report."""
        report = DoctorReport(
            reticulum_config_dir=self.reticulum_config_dir,
            bot_hash=self._bot_hash(),
            tips=list(COMMON_TIPS),
            generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            lxmfy_version=LXMFY_VERSION,
            privacy=self.privacy,
        )
        report.checks.extend(self.check_environment())
        report.checks.extend(self.check_instance())
        report.checks.extend(self.check_disk_permissions())
        report.checks.extend(self.check_interfaces())
        report.checks.extend(self.check_announce(try_announce=try_announce))
        report.checks.extend(self.check_send_pipeline())
        report.checks.extend(self.check_delivery_timeline())
        report.checks.extend(self.check_bot_identity())

        if destination:
            report.probe = self.probe_destination(
                destination,
                request_path=request_path,
                wait=wait,
            )
            report.checks.extend(
                self.diagnose_send(destination, probe=report.probe),
            )

        send_b, recv_b = self._collect_blockers(report.checks)
        report.send_blockers = send_b
        report.receive_blockers = recv_b
        report.checks = sort_checks_by_severity(report.checks)
        verdict, steps = build_verdict(
            report.checks,
            send_blockers=send_b,
            receive_blockers=recv_b,
            probe=report.probe,
        )
        report.verdict = verdict
        report.next_steps = steps
        return report

    def compare_destinations(
        self,
        left: str,
        right: str,
        *,
        request_path: bool = False,
        wait: float = 0.0,
    ) -> dict[str, Any]:
        """Compare path/identity status for two destination hashes."""
        a = self.probe_destination(left, request_path=request_path, wait=wait)
        b = self.probe_destination(right, request_path=request_path, wait=wait)
        result: dict[str, Any] = {
            "left": a.to_dict(privacy=self.privacy),
            "right": b.to_dict(privacy=self.privacy),
            "both_valid": a.valid_hash and b.valid_hash,
            "both_identity_known": a.identity_known and b.identity_known,
            "both_have_path": a.has_path and b.has_path,
            "notes": [],
        }
        if a.valid_hash and b.valid_hash and a.destination == b.destination:
            result["notes"].append("Both hashes normalize to the same destination")
        if a.identity_known and not b.identity_known:
            result["notes"].append("Left identity known, right unknown")
        elif b.identity_known and not a.identity_known:
            result["notes"].append("Right identity known, left unknown")
        if a.has_path and not b.has_path:
            result["notes"].append("Path exists to left only")
        elif b.has_path and not a.has_path:
            result["notes"].append("Path exists to right only")
        if result["both_identity_known"] and result["both_have_path"]:
            result["notes"].append("Both sides look reachable from this node")
        return result

    def format_report_text(self, report: DoctorReport) -> str:
        """Format a plain-text privacy-friendly report for files/sharing."""
        lines: list[str] = []
        data = report.to_dict()
        lines.append("=" * 60)
        lines.append("LXMFy Debugger Report")
        lines.append("=" * 60)
        lines.append(f"generated_at: {data.get('generated_at')}")
        lines.append(f"lxmfy_version: {data.get('lxmfy_version')}")
        lines.append(f"privacy_redacted: {data.get('privacy')}")
        lines.append(f"reticulum_config: {data.get('reticulum_config_dir')}")
        lines.append(f"bot_delivery_hash: {data.get('bot_hash') or '(unknown)'}")
        lines.append(f"verdict: {data.get('verdict')}")
        lines.append("")
        if report.next_steps:
            lines.append("-" * 60)
            lines.append("Next Steps")
            lines.append("-" * 60)
            for i, step in enumerate(report.next_steps, 1):
                lines.append(f"  {i}. {step}")
            lines.append("")

        by_cat: dict[str, list[CheckResult]] = {}
        for check in report.checks:
            by_cat.setdefault(check.category, []).append(check)

        for cat in CATEGORY_ORDER:
            items = by_cat.get(cat) or []
            if not items:
                continue
            lines.append("-" * 60)
            lines.append(CATEGORY_TITLES.get(cat, cat.upper()))
            lines.append("-" * 60)
            for c in sort_checks_by_severity(items):
                detail = c.detail
                if report.privacy:
                    detail = redact_sensitive_text(detail)
                lines.append(f"[{c.status.upper():5}] {c.name}: {detail}")
                if c.hint:
                    hint = c.hint
                    if report.privacy:
                        hint = redact_sensitive_text(hint)
                    lines.append(f"         hint: {hint}")
            lines.append("")

        if report.probe:
            p = report.probe.to_dict(privacy=report.privacy)
            lines.append("-" * 60)
            lines.append("Destination Probe Detail")
            lines.append("-" * 60)
            for key, val in p.items():
                if val in (None, "", [], False) and key not in {
                    "valid_hash",
                    "identity_known",
                    "has_path",
                }:
                    continue
                lines.append(f"  {key}: {val}")
            lines.append("")

        lines.append("-" * 60)
        lines.append("Blockers")
        lines.append("-" * 60)
        if report.send_blockers:
            lines.append("send:")
            lines.extend(
                f"  - {redact_sensitive_text(b) if report.privacy else b}"
                for b in report.send_blockers
            )
        else:
            lines.append("send: (none)")
        if report.receive_blockers:
            lines.append("receive:")
            lines.extend(
                f"  - {redact_sensitive_text(b) if report.privacy else b}"
                for b in report.receive_blockers
            )
        else:
            lines.append("receive: (none)")
        lines.append("")

        lines.append("-" * 60)
        lines.append("Summary")
        lines.append("-" * 60)
        lines.append(
            f"failures={data['failures']} warnings={data['warnings']} ok={data['ok']}",
        )
        lines.append("")
        lines.append("Tips:")
        lines.extend(f"  - {tip}" for tip in report.tips)
        lines.append("")
        lines.append(
            "Share this file when asking for help. It is privacy-redacted "
            "by default (home paths and full hashes truncated).",
        )
        lines.append("")
        return "\n".join(lines)

    def save_report(
        self,
        report: DoctorReport,
        path: str | None = None,
        *,
        as_json: bool = False,
    ) -> str:
        """Write report to a file and return the path used."""
        if path is None:
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            ext = "json" if as_json else "txt"
            path = os.path.abspath(f"lxmfy-debug-{stamp}.{ext}")
        else:
            path = os.path.abspath(os.path.expanduser(path))

        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        if as_json or path.endswith(".json"):
            content = json.dumps(report.to_dict(), indent=2, default=str)
        else:
            content = self.format_report_text(report)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")
        return path

    def print_report(
        self,
        report: DoctorReport,
        *,
        as_json: bool = False,
    ) -> None:
        """Print a doctor report to the terminal."""
        if as_json:
            print(json.dumps(report.to_dict(), indent=2, default=str))
            return

        print_header("LXMFy Debugger")
        print_kv("generated", report.generated_at or "?")
        print_kv("lxmfy", report.lxmfy_version or LXMFY_VERSION)
        print_kv(
            "reticulum_config",
            redact_path(report.reticulum_config_dir)
            if report.privacy
            else (report.reticulum_config_dir or "?"),
        )
        if report.bot_hash:
            shown = redact_hash(report.bot_hash) if report.privacy else report.bot_hash
            print_kv("bot_delivery_hash", shown, ok=True)
        else:
            print_kv("bot_delivery_hash", "(unknown)", ok=None)
        print_kv("privacy_redacted", str(report.privacy))
        print_kv("verdict", report.verdict or "unknown")
        if report.next_steps:
            print_section("Next Steps")
            for i, step in enumerate(report.next_steps, 1):
                print_info(f"{i}. {step}")

        by_cat: dict[str, list[CheckResult]] = {}
        for check in report.checks:
            by_cat.setdefault(check.category, []).append(check)

        for cat in CATEGORY_ORDER:
            items = by_cat.get(cat) or []
            if not items:
                continue
            print_section(CATEGORY_TITLES.get(cat, cat))
            for check in sort_checks_by_severity(items):
                detail = check.detail
                hint = check.hint
                if report.privacy:
                    detail = redact_sensitive_text(detail)
                    if hint:
                        hint = redact_sensitive_text(hint)
                print_check(check.name, check.status, detail, hint)

        if report.probe:
            print_section("Destination Probe")
            p = report.probe
            dest = redact_hash(p.destination) if report.privacy else p.destination
            print_kv("destination", dest)
            print_kv("valid_hash", str(p.valid_hash), ok=p.valid_hash)
            print_kv("identity_known", str(p.identity_known), ok=p.identity_known)
            print_kv("has_path", str(p.has_path), ok=p.has_path)
            if p.hops is not None:
                print_kv("hops", str(p.hops))
            if p.next_hop:
                nh = redact_hash(p.next_hop) if report.privacy else p.next_hop
                print_kv("next_hop", nh)
            if p.app_data:
                ad = redact_display_name(p.app_data) if report.privacy else p.app_data
                print_kv("app_data", ad)
            if p.path_requested:
                print_kv(
                    "path_requested",
                    "yes"
                    + (f", found={p.path_found_after_wait}" if p.path_waited else ""),
                )
            if p.timeline:
                print_section("Path Timeline")
                for entry in p.timeline:
                    print_dim(f"+{entry.get('t', '?')}s  {entry.get('event')}")
            for note in p.notes:
                print_dim(note)
            for hint in p.hints:
                print_warning(hint)

        print_section("Blockers")
        if report.send_blockers:
            print_error("Send blockers:")
            for b in report.send_blockers:
                print_dim(redact_sensitive_text(b) if report.privacy else b)
        else:
            print_success("No hard send blockers detected")
        if report.receive_blockers:
            print_error("Receive blockers:")
            for b in report.receive_blockers:
                print_dim(redact_sensitive_text(b) if report.privacy else b)
        else:
            print_success("No hard receive blockers detected")

        print_section("Summary")
        data = report.to_dict()
        failures = data["failures"]
        warnings = data["warnings"]
        if failures:
            print_error(f"{failures} failure(s), {warnings} warning(s)")
        elif warnings:
            print_warning(f"No failures, {warnings} warning(s)")
        else:
            print_success("No failures or warnings")

        print_section("Common tips")
        for tip in report.tips:
            print_info(tip)

    def print_probe(
        self,
        probe: DestinationProbe,
        *,
        as_json: bool = False,
    ) -> None:
        """Print a destination probe result."""
        if as_json:
            print(json.dumps(probe.to_dict(privacy=self.privacy), indent=2))
            return

        print_header("Destination Probe")
        dest = redact_hash(probe.destination) if self.privacy else probe.destination
        print_kv("destination", dest)
        print_kv("valid_hash", str(probe.valid_hash), ok=probe.valid_hash)
        print_kv(
            "identity_known",
            str(probe.identity_known),
            ok=probe.identity_known,
        )
        print_kv("has_path", str(probe.has_path), ok=probe.has_path)
        if probe.hops is not None:
            print_kv("hops", str(probe.hops))
        if probe.next_hop:
            nh = redact_hash(probe.next_hop) if self.privacy else probe.next_hop
            print_kv("next_hop", nh)
        if probe.app_data:
            ad = redact_display_name(probe.app_data) if self.privacy else probe.app_data
            print_kv("app_data", ad)
        for note in probe.notes:
            print_dim(note)
        for hint in probe.hints:
            print_warning(hint)

        if probe.valid_hash and probe.identity_known and probe.has_path:
            print_success("Ready to attempt send to this destination")
        elif probe.valid_hash:
            print_error("Not ready to send (see hints above)")

    def _bot_hash(self) -> str | None:
        if not self.bot:
            return None
        local = getattr(self.bot, "local", None)
        if local is None or getattr(local, "hash", None) is None:
            return None
        try:
            import RNS

            return RNS.hexrep(local.hash, delimit=False)
        except Exception:
            try:
                return bytes(local.hash).hex()
            except Exception:
                return None


# Back-compat alias
MessageDebugger = Debugger


def _read_share_instance(config_file: str) -> str | None:
    try:
        with open(config_file, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip().lower()
                if stripped.startswith("share_instance"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().lower()
    except OSError:
        return None
    return None


def diagnose_destination(
    destination: str,
    *,
    reticulum_config_dir: str | None = None,
    config_path: str | None = None,
    bot: Any | None = None,
    request_path: bool = False,
    wait: float = 0.0,
    privacy: bool = True,
) -> DestinationProbe:
    """Convenience helper to probe a destination."""
    dbg = Debugger(
        reticulum_config_dir=reticulum_config_dir,
        config_path=config_path,
        bot=bot,
        privacy=privacy,
    )
    return dbg.probe_destination(
        destination,
        request_path=request_path,
        wait=wait,
    )


def default_report_path(*, as_json: bool = False) -> str:
    """Default shareable report filename in the current directory."""
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    ext = "json" if as_json else "txt"
    return os.path.abspath(f"lxmfy-debug-{stamp}.{ext}")
