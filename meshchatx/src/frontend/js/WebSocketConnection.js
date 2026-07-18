import { createEmitter } from "../libs/emitter.js";
import { reconnectDelayWithJitterMs } from "./wsConnectionSupport";

const PING_INTERVAL_MS = 25000;
const PONG_TIMEOUT_MS = 12000;
const BASE_RECONNECT_MS = 1000;
const MAX_RECONNECT_MS = 60000;
const JITTER_MAX_MS = 400;

class WebSocketConnection {
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
        this._lastReceivedTime = Date.now();
        this._hasEventListeners = false;
        this._isForcedReconnect = false;
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

    emit(type, event) {
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
            if (this.destroyed) {
                return;
            }
            if (this._isForcedReconnect) {
                this._isForcedReconnect = false;
                return;
            }
            if (this._hadSuccessfulOpen) {
                this._pendingReconnectUi = true;
            }
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
            try {
                const data = JSON.parse(message.data);
                if (data && data.type === "pong") {
                    this._clearPongTimeout();
                    return;
                }
            } catch {
                // non-json: forward
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
        if (idleTime > PING_INTERVAL_MS) {
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

    send(message) {
        if (this.ws != null && this.ws.readyState === WebSocket.OPEN) {
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
