// SPDX-License-Identifier: 0BSD
// Bug-hunt: wsEventRegistry.dispatchWsEvent sequential await +
// WebSocketConnection outbound-queue edge cases.
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { dispatchWsEvent, onWsEvent, offWsEvent } from "../../meshchatx/src/frontend/js/registries/wsEventRegistry.ts";

function makeWsImpl() {
    return class MockWebSocket {
        static CONNECTING = 0;
        static OPEN = 1;
        static CLOSING = 2;
        static CLOSED = 3;

        constructor(url) {
            this.url = url;
            this.readyState = MockWebSocket.CONNECTING;
            this._listeners = { open: [], close: [], error: [], message: [] };
            queueMicrotask(() => {
                if (this.readyState === MockWebSocket.CLOSED) {
                    return;
                }
                this.readyState = MockWebSocket.OPEN;
                this._listeners.open.forEach((fn) => fn());
            });
        }
        addEventListener(type, fn) {
            this._listeners[type]?.push(fn);
        }
        send() {}
        close(code, reason) {
            if (this.readyState === MockWebSocket.CLOSED) return;
            this.readyState = MockWebSocket.CLOSED;
            queueMicrotask(() => this._listeners.close.forEach((fn) => fn({ code, reason })));
        }
    };
}

function makeWindowMock(extra = {}) {
    const target = new EventTarget();
    return {
        api: {},
        location: { origin: "http://127.0.0.1:5173" },
        addEventListener: target.addEventListener.bind(target),
        removeEventListener: target.removeEventListener.bind(target),
        dispatchEvent: target.dispatchEvent.bind(target),
        ...extra,
    };
}

describe("bughunt: dispatchWsEvent sequential await", () => {
    it("a slow first handler delays later same-type handlers", async () => {
        const order = [];
        let releaseSlow;
        const slow = vi.fn(
            () =>
                new Promise((resolve) => {
                    releaseSlow = () => {
                        order.push("slow-done");
                        resolve();
                    };
                })
        );
        const fast = vi.fn(() => {
            order.push("fast");
        });
        onWsEvent("bughunt.event", slow);
        onWsEvent("bughunt.event", fast);
        try {
            const p = dispatchWsEvent("bughunt.event", {});
            await new Promise((r) => setTimeout(r, 10));
            // The fast handler is registered second; it must not wait on slow.
            expect(fast, "fast handler was blocked behind slow handler").toHaveBeenCalled();
            releaseSlow();
            await p;
        } finally {
            offWsEvent("bughunt.event", slow);
            offWsEvent("bughunt.event", fast);
        }
    });

    it("sync handlers still run in registration order", async () => {
        const order = [];
        const a = () => order.push("a");
        const b = () => order.push("b");
        onWsEvent("bughunt.order", a);
        onWsEvent("bughunt.order", b);
        try {
            await dispatchWsEvent("bughunt.order", {});
            expect(order).toEqual(["a", "b"]);
        } finally {
            offWsEvent("bughunt.order", a);
            offWsEvent("bughunt.order", b);
        }
    });
});

describe("bughunt: WebSocketConnection outbound queue", () => {
    beforeEach(() => {
        vi.resetModules();
        global.window = makeWindowMock();
        global.WebSocket = makeWsImpl();
    });
    afterEach(() => {
        vi.useRealTimers();
    });

    it("destroy() must emit queue_expired for pending request_ids", async () => {
        const { default: WebSocketConnection } = await import(
            "../../meshchatx/src/frontend/js/WebSocketConnection"
        );
        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === WebSocket.OPEN);
        WebSocketConnection._sessionReady = false;

        const expired = [];
        WebSocketConnection.on("queue_expired", (e) => expired.push(e.request_id));
        const ok = WebSocketConnection.sendQueued(
            JSON.stringify({ type: "config.set", request_id: "req-destroy" })
        );
        expect(ok).toBe(true);
        expect(WebSocketConnection._outboundQueue).toHaveLength(1);

        WebSocketConnection.destroy();
        // The queue_expired contract exists so request_id-correlated callers
        // settle instead of hanging. destroy() drops the queue silently.
        expect(expired, "destroy() dropped queued request_id without queue_expired").toContain("req-destroy");
    });

    it("expired queued items emit queue_expired on flush", async () => {
        vi.useFakeTimers({ shouldAdvanceTime: true });
        const { default: WebSocketConnection } = await import(
            "../../meshchatx/src/frontend/js/WebSocketConnection"
        );
        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === WebSocket.OPEN);
        WebSocketConnection._sessionReady = false;

        const expired = [];
        WebSocketConnection.on("queue_expired", (e) => expired.push(e.request_id));
        WebSocketConnection.sendQueued(JSON.stringify({ type: "config.set", request_id: "old-req" }));
        // Age the item past the 30s TTL, then deliver the first inbound frame.
        await vi.advanceTimersByTimeAsync(31000);
        WebSocketConnection.ws.onmessage({ data: JSON.stringify({ type: "config" }) });
        expect(expired).toContain("old-req");
        WebSocketConnection.destroy();
    });
});
