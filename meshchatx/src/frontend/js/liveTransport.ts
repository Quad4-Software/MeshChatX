// SPDX-License-Identifier: 0BSD

import { createEmitter, type Emitter, type EmitterHandler } from "../libs/emitter.js";
import WebSocketConnection, { type LiveSendBridge } from "./WebSocketConnection.js";
import { chooseLiveTransport } from "./wsLiveSync.js";
import { clientSupportsWebTransport, encodeWtJsonLine, feedWtJsonLines } from "./wtJsonFraming.js";

const WT_CONNECT_BUDGET_MS = 4000;

export type LiveTransportMode = string;

export type WebTransportServerInfo = {
    server_available?: boolean;
    url?: string;
    cert_sha256_b64?: string;
    [key: string]: unknown;
};

export type LiveTransportConfigureOptions = {
    mode?: LiveTransportMode;
    webtransport?: WebTransportServerInfo;
};

export type LiveTransportConnectResult = {
    transport: "webtransport" | "websocket";
    fellBack: boolean;
};

type LiveTransportSource = {
    on: (event: string | symbol, handler: EmitterHandler) => void;
    off: (event: string | symbol, handler?: EmitterHandler) => void;
    send: (message: string) => boolean;
    sendQueued?: (message: string) => boolean;
    isOpen: () => boolean;
};

function setWsLiveSendBridge(bridge: LiveSendBridge | null): void {
    if (typeof WebSocketConnection.setLiveSendBridge === "function") {
        WebSocketConnection.setLiveSendBridge(bridge);
    }
}

function b64ToBytes(b64: string): Uint8Array | null {
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

/** Experimental WebTransport live session (newline JSON on one bidi stream). */
class WebTransportLiveSession {
    emitter: Emitter;
    _transport: WebTransport | null;
    _writer: WritableStreamDefaultWriter<Uint8Array> | null;
    _reader: ReadableStreamDefaultReader<Uint8Array> | null;
    _buffer: string;
    _sessionReady: boolean;
    destroyed: boolean;

    constructor() {
        this.emitter = createEmitter();
        this._transport = null;
        this._writer = null;
        this._reader = null;
        this._buffer = "";
        this._sessionReady = false;
        this.destroyed = false;
    }

    on(event: string | symbol, handler: EmitterHandler): void {
        this.emitter.on(event, handler);
    }

    off(event: string | symbol, handler?: EmitterHandler): void {
        this.emitter.off(event, handler);
    }

    emit(type: string | symbol, event?: unknown): void {
        this.emitter.emit(type, event);
    }

    async connect(opts: { url: string; certSha256B64?: string }): Promise<void> {
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
        const wtOpts: WebTransportOptions = {};
        if (opts.certSha256B64) {
            const value = b64ToBytes(opts.certSha256B64);
            if (value) {
                wtOpts.serverCertificateHashes = [{ algorithm: "sha-256", value: value as BufferSource }];
            }
        }
        const transport = new WebTransport(url, wtOpts);
        const readyRace = Promise.race([
            transport.ready,
            new Promise<never>((_, reject) => {
                setTimeout(() => reject(new Error("webtransport_timeout")), WT_CONNECT_BUDGET_MS);
            }),
        ]);
        await readyRace;
        this._transport = transport;
        const stream = await transport.createBidirectionalStream();
        this._writer = stream.writable.getWriter();
        this._reader = stream.readable.getReader();
        this._sessionReady = true;
        this.emit("connected", { isReconnect: false, transport: "webtransport" });
        this.emit("ready");
        void this._readLoop();
    }

    async _readLoop(): Promise<void> {
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

    isOpen(): boolean {
        return this._transport != null && this._sessionReady;
    }

    send(message: string | object): boolean {
        if (!this.isOpen() || !this._writer) {
            return false;
        }
        let line: string;
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

    sendQueued(message: string | object): boolean {
        return this.send(message);
    }

    destroy(): void {
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

/** Facade: try experimental WebTransport then fall back to WebSocketConnection. */
class LiveTransport {
    emitter: Emitter;
    _active: LiveTransportSource;
    _wt: WebTransportLiveSession | null;
    _mode: LiveTransportMode;
    _serverInfo: WebTransportServerInfo;
    _usingWt: boolean;
    _fallbackNotified: boolean;
    _forwardCleanups: Array<() => void>;
    _boundWs: boolean;

    constructor() {
        this.emitter = createEmitter();
        this._active = WebSocketConnection;
        this._wt = null;
        this._mode = "auto";
        this._serverInfo = { server_available: false };
        this._usingWt = false;
        this._fallbackNotified = false;
        this._forwardCleanups = [];
        this._boundWs = false;
    }

    on(event: string | symbol, handler: EmitterHandler): void {
        this.emitter.on(event, handler);
    }

    off(event: string | symbol, handler?: EmitterHandler): void {
        this.emitter.off(event, handler);
    }

    emit(type: string | symbol, event?: unknown): void {
        this.emitter.emit(type, event);
    }

    configure(opts: LiveTransportConfigureOptions = {}): void {
        if (opts.mode) {
            this._mode = opts.mode;
        }
        if (opts.webtransport && typeof opts.webtransport === "object") {
            this._serverInfo = opts.webtransport;
        }
    }

    _clearForwards(): void {
        for (const fn of this._forwardCleanups) {
            fn();
        }
        this._forwardCleanups = [];
    }

    _forwardFrom(source: LiveTransportSource): void {
        this._clearForwards();
        const events = ["message", "connected", "ready", "disconnected", "queue_expired"] as const;
        for (const ev of events) {
            const handler: EmitterHandler = (payload) => this.emit(ev, payload);
            source.on(ev, handler);
            this._forwardCleanups.push(() => source.off(ev, handler));
        }
    }

    async connect(): Promise<LiveTransportConnectResult> {
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
            try {
                this._wt = new WebTransportLiveSession();
                this._forwardFrom(this._wt);
                await this._wt.connect({
                    url: this._serverInfo.url,
                    certSha256B64: this._serverInfo.cert_sha256_b64,
                });
                this._usingWt = true;
                this._active = this._wt;
                setWsLiveSendBridge({
                    send: (message) => this._wt!.send(message),
                    sendQueued: (message) => this._wt!.send(message),
                    isOpen: () => this._wt!.isOpen(),
                });
                return { transport: "webtransport", fellBack: false };
            } catch {
                this._wt?.destroy();
                this._wt = null;
                this._usingWt = false;
                this._active = WebSocketConnection;
                setWsLiveSendBridge(null);
                this._forwardFrom(WebSocketConnection);
                if (this._mode === "webtransport" || this._mode === "auto") {
                    this._fallbackNotified = true;
                    this.emit("transport_fallback", { from: "webtransport", to: "websocket" });
                }
            }
        }

        setWsLiveSendBridge(null);
        if (typeof (WebSocketConnection as { connect?: () => Promise<void> }).connect === "function") {
            await WebSocketConnection.connect();
        } else {
            WebSocketConnection.reconnect();
        }
        this._usingWt = false;
        this._active = WebSocketConnection;
        return { transport: "websocket", fellBack: this._fallbackNotified };
    }

    send(message: string): boolean {
        return this._active.send(message);
    }

    sendQueued(message: string): boolean {
        if (typeof this._active.sendQueued === "function") {
            return this._active.sendQueued(message);
        }
        return this._active.send(message);
    }

    isOpen(): boolean {
        return this._active.isOpen();
    }

    reconnect(): void {
        if (this._usingWt) {
            this._wt?.destroy();
            this._wt = null;
            this._usingWt = false;
            this._active = WebSocketConnection;
            setWsLiveSendBridge(null);
            this._forwardFrom(WebSocketConnection);
        }
        WebSocketConnection.reconnect();
    }

    forceReconnect(): void {
        if (typeof WebSocketConnection.forceReconnect === "function") {
            WebSocketConnection.forceReconnect();
        } else {
            this.reconnect();
        }
    }

    destroy(): void {
        this._wt?.destroy();
        this._wt = null;
        setWsLiveSendBridge(null);
        this._clearForwards();
        WebSocketConnection.destroy();
    }

    get activeTransport(): "webtransport" | "websocket" {
        return this._usingWt ? "webtransport" : "websocket";
    }

    get fellBackThisSession(): boolean {
        return this._fallbackNotified;
    }
}

export { chooseLiveTransport, clientSupportsWebTransport, WebTransportLiveSession };
export default new LiveTransport();
