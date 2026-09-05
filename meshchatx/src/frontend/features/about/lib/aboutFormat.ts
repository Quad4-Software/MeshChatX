// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import type { AppInfo, SandboxFeatureCard } from "./types.js";

declare const __APP_BUILD_TIME__: string | undefined;

/**
 * Format app display version with dev suffix fallback
 */
export function formatDisplayVersion(info?: AppInfo | null): string {
    const data = info || {};
    if (data.display_version) {
        return data.display_version;
    }
    const base = data.version || "unknown";
    if (data.is_dev_build && !String(base).endsWith("-dev")) {
        return `${base}-dev`;
    }
    return base;
}

/**
 * Format UI build date string from build timestamp
 */
export function formatUiBuildDate(rawDate?: string): string {
    try {
        const raw = rawDate ?? (typeof __APP_BUILD_TIME__ !== "undefined" ? __APP_BUILD_TIME__ : "");
        if (!raw) {
            return "";
        }
        const d = new Date(raw);
        if (Number.isNaN(d.getTime())) {
            return raw;
        }
        return d.toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
        });
    } catch {
        return "";
    }
}

/**
 * Format CPU usage percentage
 */
export function formatCpuPercent(value: unknown): string {
    const n = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(n)) {
        return t("about.path_unknown");
    }
    return `${n.toFixed(n >= 10 ? 0 : 1)}%`;
}

/**
 * Format connected timestamp for active sessions
 */
export function formatSessionConnectedAt(value: unknown): string {
    const ts = Number(value);
    if (!Number.isFinite(ts) || ts <= 0) {
        return "unknown";
    }
    try {
        return new Date(ts * 1000).toLocaleString();
    } catch {
        return "unknown";
    }
}

/**
 * Format path table size label
 */
export function formatPathTableSize(stats?: AppInfo["reticulum_stats"]): string | null {
    const cleanup = stats?.memory_cleanup;
    const total = stats?.total_paths;
    const pathSize =
        cleanup && typeof cleanup === "object" && cleanup.path_table_size != null ? cleanup.path_table_size : total;
    if (pathSize == null) {
        return null;
    }
    return t("about.path_table_count", { count: pathSize });
}

/**
 * Format memory pressure label
 */
export function formatMemoryPressure(stats?: AppInfo["reticulum_stats"]): string {
    const cleanup = stats?.memory_cleanup;
    if (!cleanup || typeof cleanup !== "object") {
        return t("about.memory_pressure_normal");
    }
    if (cleanup.sqlite_relaxed) {
        return t("about.memory_pressure_relaxed");
    }
    return t("about.memory_pressure_normal");
}

/**
 * Memory pressure tone class
 */
export function memoryPressureToneClass(stats?: AppInfo["reticulum_stats"]): string {
    const cleanup = stats?.memory_cleanup;
    if (cleanup && typeof cleanup === "object" && cleanup.sqlite_relaxed) {
        return "text-amber-600 dark:text-amber-400";
    }
    return "opacity-70";
}

/**
 * Battery status text label
 */
export function batteryStatusLabel(
    batteryStatus: { supported?: boolean; level?: number | null; charging?: boolean | null } | null
): string {
    if (!batteryStatus || !batteryStatus.supported) {
        return t("about.env_battery_unavailable");
    }
    const level = batteryStatus.level != null ? `${batteryStatus.level}%` : t("about.path_unknown");
    if (batteryStatus.charging === true) {
        return t("about.env_battery_charging", { percent: level });
    }
    if (batteryStatus.charging === false) {
        return t("about.env_battery_on_battery", { percent: level });
    }
    return level;
}

/**
 * Battery status tone class
 */
export function batteryStatusToneClass(
    batteryStatus: { supported?: boolean; level?: number | null; charging?: boolean | null } | null
): string {
    if (!batteryStatus || !batteryStatus.supported) {
        return "opacity-70";
    }
    if (batteryStatus.charging) {
        return "text-emerald-600 dark:text-emerald-400";
    }
    const level = batteryStatus.level;
    if (level != null && level <= 15) {
        return "text-red-600 dark:text-red-400";
    }
    if (level != null && level <= 30) {
        return "text-amber-600 dark:text-amber-400";
    }
    return "";
}

/**
 * Status pill CSS class
 */
export function statusPillClass(isGood: boolean): string {
    return isGood
        ? "inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300 px-3 py-1 text-xs font-semibold"
        : "inline-flex items-center gap-1 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300 px-3 py-1 text-xs font-semibold";
}

/**
 * Sandbox feature card background and border class
 */
export function sandboxCardClass(card: SandboxFeatureCard): string {
    if (card.active) {
        return "border-emerald-500/35 bg-emerald-500/5 dark:bg-emerald-900/20";
    }
    if (card.warn) {
        return "border-amber-500/35 bg-amber-500/5 dark:bg-amber-950/20";
    }
    return "border-gray-200/60 dark:border-zinc-800/80";
}

/**
 * Sandbox feature card icon class
 */
export function sandboxIconClass(card: SandboxFeatureCard): string {
    if (card.active) {
        return "text-emerald-600 dark:text-emerald-400 border-emerald-500/35 bg-emerald-500/10";
    }
    if (card.unavailable) {
        return "text-sem-fg-muted border-gray-200/60 dark:border-zinc-800/80 bg-gray-50/70 dark:bg-zinc-900/40";
    }
    return "text-sem-fg-muted border-gray-200/60 dark:border-zinc-800/80";
}

/**
 * Sandbox feature card badge class
 */
export function sandboxBadgeClass(card: SandboxFeatureCard): string {
    if (card.active) {
        return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300";
    }
    if (card.unavailable) {
        return "bg-gray-100 text-gray-600 dark:bg-zinc-800 dark:text-gray-300";
    }
    if (card.warn) {
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300";
    }
    return "bg-gray-100 text-gray-600 dark:bg-zinc-800 dark:text-gray-300";
}
