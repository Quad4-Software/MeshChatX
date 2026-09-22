// SPDX-License-Identifier: 0BSD

import { notifyAppStateListeners } from "./appState.js";

type Listener = () => void;

const listeners = new Set<Listener>();

// Top-level key ("config", "authenticated", ...) -> listeners that only wake
// when that domain mutates. targetKeys maps raw child objects back to their
// root key so nested writes like state.config.x resolve to "config".
const keyListeners = new Map<string, Set<Listener>>();
const targetKeys = new WeakMap<object, string>();

let batchDepth = 0;
let pendingNotify = false;
const pendingKeys = new Set<string>();

function notify(changedKey?: string): void {
    if (batchDepth > 0) {
        pendingNotify = true;
        if (changedKey !== undefined) {
            pendingKeys.add(changedKey);
        }
        return;
    }
    for (const listener of listeners) {
        try {
            listener();
        } catch {
            /* ignore */
        }
    }
    if (changedKey !== undefined) {
        for (const listener of keyListeners.get(changedKey) ?? []) {
            try {
                listener();
            } catch {
                /* ignore */
            }
        }
    }
    notifyAppStateListeners(globalState);
}

/** Run fn while coalescing GlobalState notifications into a single flush. */
export function batchGlobalState(fn: () => void): void {
    batchDepth += 1;
    try {
        fn();
    } finally {
        batchDepth -= 1;
        if (batchDepth === 0 && pendingNotify) {
            pendingNotify = false;
            const keys = [...pendingKeys];
            pendingKeys.clear();
            // Global listeners run once; key listeners run for each domain
            // that changed during the batch.
            for (const listener of listeners) {
                try {
                    listener();
                } catch {
                    /* ignore */
                }
            }
            for (const key of keys) {
                for (const listener of keyListeners.get(key) ?? []) {
                    try {
                        listener();
                    } catch {
                        /* ignore */
                    }
                }
            }
            notifyAppStateListeners(globalState);
        }
    }
}

/** Subscribe to GlobalState mutations. Returns unsubscribe. */
export function subscribeGlobalState(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

/**
 * Subscribe to one top-level state domain only, e.g. "config". The listener
 * fires when that key is assigned or when a nested write happens under the
 * object stored at that key. Returns unsubscribe.
 */
export function subscribeGlobalStateKey(key: string, listener: Listener): () => void {
    let set = keyListeners.get(key);
    if (!set) {
        set = new Set();
        keyListeners.set(key, set);
    }
    set.add(listener);
    return () => set.delete(listener);
}

const proxyCache = new WeakMap<object, object>();

function wrapDeep<T extends object>(value: T): T {
    const cached = proxyCache.get(value);
    if (cached) {
        return cached as T;
    }
    const wrapped = new Proxy(value, {
        get(target, prop, receiver) {
            const result = Reflect.get(target, prop, receiver);
            if (result && typeof result === "object" && !(result instanceof Set)) {
                // Track which root domain this child belongs to so nested
                // writes can notify key-scoped subscribers.
                const key = targetKeys.get(target) ?? (target === rawState ? String(prop) : undefined);
                if (key !== undefined) {
                    targetKeys.set(result, key);
                }
                return wrapDeep(result as object);
            }
            return result;
        },
        set(target, prop, next, receiver) {
            const prev = Reflect.get(target, prop, receiver);
            const ok = Reflect.set(target, prop, next, receiver);
            if (ok && prev !== next) {
                const key = targetKeys.get(target) ?? (target === rawState ? String(prop) : undefined);
                notify(key);
            }
            return ok;
        },
    }) as T;
    proxyCache.set(value, wrapped);
    return wrapped;
}

const rawState = {
    authSessionResolved: false,
    authEnabled: false,
    isLoopbackBind: true,
    authenticated: false,
    pluginsEnabled: true,
    detailedOutboundSendStatus: false,
    outboundTransferProgressEnabled: true,
    messageTimestampGroupingEnabled: true,
    unreadConversationsCount: 0,
    relayChatUnreadCount: 0,
    missedCallsCount: 0,
    activeCallTab: "phone",
    blockedDestinations: [] as unknown[],
    modifiedInterfaceNames: new Set<string>(),
    hasPendingInterfaceChanges: false,
    networkDegraded: false,
    networkDegradedError: null as string | null,
    networkStarting: false,
    networkReady: true,
    liveTransportReady: false,
    demoMode: false,
    config: {
        show_unknown_contact_banner: true,
        banished_effect_enabled: true,
        banished_text: "BANISHED",
        banished_color: "#dc2626",
        message_outbound_bubble_color: "#4f46e5",
        message_inbound_bubble_color: null as string | null,
        message_failed_bubble_color: "#ef4444",
        message_waiting_bubble_color: "#e5e7eb",
        nomad_render_markdown_enabled: true,
        nomad_render_html_enabled: true,
        nomad_render_plaintext_enabled: true,
        nomad_micron_wasm_enabled: true,
        nomad_micron_default_engine: "js",
        nomad_default_page_path: "/page/index.mu",
        ui_transparency: 0,
        ui_glass_enabled: true,
        message_list_virtualization: true,
        warn_on_stranger_links: true,
        messages_sidebar_position: "left",
        messages_multi_pane_enabled: true,
        delivery_helptips_enabled: true,
        nomad_tabs_enabled: true,
        rrc_enabled: true,
        rrc_unread_badges_enabled: true,
        live_transport_mode: "auto",
        webtransport_sidecar_enabled: false,
    } as Record<string, unknown>,
};

const globalState = wrapDeep(rawState);

export function mergeGlobalConfig(next: Record<string, unknown> | null | undefined): void {
    if (!next || typeof next !== "object") {
        return;
    }
    const prev = globalState.config && typeof globalState.config === "object" ? globalState.config : {};
    globalState.config = { ...prev, ...next };
}

export default globalState;
