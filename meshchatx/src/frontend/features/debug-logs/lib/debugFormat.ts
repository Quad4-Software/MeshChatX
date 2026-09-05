// SPDX-License-Identifier: 0BSD

export type DebugLogLine = {
    timestamp?: unknown;
    level?: string;
    module?: string;
    message?: string;
    is_anomaly?: boolean;
    anomaly_type?: string;
};

export function formatDebugTime(timestamp: unknown): string {
    try {
        const ts = typeof timestamp === "number" ? timestamp * 1000 : (timestamp as string | number | Date);
        return new Date(ts).toLocaleString();
    } catch {
        return String(timestamp);
    }
}

export function debugLevelClass(level: string): string {
    const l = String(level || "").toUpperCase();
    if (l === "ERROR" || l === "CRITICAL") return "text-red-500";
    if (l === "WARNING") return "text-orange-500";
    if (l === "INFO") return "text-blue-500";
    if (l === "DEBUG") return "text-gray-500";
    return "text-gray-400";
}

export function formatLogLine(log: DebugLogLine, formatTime: (ts: unknown) => string = formatDebugTime): string {
    return `${formatTime(log.timestamp)} [${log.level}] [${log.module}] ${log.message}${log.is_anomaly ? " [ANOMALY:" + (log.anomaly_type || "unknown") + "]" : ""}`;
}
