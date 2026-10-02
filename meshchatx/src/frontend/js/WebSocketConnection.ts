import { createEmitter } from "../libs/emitter.js";
import { reconnectDelayWithJitterMs } from "./wsConnectionSupport";

const PING_INTERVAL_MS = 25000;
const PONG_TIMEOUT_MS = 12000;
const BASE_RECONNECT_MS = 1000;
const MAX_RECONNECT_MS = 60000;
const JITTER_MAX_MS = 400;
// Foreground recovery: prefer a ping for longer before tearing down a still-OPEN socket.
// Android WebViews often idle past one ping interval while backgrounded without a dead link.
const FOREGROUND_FORCE_RECONNECT_IDLE_MS = 90000;
const OUTBOUND_QUEUE_MAX = 32;
const OUTBOUND_QUEUE_TTL_MS = 30000;

/** Events this connection emits. Values are the payload types. */
export type WsEventMap = {
    connected: { isReconnect: boolean };
    disconnected: void;
    ready: void;
    message: MessageEvent;
    queue_expired: { request_id: unknown };
};

export type WsEventName = keyof WsEventMap;

export type WsHandler<K extends WsEventName> = (event: WsEventMap[K]) => void;

export interface LiveSendBridge {
    send(message: string): boolean;
    sendQueued?(message: string): boolean;
    isOpen?(): boolean;
}

interface QueuedMessage {
    message: string;
    requestId: unknown;
    expiresAt: number;
}

class WebSocketConnection {
    emitter = createEmitter();
    ws: WebSocket | null = null;
    _heartbeatInterval: ReturnType<typeof setInterval> | null = null;
    _pongTimeout: ReturnType<typeof setTimeout> | null = null;
    _reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    _reconnectAttempt = 0;
    initialized = false;
    destroyed = false;
    _hadSuccessfulOpen = false;
    _pendingReconnectUi = false;
    _sessionReady = false;
    _lastReceivedTime = Date.now();
    _hasEventListeners = false;
    _isForcedReconnect = false;
    _outboundQueue: QueuedMessage[] = [];
    _liveSendBridge: LiveSendBridge | null = null;
    _bootstrapRetryTimeout: ReturnType<typeof setTimeout> | null = null;
    _onVisibilityChange: (() => void) | null = null;
    _onWindowFocus: (() => void) | null = null;
    _onWindowOnline: (() => void) | null = null;

    /**
     * Swap the outbound channel to a live transport bridge (e.g. WebTransport).
     * Queued messages drain through the bridge so they are not stranded.
     */
    setLiveSendBridge(bridge: LiveSendBridge | null): void {
        this._liveSendBridge = bridge;
        if (bridge && this._outboundQueue.length) {
            const now = Date.now();
            const pending = this._outboundQueue;
            this._outboundQueue = [];
            for (const item of pending) {
                if (item.expiresAt != null && item.expiresAt < now) {
                    this.emit("queue_expired", { request_id: item.requestId });
                    continue;
                }
                try {
                    if (typeof bridge.sendQueued === "function") {
                        bridge.sendQueued(item.message);
                    } else {
                        bridge.send(item.message);
                    }
                } catch {
                    // drop
                }
            }
        }
    }

    async connect(): Promise<void> {
        this.destroyed = false;
        // A fresh connect must not inherit a stale backoff stage from a
        // previous session.
        this._reconnectAttempt = 0;

        if (typeof window === "undefined" || !(window as any).api) {
            if (this._bootstrapRetryTimeout != null) {
                clearTimeout(this._bootstrapRetryTimeout);
            }
            this._bootstrapRetryTimeout = setTimeout(() => {
                this._bootstrapRetryTimeout = null;
                this.connect();
            }, 100);
            return;
        }

        this.initialized = true;

        if (typeof window !== "undefined" && window.addEventListener) {
            if (!this._hasEventListeners) {
                this._onVisibilityChange = () => {
                    if (typeof document !== "undefined" && document.visibilityState === "visible") {
                        this.handleForegroundOrNetworkChange();
                    }
                };
                this._onWindowFocus = () => {
                    this.handleForegroundOrNetworkChange();
                };
                this._onWindowOnline = () => {
                    this.handleForegroundOrNetworkChange();
                };
                window.addEventListener("visibilitychange", this._onVisibilityChange);
                window.addEventListener("focus", this._onWindowFocus);
                window.addEventListener("online", this._onWindowOnline);
                this._hasEventListeners = true;
            }
        }

        this.reconnect();
    }

    on<K extends WsEventName>(event: K, handler: WsHandler<K>): void {
        this.emitter.on(event, handler as (data: unknown) => void);
    }

    off<K extends WsEventName>(event: K, handler: WsHandler<K>): void {
        this.emitter.off(event, handler as (data: unknown) => void);
    }

    emit<K extends WsEventName>(type: K, event?: WsEventMap[K]): void {
        this.emitter.emit(type, event);
    }

    _clearHeartbeat(): void {
        if (this._heartbeatInterval != null) {
            clearInterval(this._heartbeatInterval);
            this._heartbeatInterval = null;
        }
    }

    _clearPongTimeout(): void {
        if (this._pongTimeout != null) {
            clearTimeout(this._pongTimeout);
            this._pongTimeout = null;
        }
    }

    _stopHeartbeat(): void {
        this._clearHeartbeat();
        this._clearPongTimeout();
    }

    _sendAppPing(): void {
        if (this.destroyed || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }
        const socket = this.ws;
        try {
            socket.send(JSON.stringify({ type: "ping" }));
        } catch {
            return;
        }
        this._clearPongTimeout();
        this._pongTimeout = setTimeout(() => {
            this._pongTimeout = null;
            // The socket that armed this timeout may have been replaced by a
            // reconnect that never saw its close event. Only time out the
            // socket that is still current.
            if (this.destroyed || this.ws !== socket) {
                return;
            }
            try {
                socket.close(4000, "heartbeat timeout");
            } catch {
                // ignore
            }
        }, PONG_TIMEOUT_MS);
    }

    _startHeartbeat(): void {
        this._stopHeartbeat();
        this._heartbeatInterval = setInterval(() => {
            this._sendAppPing();
        }, PING_INTERVAL_MS);
        this._sendAppPing();
    }

    reconnect(): void {
        if (!this.initialized || this.destroyed || typeof window === "undefined" || !window.location) {
            return;
        }

        // Don't tear down a connection that is already open, and don't
        // abandon one that is already in flight (e.g. triggered again by a
        // near-simultaneous focus/visibilitychange/online event) - doing so
        // would thrash the socket and could delay recovery indefinitely.
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            return;
        }

        // A new attempt is starting now, so any previously scheduled
        // backoff retry (from an earlier close) is redundant - drop it so
        // it can't later fire and interfere with this attempt.
        if (this._reconnectTimeout != null) {
            clearTimeout(this._reconnectTimeout);
            this._reconnectTimeout = null;
        }

        if (this.ws) {
            try {
                this.ws.close();
            } catch {
                // ignore
            }
            this.ws = null;
        }

        const wsUrl = window.location.origin.replace(/^https/, "wss").replace(/^http/, "ws") + "/ws";
        const socket = new WebSocket(wsUrl);
        this.ws = socket;
        // The forced-close that spawned this attempt belongs to the previous
        // socket. Its close event arrives later and is ignored via the stale
        // socket guard, so the flag must not leak into this socket's lifecycle.
        this._isForcedReconnect = false;

        socket.addEventListener("open", () => {
            if (this.destroyed || socket !== this.ws) {
                return;
            }
            if (this._reconnectTimeout != null) {
                clearTimeout(this._reconnectTimeout);
                this._reconnectTimeout = null;
            }
            this._reconnectAttempt = 0;
            this._sessionReady = false;
            this._stopHeartbeat();
            this._startHeartbeat();
            const isReconnect = this._pendingReconnectUi;
            this._pendingReconnectUi = false;
            this._hadSuccessfulOpen = true;
            this._lastReceivedTime = Date.now();
            this.emit("connected", { isReconnect });
        });

        socket.addEventListener("close", () => {
            // A close from a superseded socket must not tear down the live
            // connection's heartbeat or emit a stale disconnected event.
            if (socket !== this.ws) {
                return;
            }
            this._stopHeartbeat();
            this._sessionReady = false;
            if (this.destroyed) {
                return;
            }
            if (this._isForcedReconnect) {
                this._isForcedReconnect = false;
                return;
            }
            // Startup races (backend still binding) must not flash a disconnect banner.
            if (!this._hadSuccessfulOpen) {
                const delay = reconnectDelayWithJitterMs(
                    this._reconnectAttempt,
                    BASE_RECONNECT_MS,
                    MAX_RECONNECT_MS,
                    JITTER_MAX_MS
                );
                this._reconnectAttempt += 1;
                if (this._reconnectTimeout != null) {
                    clearTimeout(this._reconnectTimeout);
                }
                this._reconnectTimeout = setTimeout(() => {
                    this._reconnectTimeout = null;
                    if (!this.destroyed) {
                        this.reconnect();
                    }
                }, delay);
                return;
            }
            this._pendingReconnectUi = true;
            this.emit("disconnected");
            const delay = reconnectDelayWithJitterMs(
                this._reconnectAttempt,
                BASE_RECONNECT_MS,
                MAX_RECONNECT_MS,
                JITTER_MAX_MS
            );
            this._reconnectAttempt += 1;
            if (this._reconnectTimeout != null) {
                clearTimeout(this._reconnectTimeout);
            }
            this._reconnectTimeout = setTimeout(() => {
                this._reconnectTimeout = null;
                if (!this.destroyed) {
                    this.reconnect();
                }
            }, delay);
        });

        socket.addEventListener("error", () => {
            // close event will follow, and reconnect is scheduled there
        });

        socket.onmessage = (message: MessageEvent) => {
            if (socket !== this.ws) {
                return;
            }
            this._lastReceivedTime = Date.now();
            let isPong = false;
            try {
                const data = JSON.parse(message.data);
                if (data && data.type === "pong") {
                    this._clearPongTimeout();
                    isPong = true;
                }
            } catch {
                // non-json: forward
            }
            if (!this._sessionReady) {
                this._sessionReady = true;
                this.emit("ready");
                this._flushOutboundQueue();
            }
            if (isPong) {
                return;
            }
            this.emit("message", message);
        };
    }

    handleForegroundOrNetworkChange(): void {
        if (!this.initialized || this.destroyed) {
            return;
        }

        // A connection attempt is already in flight (e.g. a previous
        // foreground/network event just started one) - let it resolve on
        // its own rather than tearing it down and starting another.
        if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            return;
        }

        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.reconnect();
            return;
        }

        const idleTime = Date.now() - this._lastReceivedTime;
        if (idleTime > FOREGROUND_FORCE_RECONNECT_IDLE_MS) {
            this.forceReconnect();
        } else {
            this._sendAppPing();
        }
    }

    forceReconnect(): void {
        if (!this.initialized || this.destroyed) {
            return;
        }
        if (this.ws) {
            // Suppress the disconnect banner. Still mark reconnect so CSRF/config
            // resync after background-tab stalls, but App only celebrates if the
            // disconnect banner was actually shown.
            if (this._hadSuccessfulOpen) {
                this._pendingReconnectUi = true;
            }
            this._isForcedReconnect = true;
            try {
                this.ws.close();
            } catch {
                // ignore
            }
            this.ws = null;
        }
        this.reconnect();
    }

    destroy(): void {
        this.destroyed = true;
        this.initialized = false;
        this._hadSuccessfulOpen = false;
        this._pendingReconnectUi = false;
        this._sessionReady = false;
        this._reconnectAttempt = 0;
        this._outboundQueue = [];
        this._stopHeartbeat();
        if (this._reconnectTimeout != null) {
            clearTimeout(this._reconnectTimeout);
            this._reconnectTimeout = null;
        }
        if (this._bootstrapRetryTimeout != null) {
            clearTimeout(this._bootstrapRetryTimeout);
            this._bootstrapRetryTimeout = null;
        }
        if (this._hasEventListeners && typeof window !== "undefined" && window.removeEventListener) {
            window.removeEventListener("visibilitychange", this._onVisibilityChange!);
            window.removeEventListener("focus", this._onWindowFocus!);
            window.removeEventListener("online", this._onWindowOnline!);
            this._hasEventListeners = false;
            this._onVisibilityChange = null;
            this._onWindowFocus = null;
            this._onWindowOnline = null;
        }
        if (this.ws) {
            try {
                this.ws.close();
            } catch {
                // ignore
            }
            this.ws = null;
        }
    }

    isOpen(): boolean {
        if (this._liveSendBridge && typeof this._liveSendBridge.isOpen === "function") {
            return this._liveSendBridge.isOpen();
        }
        return this.ws != null && this.ws.readyState === WebSocket.OPEN;
    }

    _flushOutboundQueue(): void {
        if (this._liveSendBridge) {
            return;
        }
        if (!this.isOpen() || !this._outboundQueue.length) {
            return;
        }
        const now = Date.now();
        const pending = this._outboundQueue;
        this._outboundQueue = [];
        for (const item of pending) {
            if (item.expiresAt != null && item.expiresAt < now) {
                this.emit("queue_expired", { request_id: item.requestId });
                continue;
            }
            try {
                this.ws!.send(item.message);
            } catch {
                // drop
            }
        }
    }

    /**
     * Queue a mutator JSON string until the socket is ready.
     * Only messages that include request_id are queued (idempotent matching).
     */
    sendQueued(message: string): boolean {
        if (typeof message !== "string" || this.destroyed) {
            return false;
        }
        if (this._liveSendBridge) {
            if (typeof this._liveSendBridge.sendQueued === "function") {
                return this._liveSendBridge.sendQueued(message);
            }
            return this._liveSendBridge.send(message);
        }
        if (this.isOpen() && this._sessionReady) {
            try {
                this.ws!.send(message);
                return true;
            } catch {
                return false;
            }
        }
        let requestId: unknown = null;
        try {
            const parsed = JSON.parse(message);
            if (parsed && parsed.request_id != null) {
                requestId = parsed.request_id;
            }
        } catch {
            return false;
        }
        if (requestId == null) {
            return false;
        }
        if (this._outboundQueue.length >= OUTBOUND_QUEUE_MAX) {
            // Surface the eviction so request_id-correlated callers can settle
            // instead of hanging until their own timeout.
            const evicted = this._outboundQueue.shift()!;
            this.emit("queue_expired", { request_id: evicted.requestId });
        }
        this._outboundQueue.push({
            message,
            requestId,
            expiresAt: Date.now() + OUTBOUND_QUEUE_TTL_MS,
        });
        return true;
    }

    send(message: string): boolean {
        if (this._liveSendBridge) {
            return this._liveSendBridge.send(message);
        }
        if (this.isOpen()) {
            this.ws!.send(message);
            return true;
        }
        return false;
    }

    ping(): void {
        try {
            this.send(
                JSON.stringify({
                    type: "ping",
                })
            );
        } catch {
            // ignore
        }
    }
}

export default new WebSocketConnection();
