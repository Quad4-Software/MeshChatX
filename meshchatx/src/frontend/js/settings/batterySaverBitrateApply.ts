// SPDX-License-Identifier: 0BSD

import type { ApiClient } from "../apiClient.js";
import { buildBitrateApplyPayload, loadBatterySaverPrefs, saveBatterySaverPrefs } from "./batterySaverPrefs.js";

export type BatterySaverBitrateOpts = {
    api?: Pick<ApiClient, "get" | "post">;
    reload?: boolean;
};

export type BatterySaverBitrateResult = {
    updated: string[];
    reloaded: boolean;
};

/** Apply configured battery-saver bitrate caps and optionally reload RNS. */
export async function applyBatterySaverBitrateLimits(
    opts: BatterySaverBitrateOpts = {}
): Promise<BatterySaverBitrateResult> {
    const api =
        opts.api ||
        (typeof window !== "undefined" ? (window as unknown as { api?: Pick<ApiClient, "get" | "post"> }).api : null);
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
    const interfaces = (listResp?.data as { interfaces?: Record<string, unknown> })?.interfaces || {};
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
        updated: (resp?.data as { updated?: string[] })?.updated || Object.keys(bitrates),
        reloaded: Boolean((resp?.data as { reloaded?: boolean })?.reloaded),
    };
}

/** Restore bitrates saved before the last apply, then reload RNS. */
export async function restoreBatterySaverBitrateLimits(
    opts: BatterySaverBitrateOpts = {}
): Promise<BatterySaverBitrateResult> {
    const api =
        opts.api ||
        (typeof window !== "undefined" ? (window as unknown as { api?: Pick<ApiClient, "get" | "post"> }).api : null);
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
        updated: (resp?.data as { updated?: string[] })?.updated || Object.keys(previous),
        reloaded: Boolean((resp?.data as { reloaded?: boolean })?.reloaded),
    };
}
