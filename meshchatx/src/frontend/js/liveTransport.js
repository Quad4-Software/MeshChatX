// SPDX-License-Identifier: 0BSD

import { createEmitter } from "../libs/emitter.js";
import WebSocketConnection from "./WebSocketConnection.js";
import { chooseLiveTransport } from "./wsLiveSync.js";
import { clientSupportsWebTransport, encodeWtJsonLine, feedWtJsonLines } from "./wtJsonFraming.js";

const WT_CONNECT_BUDGET_MS = 4000;

/**
 * @param {{ send: (message: string) => boolean, sendQueued?: (message: string) => boolean, isOpen?: () => boolean } | null} bridge
 */
function setWsLiveSendBridge(bridge) {
    if (typeof WebSocketConnection.setLiveSendBridge === "function") {
        WebSocketConnection.setLiveSendBridge(bridge);
    }
}

/**
 * @param {string} b64
 * @returns {Uint8Array | null}
 */
function b64ToBytes(b64) {
    try {
        const bin = atob(b64);
        const out = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) {
            out[i] = bin.charCodeAt(i);
        }
        return out;
    } catch {
        return null;
    }
}

/**
 * Experimental WebTransport live session (newline JSON on one bidi stream).
 */
class WebTransportLiveSession {
    constructor() {
        this.emitter = createEmitter();
        this._transport = null;
        this._writer = null;
        this._reader = null;
        this._buffer = "";
        this._sessionReady = false;
        this.destroyed = false;
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

    /**
     * @param {{ url: string, certSha256B64?: string }} opts
     */
    async connect(opts) {
        if (this.destroyed) {
            throw new Error("destroyed");
        }
        if (!clientSupportsWebTransport()) {
            throw new Error("webtransport_unsupported");
        }
        const url = opts.url;
        if (!url) {
            throw new Error("missing_url");
        }
        /** @type {Record<string, unknown>} */
        const wtOpts = {};
        if (opts.certSha256B64) {
            const value = b64ToBytes(opts.certSha256B64);
            if (value) {
                wtOpts.serverCertificateHashes = [{ algorithm: "sha-256", value }];
            }
        }
        const transport = new WebTransport(url, wtOpts);
        this._transport = transport;
        let timeoutId = null;
        const readyRace = Promise.race([
            transport.ready,
            new Promise((_, reject) => {
                timeoutId = setTimeout(() => reject(new Error("webtransport_timeout")), WT_CONNECT_BUDGET_MS);
            }),
        ]);
        try {
            await readyRace;
        } finally {
            if (timeoutId != null) {
                clearTimeout(timeoutId);
            }
        }
        if (this.destroyed) {
            try {
                transport.close();
            } catch {
                // ignore
            }
            throw new Error("destroyed");
        }
        const stream = await transport.createBidirectionalStream();
        this._writer = stream.writable.getWriter();
        this._reader = stream.readable.getReader();
        this._sessionReady = true;
        this.emit("connected", { isReconnect: false, transport: "webtransport" });
        this.emit("ready");
        void this._readLoop();
    }

    async _readLoop() {
        const decoder = new TextDecoder();
        try {
            while (this._reader && !this.destroyed) {
                const { value, done } = await this._reader.read();
                if (done) {
                    break;
                }
                const text = decoder.decode(value, { stream: true });
                const fed = feedWtJsonLines(this._buffer, text);
                this._buffer = fed.buffer;
                for (const obj of fed.objects) {
                    this.emit("message", { data: JSON.stringify(obj) });
                }
                if (fed.errors.length) {
                    this.emit("error", { code: "frame_error", errors: fed.errors });
                    break;
                }
            }
        } catch {
            // closed
        }
        this._sessionReady = false;
        this.emit("disconnected");
    }

    isOpen() {
        return this._transport != null && this._sessionReady;
    }

    send(message) {
        if (!this.isOpen() || !this._writer) {
            return false;
        }
        let line;
        if (typeof message === "string") {
            try {
                const obj = JSON.parse(message);
                line = encodeWtJsonLine(obj);
            } catch {
                return false;
            }
        } else {
            line = encodeWtJsonLine(message);
        }
        const bytes = new TextEncoder().encode(line);
        void this._writer.write(bytes);
        return true;
    }

    sendQueued(message) {
        return this.send(message);
    }

    destroy() {
        this.destroyed = true;
        this._sessionReady = false;
        try {
            this._transport?.close();
        } catch {
            // ignore
        }
        this._transport = null;
        this._writer = null;
        this._reader = null;
    }
}

/**
 * Facade: try experimental WebTransport then fall back to WebSocketConnection.
 */
class LiveTransport {
    constructor() {
        this.emitter = createEmitter();
        this._active = WebSocketConnection;
        this._wt = null;
        this._mode = "auto";
        this._serverInfo = { server_available: false };
        this._usingWt = false;
        this._fallbackNotified = false;
        this._forwardBySource = new Map();
        this._connectingWt = null;
        this._boundWs = false;
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

    /**
     * @param {{ mode?: string, webtransport?: object }} opts
     */
    configure(opts = {}) {
        if (opts.mode) {
            this._mode = opts.mode;
        }
        if (opts.webtransport && typeof opts.webtransport === "object") {
            this._serverInfo = opts.webtransport;
        }
    }

    _clearForwards(source) {
        if (source == null) {
            for (const fns of this._forwardBySource.values()) {
                for (const fn of fns) {
                    fn();
                }
            }
            this._forwardBySource.clear();
            return;
        }
        const fns = this._forwardBySource.get(source) || [];
        for (const fn of fns) {
            fn();
        }
        this._forwardBySource.delete(source);
    }

    _forwardFrom(source) {
        this._clearForwards(source);
        const events = ["message", "connected", "ready", "disconnected", "queue_expired"];
        const fns = [];
        for (const ev of events) {
            const handler = (payload) => this.emit(ev, payload);
            source.on(ev, handler);
            fns.push(() => source.off(ev, handler));
        }
        this._forwardBySource.set(source, fns);
    }

    async connect() {
        if (!this._boundWs) {
            this._forwardFrom(WebSocketConnection);
            this._boundWs = true;
        }

        const serverAvailable = this._serverInfo?.server_available === true;
        const choice = chooseLiveTransport({
            mode: this._mode,
            clientSupportsWebTransport: clientSupportsWebTransport(),
            serverAvailable,
            webTransportConnectOk: null,
        });

        if (choice === "webtransport" && this._serverInfo?.url) {
            // A concurrent or repeated connect abandons any in-flight session.
            this._clearForwards(this._connectingWt);
            this._connectingWt?.destroy();
            const session = new WebTransportLiveSession();
            this._connectingWt = session;
            try {
                // Forward the candidate alongside WebSocket during the attempt
                // so its initial connected/ready events reach consumers while
                // WebSocket events keep flowing. WS forwards drop on success.
                this._forwardFrom(session);
                await session.connect({
                    url: this._serverInfo.url,
                    certSha256B64: this._serverInfo.cert_sha256_b64,
                });
                if (this._connectingWt !== session) {
                    this._clearForwards(session);
                    session.destroy();
                    return { transport: "webtransport", fellBack: false, superseded: true };
                }
                this._connectingWt = null;
                this._wt = session;
                this._clearForwards(WebSocketConnection);
                this._boundWs = false;
                this._usingWt = true;
                this._active = this._wt;
                setWsLiveSendBridge({
                    send: (message) => this._wt.send(message),
                    sendQueued: (message) => this._wt.send(message),
                    isOpen: () => this._wt.isOpen(),
                });
                return { transport: "webtransport", fellBack: false };
            } catch {
                this._clearForwards(session);
                session.destroy();
                if (this._connectingWt !== session) {
                    // A newer connect already superseded this session. Leave
                    // the active transport state alone.
                    return { transport: "webtransport", fellBack: false, superseded: true };
                }
                this._connectingWt = null;
                this._wt = null;
                this._usingWt = false;
                this._active = WebSocketConnection;
                setWsLiveSendBridge(null);
                this._forwardFrom(WebSocketConnection);
                this._boundWs = true;
                if (this._mode === "webtransport" || this._mode === "auto") {
                    this._fallbackNotified = true;
                    this.emit("transport_fallback", { from: "webtransport", to: "websocket" });
                }
            }
        }

        setWsLiveSendBridge(null);
        if (typeof WebSocketConnection.connect === "function") {
            await WebSocketConnection.connect();
        } else {
            WebSocketConnection.reconnect();
        }
        this._usingWt = false;
        this._active = WebSocketConnection;
        return { transport: "websocket", fellBack: this._fallbackNotified };
    }

    send(message) {
        return this._active.send(message);
    }

    sendQueued(message) {
        if (typeof this._active.sendQueued === "function") {
            return this._active.sendQueued(message);
        }
        return this._active.send(message);
    }

    isOpen() {
        return this._active.isOpen();
    }

    reconnect() {
        this._clearForwards(this._connectingWt);
        this._connectingWt?.destroy();
        this._connectingWt = null;
        if (this._usingWt) {
            this._wt?.destroy();
            this._wt = null;
            this._usingWt = false;
            this._active = WebSocketConnection;
            setWsLiveSendBridge(null);
            this._forwardFrom(WebSocketConnection);
            this._boundWs = true;
        }
        WebSocketConnection.reconnect();
    }

    forceReconnect() {
        if (typeof WebSocketConnection.forceReconnect === "function") {
            WebSocketConnection.forceReconnect();
        } else {
            this.reconnect();
        }
    }

    destroy() {
        this._clearForwards(this._connectingWt);
        this._connectingWt?.destroy();
        this._connectingWt = null;
        this._wt?.destroy();
        this._wt = null;
        setWsLiveSendBridge(null);
        this._clearForwards();
        WebSocketConnection.destroy();
    }

    get activeTransport() {
        return this._usingWt ? "webtransport" : "websocket";
    }

    get fellBackThisSession() {
        return this._fallbackNotified;
    }
}

export { chooseLiveTransport, clientSupportsWebTransport, WebTransportLiveSession };
export default new LiveTransport();
