import { describe, it, expect } from "vitest";
import {
    TIMESTAMP_CLUSTER_GAP_MS,
    buildTimestampGroupedOldestFirst,
    calendarDayKeyFromDate,
    displayGroupIsOutbound,
    displayGroupSortBoundsMs,
} from "../../meshchatx/src/frontend/js/messageTimestampGrouping.js";

describe("messageTimestampGrouping", () => {
    it("calendarDayKeyFromDate uses local calendar fields", () => {
        const d = new Date(2026, 3, 26, 23, 59);
        expect(calendarDayKeyFromDate(d)).toBe("2026-04-26");
    });

    it("inserts a date divider when calendar day changes", () => {
        const a = {
            type: "single",
            key: "a",
            chatItem: { is_outbound: false, lxmf_message: { created_at: "2026-04-25T12:00:00Z", hash: "a" } },
        };
        const b = {
            type: "single",
            key: "b",
            chatItem: { is_outbound: false, lxmf_message: { created_at: "2026-04-28T12:00:00Z", hash: "b" } },
        };
        const out = buildTimestampGroupedOldestFirst([a, b]);
        const dividers = out.filter((x) => x.type === "dateDivider");
        expect(dividers.length).toBeGreaterThanOrEqual(2);
        expect(
            out
                .filter((x) => x.type === "single")
                .map((x) => x.key)
                .join(",")
        ).toBe("a,b");
    });

    it("hides timestamp on middle messages of a same-side cluster within gap", () => {
        const t0 = "2026-04-26T12:00:00Z";
        const t1 = "2026-04-26T12:01:00Z";
        const t2 = "2026-04-26T12:02:00Z";
        const m0 = {
            type: "single",
            key: "m0",
            chatItem: { is_outbound: true, lxmf_message: { created_at: t0, hash: "h0" } },
        };
        const m1 = {
            type: "single",
            key: "m1",
            chatItem: { is_outbound: true, lxmf_message: { created_at: t1, hash: "h1" } },
        };
        const m2 = {
            type: "single",
            key: "m2",
            chatItem: { is_outbound: true, lxmf_message: { created_at: t2, hash: "h2" } },
        };
        const out = buildTimestampGroupedOldestFirst([m0, m1, m2]).filter((x) => x.type === "single");
        expect(out[0].showTimestamp).toBe(true);
        expect(out[1].showTimestamp).toBe(true);
        expect(out[2].showTimestamp).toBe(true);
    });

    it("starts a new cluster after TIMESTAMP_CLUSTER_GAP_MS", () => {
        const t0 = "2026-04-26T12:00:00Z";
        const t1 = new Date(new Date(t0).getTime() + TIMESTAMP_CLUSTER_GAP_MS + 60 * 1000).toISOString();
        const a = {
            type: "single",
            key: "a",
            chatItem: { is_outbound: true, lxmf_message: { created_at: t0, hash: "a" } },
        };
        const b = {
            type: "single",
            key: "b",
            chatItem: { is_outbound: true, lxmf_message: { created_at: t1, hash: "b" } },
        };
        const out = buildTimestampGroupedOldestFirst([a, b]).filter((x) => x.type === "single");
        expect(out[0].showTimestamp).toBe(true);
        expect(out[1].showTimestamp).toBe(true);
    });

    it("with grouping disabled, omits date dividers and shows timestamp on every message", () => {
        const a = {
            type: "single",
            key: "a",
            chatItem: { is_outbound: false, lxmf_message: { created_at: "2026-04-25T12:00:00Z", hash: "a" } },
        };
        const b = {
            type: "single",
            key: "b",
            chatItem: { is_outbound: false, lxmf_message: { created_at: "2026-04-28T12:00:00Z", hash: "b" } },
        };
        const out = buildTimestampGroupedOldestFirst([a, b], { groupingEnabled: false });
        expect(out.filter((x) => x.type === "dateDivider")).toHaveLength(0);
        const singles = out.filter((x) => x.type === "single");
        expect(singles.every((x) => x.showTimestamp === true)).toBe(true);
    });

    it("displayGroupSortBoundsMs spans image group min/max", () => {
        const g = {
            type: "imageGroup",
            key: "ig",
            items: [
                { is_outbound: true, lxmf_message: { created_at: "2026-04-26T12:00:00Z" } },
                { is_outbound: true, lxmf_message: { created_at: "2026-04-26T12:05:00Z" } },
            ],
        };
        const b = displayGroupSortBoundsMs(g);
        expect(b.max - b.min).toBe(5 * 60 * 1000);
        expect(displayGroupIsOutbound(g)).toBe(true);
    });
});
