import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

        send(data) {
            if (data.includes('"type":"ping"')) {
                queueMicrotask(() => {
                    this._listeners.message.forEach((fn) => fn({ data: JSON.stringify({ type: "pong" }) }));
                });
            }
        }

        close(code, reason) {
            if (this.readyState === MockWebSocket.CLOSED) {
                return;
            }
            this.readyState = MockWebSocket.CLOSED;
            queueMicrotask(() => {
                this._listeners.close.forEach((fn) => fn({ code, reason }));
            });
        }
    };
}

describe("WebSocketConnection module", () => {
    beforeEach(() => {
        vi.resetModules();
        global.window = {
            api: {},
            location: { origin: "http://127.0.0.1:5173" },
        };
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("emits connected then disconnected on close and reconnects with backoff", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        vi.useFakeTimers({ shouldAdvanceTime: true });

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        const connected = vi.fn();
        const disconnected = vi.fn();
        WebSocketConnection.on("connected", connected);
        WebSocketConnection.on("disconnected", disconnected);

        await WebSocketConnection.connect();

        await vi.waitUntil(() => connected.mock.calls.length >= 1);
        expect(connected.mock.calls[0][0]).toEqual({ isReconnect: false });

        const firstWs = WebSocketConnection.ws;
        firstWs.close(1000, "test");

        await vi.waitUntil(() => disconnected.mock.calls.length >= 1);

        const delay = 1000;
        await vi.advanceTimersByTimeAsync(delay + 500);

        await vi.waitUntil(() => WebSocketConnection.ws && WebSocketConnection.ws !== firstWs);

        await vi.waitUntil(() => connected.mock.calls.length >= 2);
        expect(connected.mock.calls[1][0]).toEqual({ isReconnect: true });

        WebSocketConnection.destroy();
    });

    it("strips pong from message stream", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        const onMessage = vi.fn();
        WebSocketConnection.on("message", onMessage);

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);

        const sock = WebSocketConnection.ws;
        sock.onmessage({ data: JSON.stringify({ type: "pong" }) });

        expect(onMessage).not.toHaveBeenCalled();

        sock.onmessage({ data: JSON.stringify({ type: "config", config: {} }) });

        expect(onMessage).toHaveBeenCalledTimes(1);

        WebSocketConnection.destroy();
    });
});
