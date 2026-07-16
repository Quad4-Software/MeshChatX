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

/**
 * @typedef {object} DeviceBatteryStatus
 * @property {boolean} supported
 * @property {number|null} level Percent 0-100, or null when unknown
 * @property {boolean|null} charging
 * @property {"android"|"electron"|"web"|null} source
 */

/**
 * @param {unknown} value
 * @param {{ unitFraction?: boolean }} [options]
 * @returns {number|null}
 */
export function normalizeBatteryPercent(value, options = {}) {
    if (value == null || value === "") {
        return null;
    }
    const n = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(n)) {
        return null;
    }
    const unitFraction = Boolean(options.unitFraction);
    let pct;
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

/**
 * @param {unknown} raw
 * @param {"android"|"electron"|"web"|null} source
 * @returns {DeviceBatteryStatus|null}
 */
export function normalizeBatteryStatus(raw, source = null) {
    if (raw == null || typeof raw !== "object" || Array.isArray(raw)) {
        return null;
    }
    const resolvedSource = source || raw.source || null;
    const level = normalizeBatteryPercent(raw.level ?? raw.percent ?? raw.charge_percent ?? raw.capacity, {
        unitFraction: resolvedSource === "web",
    });
    let charging = null;
    if (typeof raw.charging === "boolean") {
        charging = raw.charging;
    } else if (raw.charging === 1 || raw.charging === "1" || raw.charging === "true") {
        charging = true;
    } else if (raw.charging === 0 || raw.charging === "0" || raw.charging === "false") {
        charging = false;
    } else if (typeof raw.on_battery === "boolean") {
        charging = !raw.on_battery;
    } else if (typeof raw.is_charging === "boolean") {
        charging = raw.is_charging;
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

/**
 * @param {string|object|null|undefined} payload
 * @returns {DeviceBatteryStatus|null}
 */
export function parseAndroidBatteryPayload(payload) {
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

/**
 * @returns {Promise<DeviceBatteryStatus|null>}
 */
async function probeAndroidBattery() {
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

/**
 * @returns {Promise<DeviceBatteryStatus|null>}
 */
async function probeElectronBattery() {
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

/**
 * @returns {Promise<DeviceBatteryStatus|null>}
 */
async function probeWebBattery() {
    if (typeof navigator === "undefined" || typeof navigator.getBattery !== "function") {
        return null;
    }
    try {
        const battery = await navigator.getBattery();
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
 *
 * @param {{ allowWeb?: boolean }} [options]
 * @returns {Promise<DeviceBatteryStatus|null>}
 */
export async function getDeviceBatteryStatus(options = {}) {
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

/**
 * Material icon name for a battery reading.
 *
 * @param {DeviceBatteryStatus|null|undefined} status
 * @returns {string}
 */
export function batteryStatusIconName(status) {
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

/**
 * Whether a reading came from a native host shell (not browser fakes).
 *
 * @param {DeviceBatteryStatus|null|undefined} status
 * @returns {boolean}
 */
export function isNativeBatteryStatus(status) {
    return Boolean(status && status.supported && (status.source === "android" || status.source === "electron"));
}

/**
 * Format a process create_time (unix seconds) as a short uptime label.
 *
 * @param {unknown} createTime
 * @param {number} [nowMs]
 * @returns {string|null}
 */
export function formatProcessUptime(createTime, nowMs = Date.now()) {
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

/**
 * @typedef {object} AppBatteryUsage
 * @property {number|null} [estimated_percent_per_hour]
 * @property {string|null} [intensity]
 * @property {number|null} [machine_share_percent]
 * @property {number|null} [avg_cpu_percent]
 * @property {string|null} [confidence]
 */

/**
 * Primary label for estimated MeshChatX battery drain.
 *
 * @param {AppBatteryUsage|null|undefined} usage
 * @param {(key: string, values?: object) => string} t
 * @returns {string|null}
 */
export function formatAppBatteryUsageLabel(usage, t) {
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

/**
 * Secondary label for MeshChatX share of device CPU capacity.
 *
 * @param {AppBatteryUsage|null|undefined} usage
 * @param {(key: string, values?: object) => string} t
 * @returns {string|null}
 */
export function formatAppBatteryShareLabel(usage, t) {
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

/**
 * Tone class for estimated drain intensity.
 *
 * @param {AppBatteryUsage|null|undefined} usage
 * @returns {string}
 */
export function appBatteryUsageToneClass(usage) {
    const intensity = usage?.intensity;
    if (intensity === "very_high" || intensity === "high") {
        return "text-amber-700 dark:text-amber-300";
    }
    if (intensity === "moderate") {
        return "text-sky-700 dark:text-sky-300";
    }
    return "";
}
