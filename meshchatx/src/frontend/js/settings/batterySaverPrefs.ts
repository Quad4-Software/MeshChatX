// SPDX-License-Identifier: 0BSD

/**
 * Battery saver preferences (localStorage).
 * Safe UI/runtime throttles plus optional forced interface bitrates.
 */

import GlobalEmitter from "../GlobalEmitter";

export const BATTERY_SAVER_STORAGE_KEY = "meshchatx.batterySaver";
export const BATTERY_SAVER_CHANGED_EVENT = "battery-saver-prefs-changed";

/** @typedef {object} BatterySaverPrefs
 * @property {boolean} enabled
 * @property {boolean} disableVisualiserDiscovery
 * @property {boolean} hideOfflineInterfaces
 * @property {number} maxVisualiserInterfaces 0 = unlimited
 * @property {number} visualiserReloadSeconds 0 = disable auto-reload while saver on
 * @property {boolean} disableVisualiserLiveLayout
 * @property {boolean} reduceBackgroundPolling
 * @property {number} backgroundPollMultiplier
 * @property {boolean} reduceInterfacesDiscovery
 * @property {number} interfacesStatsPollSeconds
 * @property {number} interfacesDiscoveryPollSeconds
 * @property {boolean} applyInterfaceBitrateLimits
 * @property {Record<string, number>} interfaceBitrateLimits name -> bps
 * @property {Record<string, number|null>} interfaceBitratePrevious snapshot before apply
 */

/** @type {BatterySaverPrefs} */
export const BATTERY_SAVER_DEFAULTS = Object.freeze({
    enabled: false,
    disableVisualiserDiscovery: true,
    hideOfflineInterfaces: true,
    maxVisualiserInterfaces: 8,
    visualiserReloadSeconds: 60,
    disableVisualiserLiveLayout: true,
    reduceBackgroundPolling: true,
    backgroundPollMultiplier: 3,
    reduceInterfacesDiscovery: true,
    interfacesStatsPollSeconds: 5,
    interfacesDiscoveryPollSeconds: 30,
    applyInterfaceBitrateLimits: false,
    interfaceBitrateLimits: Object.freeze({}),
    interfaceBitratePrevious: Object.freeze({}),
});

/**
 * @param {unknown} raw
 * @returns {Record<string, number>}
 */
export function normalizeBitrateLimitsMap(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        return {};
    }
    /** @type {Record<string, number>} */
    const out: any = {};
    for (const [name, value] of Object.entries(raw)) {
        const key = String(name || "").trim();
        if (!key) continue;
        const bps = Number(value);
        if (!Number.isFinite(bps) || bps < 0) continue;
        out[key] = Math.round(bps);
    }
    return out;
}

/**
 * @param {unknown} raw
 * @returns {Record<string, number|null>}
 */
export function normalizeBitratePreviousMap(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        return {};
    }
    /** @type {Record<string, number|null>} */
    const out: any = {};
    for (const [name, value] of Object.entries(raw)) {
        const key = String(name || "").trim();
        if (!key) continue;
        if (value == null || value === "") {
            out[key] = null;
            continue;
        }
        const bps = Number(value);
        if (!Number.isFinite(bps) || bps < 0) continue;
        out[key] = Math.round(bps);
    }
    return out;
}

/**
 * @param {unknown} raw
 * @returns {BatterySaverPrefs}
 */
export function normalizeBatterySaverPrefs(raw) {
    const src = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
    const mult = Number(src.backgroundPollMultiplier);
    const maxIfaces = Number(src.maxVisualiserInterfaces);
    const vizReload = Number(src.visualiserReloadSeconds);
    const statsPoll = Number(src.interfacesStatsPollSeconds);
    const discPoll = Number(src.interfacesDiscoveryPollSeconds);
    return {
        enabled: src.enabled === true,
        disableVisualiserDiscovery: src.disableVisualiserDiscovery !== false,
        hideOfflineInterfaces: src.hideOfflineInterfaces !== false,
        maxVisualiserInterfaces: Number.isFinite(maxIfaces)
            ? Math.max(0, Math.min(128, Math.round(maxIfaces)))
            : BATTERY_SAVER_DEFAULTS.maxVisualiserInterfaces,
        visualiserReloadSeconds: Number.isFinite(vizReload)
            ? Math.max(0, Math.min(600, Math.round(vizReload)))
            : BATTERY_SAVER_DEFAULTS.visualiserReloadSeconds,
        disableVisualiserLiveLayout: src.disableVisualiserLiveLayout !== false,
        reduceBackgroundPolling: src.reduceBackgroundPolling !== false,
        backgroundPollMultiplier: Number.isFinite(mult)
            ? Math.max(2, Math.min(10, Math.round(mult)))
            : BATTERY_SAVER_DEFAULTS.backgroundPollMultiplier,
        reduceInterfacesDiscovery: src.reduceInterfacesDiscovery !== false,
        interfacesStatsPollSeconds: Number.isFinite(statsPoll)
            ? Math.max(1, Math.min(120, Math.round(statsPoll)))
            : BATTERY_SAVER_DEFAULTS.interfacesStatsPollSeconds,
        interfacesDiscoveryPollSeconds: Number.isFinite(discPoll)
            ? Math.max(5, Math.min(300, Math.round(discPoll)))
            : BATTERY_SAVER_DEFAULTS.interfacesDiscoveryPollSeconds,
        applyInterfaceBitrateLimits: src.applyInterfaceBitrateLimits === true,
        interfaceBitrateLimits: normalizeBitrateLimitsMap(src.interfaceBitrateLimits),
        interfaceBitratePrevious: normalizeBitratePreviousMap(src.interfaceBitratePrevious),
    };
}

/**
 * @returns {BatterySaverPrefs}
 */
export function loadBatterySaverPrefs() {
    try {
        if (typeof localStorage === "undefined") {
            return { ...BATTERY_SAVER_DEFAULTS, interfaceBitrateLimits: {}, interfaceBitratePrevious: {} };
        }
        const raw = localStorage.getItem(BATTERY_SAVER_STORAGE_KEY);
        if (raw == null || raw === "") {
            return { ...BATTERY_SAVER_DEFAULTS, interfaceBitrateLimits: {}, interfaceBitratePrevious: {} };
        }
        return normalizeBatterySaverPrefs(JSON.parse(raw));
    } catch {
        return { ...BATTERY_SAVER_DEFAULTS, interfaceBitrateLimits: {}, interfaceBitratePrevious: {} };
    }
}

/**
 * @param {Partial<BatterySaverPrefs>} patch
 * @returns {BatterySaverPrefs}
 */
export function saveBatterySaverPrefs(patch) {
    const next = normalizeBatterySaverPrefs({ ...loadBatterySaverPrefs(), ...patch });
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem(BATTERY_SAVER_STORAGE_KEY, JSON.stringify(next));
        }
    } catch {
        /* ignore */
    }
    GlobalEmitter.emit(BATTERY_SAVER_CHANGED_EVENT, next);
    return next;
}

/**
 * @param {number} baseMs
 * @param {BatterySaverPrefs} [prefs]
 * @returns {number}
 */
export function applyBackgroundPollInterval(baseMs, prefs = loadBatterySaverPrefs()) {
    const base = Number(baseMs);
    if (!Number.isFinite(base) || base <= 0) {
        return baseMs;
    }
    if (!prefs.enabled || !prefs.reduceBackgroundPolling) {
        return base;
    }
    return Math.round(base * prefs.backgroundPollMultiplier);
}

/**
 * Effective visualiser auto-reload interval in ms, or null to disable.
 * @param {number} defaultMs
 * @param {BatterySaverPrefs} [prefs]
 * @returns {number|null}
 */
export function effectiveVisualiserReloadMs(defaultMs, prefs = loadBatterySaverPrefs()) {
    if (!prefs.enabled) {
        return defaultMs;
    }
    if (prefs.visualiserReloadSeconds <= 0) {
        return null;
    }
    return prefs.visualiserReloadSeconds * 1000;
}

/**
 * @param {BatterySaverPrefs} [prefs]
 * @returns {string[]}
 */
export function activeBatterySaverMeasures(prefs = loadBatterySaverPrefs()) {
    if (!prefs.enabled) {
        return [];
    }
    const out = [];
    if (prefs.disableVisualiserDiscovery) out.push("disableVisualiserDiscovery");
    if (prefs.hideOfflineInterfaces) out.push("hideOfflineInterfaces");
    if (prefs.maxVisualiserInterfaces > 0) out.push("maxVisualiserInterfaces");
    if (prefs.visualiserReloadSeconds === 0) out.push("disableVisualiserAutoReload");
    else if (prefs.visualiserReloadSeconds > 15) out.push("slowVisualiserReload");
    if (prefs.disableVisualiserLiveLayout) out.push("disableVisualiserLiveLayout");
    if (prefs.reduceBackgroundPolling) out.push("reduceBackgroundPolling");
    if (prefs.reduceInterfacesDiscovery) out.push("reduceInterfacesDiscovery");
    if (prefs.applyInterfaceBitrateLimits && Object.keys(prefs.interfaceBitrateLimits || {}).length > 0) {
        out.push("applyInterfaceBitrateLimits");
    }
    return out;
}

/**
 * @param {Record<string, any>} interfacesMap
 * @param {Record<string, number>} limits
 * @returns {{ bitrates: Record<string, number>, previous: Record<string, number|null> }}
 */
export function buildBitrateApplyPayload(interfacesMap, limits) {
    const bitrates: any = {};
    const previous: any = {};
    const src = interfacesMap && typeof interfacesMap === "object" ? interfacesMap : {};
    const lim = normalizeBitrateLimitsMap(limits);
    for (const [name, bps] of Object.entries(lim)) {
        if (!(name in src)) continue;
        const current = src[name]?.bitrate;
        const parsed = current == null || current === "" ? null : Number(current);
        previous[name] = Number.isFinite(parsed) ? Math.round(parsed) : null;
        bitrates[name] = bps;
    }
    return { bitrates, previous };
}
