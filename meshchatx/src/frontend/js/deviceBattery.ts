// SPDX-License-Identifier: 0BSD

/**
 * Host device battery probe for laptops and mobile shells.
 *
 * Order: Android bridge, then Electron IPC.
 * The Chromium Battery Status API is opt-in only. Headless and Docker
 * Chromium builds often report a fake "charging 100%" reading.
 */

import AndroidBridge from "./rnode/AndroidBridge.js";
import ElectronUtils from "./ElectronUtils.js";

export interface DeviceBatteryStatus {
    supported: boolean;
    level: number | null; // Percent 0-100, or null when unknown
    charging: boolean | null;
    source: "android" | "electron" | "web" | null;
}

export function normalizeBatteryPercent(value: unknown, options: { unitFraction?: boolean } = {}): number | null {
    if (value == null || value === "") {
        return null;
    }
    const n = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(n)) {
        return null;
    }
    const unitFraction = Boolean(options.unitFraction);
    let pct: number;
    if (unitFraction) {
        // Chromium Battery Status API: 0.0-1.0
        pct = n * 100;
    } else if (n > 0 && n < 1) {
        // Ambiguous float without an explicit scale: treat as a fraction.
        pct = n * 100;
    } else {
        // Native bridges report whole percents (including 0, 1, and 100).
        pct = n;
    }
    if (pct < 0 || pct > 100) {
        return null;
    }
    return Math.round(pct);
}

export function normalizeBatteryStatus(
    raw: unknown,
    source: "android" | "electron" | "web" | null = null
): DeviceBatteryStatus | null {
    if (raw == null || typeof raw !== "object" || Array.isArray(raw)) {
        return null;
    }
    const r = raw as Record<string, any>;
    const resolvedSource = source || r.source || null;
    const level = normalizeBatteryPercent(r.level ?? r.percent ?? r.charge_percent ?? r.capacity, {
        unitFraction: resolvedSource === "web",
    });
    let charging: boolean | null = null;
    if (typeof r.charging === "boolean") {
        charging = r.charging;
    } else if (r.charging === 1 || r.charging === "1" || r.charging === "true") {
        charging = true;
    } else if (r.charging === 0 || r.charging === "0" || r.charging === "false") {
        charging = false;
    } else if (typeof r.on_battery === "boolean") {
        charging = !r.on_battery;
    } else if (typeof r.is_charging === "boolean") {
        charging = r.is_charging;
    }
    if (level == null && charging == null) {
        return null;
    }
    return {
        supported: true,
        level,
        charging,
        source: resolvedSource,
    };
}

export function parseAndroidBatteryPayload(payload: string | object | null | undefined): DeviceBatteryStatus | null {
    if (payload == null || payload === "") {
        return null;
    }
    let raw = payload;
    if (typeof payload === "string") {
        try {
            raw = JSON.parse(payload);
        } catch {
            return null;
        }
    }
    return normalizeBatteryStatus(raw, "android");
}

async function probeAndroidBattery(): Promise<DeviceBatteryStatus | null> {
    try {
        const bridge = new AndroidBridge();
        if (!bridge.isAvailable()) {
            return null;
        }
        const payload = bridge.getBatteryStatus();
        return parseAndroidBatteryPayload(payload);
    } catch {
        return null;
    }
}

async function probeElectronBattery(): Promise<DeviceBatteryStatus | null> {
    if (!ElectronUtils.isElectron()) {
        return null;
    }
    try {
        const raw = await ElectronUtils.getBatteryStatus();
        return normalizeBatteryStatus(raw, "electron");
    } catch {
        return null;
    }
}

async function probeWebBattery(): Promise<DeviceBatteryStatus | null> {
    if (typeof navigator === "undefined" || typeof (navigator as any).getBattery !== "function") {
        return null;
    }
    try {
        const battery = await (navigator as any).getBattery();
        if (!battery) {
            return null;
        }
        return normalizeBatteryStatus(
            {
                level: battery.level,
                charging: battery.charging,
            },
            "web"
        );
    } catch {
        return null;
    }
}

/**
 * Read host battery when a native shell exposes it.
 *
 * Web Battery Status is off by default (Docker / headless Chromium lies).
 * Pass `{ allowWeb: true }` only when the caller accepts that risk.
 */
export async function getDeviceBatteryStatus(
    options: { allowWeb?: boolean } = {}
): Promise<DeviceBatteryStatus | null> {
    const allowWeb = Boolean(options.allowWeb);
    const androidStatus = await probeAndroidBattery();
    if (androidStatus) {
        return androidStatus;
    }
    const electronStatus = await probeElectronBattery();
    if (electronStatus) {
        return electronStatus;
    }
    if (allowWeb) {
        return probeWebBattery();
    }
    return null;
}

export function batteryStatusIconName(status: DeviceBatteryStatus | null | undefined): string {
    if (!status || !status.supported) {
        return "battery-unknown";
    }
    if (status.charging) {
        return "battery-charging";
    }
    const level = status.level;
    if (level == null) {
        return "battery";
    }
    if (level <= 15) {
        return "battery-alert";
    }
    if (level <= 30) {
        return "battery-low";
    }
    if (level >= 90) {
        return "battery";
    }
    return "battery-medium";
}

export function isNativeBatteryStatus(status: DeviceBatteryStatus | null | undefined): boolean {
    return Boolean(status && status.supported && (status.source === "android" || status.source === "electron"));
}

export function formatProcessUptime(createTime: unknown, nowMs = Date.now()): string | null {
    const started = typeof createTime === "number" ? createTime : Number(createTime);
    if (!Number.isFinite(started) || started <= 0) {
        return null;
    }
    const seconds = Math.max(0, Math.floor(nowMs / 1000 - started));
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (days > 0) {
        return `${days}d ${hours}h`;
    }
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    }
    return `${secs}s`;
}

export interface AppBatteryUsage {
    estimated_percent_per_hour?: number | null;
    intensity?: string | null;
    machine_share_percent?: number | null;
    avg_cpu_percent?: number | null;
    confidence?: string | null;
}

export function formatAppBatteryUsageLabel(
    usage: AppBatteryUsage | null | undefined,
    t: (key: string, values?: Record<string, unknown>) => string
): string | null {
    if (!usage || typeof usage !== "object") {
        return null;
    }
    if (usage.confidence === "warming_up" || usage.estimated_percent_per_hour == null) {
        return t("about.app_battery_use_warming");
    }
    const rate = Number(usage.estimated_percent_per_hour);
    if (!Number.isFinite(rate)) {
        return null;
    }
    const rateText = `${rate.toFixed(rate >= 10 ? 0 : 1)}%/hr`;
    if (usage.intensity) {
        return t("about.app_battery_use_with_intensity", {
            rate: rateText,
            intensity: t(`about.app_battery_intensity_${usage.intensity}`),
        });
    }
    return t("about.app_battery_use_rate", { rate: rateText });
}

export function formatAppBatteryShareLabel(
    usage: AppBatteryUsage | null | undefined,
    t: (key: string, values?: Record<string, unknown>) => string
): string | null {
    if (!usage || typeof usage !== "object") {
        return null;
    }
    const share = Number(usage.machine_share_percent);
    if (!Number.isFinite(share)) {
        return null;
    }
    return t("about.app_battery_share_value", {
        percent: share.toFixed(share >= 10 ? 0 : 1),
    });
}

export function appBatteryUsageToneClass(usage: AppBatteryUsage | null | undefined): string {
    const intensity = usage?.intensity;
    if (intensity === "very_high" || intensity === "high") {
        return "text-amber-700 dark:text-amber-300";
    }
    if (intensity === "moderate") {
        return "text-sky-700 dark:text-sky-300";
    }
    return "";
}
