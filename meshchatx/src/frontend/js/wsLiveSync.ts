// SPDX-License-Identifier: 0BSD

/**
 * Track broadcast seq and recover gaps via sync.subscribe + REST snapshot.
 */

const STORAGE_PREFIX = "meshchatx_ws_last_seq:";

export type LiveTransportChoice = "webtransport" | "websocket";

export type ChooseLiveTransportInput = {
    mode: string;
    clientSupportsWebTransport: boolean;
    serverAvailable: boolean;
    webTransportConnectOk: boolean | null;
};

export type SyncSubscribeReply = {
    status?: string;
    resync?: boolean;
    current_seq?: number;
    type?: string;
    [key: string]: unknown;
};

export type WsLiveSyncConnection = {
    on: (event: string, handler: (...args: any[]) => void) => void;
    off: (event: string, handler: (...args: any[]) => void) => void;
    send?: (message: string) => unknown;
    sendQueued?: (message: string) => unknown;
};

export type InstallWsLiveSyncOptions = {
    connection: WsLiveSyncConnection;
    onMessagePayload?: (payload: Record<string, unknown>) => void;
    onNeedsResync: () => Promise<void>;
    getStorageKey?: () => string;
};

export type WsLiveSyncHandle = {
    getLastSeq: () => number;
    clearCursor: () => void;
    requestSyncSubscribe: () => Promise<void>;
    dispose: () => void;
};

export function seqStorageKey(origin?: string): string {
    const o = origin || (typeof window !== "undefined" ? window.location.origin : "");
    return `${STORAGE_PREFIX}${o || "default"}`;
}

export function loadLastSeq(key: string): number {
    try {
        if (typeof sessionStorage === "undefined") {
            return 0;
        }
        const raw = sessionStorage.getItem(key);
        const n = Number.parseInt(raw || "0", 10);
        return Number.isFinite(n) && n >= 0 ? n : 0;
    } catch {
        return 0;
    }
}

export function saveLastSeq(key: string, seq: number): void {
    try {
        if (typeof sessionStorage === "undefined") {
            return;
        }
        sessionStorage.setItem(key, String(Math.max(0, Math.floor(seq))));
    } catch {
        // ignore quota / private mode
    }
}

export function clearLastSeq(key: string): void {
    try {
        if (typeof sessionStorage === "undefined") {
            return;
        }
        sessionStorage.removeItem(key);
    } catch {
        // ignore
    }
}

export function nextLastSeqFromPayload(payload: unknown, lastSeq: number): number {
    if (!payload || typeof payload !== "object") {
        return lastSeq;
    }
    const seq = (payload as { seq?: unknown }).seq;
    if (typeof seq !== "number" || !Number.isFinite(seq) || seq < 0) {
        return lastSeq;
    }
    return Math.max(lastSeq, Math.floor(seq));
}

export function syncSubscribeRequiresResync(reply: SyncSubscribeReply | null | undefined): boolean {
    if (!reply || typeof reply !== "object") {
        return false;
    }
    if (reply.resync === true) {
        return true;
    }
    return reply.status === "gap";
}

/** Pure oracle for transport mode selection. */
export function chooseLiveTransport(input: ChooseLiveTransportInput): LiveTransportChoice {
    const mode = input.mode || "auto";
    if (mode === "websocket") {
        return "websocket";
    }
    const canTry =
        (mode === "auto" || mode === "webtransport") &&
        input.clientSupportsWebTransport === true &&
        input.serverAvailable === true;
    if (!canTry) {
        return "websocket";
    }
    if (input.webTransportConnectOk === false) {
        return "websocket";
    }
    if (input.webTransportConnectOk === true) {
        return "webtransport";
    }
    return "webtransport";
}

export function installWsLiveSync(options: InstallWsLiveSyncOptions): WsLiveSyncHandle {
    const connection = options.connection;
    const onNeedsResync = options.onNeedsResync;
    const getStorageKey = options.getStorageKey || (() => seqStorageKey());
    let lastSeq = loadLastSeq(getStorageKey());
    let syncInFlight = false;
    let disposed = false;

    function persist() {
        saveLastSeq(getStorageKey(), lastSeq);
    }

    function notePayload(payload: Record<string, unknown>) {
        if (!payload || typeof payload !== "object") {
            return;
        }
        lastSeq = nextLastSeqFromPayload(payload, lastSeq);
        persist();
        if (typeof options.onMessagePayload === "function") {
            options.onMessagePayload(payload);
        }
    }

    async function requestSyncSubscribe() {
        if (disposed || syncInFlight) {
            return;
        }
        syncInFlight = true;
        try {
            const requestId = `sync-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
            const msg = JSON.stringify({
                type: "sync.subscribe",
                since_seq: lastSeq,
                request_id: requestId,
            });
            if (typeof connection.sendQueued === "function") {
                connection.sendQueued(msg);
            } else if (typeof connection.send === "function") {
                connection.send(msg);
            }
        } finally {
            syncInFlight = false;
        }
    }

    async function handleSyncReply(payload: SyncSubscribeReply) {
        if (!syncSubscribeRequiresResync(payload)) {
            if (typeof payload?.current_seq === "number") {
                lastSeq = Math.max(lastSeq, Math.floor(payload.current_seq));
                persist();
            }
            return;
        }
        await onNeedsResync();
        if (typeof payload?.current_seq === "number") {
            lastSeq = Math.max(lastSeq, Math.floor(payload.current_seq));
            persist();
        }
    }

    function onMessage(message: unknown) {
        try {
            const raw = message as { data?: unknown } | string | Record<string, unknown>;
            const data =
                typeof (raw as { data?: unknown })?.data === "string"
                    ? JSON.parse((raw as { data: string }).data)
                    : raw;
            if (!data || typeof data !== "object") {
                return;
            }
            const payload = data as SyncSubscribeReply;
            notePayload(payload);
            if (payload.type === "sync.subscribe") {
                void handleSyncReply(payload);
            }
        } catch {
            // ignore
        }
    }

    function onReady() {
        void requestSyncSubscribe();
    }

    connection.on("message", onMessage);
    connection.on("ready", onReady);

    return {
        getLastSeq: () => lastSeq,
        clearCursor: () => {
            lastSeq = 0;
            clearLastSeq(getStorageKey());
        },
        requestSyncSubscribe,
        dispose: () => {
            disposed = true;
            connection.off("message", onMessage);
            connection.off("ready", onReady);
        },
    };
}
