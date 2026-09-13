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
    const handlers = emitter.all.get(type);
    if (!handlers || handlers.length === 0) {
        return;
    }
    for (const handler of handlers) {
        // One faulty handler must not starve the rest of the listeners for
        // this event type.
        try {
            await (handler as WsEventHandler)(payload);
        } catch (e) {
            console.error(`wsEventRegistry handler for "${type}" failed`, e);
        }
    }
}

export function listRegisteredWsEventTypes(): string[] {
    return Array.from(emitter.all.keys()).map(String);
}
