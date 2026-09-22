// SPDX-License-Identifier: 0BSD

import { createEmitter, type EmitterHandler } from "../../libs/emitter.js";

/** Loose payload so feature handlers can narrow locally. */
export type WsEventHandler = (payload: any) => void | Promise<void>;

const emitter = createEmitter();

export function onWsEvent(type: string, handler: WsEventHandler): void {
    emitter.on(type, handler as EmitterHandler);
}

export function offWsEvent(type: string, handler: WsEventHandler): void {
    emitter.off(type, handler as EmitterHandler);
}

export async function dispatchWsEvent(type: string, payload: Record<string, unknown>): Promise<void> {
    const handlers = emitter.all.get(type)?.slice();
    if (!handlers || handlers.length === 0) {
        return;
    }
    // Handlers are invoked in registration order but their async work runs
    // concurrently so a slow handler cannot starve the rest. One faulty
    // handler must not starve the other listeners for this event type.
    const pending: Promise<void>[] = [];
    for (const handler of handlers) {
        try {
            const result = (handler as WsEventHandler)(payload);
            if (result && typeof result.then === "function") {
                pending.push(
                    result.catch((e) => {
                        console.error(`wsEventRegistry handler for "${type}" failed`, e);
                    })
                );
            }
        } catch (e) {
            console.error(`wsEventRegistry handler for "${type}" failed`, e);
        }
    }
    await Promise.all(pending);
}

export function listRegisteredWsEventTypes(): string[] {
    return Array.from(emitter.all.keys()).map(String);
}
