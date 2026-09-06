export type BrowserTabLayout = {
    tabs: Array<{
        destinationHash?: unknown;
        path?: unknown;
        title?: unknown;
        [key: string]: unknown;
    }>;
    activeIndex: number;
    [key: string]: unknown;
};

export type MessagePanesLayout = {
    panes: unknown[];
    focusedIndex: number;
    identities?: unknown[];
    [key: string]: unknown;
};

export type SessionLayout = {
    selectedSessionId: string | null;
    [key: string]: unknown;
};

export type SidebarFeatureId = "app" | "messages" | "nomadnetwork" | "relayChat";

const NOMAD_TABS_KEY = "meshchatx.nomadnet.tabs";
const MAP_TABS_KEY = "meshchatx.map.tabs";
const MESSAGE_PANES_KEY = "meshchatx.messages.panes";
const RNSH_LAYOUT_KEY = "meshchatx.rnsh.layout";
const RNX_LAYOUT_KEY = "meshchatx.rnx.layout";
const FEATURE_SIDEBAR_COLLAPSED_KEYS: Record<SidebarFeatureId, string> = {
    app: "meshchatx.sidebar.app",
    messages: "meshchatx.sidebar.messages",
    nomadnetwork: "meshchatx.sidebar.nomadnetwork",
    relayChat: "meshchatx.sidebar.relay-chat",
};
const LEGACY_RELAY_SIDEBAR_COLLAPSED_KEY = "relayChatSidebarCollapsed";

/** Safely read and parse a JSON value from localStorage. */
function readJson(key: string): unknown {
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

/** Safely serialise and store a JSON value in localStorage. */
function writeJson(key: string, value: unknown): void {
    try {
        if (typeof window === "undefined" || !window.localStorage) {
            return;
        }
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // persistence is best-effort. Ignore quota or availability errors
    }
}

/** Load the persisted NomadNet browser tab layout. */
export function loadNomadTabs(): BrowserTabLayout | null {
    const data = readJson(NOMAD_TABS_KEY) as BrowserTabLayout | null;
    if (!data || !Array.isArray(data.tabs)) {
        return null;
    }
    return data;
}

/** Persist the NomadNet browser tab layout. */
export function saveNomadTabs(state: BrowserTabLayout): void {
    writeJson(NOMAD_TABS_KEY, state);
}

/** Load the persisted Map browser tab layout. */
export function loadMapTabs(): BrowserTabLayout | null {
    const data = readJson(MAP_TABS_KEY) as BrowserTabLayout | null;
    if (!data || !Array.isArray(data.tabs)) {
        return null;
    }
    return data;
}

/** Persist the Map browser tab layout. */
export function saveMapTabs(state: BrowserTabLayout): void {
    writeJson(MAP_TABS_KEY, state);
}

/** Load the persisted Messages pane layout. */
export function loadMessagePanes(): MessagePanesLayout | null {
    const data = readJson(MESSAGE_PANES_KEY) as MessagePanesLayout | null;
    if (!data || !Array.isArray(data.panes)) {
        return null;
    }
    return data;
}

/** Persist the Messages pane layout. */
export function saveMessagePanes(state: MessagePanesLayout): void {
    writeJson(MESSAGE_PANES_KEY, state);
}

/** Clear persisted Messages pane layout (used on identity switch). */
export function clearMessagePanes(): void {
    writeJson(MESSAGE_PANES_KEY, { panes: [], focusedIndex: 0, identities: [] });
}

/** Load persisted RNSH manager UI layout. */
export function loadRnshLayout(): SessionLayout | null {
    const data = readJson(RNSH_LAYOUT_KEY);
    if (!data || typeof data !== "object") {
        return null;
    }
    return data as SessionLayout;
}

/** Persist RNSH manager UI layout. */
export function saveRnshLayout(state: SessionLayout): void {
    writeJson(RNSH_LAYOUT_KEY, state);
}

/** Load persisted RNX manager UI layout. */
export function loadRnxLayout(): SessionLayout | null {
    const data = readJson(RNX_LAYOUT_KEY);
    if (!data || typeof data !== "object") {
        return null;
    }
    return data as SessionLayout;
}

/** Persist RNX manager UI layout. */
export function saveRnxLayout(state: SessionLayout): void {
    writeJson(RNX_LAYOUT_KEY, state);
}

/** Load a persisted feature sidebar collapsed flag. */
export function loadFeatureSidebarCollapsed(feature: SidebarFeatureId): boolean | null {
    const key = FEATURE_SIDEBAR_COLLAPSED_KEYS[feature];
    if (!key) {
        return null;
    }
    const saved = readJson(key);
    if (saved === true || saved === false) {
        return saved;
    }
    if (feature === "relayChat") {
        try {
            if (typeof window !== "undefined" && window.localStorage) {
                const legacy = window.localStorage.getItem(LEGACY_RELAY_SIDEBAR_COLLAPSED_KEY);
                if (legacy === "1") {
                    return true;
                }
                if (legacy === "0") {
                    return false;
                }
            }
        } catch {
            return null;
        }
    }
    return null;
}

/** Persist a feature sidebar collapsed flag. */
export function saveFeatureSidebarCollapsed(feature: SidebarFeatureId, collapsed: boolean): void {
    const key = FEATURE_SIDEBAR_COLLAPSED_KEYS[feature];
    if (!key) {
        return;
    }
    writeJson(key, collapsed === true);
    if (feature === "relayChat") {
        try {
            if (typeof window !== "undefined" && window.localStorage) {
                window.localStorage.setItem(LEGACY_RELAY_SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
            }
        } catch {
            // persistence is best-effort
        }
    }
}
