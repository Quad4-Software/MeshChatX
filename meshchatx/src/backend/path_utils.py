# SPDX-License-Identifier: 0BSD

import RNS

# One path-request packet is about 234 bytes plus IFAC. 240 covers that.
PATH_EXCHANGE_BYTES = 240
LINK_ESTABLISHMENT_MARGIN_S = 5.0
_FALLBACK_PATH_TIMEOUT_S = 15.0


def min_window_bitrate() -> float:
    try:
        value = float(RNS.Reticulum.MINIMUM_BITRATE)
        if value > 0:
            return value
    except Exception:
        pass
    return 5.0


# Kept as a name for tests and callers. Equals RNS.Reticulum.MINIMUM_BITRATE (5).
MIN_WINDOW_BITRATE = min_window_bitrate()


def slowest_online_bitrate(reticulum=None):
    try:
        if reticulum is None:
            reticulum = RNS.Reticulum.get_instance()
        stats = reticulum.get_interface_stats()
        bitrates = [
            i["bitrate"]
            for i in stats["interfaces"]
            if i.get("status") and i.get("bitrate")
        ]
        if bitrates:
            return min(bitrates)
    except Exception:
        pass
    return None


def _rns_path_request_timeout() -> float:
    try:
        return float(RNS.Transport.PATH_REQUEST_TIMEOUT)
    except Exception:
        return _FALLBACK_PATH_TIMEOUT_S


def path_response_window(destination_hash, reticulum=None) -> float:
    """Seconds to wait for a cold path response on the slowest online interface.

    Uses Reticulum.get_first_hop_timeout so a shared rnsd client sees the
    instance interface timeouts, not the local socket timeout.
    """
    window = 0.0
    try:
        if reticulum is None:
            reticulum = RNS.Reticulum.get_instance()
        window = float(reticulum.get_first_hop_timeout(destination_hash))
    except Exception:
        window = 0.0
    bitrate = slowest_online_bitrate(reticulum)
    if bitrate:
        floor_bps = min_window_bitrate()
        window = max(
            window,
            2 * (PATH_EXCHANGE_BYTES * 8 / max(float(bitrate), floor_bps)) + 10,
        )
    return max(window, _rns_path_request_timeout())


def link_establishment_window(
    link,
    destination_hash=None,
    reticulum=None,
) -> float:
    """Seconds to wait for a new RNS Link, from link.establishment_timeout.

    Adds LINK_ESTABLISHMENT_MARGIN_S. Falls back to path_response_window
    when RNS did not report an establishment timeout.
    """
    rns_timeout = getattr(link, "establishment_timeout", None)
    if isinstance(rns_timeout, (int, float)) and rns_timeout > 0:
        return float(rns_timeout) + LINK_ESTABLISHMENT_MARGIN_S
    if destination_hash is not None:
        return path_response_window(destination_hash, reticulum)
    return _rns_path_request_timeout()
