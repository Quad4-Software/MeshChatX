// SPDX-License-Identifier: 0BSD AND MIT

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
 * Prefers seq. Falls back to kind/ts/src/text for older payloads without seq.
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
 * True when existing should sort after msg. Compares by seq first and
 * falls back to the timestamp for payloads without seq.
 * @param {object} existing
 * @param {object} msg
 * @returns {boolean}
 */
function relayMessageSortsAfter(existing, msg) {
    const existingSeq = typeof existing?.seq === "number" ? existing.seq : null;
    const msgSeq = typeof msg?.seq === "number" ? msg.seq : null;
    if (existingSeq !== null && msgSeq !== null) {
        return existingSeq > msgSeq;
    }
    const existingTs = Number(existing?.ts);
    const msgTs = Number(msg?.ts);
    if (Number.isFinite(existingTs) && Number.isFinite(msgTs)) {
        return existingTs > msgTs;
    }
    return false;
}

/**
 * Merge extras that are not already represented in base (by seq / fallback
 * key). New entries land in seq/timestamp order instead of always at the
 * tail so an un-ignored peer's historical messages do not appear below
 * newer arrivals.
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
        if (!msg || relayMessageAlreadyPresent(out, msg)) {
            continue;
        }
        let idx = out.length;
        for (let i = 0; i < out.length; i++) {
            if (relayMessageSortsAfter(out[i], msg)) {
                idx = i;
                break;
            }
        }
        out.splice(idx, 0, msg);
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
    if (msg.event === "join" || msg.event === "part") {
        return true;
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
 * Peer join/part presence lines only: own-join confirmations ("You joined")
 * and connection events stay visible when presence muting is on. Detects the
 * backend msg.event tag and falls back to the generated text for older
 * history entries.
 * @param {object} msg
 * @returns {boolean}
 */
export function isRelayPeerJoinPartMessage(msg) {
    if (!msg || msg.kind !== "system") {
        return false;
    }
    if (msg.event === "join" || msg.event === "part") {
        return true;
    }
    const text = typeof msg.text === "string" ? msg.text.trim() : "";
    return text.endsWith(" joined") || text.endsWith(" left");
}

/**
 * @param {object} msg
 * @returns {"joined"|"left"|"connection"}
 */
export function relayPresenceEventKind(msg) {
    if (msg?.event === "part") {
        return "left";
    }
    if (msg?.event === "join") {
        return "joined";
    }
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
 * @param {{ hideJoinPart?: boolean }} [options]
 * @returns {{ type: string, dayKey?: string, msg?: object, id?: string, messages?: object[], joinedCount?: number, leftCount?: number, connectionCount?: number }[]}
 */
export function buildRelayMessageTimeline(messages, options = {}) {
    const hideJoinPart = options.hideJoinPart === true;
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
        if (hideJoinPart && isRelayPeerJoinPartMessage(msg)) {
            continue;
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
    // Rolling fingerprint over per-message fields that affect grouping.
    // Length+min/max alone misses in-place edits (flag flips, text updates)
    // and leaves the cached timeline stale.
    let fingerprint = 0;
    for (const msg of messages) {
        const seq = typeof msg?.seq === "number" ? msg.seq : 0;
        const textLen = typeof msg?.text === "string" ? msg.text.length : 0;
        fingerprint =
            (fingerprint * 31 +
                seq +
                textLen * 7 +
                (msg?.highlighted ? 1 : 0) +
                (msg?.localMention ? 2 : 0) +
                (msg?.event ? 4 : 0)) |
            0;
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
    return `${messages.length}\u241f${minSeq ?? ""}\u241f${maxSeq ?? ""}\u241f${fingerprint}`;
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
 * @param {{ hideJoinPart?: boolean }} [options]
 * @returns {object[]}
 */
export function prependRelayMessageTimeline(existingTimeline, prependedMessagesOldestFirst, options = {}) {
    const prepended = prependedMessagesOldestFirst || [];
    const existing = existingTimeline || [];
    if (prepended.length === 0) {
        return existing;
    }
    if (existing.length === 0) {
        return buildRelayMessageTimeline(prepended, options);
    }
    const prefixTimeline = buildRelayMessageTimeline(prepended, options);
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
    // A contiguous presence run can straddle the page boundary. Without this
    // merge it renders as two adjacent groups. The existing timeline usually
    // opens with a dateDivider, so look past it before checking for presence.
    const prefixPresence =
        lastPrefix?.type === "presenceGroup"
            ? lastPrefix.messages
            : lastPrefix?.type === "message" && isRelayPresenceSystemMessage(lastPrefix.msg)
              ? [lastPrefix.msg]
              : null;
    let leadDivider = null;
    let existingHead = existing;
    if (firstExisting?.type === "dateDivider" && existing.length > 1) {
        leadDivider = firstExisting;
        existingHead = existing.slice(1);
    }
    const headFirst = existingHead[0];
    const existingPresence =
        headFirst?.type === "presenceGroup"
            ? headFirst.messages
            : headFirst?.type === "message" && isRelayPresenceSystemMessage(headFirst.msg)
              ? [headFirst.msg]
              : null;
    // Do not merge across a day boundary: the divider must match the day of
    // the presence messages on both sides of the seam.
    const dayKeyOf = (msg) => {
        const ms = typeof msg?.ts === "number" ? msg.ts : Number(msg?.ts);
        const d = new Date(ms);
        return Number.isNaN(d.getTime()) ? null : calendarDayKeyFromDate(d);
    };
    if (
        prefixPresence &&
        existingPresence &&
        dayKeyOf(prefixPresence[prefixPresence.length - 1]) === dayKeyOf(existingPresence[0]) &&
        (leadDivider === null || leadDivider.dayKey === dayKeyOf(existingPresence[0]))
    ) {
        const merged = buildPresenceGroup(prefixPresence.concat(existingPresence));
        // Keep the already-rendered group's id: expansion state is keyed
        // by it, and a fresh id would collapse the group when older
        // history is prepended.
        if (headFirst?.type === "presenceGroup" && headFirst.id) {
            merged.id = headFirst.id;
        }
        const head = leadDivider ? [leadDivider] : [];
        return prefixTimeline.slice(0, -1).concat(head, [merged], existingHead.slice(1));
    }
    return prefixTimeline.concat(existing);
}
