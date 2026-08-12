// SPDX-License-Identifier: 0BSD

/**
 * Session-scoped database health toast gating.
 *
 * /api/v1/app/info is polled about every 15s. database_health_issues stay set
 * for the whole process after open, so showing a toast on every poll spams.
 * Show once per issue fingerprint per session. Identity switch resets.
 */

export const DATABASE_HEALTH_TOAST_KEY = "database-health-warning";
export const DATABASE_HEALTH_TOAST_DURATION_MS = 0;
export const DATABASE_HEALTH_FALLBACK_MESSAGE = "Database issue detected. Check About > Database.";

let lastFingerprint = "";

export function resetDatabaseHealthWarningState() {
    lastFingerprint = "";
}

export function resetDatabaseHealthWarningStateForTests() {
    lastFingerprint = "";
}

/**
 * @param {unknown} issues
 * @returns {string}
 */
export function fingerprintDatabaseHealthIssues(issues) {
    if (!Array.isArray(issues) || issues.length === 0) {
        return "";
    }
    const parts = [];
    for (const item of issues) {
        if (typeof item !== "string") {
            continue;
        }
        const trimmed = item.trim();
        if (trimmed) {
            parts.push(trimmed);
        }
    }
    return parts.join("\n");
}

/**
 * @param {unknown} issues
 * @param {{ warning: (message: string, duration?: number, key?: string | null) => void }} toastUtils
 * @returns {boolean} true when a toast was shown
 */
export function showDatabaseHealthIssuesToastIfNeeded(issues, toastUtils) {
    const fingerprint = fingerprintDatabaseHealthIssues(issues);
    if (!fingerprint) {
        lastFingerprint = "";
        return false;
    }
    if (fingerprint === lastFingerprint) {
        return false;
    }
    if (!toastUtils || typeof toastUtils.warning !== "function") {
        return false;
    }
    const message = fingerprint.replace(/\n/g, " ") || DATABASE_HEALTH_FALLBACK_MESSAGE;
    toastUtils.warning(message, DATABASE_HEALTH_TOAST_DURATION_MS, DATABASE_HEALTH_TOAST_KEY);
    lastFingerprint = fingerprint;
    return true;
}
