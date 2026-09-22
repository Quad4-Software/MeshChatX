// SPDX-License-Identifier: 0BSD

/**
 * Explicit store facade over the config domain of GlobalState. Subscribers
 * here wake only when config mutates; unrelated domains (unread counters,
 * call state, interface flags) do not fire them. This is the first domain
 * carved out of broadcast GlobalState subscriptions; new domains should
 * follow the same pattern via subscribeGlobalStateKey.
 */

import globalState, { subscribeGlobalStateKey } from "./GlobalState.js";

type Listener = () => void;

/** Fires when GlobalState.config is replaced or any nested config write happens. */
export function subscribeConfig(listener: Listener): () => void {
    return subscribeGlobalStateKey("config", listener);
}

export function getConfig(): Record<string, unknown> {
    const cfg = globalState.config;
    return cfg && typeof cfg === "object" ? cfg : {};
}

export function getConfigValue<T>(key: string, fallback: T): T {
    const value = getConfig()[key];
    return value === undefined ? fallback : (value as T);
}
