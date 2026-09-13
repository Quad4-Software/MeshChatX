// SPDX-License-Identifier: 0BSD

import GlobalState from "../../../js/GlobalState.js";
import {
    loadVisualiserDisplayPrefs,
    persistVisualiserAutoReload,
    persistVisualiserLiveLayout,
    persistVisualiserRenderer,
    persistVisualiserViewMode,
    VISUALISER_DISPLAY_PREFS_CHANGED,
} from "../../../js/settings/settingsVisualiserPrefs.js";
import { HOP_MAX_FILTER_STORAGE_KEY } from "./constants.js";

export {
    loadVisualiserDisplayPrefs,
    persistVisualiserAutoReload,
    persistVisualiserLiveLayout,
    persistVisualiserRenderer,
    persistVisualiserViewMode,
    VISUALISER_DISPLAY_PREFS_CHANGED,
};

export function resolveVisualiserIsDark(): boolean {
    const theme = (GlobalState as { config?: { theme?: string } })?.config?.theme;
    if (theme === "light") {
        return false;
    }
    if (theme === "dark") {
        return true;
    }
    if (typeof document !== "undefined") {
        return document.documentElement.classList.contains("dark");
    }
    return false;
}

export function readStoredHopMaxFilter(): number | null {
    if (typeof localStorage === "undefined") {
        return 4;
    }
    try {
        const raw = localStorage.getItem(HOP_MAX_FILTER_STORAGE_KEY);
        if (raw === null || raw === "") {
            return 4;
        }
        const parsed = parseInt(raw, 10);
        if (Number.isFinite(parsed) && parsed >= 0) {
            return Math.min(128, parsed);
        }
    } catch {
        return 4;
    }
    return 4;
}

export function writeStoredHopMaxFilter(v: number | null): void {
    if (typeof localStorage === "undefined") {
        return;
    }
    try {
        if (v === null) {
            localStorage.setItem(HOP_MAX_FILTER_STORAGE_KEY, "");
        } else {
            localStorage.setItem(HOP_MAX_FILTER_STORAGE_KEY, String(v));
        }
    } catch {
        /* localStorage unavailable */
    }
}
