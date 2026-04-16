import GlobalEmitter from "../GlobalEmitter";

const KEY_DISABLED = "meshchatx.visualiser.showDisabledInterfaces";
const KEY_DISCOVERED = "meshchatx.visualiser.showDiscoveredInterfaces";

/**
 * @returns {{ showDisabledInterfaces: boolean, showDiscoveredInterfaces: boolean }}
 */
export function loadVisualiserDisplayPrefs() {
    try {
        if (typeof localStorage !== "undefined") {
            return {
                showDisabledInterfaces: localStorage.getItem(KEY_DISABLED) === "true",
                showDiscoveredInterfaces: localStorage.getItem(KEY_DISCOVERED) === "true",
            };
        }
    } catch {
        /* localStorage unavailable */
    }
    return {
        showDisabledInterfaces: false,
        showDiscoveredInterfaces: false,
    };
}

/**
 * @param {boolean} val
 */
export function persistVisualiserShowDisabled(val) {
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem(KEY_DISABLED, val ? "true" : "false");
        }
    } catch {
        /* ignore */
    }
    GlobalEmitter.emit("visualiser-display-prefs-changed");
}

/**
 * @param {boolean} val
 */
export function persistVisualiserShowDiscovered(val) {
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem(KEY_DISCOVERED, val ? "true" : "false");
        }
    } catch {
        /* ignore */
    }
    GlobalEmitter.emit("visualiser-display-prefs-changed");
}
