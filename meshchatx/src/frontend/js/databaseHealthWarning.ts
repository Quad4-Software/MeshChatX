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

export function resetDatabaseHealthWarningState(): void {
    lastFingerprint = "";
}

export function resetDatabaseHealthWarningStateForTests(): void {
    lastFingerprint = "";
}

export function fingerprintDatabaseHealthIssues(issues: unknown): string {
    if (!Array.isArray(issues) || issues.length === 0) {
        return "";
    }
    const parts: string[] = [];
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

export type ToastWarningUtils = {
    warning: (message: string, duration?: number, key?: string | null) => void;
};

/** Returns true when a toast was shown. */
export function showDatabaseHealthIssuesToastIfNeeded(
    issues: unknown,
    toastUtils: ToastWarningUtils | null | undefined
): boolean {
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
