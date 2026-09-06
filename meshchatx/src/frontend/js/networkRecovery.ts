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

export function networkErrorText(error: unknown): string {
    return String(error || "").trim();
}

export function isLikelyInterfaceRecoveryError(error: unknown): boolean {
    const text = networkErrorText(error).toLowerCase();
    if (!text) {
        return false;
    }
    if (isDatabaseRecoveryError(error)) {
        return false;
    }
    return INTERFACE_HINTS.some((hint) => text.includes(hint));
}

export function isDatabaseRecoveryError(error: unknown): boolean {
    const text = networkErrorText(error).toLowerCase();
    if (!text) {
        return false;
    }
    return DATABASE_RECOVERY_HINTS.some((hint) => text.includes(hint));
}

/**
 * Route name to open after degraded startup, or null to leave the user on the
 * current page (banner actions still apply).
 */
export function recoveryRouteForNetworkError(error: unknown): "interfaces" | null {
    if (isLikelyInterfaceRecoveryError(error)) {
        return "interfaces";
    }
    return null;
}

export type RecoveryLocation = {
    name: string;
    hash?: string;
};

/** Full route location for degraded startup when the UI should jump to recovery. */
export function recoveryLocationForNetworkError(error: unknown): RecoveryLocation | null {
    if (isDatabaseRecoveryError(error)) {
        return { name: "about", hash: "#about-database-backups" };
    }
    const routeName = recoveryRouteForNetworkError(error);
    if (routeName) {
        return { name: routeName };
    }
    return null;
}
