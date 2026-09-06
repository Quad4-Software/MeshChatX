// SPDX-License-Identifier: 0BSD

import LiveTransport from "../liveTransport.js";
import { dispatchWsEvent } from "./wsEventRegistry.js";

let bridgeInstalled = false;

export function installWsEventBridge() {
    if (bridgeInstalled) {
        return;
    }
    bridgeInstalled = true;

    LiveTransport.on("message", async (message) => {
        try {
            const json = JSON.parse(message.data);
            if (json && typeof json.type === "string") {
                await dispatchWsEvent(json.type, json);
            }
        } catch {
            // non-json payloads are ignored by the typed router
        }
    });
}

export function resetWsEventBridgeForTests() {
    bridgeInstalled = false;
}
