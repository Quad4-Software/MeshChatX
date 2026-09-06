// SPDX-License-Identifier: 0BSD

import { describe, expect, it, beforeEach } from "vitest";
import { chooseLiveTransport } from "../../meshchatx/src/frontend/js/wsLiveSync.js";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection.js";

const MODES = ["auto", "websocket", "webtransport"];

describe("liveTransport mode fuzz table", () => {
    it("covers mode x support x server x connect outcomes", () => {
        for (const mode of MODES) {
            for (const clientSupportsWebTransport of [true, false]) {
                for (const serverAvailable of [true, false]) {
                    for (const webTransportConnectOk of [null, true, false]) {
                        const got = chooseLiveTransport({
                            mode,
                            clientSupportsWebTransport,
                            serverAvailable,
                            webTransportConnectOk,
                        });
                        if (mode === "websocket") {
                            expect(got).toBe("websocket");
                            continue;
                        }
                        const canTry = clientSupportsWebTransport && serverAvailable;
                        if (!canTry) {
                            expect(got).toBe("websocket");
                            continue;
                        }
                        if (webTransportConnectOk === false) {
                            expect(got).toBe("websocket");
                        } else {
                            expect(got).toBe("webtransport");
                        }
                    }
                }
            }
        }
    });
});

describe("WebSocketConnection live send bridge", () => {
    beforeEach(() => {
        WebSocketConnection.setLiveSendBridge(null);
    });

    it("routes send through bridge when set", () => {
        const sent = [];
        WebSocketConnection.setLiveSendBridge({
            send: (message) => {
                sent.push(message);
                return true;
            },
            isOpen: () => true,
        });
        expect(WebSocketConnection.isOpen()).toBe(true);
        expect(WebSocketConnection.send("hello")).toBe(true);
        expect(sent).toEqual(["hello"]);
        WebSocketConnection.setLiveSendBridge(null);
        expect(WebSocketConnection.send("bye")).toBe(false);
    });
});
