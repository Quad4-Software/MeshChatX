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

const DATABASE_RECOVERY_HINTS = [
    "database version",
    "newer than this meshchatx build",
    "database initialization failed",
    "schema migration",
    "restore a backup",
    "databasetoonew",
    "premigrationbackup",
    "postmigrationverification",
    "quick_check failed",
    "integrity failure",
];

/**
 * @param {unknown} error
 * @returns {string}
 */
export function networkErrorText(error) {
    return String(error || "").trim();
}

/**
 * @param {unknown} error
 * @returns {boolean}
 */
export function isLikelyInterfaceRecoveryError(error) {
    const text = networkErrorText(error).toLowerCase();
    if (!text) {
        return false;
    }
    if (isDatabaseRecoveryError(error)) {
        return false;
    }
    return INTERFACE_HINTS.some((hint) => text.includes(hint));
}

/**
 * @param {unknown} error
 * @returns {boolean}
 */
export function isDatabaseRecoveryError(error) {
    const text = networkErrorText(error).toLowerCase();
    if (!text) {
        return false;
    }
    return DATABASE_RECOVERY_HINTS.some((hint) => text.includes(hint));
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

/**
 * Full route location for degraded startup when the UI should jump to recovery.
 * @param {unknown} error
 * @returns {{ name: string, hash?: string } | null}
 */
export function recoveryLocationForNetworkError(error) {
    if (isDatabaseRecoveryError(error)) {
        return { name: "about", hash: "#about-database-backups" };
    }
    const routeName = recoveryRouteForNetworkError(error);
    if (routeName) {
        return { name: routeName };
    }
    return null;
}
