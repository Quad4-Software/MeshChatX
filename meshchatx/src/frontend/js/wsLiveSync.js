// SPDX-License-Identifier: 0BSD

/**
 * Track broadcast seq and recover gaps via sync.subscribe + REST snapshot.
 */

const STORAGE_PREFIX = "meshchatx_ws_last_seq:";

/**
 * @param {string} [origin]
 * @returns {string}
 */
export function seqStorageKey(origin) {
    const o = origin || (typeof window !== "undefined" ? window.location.origin : "");
    return `${STORAGE_PREFIX}${o || "default"}`;
}

/**
 * @param {string} key
 * @returns {number}
 */
export function loadLastSeq(key) {
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

/**
 * @param {string} key
 * @param {number} seq
 */
export function saveLastSeq(key, seq) {
    try {
        if (typeof sessionStorage === "undefined") {
            return;
        }
        sessionStorage.setItem(key, String(Math.max(0, Math.floor(seq))));
    } catch {
        // ignore quota / private mode
    }
}

/**
 * @param {string} key
 */
export function clearLastSeq(key) {
    try {
        if (typeof sessionStorage === "undefined") {
            return;
        }
        sessionStorage.removeItem(key);
    } catch {
        // ignore
    }
}

/**
 * @param {unknown} payload
 * @param {number} lastSeq
 * @returns {number}
 */
export function nextLastSeqFromPayload(payload, lastSeq) {
    if (!payload || typeof payload !== "object") {
        return lastSeq;
    }
    const seq = /** @type {{ seq?: unknown }} */ (payload).seq;
    if (typeof seq !== "number" || !Number.isFinite(seq) || seq < 0) {
        return lastSeq;
    }
    return Math.max(lastSeq, Math.floor(seq));
}

/**
 * @param {{ status?: string, resync?: boolean }} reply
 * @returns {boolean}
 */
export function syncSubscribeRequiresResync(reply) {
    if (!reply || typeof reply !== "object") {
        return false;
    }
    if (reply.resync === true) {
        return true;
    }
    return reply.status === "gap";
}

/**
 * Pure oracle for transport mode selection.
 * @param {{
 *   mode: string,
 *   clientSupportsWebTransport: boolean,
 *   serverAvailable: boolean,
 *   webTransportConnectOk: boolean | null,
 * }} input
 * @returns {"webtransport" | "websocket"}
 */
export function chooseLiveTransport(input) {
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

/**
 * @param {object} options
 * @param {() => object} options.connection Emitter with on/off/send/sendQueued
 * @param {(payload: object) => void} [options.onMessagePayload]
 * @param {() => Promise<void>} options.onNeedsResync
 * @param {() => string} [options.getStorageKey]
 */
export function installWsLiveSync(options) {
    const connection = options.connection;
    const onNeedsResync = options.onNeedsResync;
    const getStorageKey = options.getStorageKey || (() => seqStorageKey());
    let lastSeq = loadLastSeq(getStorageKey());
    let syncInFlight = false;
    let disposed = false;

    function persist() {
        saveLastSeq(getStorageKey(), lastSeq);
    }

    function notePayload(payload) {
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

    async function handleSyncReply(payload) {
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

    function onMessage(message) {
        try {
            const data = typeof message?.data === "string" ? JSON.parse(message.data) : message;
            if (!data || typeof data !== "object") {
                return;
            }
            notePayload(data);
            if (data.type === "sync.subscribe") {
                void handleSyncReply(data);
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
