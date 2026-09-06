// SPDX-License-Identifier: 0BSD

import GlobalEmitter from "../GlobalEmitter";

const KEY_DISABLED = "meshchatx.visualiser.showDisabledInterfaces";
const KEY_DISCOVERED = "meshchatx.visualiser.showDiscoveredInterfaces";
const KEY_LIVE_LAYOUT = "meshchatx.visualiser.enablePhysics";
const KEY_AUTO_RELOAD = "meshchatx.visualiser.autoReload";
const KEY_RENDERER = "meshchatx.visualiser.renderer";
const KEY_VIEW_MODE = "meshchatx.visualiser.viewMode";

export const VISUALISER_DISPLAY_PREFS_CHANGED = "visualiser-display-prefs-changed";

export type VisualiserRendererPref = "auto" | "webgl" | "vis";
export type VisualiserViewModePref = "flat" | "planet";

export type VisualiserDisplayPrefs = {
    showDisabledInterfaces: boolean;
    showDiscoveredInterfaces: boolean;
    enablePhysics: boolean;
    autoReload: boolean;
    renderer: VisualiserRendererPref;
    viewMode: VisualiserViewModePref;
};

export type PersistEmitOpts = {
    emit?: boolean;
};

export const VISUALISER_RENDERER_OPTIONS: VisualiserRendererPref[] = ["auto", "webgl", "vis"];
export const VISUALISER_VIEW_MODE_OPTIONS: VisualiserViewModePref[] = ["flat", "planet"];

function readBool(key: string, defaultValue: boolean): boolean {
    try {
        if (typeof localStorage === "undefined") {
            return defaultValue;
        }
        const raw = localStorage.getItem(key);
        if (raw === "true") return true;
        if (raw === "false") return false;
    } catch {
        /* localStorage unavailable */
    }
    return defaultValue;
}

function writeBool(key: string, val: boolean): void {
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem(key, val ? "true" : "false");
        }
    } catch {
        /* ignore */
    }
}

export function normalizeVisualiserRenderer(raw: unknown): VisualiserRendererPref {
    if (raw === "webgl" || raw === "vis" || raw === "auto") {
        return raw;
    }
    return "auto";
}

export function normalizeVisualiserViewMode(raw: unknown): VisualiserViewModePref {
    return raw === "planet" ? "planet" : "flat";
}

function readViewMode(): VisualiserViewModePref {
    try {
        if (typeof localStorage === "undefined") {
            return "flat";
        }
        return normalizeVisualiserViewMode(localStorage.getItem(KEY_VIEW_MODE));
    } catch {
        return "flat";
    }
}

function readRenderer(): VisualiserRendererPref {
    try {
        if (typeof localStorage === "undefined") {
            return "auto";
        }
        return normalizeVisualiserRenderer(localStorage.getItem(KEY_RENDERER));
    } catch {
        return "auto";
    }
}

export function loadVisualiserDisplayPrefs(): VisualiserDisplayPrefs {
    return {
        showDisabledInterfaces: readBool(KEY_DISABLED, false),
        showDiscoveredInterfaces: readBool(KEY_DISCOVERED, false),
        // Live Layout defaults on when never set.
        enablePhysics: readBool(KEY_LIVE_LAYOUT, true),
        autoReload: readBool(KEY_AUTO_RELOAD, false),
        renderer: readRenderer(),
        viewMode: readViewMode(),
    };
}

export function persistVisualiserShowDisabled(val: boolean): void {
    writeBool(KEY_DISABLED, val === true);
    GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
}

export function persistVisualiserShowDiscovered(val: boolean): void {
    writeBool(KEY_DISCOVERED, val === true);
    GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
}

export function persistVisualiserLiveLayout(val: boolean, opts: PersistEmitOpts = {}): void {
    writeBool(KEY_LIVE_LAYOUT, val === true);
    if (opts.emit !== false) {
        GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
    }
}

export function persistVisualiserAutoReload(val: boolean, opts: PersistEmitOpts = {}): void {
    writeBool(KEY_AUTO_RELOAD, val === true);
    if (opts.emit !== false) {
        GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
    }
}

export function persistVisualiserRenderer(val: unknown, opts: PersistEmitOpts = {}): void {
    const next = normalizeVisualiserRenderer(val);
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem(KEY_RENDERER, next);
        }
    } catch {
        /* ignore */
    }
    if (opts.emit !== false) {
        GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
    }
}

export function persistVisualiserViewMode(val: unknown, opts: PersistEmitOpts = {}): void {
    const next = normalizeVisualiserViewMode(val);
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem(KEY_VIEW_MODE, next);
        }
    } catch {
        /* ignore */
    }
    if (opts.emit !== false) {
        GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
    }
}
