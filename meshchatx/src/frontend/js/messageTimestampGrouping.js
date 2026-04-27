/** Gap after which the next message starts a new time cluster (ms). */
export const TIMESTAMP_CLUSTER_GAP_MS = 5 * 60 * 1000;

/**
 * @param {unknown} datetimeString
 * @returns {Date | null}
 */
export function parseMessageDate(datetimeString) {
    if (!datetimeString) {
        return null;
    }
    let dateString = String(datetimeString);
    if (!dateString.includes("Z") && !dateString.includes("+")) {
        dateString = dateString.replace(" ", "T") + "Z";
    }
    const date = new Date(dateString);
    return Number.isNaN(date.getTime()) ? null : date;
}

/**
 * Local calendar day key for grouping.
 * @param {Date} d
 * @returns {string | null}
 */
export function calendarDayKeyFromDate(d) {
    if (!d || Number.isNaN(d.getTime())) {
        return null;
    }
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

/**
 * @param {unknown} group
 * @returns {{ min: number, max: number }}
 */
export function displayGroupSortBoundsMs(group) {
    if (!group || typeof group !== "object") {
        return { min: 0, max: 0 };
    }
    if (group.type === "single") {
        const t = parseMessageDate(group.chatItem?.lxmf_message?.created_at)?.getTime() ?? 0;
        return { min: t, max: t };
    }
    if (group.type === "imageGroup" && Array.isArray(group.items) && group.items.length > 0) {
        let minT = Infinity;
        let maxT = -Infinity;
        for (const it of group.items) {
            const t = parseMessageDate(it?.lxmf_message?.created_at)?.getTime();
            if (t && !Number.isNaN(t)) {
                minT = Math.min(minT, t);
                maxT = Math.max(maxT, t);
            }
        }
        if (minT === Infinity) {
            return { min: 0, max: 0 };
        }
        return { min: minT, max: maxT };
    }
    return { min: 0, max: 0 };
}

/**
 * @param {unknown} group
 * @returns {boolean}
 */
export function displayGroupIsOutbound(group) {
    if (group?.type === "single") {
        return !!group.chatItem?.is_outbound;
    }
    if (group?.type === "imageGroup" && group.items?.[0]) {
        return !!group.items[0].is_outbound;
    }
    return false;
}

/**
 * Inserts date dividers and sets `showTimestamp` on each message row (true on the
 * chronologically last message of each cluster, i.e. the bubble that should show the time).
 * @param {unknown[]} groupsOldestFirst
 * @param {{ groupingEnabled?: boolean }} [options]
 * @returns {unknown[]}
 */
export function buildTimestampGroupedOldestFirst(groupsOldestFirst, options = {}) {
    const groupingEnabled = options.groupingEnabled !== false;
    if (!groupsOldestFirst?.length) {
        return [];
    }
    const onlyMsg = groupsOldestFirst.filter((g) => g && (g.type === "single" || g.type === "imageGroup"));
    if (!groupingEnabled) {
        return onlyMsg.map((g) => ({ ...g, showTimestamp: true }));
    }
    const showFlags = [];
    for (let i = 0; i < onlyMsg.length; i++) {
        const g = onlyMsg[i];
        const next = onlyMsg[i + 1];
        let show = true;
        if (next) {
            const cb = displayGroupSortBoundsMs(g);
            const nb = displayGroupSortBoundsMs(next);
            const sameSide = displayGroupIsOutbound(g) === displayGroupIsOutbound(next);
            const gap = nb.min - cb.max;
            show = !sameSide || gap >= TIMESTAMP_CLUSTER_GAP_MS || gap < 0;
        }
        showFlags.push(show);
    }

    const out = [];
    let prevDayKey = null;
    for (let i = 0; i < onlyMsg.length; i++) {
        const g = onlyMsg[i];
        const bounds = displayGroupSortBoundsMs(g);
        const dayKey = bounds.min ? calendarDayKeyFromDate(new Date(bounds.min)) : null;
        if (dayKey && dayKey !== prevDayKey) {
            out.push({
                type: "dateDivider",
                dayKey,
                key: `date-div-${dayKey}-${out.length}`,
            });
            prevDayKey = dayKey;
        }
        out.push({ ...g, showTimestamp: showFlags[i] });
    }
    return out;
}
