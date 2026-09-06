// SPDX-License-Identifier: 0BSD

/**
 * Small mitt-compatible event emitter.
 * Handlers are stored as arrays on a Map keyed by event type.
 * Wildcard listeners use type "*".
 * Emit uses a snapshot so handlers may safely on/off during emit.
 */

/** Payload is untyped so typed listeners stay assignable (bivariant in practice). */
export type EmitterHandler = (event?: any) => void;
export type WildcardHandler = (type: string | symbol, event: unknown) => void;
export type HandlerMap = Map<string | symbol, Array<EmitterHandler | WildcardHandler>>;

export type Emitter = {
    all: HandlerMap;
    on: (type: string | symbol, handler: EmitterHandler | WildcardHandler) => void;
    off: (type: string | symbol, handler?: EmitterHandler | WildcardHandler) => void;
    emit: (type: string | symbol, event?: unknown) => void;
};

export function createEmitter(all: HandlerMap = new Map()): Emitter {
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
                    (handler as EmitterHandler)(event);
                }
            }
            const wild = all.get("*");
            if (wild) {
                for (const handler of wild.slice()) {
                    (handler as WildcardHandler)(type, event);
                }
            }
        },
    };
}

export default function emitter(all?: HandlerMap): Emitter {
    return createEmitter(all);
}
