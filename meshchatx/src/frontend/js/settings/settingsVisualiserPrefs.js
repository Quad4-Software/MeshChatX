// SPDX-License-Identifier: 0BSD AND MIT

import GlobalEmitter from "../GlobalEmitter";

const KEY_DISABLED = "meshchatx.visualiser.showDisabledInterfaces";
const KEY_DISCOVERED = "meshchatx.visualiser.showDiscoveredInterfaces";
const KEY_LIVE_LAYOUT = "meshchatx.visualiser.enablePhysics";
const KEY_AUTO_RELOAD = "meshchatx.visualiser.autoReload";
const KEY_RENDERER = "meshchatx.visualiser.renderer";
const KEY_VIEW_MODE = "meshchatx.visualiser.viewMode";

export const VISUALISER_DISPLAY_PREFS_CHANGED = "visualiser-display-prefs-changed";

/** @typedef {"auto" | "webgl" | "vis"} VisualiserRendererPref */
/** @typedef {"flat" | "planet"} VisualiserViewModePref */

export const VISUALISER_RENDERER_OPTIONS = ["auto", "webgl", "vis"];
export const VISUALISER_VIEW_MODE_OPTIONS = ["flat", "planet"];

/**
 * @param {string} key
 * @param {boolean} defaultValue
 * @returns {boolean}
 */
function readBool(key, defaultValue) {
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

/**
 * @param {string} key
 * @param {boolean} val
 */
function writeBool(key, val) {
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem(key, val ? "true" : "false");
        }
    } catch {
        /* ignore */
    }
}

/**
 * @param {unknown} raw
 * @returns {VisualiserRendererPref}
 */
export function normalizeVisualiserRenderer(raw) {
    if (raw === "webgl" || raw === "vis" || raw === "auto") {
        return raw;
    }
    return "auto";
}

/**
 * @param {unknown} raw
 * @returns {VisualiserViewModePref}
 */
export function normalizeVisualiserViewMode(raw) {
    return raw === "planet" ? "planet" : "flat";
}

/**
 * @returns {VisualiserViewModePref}
 */
function readViewMode() {
    try {
        if (typeof localStorage === "undefined") {
            return "flat";
        }
        return normalizeVisualiserViewMode(localStorage.getItem(KEY_VIEW_MODE));
    } catch {
        return "flat";
    }
}

/**
 * @returns {VisualiserRendererPref}
 */
function readRenderer() {
    try {
        if (typeof localStorage === "undefined") {
            return "auto";
        }
        return normalizeVisualiserRenderer(localStorage.getItem(KEY_RENDERER));
    } catch {
        return "auto";
    }
}

/**
 * @returns {{
 *   showDisabledInterfaces: boolean,
 *   showDiscoveredInterfaces: boolean,
 *   enablePhysics: boolean,
 *   autoReload: boolean,
 *   renderer: VisualiserRendererPref,
 *   viewMode: VisualiserViewModePref,
 * }}
 */
export function loadVisualiserDisplayPrefs() {
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

/**
 * @param {boolean} val
 */
export function persistVisualiserShowDisabled(val) {
    writeBool(KEY_DISABLED, val === true);
    GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
}

/**
 * @param {boolean} val
 */
export function persistVisualiserShowDiscovered(val) {
    writeBool(KEY_DISCOVERED, val === true);
    GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
}

/**
 * @param {boolean} val
 * @param {{ emit?: boolean }} [opts]
 */
export function persistVisualiserLiveLayout(val, opts = {}) {
    writeBool(KEY_LIVE_LAYOUT, val === true);
    if (opts.emit !== false) {
        GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
    }
}

/**
 * @param {boolean} val
 * @param {{ emit?: boolean }} [opts]
 */
export function persistVisualiserAutoReload(val, opts = {}) {
    writeBool(KEY_AUTO_RELOAD, val === true);
    if (opts.emit !== false) {
        GlobalEmitter.emit(VISUALISER_DISPLAY_PREFS_CHANGED);
    }
}

/**
 * @param {unknown} val
 * @param {{ emit?: boolean }} [opts]
 */
export function persistVisualiserRenderer(val, opts = {}) {
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

/**
 * @param {unknown} val
 * @param {{ emit?: boolean }} [opts]
 */
export function persistVisualiserViewMode(val, opts = {}) {
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
