# SPDX-License-Identifier: 0BSD AND MIT


def coerce_rnode_frequency_hz(value):
    """Return RNode carrier frequency as integer Hz for Reticulum config.

    Reticulum reads ``frequency`` with ``int()``; MHz-style decimals (868.825)
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


class InterfaceEditor:
    coerce_rnode_frequency_hz = staticmethod(coerce_rnode_frequency_hz)

    @staticmethod
    def update_value(interface_details: dict, data: dict, key: str):
        # update value if provided and not empty
        value = data.get(key)
        if value is not None and value != "":
            interface_details[key] = value
            return

        # otherwise remove existing value
        interface_details.pop(key, None)
