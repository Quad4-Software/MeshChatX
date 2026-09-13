// SPDX-License-Identifier: 0BSD

/**
 * Battery saver preferences (localStorage).
 * Safe UI/runtime throttles plus optional forced interface bitrates.
 */

import GlobalEmitter from "../GlobalEmitter";

export const BATTERY_SAVER_STORAGE_KEY = "meshchatx.batterySaver";
export const BATTERY_SAVER_CHANGED_EVENT = "battery-saver-prefs-changed";

export interface BatterySaverPrefs {
    enabled: boolean;
    disableVisualiserDiscovery: boolean;
    hideOfflineInterfaces: boolean;
    maxVisualiserInterfaces: number; // 0 = unlimited
    visualiserReloadSeconds: number; // 0 = disable auto-reload while saver on
    disableVisualiserLiveLayout: boolean;
    reduceBackgroundPolling: boolean;
    backgroundPollMultiplier: number;
    reduceInterfacesDiscovery: boolean;
    interfacesStatsPollSeconds: number;
    interfacesDiscoveryPollSeconds: number;
    applyInterfaceBitrateLimits: boolean;
    interfaceBitrateLimits: Record<string, number>; // name -> bps
    interfaceBitratePrevious: Record<string, number | null>; // snapshot before apply
}

export const BATTERY_SAVER_DEFAULTS: BatterySaverPrefs = Object.freeze({
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

export function normalizeBitrateLimitsMap(raw: unknown): Record<string, number> {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        return {};
    }
    const out: Record<string, number> = {};
    for (const [name, value] of Object.entries(raw as Record<string, unknown>)) {
        const key = String(name || "").trim();
        if (!key) continue;
        const bps = Number(value);
        if (!Number.isFinite(bps) || bps < 0) continue;
        out[key] = Math.round(bps);
    }
    return out;
}

export function normalizeBitratePreviousMap(raw: unknown): Record<string, number | null> {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        return {};
    }
    const out: Record<string, number | null> = {};
    for (const [name, value] of Object.entries(raw as Record<string, unknown>)) {
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

export function normalizeBatterySaverPrefs(raw: unknown): BatterySaverPrefs {
    const src = raw && typeof raw === "object" && !Array.isArray(raw) ? (raw as Record<string, any>) : {};
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

export function loadBatterySaverPrefs(): BatterySaverPrefs {
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

export function saveBatterySaverPrefs(patch: Partial<BatterySaverPrefs>): BatterySaverPrefs {
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

export function applyBackgroundPollInterval(
    baseMs: number,
    prefs: BatterySaverPrefs = loadBatterySaverPrefs()
): number {
    const base = Number(baseMs);
    if (!Number.isFinite(base) || base <= 0) {
        return baseMs;
    }
    if (!prefs.enabled || !prefs.reduceBackgroundPolling) {
        return base;
    }
    return Math.round(base * prefs.backgroundPollMultiplier);
}

export function effectiveVisualiserReloadMs(
    defaultMs: number,
    prefs: BatterySaverPrefs = loadBatterySaverPrefs()
): number | null {
    if (!prefs.enabled) {
        return defaultMs;
    }
    if (prefs.visualiserReloadSeconds <= 0) {
        return null;
    }
    return prefs.visualiserReloadSeconds * 1000;
}

export function activeBatterySaverMeasures(prefs?: any): string[] {
    const p = prefs || loadBatterySaverPrefs();
    if (!p?.enabled) {
        return [];
    }
    const out: string[] = [];
    if (p.disableVisualiserDiscovery) out.push("disableVisualiserDiscovery");
    if (p.hideOfflineInterfaces) out.push("hideOfflineInterfaces");
    if (p.maxVisualiserInterfaces > 0) out.push("maxVisualiserInterfaces");
    if (p.visualiserReloadSeconds === 0) out.push("disableVisualiserAutoReload");
    else if (p.visualiserReloadSeconds > 15) out.push("slowVisualiserReload");
    if (p.disableVisualiserLiveLayout) out.push("disableVisualiserLiveLayout");
    if (p.reduceBackgroundPolling) out.push("reduceBackgroundPolling");
    if (p.reduceInterfacesDiscovery) out.push("reduceInterfacesDiscovery");
    if (p.applyInterfaceBitrateLimits && Object.keys(p.interfaceBitrateLimits || {}).length > 0) {
        out.push("applyInterfaceBitrateLimits");
    }
    return out;
}

export function buildBitrateApplyPayload(
    interfacesMap: Record<string, any>,
    limits: Record<string, number>
): { bitrates: Record<string, number>; previous: Record<string, number | null> } {
    const bitrates: Record<string, number> = {};
    const previous: Record<string, number | null> = {};
    const src = interfacesMap && typeof interfacesMap === "object" ? interfacesMap : {};
    const lim = normalizeBitrateLimitsMap(limits);
    for (const [name, bps] of Object.entries(lim)) {
        if (!(name in src)) continue;
        const current = src[name]?.bitrate;
        const parsed = current == null || current === "" ? null : Number(current);
        previous[name] = Number.isFinite(parsed) && parsed !== null ? Math.round(parsed) : null;
        bitrates[name] = bps;
    }
    return { bitrates, previous };
}
