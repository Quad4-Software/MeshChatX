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

class WebSocketConnection {
    declare _hadSuccessfulOpen: boolean;
    declare _hasEventListeners: boolean;
    declare _heartbeatInterval: any;
    declare _isForcedReconnect: boolean;
    declare _lastReceivedTime: any;
    declare _liveSendBridge: any;
    declare _outboundQueue: any[];
    declare _pendingReconnectUi: boolean;
    declare _pongTimeout: any;
    declare _reconnectAttempt: number;
    declare _reconnectTimeout: any;
    declare _sessionReady: boolean;
    declare destroyed: boolean;
    declare emitter: any;
    declare initialized: boolean;
    declare ws: any;
    constructor() {
        this.emitter = createEmitter();
        this.ws = null;
        this._heartbeatInterval = null;
        this._pongTimeout = null;
        this._reconnectTimeout = null;
        this._reconnectAttempt = 0;
        this.initialized = false;
        this.destroyed = false;
        this._hadSuccessfulOpen = false;
        this._pendingReconnectUi = false;
        this._sessionReady = false;
        this._lastReceivedTime = Date.now();
        this._hasEventListeners = false;
        this._isForcedReconnect = false;
        this._outboundQueue = [];
        // When LiveTransport uses WebTransport, page code that still calls
        // WebSocketConnection.send must ride the active live channel.
        this._liveSendBridge = null;
    }

    /**
     * @param {{ send: (message: string) => boolean, sendQueued?: (message: string) => boolean, isOpen?: () => boolean } | null} bridge
     */
    setLiveSendBridge(bridge) {
        this._liveSendBridge = bridge;
    }

    async connect() {
        this.destroyed = false;

        if (typeof window === "undefined" || !window.api) {
            setTimeout(() => this.connect(), 100);
            return;
        }

        this.initialized = true;

        if (typeof window !== "undefined" && window.addEventListener) {
            if (!this._hasEventListeners) {
                window.addEventListener("visibilitychange", () => {
                    if (typeof document !== "undefined" && document.visibilityState === "visible") {
                        this.handleForegroundOrNetworkChange();
                    }
                });
                window.addEventListener("focus", () => {
                    this.handleForegroundOrNetworkChange();
                });
                window.addEventListener("online", () => {
                    this.handleForegroundOrNetworkChange();
                });
                this._hasEventListeners = true;
            }
        }

        this.reconnect();
    }

    on(event, handler) {
        this.emitter.on(event, handler);
    }

    off(event, handler) {
        this.emitter.off(event, handler);
    }

    emit(type, event?) {
        this.emitter.emit(type, event);
    }

    _clearHeartbeat() {
        if (this._heartbeatInterval != null) {
            clearInterval(this._heartbeatInterval);
            this._heartbeatInterval = null;
        }
    }

    _clearPongTimeout() {
        if (this._pongTimeout != null) {
            clearTimeout(this._pongTimeout);
            this._pongTimeout = null;
        }
    }

    _stopHeartbeat() {
        this._clearHeartbeat();
        this._clearPongTimeout();
    }

    _sendAppPing() {
        if (this.destroyed || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }
        try {
            this.ws.send(JSON.stringify({ type: "ping" }));
        } catch {
            return;
        }
        this._clearPongTimeout();
        this._pongTimeout = setTimeout(() => {
            this._pongTimeout = null;
            if (this.destroyed || !this.ws) {
                return;
            }
            try {
                this.ws.close(4000, "heartbeat timeout");
            } catch {
                // ignore
            }
        }, PONG_TIMEOUT_MS);
    }

    _startHeartbeat() {
        this._stopHeartbeat();
        this._heartbeatInterval = setInterval(() => {
            this._sendAppPing();
        }, PING_INTERVAL_MS);
        this._sendAppPing();
    }

    reconnect() {
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
        this.ws = new WebSocket(wsUrl);

        this.ws.addEventListener("open", () => {
            if (this.destroyed) {
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

        this.ws.addEventListener("close", () => {
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

        this.ws.addEventListener("error", () => {
            // close event will follow, and reconnect is scheduled there
        });

        this.ws.onmessage = (message) => {
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

    handleForegroundOrNetworkChange() {
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

    forceReconnect() {
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

    destroy() {
        this.destroyed = true;
        this.initialized = false;
        this._hadSuccessfulOpen = false;
        this._pendingReconnectUi = false;
        this._sessionReady = false;
        this._outboundQueue = [];
        this._stopHeartbeat();
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
    }

    isOpen() {
        if (this._liveSendBridge && typeof this._liveSendBridge.isOpen === "function") {
            return this._liveSendBridge.isOpen();
        }
        return this.ws != null && this.ws.readyState === WebSocket.OPEN;
    }

    _flushOutboundQueue() {
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
                this.ws.send(item.message);
            } catch {
                // drop
            }
        }
    }

    /**
     * Queue a mutator JSON string until the socket is ready.
     * Only messages that include request_id are queued (idempotent matching).
     * @param {string} message
     * @returns {boolean} true if sent or queued
     */
    sendQueued(message) {
        if (typeof message !== "string") {
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
                this.ws.send(message);
                return true;
            } catch {
                return false;
            }
        }
        let requestId = null;
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
            this._outboundQueue.shift();
        }
        this._outboundQueue.push({
            message,
            requestId,
            expiresAt: Date.now() + OUTBOUND_QUEUE_TTL_MS,
        });
        return true;
    }

    send(message) {
        if (this._liveSendBridge) {
            return this._liveSendBridge.send(message);
        }
        if (this.isOpen()) {
            this.ws.send(message);
            return true;
        }
        return false;
    }

    ping() {
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
