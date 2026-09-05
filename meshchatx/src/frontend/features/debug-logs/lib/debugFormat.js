// SPDX-License-Identifier: 0BSD

/**
 * @param {unknown} timestamp
 * @returns {string}
 */
export function formatDebugTime(timestamp) {
    try {
        const ts = typeof timestamp === "number" ? timestamp * 1000 : timestamp;
        return new Date(ts).toLocaleString();
    } catch {
        return String(timestamp);
    }
}

/**
 * @param {string} level
 * @returns {string}
 */
export function debugLevelClass(level) {
    const l = String(level || "").toUpperCase();
    if (l === "ERROR" || l === "CRITICAL") return "text-red-500";
    if (l === "WARNING") return "text-orange-500";
    if (l === "INFO") return "text-blue-500";
    if (l === "DEBUG") return "text-gray-500";
    return "text-gray-400";
}

/**
 * @param {object} log
 * @param {(ts: unknown) => string} formatTime
 * @returns {string}
 */
export function formatLogLine(log, formatTime = formatDebugTime) {
    return `${formatTime(log.timestamp)} [${log.level}] [${log.module}] ${log.message}${log.is_anomaly ? " [ANOMALY:" + (log.anomaly_type || "unknown") + "]" : ""}`;
}
