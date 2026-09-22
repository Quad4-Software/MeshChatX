// SPDX-License-Identifier: 0BSD AND MIT

const RELAY_LAYOUT_KEY = "meshchatx.relay.layout";

// Fields of the pre-bucket flat layout shape, stripped when the store is
// rewritten in per-identity form.
const LEGACY_LAYOUT_FIELDS = [
    "view",
    "selectedHubHash",
    "selectedRoom",
    "expandedHubs",
    "availableRoomsExpanded",
    "relaySidebarCollapsed",
];

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

function normalizeIdentityKey(identityKey) {
    return typeof identityKey === "string" && identityKey ? identityKey : "_";
}

function looksLikeFlatLayout(data) {
    return LEGACY_LAYOUT_FIELDS.some((field) => field in data);
}

export function loadRelayLayout(identityKey = "_") {
    const key = normalizeIdentityKey(identityKey);
    const data = readJson(RELAY_LAYOUT_KEY);
    if (!data || typeof data !== "object" || Array.isArray(data)) {
        return null;
    }
    const bucket = data[key];
    if (bucket && typeof bucket === "object" && !Array.isArray(bucket)) {
        return bucket;
    }
    // Builds before identity scoping stored the layout flat at the root.
    if (looksLikeFlatLayout(data)) {
        return data;
    }
    return null;
}

export function saveRelayLayout(identityKey, state) {
    const key = normalizeIdentityKey(identityKey);
    const root = readJson(RELAY_LAYOUT_KEY);
    const next = root && typeof root === "object" && !Array.isArray(root) ? root : {};
    for (const field of LEGACY_LAYOUT_FIELDS) {
        delete next[field];
    }
    next[key] = state;
    writeJson(RELAY_LAYOUT_KEY, next);
}
