const NOMAD_TABS_KEY = "meshchatx.nomadnet.tabs";
const MAP_TABS_KEY = "meshchatx.map.tabs";
const MESSAGE_PANES_KEY = "meshchatx.messages.panes";
const RNSH_LAYOUT_KEY = "meshchatx.rnsh.layout";

/**
 * Safely read and parse a JSON value from localStorage.
 *
 * @param {string} key storage key
 * @returns {*} parsed value, or null when missing or unreadable
 */
function readJson(key) {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return null;
        }
        const raw = window.localStorage.getItem(key);
        if (!raw) {
            return null;
        }
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

/**
 * Safely serialise and store a JSON value in localStorage.
 *
 * @param {string} key storage key
 * @param {*} value value to persist
 */
function writeJson(key, value) {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return;
        }
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // persistence is best-effort; ignore quota or availability errors
    }
}

/**
 * Load the persisted NomadNet browser tab layout.
 *
 * @returns {{tabs: Array, activeIndex: number}|null} saved layout or null
 */
export function loadNomadTabs() {
    const data = readJson(NOMAD_TABS_KEY);
    if (!data || !Array.isArray(data.tabs)) {
        return null;
    }
    return data;
}

/**
 * Persist the NomadNet browser tab layout.
 *
 * @param {{tabs: Array, activeIndex: number}} state layout to save
 */
export function saveNomadTabs(state) {
    writeJson(NOMAD_TABS_KEY, state);
}

/**
 * Load the persisted Map browser tab layout.
 *
 * @returns {{tabs: Array, activeIndex: number}|null} saved layout or null
 */
export function loadMapTabs() {
    const data = readJson(MAP_TABS_KEY);
    if (!data || !Array.isArray(data.tabs)) {
        return null;
    }
    return data;
}

/**
 * Persist the Map browser tab layout.
 *
 * @param {{tabs: Array, activeIndex: number}} state layout to save
 */
export function saveMapTabs(state) {
    writeJson(MAP_TABS_KEY, state);
}

/**
 * Load the persisted Messages pane layout.
 *
 * @returns {{panes: Array, focusedIndex: number}|null} saved layout or null
 */
export function loadMessagePanes() {
    const data = readJson(MESSAGE_PANES_KEY);
    if (!data || !Array.isArray(data.panes)) {
        return null;
    }
    return data;
}

/**
 * Persist the Messages pane layout.
 *
 * @param {{panes: Array, focusedIndex: number}} state layout to save
 */
export function saveMessagePanes(state) {
    writeJson(MESSAGE_PANES_KEY, state);
}

/**
 * Load persisted RNSH manager UI layout.
 *
 * @returns {{selectedSessionId: string|null}|null} saved layout or null
 */
export function loadRnshLayout() {
    const data = readJson(RNSH_LAYOUT_KEY);
    if (!data || typeof data !== "object") {
        return null;
    }
    return data;
}

/**
 * Persist RNSH manager UI layout.
 *
 * @param {{selectedSessionId: string|null}} state layout to save
 */
export function saveRnshLayout(state) {
    writeJson(RNSH_LAYOUT_KEY, state);
}
