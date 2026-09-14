// SPDX-License-Identifier: 0BSD

import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { chooseLiveTransport } from "../../meshchatx/src/frontend/js/wsLiveSync.js";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection.js";
import liveTransport from "../../meshchatx/src/frontend/js/liveTransport.js";

class MockWebTransport {
    static instances = [];

    constructor(url, opts) {
        this.url = url;
        this.opts = opts;
        this.closed = false;
        this.writes = [];
        this.ready = new Promise((resolve, reject) => {
            this._resolveReady = resolve;
            this._rejectReady = reject;
        });
        MockWebTransport.instances.push(this);
    }

    async createBidirectionalStream() {
        const transport = this;
        return {
            writable: {
                getWriter() {
                    return {
                        write: async (bytes) => {
                            transport.writes.push(bytes);
                        },
                    };
                },
            },
            readable: {
                getReader() {
                    return {
                        read: () => new Promise(() => {}),
                        cancel: async () => {},
                    };
                },
            },
        };
    }

    close() {
        this.closed = true;
    }
}

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

describe("LiveTransport WebTransport candidate lifecycle", () => {
    beforeEach(() => {
        MockWebTransport.instances = [];
        globalThis.WebTransport = MockWebTransport;
        vi.spyOn(WebSocketConnection, "connect").mockResolvedValue();
        vi.spyOn(WebSocketConnection, "reconnect").mockImplementation(() => {});
        liveTransport.configure({
            mode: "auto",
            webtransport: { server_available: true, url: "https://wt.example/ws" },
        });
    });

    afterEach(() => {
        liveTransport.destroy();
        vi.restoreAllMocks();
        delete globalThis.WebTransport;
    });

    it("forwards candidate events during connect and drops WebSocket forwards on success", async () => {
        const events = [];
        liveTransport.on("connected", (e) => events.push(["connected", e]));
        liveTransport.on("ready", () => events.push(["ready"]));
        liveTransport.on("message", (e) => events.push(["message", e]));

        const p = liveTransport.connect();
        expect(MockWebTransport.instances).toHaveLength(1);
        MockWebTransport.instances[0]._resolveReady();
        const result = await p;

        expect(result.transport).toBe("webtransport");
        expect(liveTransport.activeTransport).toBe("webtransport");
        expect(events.some(([t, e]) => t === "connected" && e?.transport === "webtransport")).toBe(true);
        expect(events.some(([t]) => t === "ready")).toBe(true);

        events.length = 0;
        WebSocketConnection.emit("message", { data: "ws-msg" });
        expect(events).toHaveLength(0);

        liveTransport.send(JSON.stringify({ hello: "world" }));
        expect(MockWebTransport.instances[0].writes.length).toBe(1);
    });

    it("restores WebSocket forwarding and emits transport_fallback when WebTransport fails", async () => {
        const fallbacks = [];
        const messages = [];
        liveTransport.on("transport_fallback", (e) => fallbacks.push(e));
        liveTransport.on("message", (e) => messages.push(e));

        const p = liveTransport.connect();
        MockWebTransport.instances[0]._rejectReady(new Error("nope"));
        const result = await p;

        expect(result.transport).toBe("websocket");
        expect(liveTransport.activeTransport).toBe("websocket");
        expect(fallbacks).toEqual([{ from: "webtransport", to: "websocket" }]);
        expect(WebSocketConnection.connect).toHaveBeenCalled();

        WebSocketConnection.emit("message", { data: "ws-msg" });
        expect(messages).toEqual([{ data: "ws-msg" }]);
    });

    it("supersedes an in-flight candidate on concurrent connect without leaking its events", async () => {
        const events = [];
        liveTransport.on("disconnected", () => events.push("disconnected"));

        const p1 = liveTransport.connect();
        const p2 = liveTransport.connect();

        expect(MockWebTransport.instances).toHaveLength(2);
        expect(MockWebTransport.instances[0].closed).toBe(true);

        MockWebTransport.instances[1]._resolveReady();
        const r2 = await p2;
        expect(r2.transport).toBe("webtransport");
        expect(r2.superseded).not.toBe(true);

        MockWebTransport.instances[0]._resolveReady();
        const r1 = await p1;
        expect(r1.superseded).toBe(true);

        expect(events).toHaveLength(0);
    });

    it("destroy() closes the in-flight candidate and clears forwards", async () => {
        const events = [];
        liveTransport.on("disconnected", () => events.push("disconnected"));

        const p = liveTransport.connect();
        liveTransport.destroy();

        expect(MockWebTransport.instances[0].closed).toBe(true);

        MockWebTransport.instances[0]._resolveReady();
        await p.catch(() => {});
        expect(events).toHaveLength(0);
    });
});
