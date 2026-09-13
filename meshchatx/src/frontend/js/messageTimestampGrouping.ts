/** Gap after which the next message starts a new time cluster (ms). */
export const TIMESTAMP_CLUSTER_GAP_MS = 5 * 60 * 1000;

export type MessageChatItem = {
    is_outbound?: boolean;
    lxmf_message?: {
        created_at?: unknown;
    };
};

export type DisplayGroupSingle = {
    type: "single";
    chatItem?: MessageChatItem;
    showTimestamp?: boolean;
    [key: string]: unknown;
};

export type DisplayGroupImage = {
    type: "imageGroup";
    items?: MessageChatItem[];
    showTimestamp?: boolean;
    [key: string]: unknown;
};

export type DisplayGroupMessage = DisplayGroupSingle | DisplayGroupImage;

export type DateDividerGroup = {
    type: "dateDivider";
    dayKey: string;
    key: string;
};

export type TimestampGroupedItem = DisplayGroupMessage | DateDividerGroup;

export type TimestampGroupingOptions = {
    groupingEnabled?: boolean;
};

export type SortBoundsMs = {
    min: number;
    max: number;
};

export function parseMessageDate(datetimeString: unknown): Date | null {
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

/** Local calendar day key for grouping. */
export function calendarDayKeyFromDate(d: Date): string | null {
    if (!d || Number.isNaN(d.getTime())) {
        return null;
    }
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

export function displayGroupSortBoundsMs(group: unknown): SortBoundsMs {
    if (!group || typeof group !== "object") {
        return { min: 0, max: 0 };
    }
    const g = group as DisplayGroupMessage;
    if (g.type === "single") {
        const t = parseMessageDate(g.chatItem?.lxmf_message?.created_at)?.getTime() ?? 0;
        return { min: t, max: t };
    }
    if (g.type === "imageGroup" && Array.isArray(g.items) && g.items.length > 0) {
        let minT = Infinity;
        let maxT = -Infinity;
        for (const it of g.items) {
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

export function displayGroupIsOutbound(group: unknown): boolean {
    const g = group as DisplayGroupMessage | null | undefined;
    if (g?.type === "single") {
        return !!g.chatItem?.is_outbound;
    }
    if (g?.type === "imageGroup" && g.items?.[0]) {
        return !!g.items[0].is_outbound;
    }
    return false;
}

/**
 * Inserts date dividers and sets showTimestamp on each message row (true on the
 * chronologically last message of each cluster, i.e. the bubble that should show the time).
 */
export function buildTimestampGroupedOldestFirst(
    groupsOldestFirst: unknown[],
    options: TimestampGroupingOptions = {}
): TimestampGroupedItem[] {
    const groupingEnabled = options.groupingEnabled !== false;
    if (!groupsOldestFirst?.length) {
        return [];
    }
    const onlyMsg = groupsOldestFirst.filter(
        (g): g is DisplayGroupMessage =>
            !!g &&
            typeof g === "object" &&
            ((g as DisplayGroupMessage).type === "single" || (g as DisplayGroupMessage).type === "imageGroup")
    );
    if (!groupingEnabled) {
        return onlyMsg.map((g) => ({ ...g, showTimestamp: true }));
    }
    const showFlags: boolean[] = [];
    for (let i = 0; i < onlyMsg.length; i++) {
        const g = onlyMsg[i];
        const next = onlyMsg[i + 1];
        let show = true;
        if (next && !displayGroupIsOutbound(g)) {
            const cb = displayGroupSortBoundsMs(g);
            const nb = displayGroupSortBoundsMs(next);
            const sameSide = displayGroupIsOutbound(g) === displayGroupIsOutbound(next);
            const gap = nb.min - cb.max;
            show = !sameSide || gap >= TIMESTAMP_CLUSTER_GAP_MS || gap < 0;
        }
        showFlags.push(show);
    }

    const out: TimestampGroupedItem[] = [];
    let prevDayKey: string | null = null;
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
