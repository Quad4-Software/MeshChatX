// SPDX-License-Identifier: 0BSD

import { createEmitter } from "../../libs/emitter";

export type WsEventType = string;
export type WsEventHandler = (payload: Record<string, unknown>) => void | Promise<void>;

const emitter = createEmitter();

export function onWsEvent(type: WsEventType, handler: WsEventHandler): void {
    emitter.on(type, handler);
}

export function offWsEvent(type: WsEventType, handler: WsEventHandler): void {
    emitter.off(type, handler);
}

export async function dispatchWsEvent(type: WsEventType, payload: Record<string, unknown>): Promise<void> {
    const handlers = emitter.all.get(type) as WsEventHandler[] | undefined;
    if (!handlers || handlers.length === 0) {
        return;
    }
    for (const handler of handlers) {
        // One faulty handler must not starve the rest of the listeners for
        // this event type.
        try {
            await handler(payload);
        } catch (e) {
            console.error(`wsEventRegistry handler for "${type}" failed`, e);
        }
    }
}

export function listRegisteredWsEventTypes(): string[] {
    return Array.from(emitter.all.keys()).filter((k): k is string => typeof k === "string");
}
