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
    return `${msg.kind || "msg"}-${msg.ts || 0}-${src}-${text.length}-${text.slice(0, 24)}`;
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

/**
 * @param {object[]} messages
 * @returns {{ type: string, dayKey?: string, msg?: object }[]}
 */
export function buildRelayMessageTimeline(messages) {
    if (!Array.isArray(messages) || messages.length === 0) {
        return [];
    }
    const out = [];
    let prevDayKey = null;
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
            out.push({ type: "dateDivider", dayKey });
            prevDayKey = dayKey;
        }
        out.push({ type: "message", msg });
    }
    return out;
}
