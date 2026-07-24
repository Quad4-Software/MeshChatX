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

/** A WebSocket mock whose pings are never answered, to exercise pong-timeout handling. */
function makeSilentWsImpl() {
    const Base = makeWsImpl();
    return class SilentWebSocket extends Base {
        send() {
            // swallow all sends (including pings) - never emit a pong
        }
    };
}

/** Minimal EventTarget-backed window mock so real focus/online/visibilitychange
 * events can be dispatched and routed through addEventListener like a browser. */
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

    it("forwards invalid JSON frames without throwing", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        const onMessage = vi.fn();
        WebSocketConnection.on("message", onMessage);

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);

        const sock = WebSocketConnection.ws;
        expect(() => sock.onmessage({ data: "<<<not-json>>>" })).not.toThrow();
        expect(onMessage).toHaveBeenCalledTimes(1);

        WebSocketConnection.destroy();
    });

    it("reconnects or pings on foreground or network change", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);

        const firstWs = WebSocketConnection.ws;
        const sendSpy = vi.spyOn(firstWs, "send");

        // 1. If idleTime is small, it should just send a ping
        WebSocketConnection._lastReceivedTime = Date.now();
        WebSocketConnection.handleForegroundOrNetworkChange();
        expect(sendSpy).toHaveBeenCalled();
        expect(WebSocketConnection.ws).toBe(firstWs);

        // 2. If idleTime is large, it should force a reconnect
        WebSocketConnection._lastReceivedTime = Date.now() - 60000;
        WebSocketConnection.handleForegroundOrNetworkChange();

        // Wait for the new WebSocket to be created and opened
        await vi.waitUntil(() => WebSocketConnection.ws && WebSocketConnection.ws !== firstWs);
        await vi.waitUntil(() => WebSocketConnection.ws.readyState === MockWS.OPEN);

        expect(WebSocketConnection.ws).not.toBe(firstWs);

        WebSocketConnection.destroy();
    });

    it("reconnect() does not thrash a connection attempt that is already in flight", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        // connect() has no internal awaits before constructing the socket,
        // so checking readyState right after calling it (without awaiting
        // the returned promise, which only settles after the queued "open"
        // microtask) reliably catches it mid-connect.
        WebSocketConnection.connect();
        const connectingWs = WebSocketConnection.ws;
        expect(connectingWs.readyState).toBe(MockWS.CONNECTING);

        // calling reconnect() again while the first attempt hasn't resolved
        // yet must not close/replace it.
        WebSocketConnection.reconnect();
        WebSocketConnection.reconnect();
        expect(WebSocketConnection.ws).toBe(connectingWs);

        await vi.waitUntil(() => WebSocketConnection.ws.readyState === MockWS.OPEN);
        expect(WebSocketConnection.ws).toBe(connectingWs);

        WebSocketConnection.destroy();
    });

    it("ignores repeated foreground/network re-triggers while a reconnect is already in flight", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);

        const firstWs = WebSocketConnection.ws;
        WebSocketConnection._lastReceivedTime = Date.now() - 60000;
        WebSocketConnection.handleForegroundOrNetworkChange();

        const connectingWs = WebSocketConnection.ws;
        expect(connectingWs).not.toBe(firstWs);
        expect(connectingWs.readyState).toBe(MockWS.CONNECTING);

        // simulate visibilitychange, focus and online all firing again
        // before the new socket has finished opening (very plausible when
        // a mobile browser/webview comes back to the foreground).
        WebSocketConnection.handleForegroundOrNetworkChange();
        WebSocketConnection.handleForegroundOrNetworkChange();
        WebSocketConnection.handleForegroundOrNetworkChange();

        expect(WebSocketConnection.ws).toBe(connectingWs);

        await vi.waitUntil(() => WebSocketConnection.ws.readyState === MockWS.OPEN);
        expect(WebSocketConnection.ws).toBe(connectingWs);

        WebSocketConnection.destroy();
    });

    it("cancels a pending backoff retry when a reconnect happens out of turn", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        vi.useFakeTimers({ shouldAdvanceTime: true });

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);

        const firstWs = WebSocketConnection.ws;
        // a real, unexpected disconnect - schedules a backoff retry
        firstWs.close(1006, "abnormal");
        await vi.waitUntil(() => WebSocketConnection._reconnectTimeout !== null);

        // something else (e.g. a foreground event) triggers an immediate,
        // out-of-turn reconnect before the backoff timer fires
        WebSocketConnection.reconnect();
        const outOfTurnWs = WebSocketConnection.ws;
        expect(outOfTurnWs).not.toBe(firstWs);
        expect(WebSocketConnection._reconnectTimeout).toBeNull();

        await vi.waitUntil(() => outOfTurnWs.readyState === MockWS.OPEN);

        // advance well past when the original backoff timer would have
        // fired (base delay ~1s, capped well under this), but short of the
        // next heartbeat/pong cycle so that unrelated timers don't muddy
        // the assertion. It must have been cancelled and not fire a
        // redundant second reconnect that would replace the healthy socket.
        await vi.advanceTimersByTimeAsync(5000);

        expect(WebSocketConnection.ws).toBe(outOfTurnWs);
        expect(WebSocketConnection.ws.readyState).toBe(MockWS.OPEN);

        WebSocketConnection.destroy();
    });

    it("forceReconnect performs a silent reconnect without emitting disconnected", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        const connected = vi.fn();
        const disconnected = vi.fn();
        WebSocketConnection.on("connected", connected);
        WebSocketConnection.on("disconnected", disconnected);

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);

        const firstWs = WebSocketConnection.ws;
        WebSocketConnection._lastReceivedTime = Date.now() - 60000;
        WebSocketConnection.handleForegroundOrNetworkChange();

        await vi.waitUntil(() => WebSocketConnection.ws && WebSocketConnection.ws !== firstWs);
        await vi.waitUntil(() => WebSocketConnection.ws.readyState === MockWS.OPEN);

        expect(disconnected).not.toHaveBeenCalled();
        expect(connected).toHaveBeenCalledTimes(2);
        // Background-tab stale recovery must still tell the shell this is a
        // reconnect so CSRF/config/status can resync (without flashing disconnect).
        expect(connected.mock.calls[1][0]).toEqual({ isReconnect: true });

        WebSocketConnection.destroy();
    });

    it("marks forced reconnect as isReconnect after a prior successful open (background-tab stall)", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        const connected = vi.fn();
        WebSocketConnection.on("connected", connected);

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);
        expect(connected.mock.calls[0][0]).toEqual({ isReconnect: false });

        const firstWs = WebSocketConnection.ws;
        // Simulate a zombie OPEN socket after the tab slept: readyState still
        // OPEN, but no frames for longer than the ping interval.
        WebSocketConnection._lastReceivedTime = Date.now() - 60000;
        WebSocketConnection.forceReconnect();

        await vi.waitUntil(() => WebSocketConnection.ws && WebSocketConnection.ws !== firstWs);
        await vi.waitUntil(() => WebSocketConnection.ws.readyState === MockWS.OPEN);

        expect(connected.mock.calls[1][0]).toEqual({ isReconnect: true });

        WebSocketConnection.destroy();
    });

    it("handleForegroundOrNetworkChange and forceReconnect are no-ops before connect() or after destroy()", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        // never connected yet
        expect(() => WebSocketConnection.handleForegroundOrNetworkChange()).not.toThrow();
        expect(() => WebSocketConnection.forceReconnect()).not.toThrow();
        expect(WebSocketConnection.ws).toBeNull();

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);
        WebSocketConnection.destroy();

        // destroyed
        expect(() => WebSocketConnection.handleForegroundOrNetworkChange()).not.toThrow();
        expect(() => WebSocketConnection.forceReconnect()).not.toThrow();
        expect(WebSocketConnection.ws).toBeNull();
    });

    it("send() and ping() are safe no-ops when there is no open socket", async () => {
        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        expect(WebSocketConnection.ws).toBeNull();
        expect(WebSocketConnection.send("hello")).toBe(false);
        expect(() => WebSocketConnection.ping()).not.toThrow();
    });

    it("registers window event listeners only once across repeated connect() calls", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;

        const addEventListenerSpy = vi.fn();
        global.window = {
            api: {},
            location: { origin: "http://127.0.0.1:5173" },
            addEventListener: addEventListenerSpy,
            removeEventListener: vi.fn(),
        };

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);
        const countAfterFirst = addEventListenerSpy.mock.calls.length;
        expect(countAfterFirst).toBeGreaterThan(0);

        WebSocketConnection.destroy();
        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);

        expect(addEventListenerSpy.mock.calls.length).toBe(countAfterFirst);

        WebSocketConnection.destroy();
    });

    it("only reacts to visibilitychange when the document becomes visible", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;
        global.window = makeWindowMock();
        global.document = { visibilityState: "hidden" };

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);

        const firstWs = WebSocketConnection.ws;
        WebSocketConnection._lastReceivedTime = Date.now() - 60000;

        // still hidden - must not trigger a reconnect
        global.window.dispatchEvent(new Event("visibilitychange"));
        expect(WebSocketConnection.ws).toBe(firstWs);
        expect(firstWs.readyState).toBe(MockWS.OPEN);

        // becoming visible should run the stale-connection check
        global.document.visibilityState = "visible";
        global.window.dispatchEvent(new Event("visibilitychange"));

        await vi.waitUntil(() => WebSocketConnection.ws && WebSocketConnection.ws !== firstWs);
        await vi.waitUntil(() => WebSocketConnection.ws.readyState === MockWS.OPEN);
        expect(WebSocketConnection.ws).not.toBe(firstWs);

        WebSocketConnection.destroy();
    });

    it("reacts to real focus and online DOM events", async () => {
        const MockWS = makeWsImpl();
        global.WebSocket = MockWS;
        global.window = makeWindowMock();
        global.document = { visibilityState: "visible" };

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === MockWS.OPEN);

        const firstWs = WebSocketConnection.ws;
        const sendSpy = vi.spyOn(firstWs, "send");

        WebSocketConnection._lastReceivedTime = Date.now();
        global.window.dispatchEvent(new Event("focus"));
        expect(sendSpy).toHaveBeenCalled();
        expect(WebSocketConnection.ws).toBe(firstWs);

        WebSocketConnection._lastReceivedTime = Date.now() - 60000;
        global.window.dispatchEvent(new Event("online"));

        await vi.waitUntil(() => WebSocketConnection.ws && WebSocketConnection.ws !== firstWs);
        await vi.waitUntil(() => WebSocketConnection.ws.readyState === MockWS.OPEN);
        expect(WebSocketConnection.ws).not.toBe(firstWs);

        WebSocketConnection.destroy();
    });

    it("closes and schedules a reconnect when a heartbeat ping goes unanswered", async () => {
        const SilentWS = makeSilentWsImpl();
        global.WebSocket = SilentWS;

        vi.useFakeTimers({ shouldAdvanceTime: true });

        const { default: WebSocketConnection } = await import("../../meshchatx/src/frontend/js/WebSocketConnection.js");

        const disconnected = vi.fn();
        WebSocketConnection.on("disconnected", disconnected);

        await WebSocketConnection.connect();
        await vi.waitUntil(() => WebSocketConnection.ws?.readyState === SilentWS.OPEN);

        const firstWs = WebSocketConnection.ws;

        // the very first heartbeat ping is sent on open but never answered;
        // once the pong timeout elapses the socket should be force-closed.
        await vi.advanceTimersByTimeAsync(12000 + 500);

        await vi.waitUntil(() => disconnected.mock.calls.length >= 1);
        expect(firstWs.readyState).toBe(SilentWS.CLOSED);

        WebSocketConnection.destroy();
    });
});
