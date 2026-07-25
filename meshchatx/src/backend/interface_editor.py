# SPDX-License-Identifier: 0BSD AND MIT

import os
import re

import RNS

_IPV4_HOST_PORT = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})$")

# Canonical Reticulum interface mode strings (RNS 1.3.7+ includes internal).
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
    }
)

# Prefer writing the long form when aliases are supplied via the API.
_INTERFACE_MODE_CANONICAL = {
    "gw": "gateway",
    "accesspoint": "access_point",
    "ap": "access_point",
    "pointtopoint": "pointtopoint",
    "ptp": "pointtopoint",
}

_YES_NO_TRUE = frozenset({"true", "yes", "1", "y", "on"})
_YES_NO_FALSE = frozenset({"false", "no", "0", "n", "off"})

# location_cmd is executed by RNS Discovery via subprocess.run([path]).
# Reject shell metacharacters and relative traversal before persisting.
_LOCATION_CMD_FORBIDDEN = re.compile(r"[\x00-\x1f\x7f;&|`$<>\\\"'*?\[\]{}()!#]")


def normalize_rnode_tcp_port(port: str) -> str:
    """Normalize RNodeInterface port when using tcp://.

    Reticulum's TCPConnection (RNS/Interfaces/RNodeInterface.py) calls
    socket.getaddrinfo(target_host, 7633). The first argument must be a hostname or IP **only**; an embedded :port
    breaks resolution. Config may list legacy tcp://host:7633 or tcp://host:;
    strip those so storage matches tcp://<host>.
    """
    raw = str(port).strip()
    low = raw.lower()
    scheme = "tcp://"
    if not low.startswith(scheme):
        return raw
    rest = raw[len(scheme) :].strip()
    while rest.endswith(":"):
        rest = rest[:-1]
    if not rest:
        return scheme
    if rest.startswith("["):
        close = rest.find("]")
        if close != -1 and len(rest) > close + 1 and rest[close + 1] == ":":
            tail = rest[close + 2 :]
            if tail.isdigit() and 1 <= int(tail) <= 65535:
                rest = rest[: close + 1]
        return scheme + rest
    m = _IPV4_HOST_PORT.match(rest)
    if m and int(m.group(2)) <= 65535:
        rest = m.group(1)
    elif rest.count(":") == 1:
        head, tail = rest.split(":", 1)
        if tail.isdigit() and 1 <= int(tail) <= 65535:
            rest = head
    return scheme + rest


def coerce_rnode_frequency_hz(value):
    """Return RNode carrier frequency as integer Hz for Reticulum config.

    Reticulum reads frequency with int(); MHz-style decimals (868.825)
    must not be stored verbatim or they truncate to invalid values. Accepts
    Hz integers, bare MHz-style numbers below 1e6, and strings with optional
    ghz/mhz/khz/hz suffix (ASCII, case-insensitive).
    """
    if value is None or value == "":
        return value
    raw = str(value).strip()
    s = raw.lower().replace("_", "")
    mult = 1.0
    for suffix, m in (("ghz", 1e9), ("mhz", 1e6), ("khz", 1e3), ("hz", 1.0)):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            mult = m
            break
    f = float(s) * mult
    if f <= 0:
        return int(round(f))
    if f >= 1_000_000:
        return int(round(f))
    is_integer = abs(f - round(f)) < 1e-9
    if (not is_integer) or (is_integer and f < 10_000):
        f *= 1_000_000.0
    return int(round(f))


RNODE_TXPOWER_MIN = 0
RNODE_TXPOWER_MAX = 37


def normalize_rnode_txpower(value):
    """Return integer dBm for Reticulum RNodeInterface config."""
    if value is None or value == "":
        return value
    return int(float(str(value).strip()))


def validate_rnode_txpower(value) -> str | None:
    """Return an API error message when TX power is invalid for Reticulum."""
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
    coerce_rnode_frequency_hz = staticmethod(coerce_rnode_frequency_hz)
    normalize_rnode_tcp_port = staticmethod(normalize_rnode_tcp_port)
    normalize_rnode_txpower = staticmethod(normalize_rnode_txpower)
    validate_rnode_txpower = staticmethod(validate_rnode_txpower)

    @staticmethod
    def sanitize_interface_section_name(name: str | None) -> str:
        """Make a name safe for Reticulum/ConfigObj [[section]] headers.

        Square brackets break ConfigObj nesting and can leave the in-memory
        interfaces map dirty after a failed write, blocking later adds.
        """
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
        """Persist fixed_mtu when valid; return an API error message otherwise."""
        value = data.get("fixed_mtu")
        if value is None or value == "":
            interface_details.pop("fixed_mtu", None)
            return None
        try:
            mtu = int(value)
        except (TypeError, ValueError):
            return "fixed_mtu must be a positive integer"
        min_mtu = InterfaceEditor.minimum_fixed_mtu()
        if mtu < min_mtu:
            return (
                f"fixed_mtu must be at least {min_mtu} bytes "
                f"(Reticulum minimum MTU; values below this prevent startup)"
            )
        interface_details["fixed_mtu"] = mtu
        return None

    @staticmethod
    def update_value(interface_details: dict, data: dict, key: str):
        # update value if provided and not empty
        value = data.get(key)
        if value is not None and value != "":
            interface_details[key] = value
            return

        # otherwise remove existing value
        interface_details.pop(key, None)

    @staticmethod
    def normalize_interface_mode(value) -> str | None:
        """Return a canonical Reticulum mode string, or None when unset."""
        if value is None or value == "":
            return None
        mode = str(value).strip().lower()
        if mode not in ALLOWED_INTERFACE_MODES:
            return None
        return _INTERFACE_MODE_CANONICAL.get(mode, mode)

    @staticmethod
    def apply_interface_mode(interface_details: dict, data: dict) -> str | None:
        """Persist mode when valid. Return an API error message otherwise."""
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
    def request_yes_no(value) -> str | None:
        """Map common truthy/falsey request values to Reticulum yes/no."""
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return "yes" if value else "no"
        s = str(value).strip().lower()
        if s in _YES_NO_TRUE:
            return "yes"
        if s in _YES_NO_FALSE:
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
        """Persist a Reticulum yes/no option. Return error text on bad input.

        When the key is absent from data, leave existing config alone unless
        default_when_missing is set (then write that yes/no or pop when None).
        """
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
    def validate_location_cmd(value) -> str | None:
        """Return an error when location_cmd is unsafe for RNS Discovery exec."""
        if value is None or value == "":
            return None
        raw = str(value).strip()
        if not raw:
            return None
        if _LOCATION_CMD_FORBIDDEN.search(raw):
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
        """Persist discovery location_cmd when valid."""
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
        """Persist a numeric option with bounds. Return error text if invalid."""
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
        """Persist BackboneInterface fast-flapping options (RNS 1.4.0)."""
        err = InterfaceEditor.apply_yes_no_option(
            interface_details,
            data,
            "block_fast_flapping",
        )
        if err:
            return err
        err = InterfaceEditor.apply_positive_number(
            interface_details,
            data,
            "fast_flapping_block_time",
            as_int=True,
            minimum=1,
            maximum=60 * 24 * 30,
        )
        if err:
            return err
        err = InterfaceEditor.apply_positive_number(
            interface_details,
            data,
            "fast_flapping_threshold",
            as_int=False,
            minimum=0.1,
            maximum=3600,
        )
        if err:
            return err
        return InterfaceEditor.apply_positive_number(
            interface_details,
            data,
            "fast_flapping_grace",
            as_int=True,
            minimum=0,
            maximum=10_000,
        )

    @staticmethod
    def sanitize_imported_rns_options(iface_body: dict) -> str | None:
        """Normalize/validate RNS 1.3.7+ options on import. Return error or None."""
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
