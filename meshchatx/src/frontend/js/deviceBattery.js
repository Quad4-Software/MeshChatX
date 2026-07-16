// SPDX-License-Identifier: 0BSD

/**
 * Host device battery probe for laptops and mobile.
 *
 * Order: Android bridge, Electron IPC, then Chromium Battery Status API.
 * Returns null when the runtime cannot expose battery state.
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
 * Read current host battery status when the platform supports it.
 *
 * @returns {Promise<DeviceBatteryStatus|null>}
 */
export async function getDeviceBatteryStatus() {
    const androidStatus = await probeAndroidBattery();
    if (androidStatus) {
        return androidStatus;
    }
    const electronStatus = await probeElectronBattery();
    if (electronStatus) {
        return electronStatus;
    }
    return probeWebBattery();
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
 * Whether the header chip should be visible.
 *
 * @param {DeviceBatteryStatus|null|undefined} status
 * @returns {boolean}
 */
export function shouldShowBatteryChip(status) {
    return Boolean(status && status.supported && status.level != null);
}
