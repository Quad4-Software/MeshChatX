// SPDX-License-Identifier: 0BSD

/**
 * Classify mesh startup / degraded errors for recovery UI.
 * Not every failure is an interface config problem.
 */

const INTERFACE_HINTS = [
    "interface",
    "interfaces",
    "rnode",
    "serial",
    "usb",
    "autointerface",
    "tcpclient",
    "udp",
    "i2p",
    "wlan",
    "kiss",
    "ax25",
    "pipeinterface",
    "rns config",
    "configobj",
];

/**
 * @param {unknown} error
 * @returns {boolean}
 */
export function isLikelyInterfaceRecoveryError(error) {
    const text = String(error || "").toLowerCase();
    if (!text) {
        return false;
    }
    return INTERFACE_HINTS.some((hint) => text.includes(hint));
}

/**
 * Route name to open after degraded startup, or null to leave the user on the
 * current page (banner actions still apply).
 * @param {unknown} error
 * @returns {"interfaces" | null}
 */
export function recoveryRouteForNetworkError(error) {
    if (isLikelyInterfaceRecoveryError(error)) {
        return "interfaces";
    }
    return null;
}
