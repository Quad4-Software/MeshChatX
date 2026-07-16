// SPDX-License-Identifier: 0BSD AND MIT

import { buildBitrateApplyPayload, loadBatterySaverPrefs, saveBatterySaverPrefs } from "./batterySaverPrefs.js";

/**
 * Apply configured battery-saver bitrate caps and optionally reload RNS.
 * @param {{ api?: { get: Function, post: Function }, reload?: boolean }} [opts]
 * @returns {Promise<{ updated: string[], reloaded: boolean }>}
 */
export async function applyBatterySaverBitrateLimits(opts = {}) {
    const api = opts.api || (typeof window !== "undefined" ? window.api : null);
    if (!api) {
        throw new Error("API client unavailable");
    }
    const prefs = loadBatterySaverPrefs();
    if (!prefs.applyInterfaceBitrateLimits) {
        return { updated: [], reloaded: false };
    }
    const limits = prefs.interfaceBitrateLimits || {};
    if (Object.keys(limits).length === 0) {
        return { updated: [], reloaded: false };
    }

    const listResp = await api.get("/api/v1/reticulum/interfaces");
    const interfaces = listResp?.data?.interfaces || {};
    const { bitrates, previous } = buildBitrateApplyPayload(interfaces, limits);
    if (Object.keys(bitrates).length === 0) {
        return { updated: [], reloaded: false };
    }

    const reload = opts.reload !== false;
    const resp = await api.post("/api/v1/reticulum/interfaces/bitrates", {
        bitrates,
        reload,
    });
    saveBatterySaverPrefs({
        interfaceBitratePrevious: {
            ...prefs.interfaceBitratePrevious,
            ...previous,
        },
    });
    return {
        updated: resp?.data?.updated || Object.keys(bitrates),
        reloaded: Boolean(resp?.data?.reloaded),
    };
}

/**
 * Restore bitrates saved before the last apply, then reload RNS.
 * @param {{ api?: { post: Function }, reload?: boolean }} [opts]
 */
export async function restoreBatterySaverBitrateLimits(opts = {}) {
    const api = opts.api || (typeof window !== "undefined" ? window.api : null);
    if (!api) {
        throw new Error("API client unavailable");
    }
    const prefs = loadBatterySaverPrefs();
    const previous = prefs.interfaceBitratePrevious || {};
    if (Object.keys(previous).length === 0) {
        return { updated: [], reloaded: false };
    }
    const reload = opts.reload !== false;
    const resp = await api.post("/api/v1/reticulum/interfaces/bitrates", {
        bitrates: previous,
        reload,
    });
    saveBatterySaverPrefs({ interfaceBitratePrevious: {} });
    return {
        updated: resp?.data?.updated || Object.keys(previous),
        reloaded: Boolean(resp?.data?.reloaded),
    };
}
