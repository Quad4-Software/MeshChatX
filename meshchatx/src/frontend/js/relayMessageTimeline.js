// SPDX-License-Identifier: 0BSD AND MIT

import { calendarDayKeyFromDate } from "./messageTimestampGrouping.js";

/**
 * @param {object} msg
 * @returns {string}
 */
export function relayMessageKey(msg) {
    if (!msg) {
        return "";
    }
    if (msg.seq != null && msg.seq !== "") {
        return `seq-${msg.seq}`;
    }
    const src = msg.src || "";
    const text = typeof msg.text === "string" ? msg.text : "";
    // Keep keys attribute-safe: never embed raw message text (XSS-shaped payloads).
    const textFrag = encodeURIComponent(text.slice(0, 24));
    return `${msg.kind || "msg"}-${msg.ts || 0}-${src}-${text.length}-${textFrag}`;
}

/**
 * True when an incoming relay message is already present in the list.
 * Prefers seq; falls back to kind/ts/src/text for older payloads without seq.
 * @param {object[]} messages
 * @param {object} incoming
 * @returns {boolean}
 */
export function relayMessageAlreadyPresent(messages, incoming) {
    if (!Array.isArray(messages) || !incoming) {
        return false;
    }
    const incomingSeq = incoming.seq;
    if (incomingSeq != null && incomingSeq !== "") {
        return messages.some((m) => m && m.seq === incomingSeq);
    }
    const key = relayMessageKey(incoming);
    if (!key) {
        return false;
    }
    return messages.some((m) => relayMessageKey(m) === key);
}

/**
 * Append extras that are not already represented in base (by seq / fallback key).
 * @param {object[]} base
 * @param {object[]} extras
 * @returns {object[]}
 */
export function mergeRelayMessages(base, extras) {
    const out = Array.isArray(base) ? [...base] : [];
    if (!Array.isArray(extras) || extras.length === 0) {
        return out;
    }
    for (const msg of extras) {
        if (msg && !relayMessageAlreadyPresent(out, msg)) {
            out.push(msg);
        }
    }
    return out;
}

const CONNECTION_EVENT_TEXTS = new Set(["Connection lost", "Disconnected from hub", "Reconnected to hub"]);

/**
 * Join/leave/connection system lines produced by the RRC client.
 * @param {object} msg
 * @returns {boolean}
 */
export function isRelayPresenceSystemMessage(msg) {
    if (!msg || msg.kind !== "system") {
        return false;
    }
    const text = typeof msg.text === "string" ? msg.text.trim() : "";
    if (!text) {
        return false;
    }
    if (CONNECTION_EVENT_TEXTS.has(text)) {
        return true;
    }
    if (text.endsWith(" joined") || text.endsWith(" left")) {
        return true;
    }
    return /^You (?:re)?joined #/i.test(text);
}

/**
 * @param {object} msg
 * @returns {"joined"|"left"|"connection"}
 */
export function relayPresenceEventKind(msg) {
    const text = typeof msg?.text === "string" ? msg.text.trim() : "";
    if (CONNECTION_EVENT_TEXTS.has(text)) {
        return "connection";
    }
    if (text.endsWith(" left")) {
        return "left";
    }
    return "joined";
}

/**
 * @param {object[]} presenceMessages
 * @returns {{ type: string, id: string, messages: object[], joinedCount: number, leftCount: number, connectionCount: number }}
 */
function buildPresenceGroup(presenceMessages) {
    let joinedCount = 0;
    let leftCount = 0;
    let connectionCount = 0;
    for (const msg of presenceMessages) {
        const kind = relayPresenceEventKind(msg);
        if (kind === "left") {
            leftCount += 1;
        } else if (kind === "connection") {
            connectionCount += 1;
        } else {
            joinedCount += 1;
        }
    }
    const firstKey = relayMessageKey(presenceMessages[0]);
    return {
        type: "presenceGroup",
        id: firstKey || `presence-${presenceMessages.length}`,
        messages: presenceMessages,
        joinedCount,
        leftCount,
        connectionCount,
    };
}

/**
 * @param {object[]} messages
 * @returns {{ type: string, dayKey?: string, msg?: object, id?: string, messages?: object[], joinedCount?: number, leftCount?: number, connectionCount?: number }[]}
 */
export function buildRelayMessageTimeline(messages) {
    if (!Array.isArray(messages) || messages.length === 0) {
        return [];
    }
    const out = [];
    let prevDayKey = null;
    /** @type {object[]} */
    let presenceBuffer = [];

    const flushPresence = () => {
        if (presenceBuffer.length === 0) {
            return;
        }
        if (presenceBuffer.length === 1) {
            out.push({ type: "message", msg: presenceBuffer[0] });
        } else {
            out.push(buildPresenceGroup(presenceBuffer));
        }
        presenceBuffer = [];
    };

    for (const msg of messages) {
        let dayKey = null;
        if (msg?.ts != null) {
            const ms = typeof msg.ts === "number" ? msg.ts : Number(msg.ts);
            const d = new Date(ms);
            if (!Number.isNaN(d.getTime())) {
                dayKey = calendarDayKeyFromDate(d);
            }
        }
        if (dayKey && dayKey !== prevDayKey) {
            flushPresence();
            out.push({ type: "dateDivider", dayKey });
            prevDayKey = dayKey;
        }
        if (isRelayPresenceSystemMessage(msg)) {
            presenceBuffer.push(msg);
            continue;
        }
        flushPresence();
        out.push({ type: "message", msg });
    }
    flushPresence();
    return out;
}
