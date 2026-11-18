// SPDX-License-Identifier: 0BSD

import LiveTransport from "../liveTransport.js";
import { dispatchWsEvent } from "./wsEventRegistry.js";

let bridgeInstalled = false;
let bridgeMessageHandler = null;

export function installWsEventBridge() {
    if (bridgeInstalled) {
        return;
    }
    bridgeInstalled = true;

    bridgeMessageHandler = async (message) => {
        try {
            const json = JSON.parse(message.data);
            if (json && typeof json.type === "string") {
                await dispatchWsEvent(json.type, json);
            }
        } catch {
            // non-json payloads are ignored by the typed router
        }
    };
    LiveTransport.on("message", bridgeMessageHandler);
}

export function resetWsEventBridgeForTests() {
    if (bridgeMessageHandler) {
        LiveTransport.off("message", bridgeMessageHandler);
        bridgeMessageHandler = null;
    }
    bridgeInstalled = false;
}
