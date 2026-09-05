// SPDX-License-Identifier: 0BSD

import { calendarDayKeyFromDate } from "./messageTimestampGrouping.js";

/** Initial room history page size (newest messages). */
export const RELAY_MESSAGES_INITIAL_PAGE_SIZE = 150;

/** Older history page size when scrolling up. */
export const RELAY_MESSAGES_PREVIOUS_PAGE_SIZE = 100;

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

/**
 * @param {object[]} messages
 * @returns {string}
 */
export function relayMessageTimelineSignature(messages) {
    if (!Array.isArray(messages) || messages.length === 0) {
        return "";
    }
    let minSeq = null;
    let maxSeq = null;
    for (const msg of messages) {
        if (typeof msg?.seq !== "number") {
            continue;
        }
        if (minSeq === null || msg.seq < minSeq) {
            minSeq = msg.seq;
        }
        if (maxSeq === null || msg.seq > maxSeq) {
            maxSeq = msg.seq;
        }
    }
    return `${messages.length}\u241f${minSeq ?? ""}\u241f${maxSeq ?? ""}`;
}

/**
 * Keep only older rows not already present. Uses seq Set for O(n) dedupe.
 *
 * @param {object[]} older
 * @param {object[]} existingMessages
 * @returns {object[]}
 */
export function filterUniqueOlderRelayMessages(older, existingMessages) {
    if (!Array.isArray(older) || older.length === 0) {
        return [];
    }
    const existingSeqs = new Set();
    if (Array.isArray(existingMessages)) {
        for (const msg of existingMessages) {
            if (msg && msg.seq != null) {
                existingSeqs.add(msg.seq);
            }
        }
    }
    const out = [];
    for (const msg of older) {
        if (!msg) {
            continue;
        }
        if (msg.seq != null) {
            if (existingSeqs.has(msg.seq)) {
                continue;
            }
            existingSeqs.add(msg.seq);
            out.push(msg);
            continue;
        }
        if (!relayMessageAlreadyPresent(existingMessages, msg) && !relayMessageAlreadyPresent(out, msg)) {
            out.push(msg);
        }
    }
    return out;
}

/**
 * Extend a cached timeline after prepending older messages (oldest-first).
 *
 * @param {object[]} existingTimeline
 * @param {object[]} prependedMessagesOldestFirst
 * @returns {object[]}
 */
export function prependRelayMessageTimeline(existingTimeline, prependedMessagesOldestFirst) {
    const prepended = prependedMessagesOldestFirst || [];
    const existing = existingTimeline || [];
    if (prepended.length === 0) {
        return existing;
    }
    if (existing.length === 0) {
        return buildRelayMessageTimeline(prepended);
    }
    const prefixTimeline = buildRelayMessageTimeline(prepended);
    if (prefixTimeline.length === 0) {
        return existing;
    }
    const lastPrefix = prefixTimeline[prefixTimeline.length - 1];
    const firstExisting = existing[0];
    if (
        lastPrefix?.type === "dateDivider" &&
        firstExisting?.type === "dateDivider" &&
        lastPrefix.dayKey === firstExisting.dayKey
    ) {
        return prefixTimeline.slice(0, -1).concat(existing);
    }
    return prefixTimeline.concat(existing);
}
