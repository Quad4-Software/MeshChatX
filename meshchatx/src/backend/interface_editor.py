# SPDX-License-Identifier: 0BSD

"""Validate and normalize Reticulum interface options before config write."""

from __future__ import annotations

import os
import re
from typing import Any

import RNS

_IPV4_HOST_PORT = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})$")

ALLOWED_INTERFACE_MODES = frozenset(
    {
        "full",
        "gateway",
        "gw",
        "access_point",
        "accesspoint",
        "ap",
        "pointtopoint",
        "ptp",
        "roaming",
        "boundary",
        "internal",
    },
)

_MODE_ALIASES = {
    "gw": "gateway",
    "accesspoint": "access_point",
    "ap": "access_point",
    "pointtopoint": "pointtopoint",
    "ptp": "pointtopoint",
}

_TRUTHY = frozenset({"true", "yes", "1", "y", "on"})
_FALSY = frozenset({"false", "no", "0", "n", "off"})

# RNS Discovery runs location_cmd via subprocess.run([path]).
_UNSAFE_LOCATION_CMD = re.compile(r"[\x00-\x1f\x7f;&|`$<>\\\"'*?\[\]{}()!#]")

RNODE_TXPOWER_MIN = 0
RNODE_TXPOWER_MAX = 37


def normalize_rnode_tcp_port(port: str) -> str:
    """Strip embedded :port from tcp:// URLs for RNode TCPConnection.

    RNS getaddrinfo expects host only. Legacy configs may use tcp://host:7633.
    """
    raw = str(port).strip()
    low = raw.lower()
    prefix = "tcp://"
    if not low.startswith(prefix):
        return raw
    rest = raw[len(prefix) :].strip()
    while rest.endswith(":"):
        rest = rest[:-1]
    if not rest:
        return prefix
    if rest.startswith("["):
        close = rest.find("]")
        if close != -1 and len(rest) > close + 1 and rest[close + 1] == ":":
            tail = rest[close + 2 :]
            if tail.isdigit() and 1 <= int(tail) <= 65535:
                rest = rest[: close + 1]
        return prefix + rest
    match = _IPV4_HOST_PORT.match(rest)
    if match and int(match.group(2)) <= 65535:
        rest = match.group(1)
    elif rest.count(":") == 1:
        head, tail = rest.split(":", 1)
        if tail.isdigit() and 1 <= int(tail) <= 65535:
            rest = head
    return prefix + rest


def coerce_rnode_frequency_hz(value: Any) -> Any:
    """Convert UI frequency input to integer Hz for RNodeInterface config."""
    if value is None or value == "":
        return value
    raw = str(value).strip()
    text = raw.lower().replace("_", "")
    scale = 1.0
    for suffix, factor in (("ghz", 1e9), ("mhz", 1e6), ("khz", 1e3), ("hz", 1.0)):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
            scale = factor
            break
    hz = float(text) * scale
    if hz <= 0:
        return int(round(hz))
    if hz >= 1_000_000:
        return int(round(hz))
    whole = abs(hz - round(hz)) < 1e-9
    if (not whole) or (whole and hz < 10_000):
        hz *= 1_000_000.0
    return int(round(hz))


def normalize_rnode_txpower(value: Any) -> Any:
    """Parse TX power as integer dBm."""
    if value is None or value == "":
        return value
    return int(float(str(value).strip()))


def validate_rnode_txpower(value: Any) -> str | None:
    """Return an error string when TX power is out of RNS range."""
    if value is None or value == "":
        return "TX power is required"
    try:
        power = normalize_rnode_txpower(value)
    except (TypeError, ValueError):
        return "TX power must be an integer dBm value"
    if not isinstance(power, int):
        return "TX power must be an integer dBm value"
    if power < RNODE_TXPOWER_MIN or power > RNODE_TXPOWER_MAX:
        return (
            f"TX power must be between {RNODE_TXPOWER_MIN} and {RNODE_TXPOWER_MAX} dBm "
            "(Reticulum RNodeInterface limit; typical SX1262 range is 0-22 dBm)"
        )
    return None


class InterfaceEditor:
    """API-facing helpers for mutating Reticulum interface config dicts."""

    coerce_rnode_frequency_hz = staticmethod(coerce_rnode_frequency_hz)
    normalize_rnode_tcp_port = staticmethod(normalize_rnode_tcp_port)
    normalize_rnode_txpower = staticmethod(normalize_rnode_txpower)
    validate_rnode_txpower = staticmethod(validate_rnode_txpower)

    @staticmethod
    def sanitize_interface_section_name(name: str | None) -> str:
        """Strip characters that break ConfigObj [[section]] headers."""
        cleaned = str(name or "").strip()
        if not cleaned:
            return ""
        cleaned = (
            cleaned.replace("[", "(")
            .replace("]", ")")
            .replace("\n", " ")
            .replace("\r", " ")
        )
        cleaned = " ".join(cleaned.split())
        return cleaned[:128]

    @staticmethod
    def minimum_fixed_mtu() -> int:
        mtu = getattr(RNS.Reticulum, "MTU", None)
        if type(mtu) is int and mtu > 0:
            return mtu
        return 500

    @staticmethod
    def apply_fixed_mtu(interface_details: dict, data: dict) -> str | None:
        """Apply fixed_mtu from request data or clear it. Return error or None."""
        value = data.get("fixed_mtu")
        if value is None or value == "":
            interface_details.pop("fixed_mtu", None)
            return None
        try:
            mtu = int(value)
        except (TypeError, ValueError):
            return "fixed_mtu must be a positive integer"
        floor = InterfaceEditor.minimum_fixed_mtu()
        if mtu < floor:
            return (
                f"fixed_mtu must be at least {floor} bytes "
                f"(Reticulum minimum MTU; values below this prevent startup)"
            )
        interface_details["fixed_mtu"] = mtu
        return None

    @staticmethod
    def update_value(interface_details: dict, data: dict, key: str) -> None:
        value = data.get(key)
        if value is not None and value != "":
            interface_details[key] = value
            return
        interface_details.pop(key, None)

    @staticmethod
    def normalize_interface_mode(value: Any) -> str | None:
        if value is None or value == "":
            return None
        mode = str(value).strip().lower()
        if mode not in ALLOWED_INTERFACE_MODES:
            return None
        return _MODE_ALIASES.get(mode, mode)

    @staticmethod
    def apply_interface_mode(interface_details: dict, data: dict) -> str | None:
        if "mode" not in data:
            return None
        value = data.get("mode")
        if value is None or value == "":
            interface_details.pop("mode", None)
            return None
        mode = InterfaceEditor.normalize_interface_mode(value)
        if mode is None:
            return (
                "mode must be one of: full, gateway, access_point, "
                "pointtopoint, roaming, boundary, internal"
            )
        interface_details["mode"] = mode
        return None

    @staticmethod
    def request_yes_no(value: Any) -> str | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return "yes" if value else "no"
        text = str(value).strip().lower()
        if text in _TRUTHY:
            return "yes"
        if text in _FALSY:
            return "no"
        return None

    @staticmethod
    def apply_yes_no_option(
        interface_details: dict,
        data: dict,
        key: str,
        *,
        default_when_missing: str | None = None,
    ) -> str | None:
        if key not in data:
            if default_when_missing is None:
                return None
            if default_when_missing in ("yes", "no"):
                interface_details[key] = default_when_missing
            else:
                interface_details.pop(key, None)
            return None
        yn = InterfaceEditor.request_yes_no(data.get(key))
        if yn is None:
            interface_details.pop(key, None)
            raw = data.get(key)
            if raw is None or raw == "":
                return None
            return f"{key} must be a boolean or yes/no value"
        interface_details[key] = yn
        return None

    @staticmethod
    def validate_location_cmd(value: Any) -> str | None:
        if value is None or value == "":
            return None
        raw = str(value).strip()
        if not raw:
            return None
        if _UNSAFE_LOCATION_CMD.search(raw):
            return (
                "location_cmd must be an absolute executable path without "
                "shell metacharacters or control characters"
            )
        if ".." in raw.replace("\\", "/").split("/"):
            return "location_cmd must not contain parent-directory segments"
        expanded = os.path.expanduser(raw)
        if not os.path.isabs(expanded):
            return "location_cmd must be an absolute path or start with ~/"
        return None

    @staticmethod
    def apply_location_cmd(interface_details: dict, data: dict) -> str | None:
        if "location_cmd" not in data:
            return None
        value = data.get("location_cmd")
        if value is None or value == "":
            interface_details.pop("location_cmd", None)
            return None
        error = InterfaceEditor.validate_location_cmd(value)
        if error is not None:
            return error
        interface_details["location_cmd"] = os.path.normpath(
            os.path.expanduser(str(value).strip()),
        )
        return None

    @staticmethod
    def apply_positive_number(
        interface_details: dict,
        data: dict,
        key: str,
        *,
        as_int: bool = False,
        minimum: float = 0,
        maximum: float | None = None,
    ) -> str | None:
        if key not in data:
            return None
        value = data.get(key)
        if value is None or value == "":
            interface_details.pop(key, None)
            return None
        try:
            number = int(value) if as_int else float(value)
        except (TypeError, ValueError):
            return f"{key} must be a number"
        if number < minimum:
            return f"{key} must be at least {minimum}"
        if maximum is not None and number > maximum:
            return f"{key} must be at most {maximum}"
        interface_details[key] = int(number) if as_int else number
        return None

    @staticmethod
    def apply_backbone_fast_flapping(
        interface_details: dict,
        data: dict,
    ) -> str | None:
        err = InterfaceEditor.apply_yes_no_option(
            interface_details,
            data,
            "block_fast_flapping",
        )
        if err:
            return err
        for key, kwargs in (
            (
                "fast_flapping_block_time",
                {"as_int": True, "minimum": 1, "maximum": 60 * 24 * 30},
            ),
            (
                "fast_flapping_threshold",
                {"as_int": False, "minimum": 0.1, "maximum": 3600},
            ),
            (
                "fast_flapping_grace",
                {"as_int": True, "minimum": 0, "maximum": 10_000},
            ),
        ):
            err = InterfaceEditor.apply_positive_number(
                interface_details,
                data,
                key,
                **kwargs,
            )
            if err:
                return err
        return None

    @staticmethod
    def sanitize_imported_rns_options(iface_body: dict) -> str | None:
        if "mode" in iface_body:
            mode = InterfaceEditor.normalize_interface_mode(iface_body.get("mode"))
            if mode is None:
                return (
                    "Imported interface mode must be one of: full, gateway, "
                    "access_point, pointtopoint, roaming, boundary, internal"
                )
            iface_body["mode"] = mode
        for key in (
            "recursive_prs",
            "announces_from_internal",
            "announces_to_internal",
            "block_fast_flapping",
        ):
            if key not in iface_body:
                continue
            yn = InterfaceEditor.request_yes_no(iface_body.get(key))
            if yn is None:
                return f"Imported interface {key} must be a boolean or yes/no value"
            iface_body[key] = yn
        if "gravity" in iface_body:
            grav = iface_body.get("gravity")
            if grav is None or grav == "":
                iface_body.pop("gravity", None)
            else:
                try:
                    iface_body["gravity"] = int(grav)
                except (TypeError, ValueError):
                    return "Imported interface gravity must be an integer"
        if "location_cmd" in iface_body:
            loc = iface_body.get("location_cmd")
            if loc is None or loc == "":
                iface_body.pop("location_cmd", None)
            else:
                error = InterfaceEditor.validate_location_cmd(loc)
                if error is not None:
                    return error
                iface_body["location_cmd"] = os.path.normpath(
                    os.path.expanduser(str(loc).strip()),
                )
        return None
