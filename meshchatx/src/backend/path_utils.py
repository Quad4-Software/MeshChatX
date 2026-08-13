# SPDX-License-Identifier: 0BSD

import RNS

MIN_WINDOW_BITRATE = 50
PATH_EXCHANGE_BYTES = 240


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


def path_response_window(destination_hash, reticulum=None) -> float:
    if reticulum is None:
        reticulum = RNS.Reticulum.get_instance()
    window = float(reticulum.get_first_hop_timeout(destination_hash))
    bitrate = slowest_online_bitrate(reticulum)
    if bitrate:
        window = max(
            window,
            2 * (PATH_EXCHANGE_BYTES * 8 / max(bitrate, MIN_WINDOW_BITRATE)) + 10,
        )
    return max(window, float(RNS.Transport.PATH_REQUEST_TIMEOUT))
