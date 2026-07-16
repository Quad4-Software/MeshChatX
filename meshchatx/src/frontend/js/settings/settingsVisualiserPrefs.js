// SPDX-License-Identifier: 0BSD AND MIT

import GlobalEmitter from "../GlobalEmitter";

const KEY_DISABLED = "meshchatx.visualiser.showDisabledInterfaces";
const KEY_DISCOVERED = "meshchatx.visualiser.showDiscoveredInterfaces";
const KEY_LIVE_LAYOUT = "meshchatx.visualiser.enablePhysics";
const KEY_AUTO_RELOAD = "meshchatx.visualiser.autoReload";

export const VISUALISER_DISPLAY_PREFS_CHANGED = "visualiser-display-prefs-changed";

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
 * @returns {{
 *   showDisabledInterfaces: boolean,
 *   showDiscoveredInterfaces: boolean,
 *   enablePhysics: boolean,
 *   autoReload: boolean,
 * }}
 */
export function loadVisualiserDisplayPrefs() {
    return {
        showDisabledInterfaces: readBool(KEY_DISABLED, false),
        showDiscoveredInterfaces: readBool(KEY_DISCOVERED, false),
        // Live Layout defaults on when never set.
        enablePhysics: readBool(KEY_LIVE_LAYOUT, true),
        autoReload: readBool(KEY_AUTO_RELOAD, false),
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
