// SPDX-License-Identifier: 0BSD

import { createEmitter } from "../../libs/emitter.js";

/** @type {ReturnType<typeof createEmitter>} */
const emitter = createEmitter();

/**
 * @param {string} type
 * @param {(payload: Record<string, unknown>) => void | Promise<void>} handler
 */
export function onWsEvent(type, handler) {
    emitter.on(type, handler);
}

/**
 * @param {string} type
 * @param {(payload: Record<string, unknown>) => void | Promise<void>} handler
 */
export function offWsEvent(type, handler) {
    emitter.off(type, handler);
}

/**
 * @param {string} type
 * @param {Record<string, unknown>} payload
 */
export async function dispatchWsEvent(type, payload) {
    const handlers = emitter.all.get(type);
    if (!handlers || handlers.length === 0) {
        return;
    }
    for (const handler of handlers) {
        await handler(payload);
    }
}

/**
 * @returns {string[]}
 */
export function listRegisteredWsEventTypes() {
    return Array.from(emitter.all.keys());
}
