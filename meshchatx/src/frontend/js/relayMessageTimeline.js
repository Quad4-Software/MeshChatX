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
    const src = msg.src || "";
    return `${msg.kind || "msg"}-${msg.ts || 0}-${src}`;
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
