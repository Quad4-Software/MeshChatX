// SPDX-License-Identifier: 0BSD

/**
 * Small mitt-compatible event emitter.
 * Handlers are stored as arrays on a Map keyed by event type.
 * Wildcard listeners use type "*".
 * Emit uses a snapshot so handlers may safely on/off during emit.
 */

/**
 * @typedef {(event: unknown) => void} EmitterHandler
 * @typedef {(type: string | symbol, event: unknown) => void} WildcardHandler
 * @typedef {Map<string | symbol, Array<EmitterHandler | WildcardHandler>>} HandlerMap
 *
 * @typedef {object} Emitter
 * @property {HandlerMap} all
 * @property {(type: string | symbol, handler: EmitterHandler | WildcardHandler) => void} on
 * @property {(type: string | symbol, handler?: EmitterHandler | WildcardHandler) => void} off
 * @property {(type: string | symbol, event?: unknown) => void} emit
 */

/**
 * @param {HandlerMap} [all]
 * @returns {Emitter}
 */
export function createEmitter(all = new Map()) {
    return {
        all,
        on(type, handler) {
            if (typeof handler !== "function") {
                return;
            }
            const list = all.get(type);
            if (list) {
                list.push(handler);
            } else {
                all.set(type, [handler]);
            }
        },
        off(type, handler) {
            const list = all.get(type);
            if (!list) {
                return;
            }
            if (handler == null) {
                all.set(type, []);
                return;
            }
            const index = list.indexOf(handler);
            if (index >= 0) {
                list.splice(index, 1);
            }
        },
        emit(type, event) {
            const list = all.get(type);
            if (list) {
                for (const handler of list.slice()) {
                    /** @type {EmitterHandler} */ handler(event);
                }
            }
            const wild = all.get("*");
            if (wild) {
                for (const handler of wild.slice()) {
                    handler(type, event);
                }
            }
        },
    };
}

/**
 * @param {HandlerMap} [all]
 * @returns {Emitter}
 */
export default function emitter(all) {
    return createEmitter(all);
}
