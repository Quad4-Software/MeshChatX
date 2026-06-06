// SPDX-License-Identifier: 0BSD AND MIT

const RELAY_LAYOUT_KEY = "meshchatx.relay.layout";

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

function writeJson(key, value) {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return;
        }
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // best-effort
    }
}

export function loadRelayLayout() {
    const data = readJson(RELAY_LAYOUT_KEY);
    if (!data || typeof data !== "object") {
        return null;
    }
    return data;
}

export function saveRelayLayout(state) {
    writeJson(RELAY_LAYOUT_KEY, state);
}
