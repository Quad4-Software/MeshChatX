import { describe, it, expect } from "vitest";
import {
    filterRelayMembers,
    filterRelayMessages,
    parseRelaySearchQuery,
    parseDateSearchToken,
} from "@/js/relayMessageSearch.js";
import { buildRelayMessageTimeline, relayMessageKey } from "@/js/relayMessageTimeline.js";

const displayName = (msg) => msg.nick || "anon";

describe("relayMessageSearch", () => {
    const messages = [
        { kind: "msg", ts: new Date("2026-06-02T12:00:00").getTime(), nick: "alice", text: "hello world" },
        { kind: "msg", ts: new Date("2026-06-01T12:00:00").getTime(), nick: "bob", text: "goodbye" },
        { kind: "system", ts: new Date("2026-06-02T13:00:00").getTime(), text: "joined" },
    ];

    it("returns empty when query is empty", () => {
        expect(filterRelayMessages(messages, "", displayName)).toEqual([]);
        expect(filterRelayMessages(messages, "   ", displayName)).toEqual([]);
    });

    it("ANDs terms by default", () => {
        const hits = filterRelayMessages(messages, "hello world", displayName);
        expect(hits).toHaveLength(1);
        expect(hits[0].nick).toBe("alice");
    });

    it("supports OR between clauses", () => {
        const hits = filterRelayMessages(messages, "hello OR goodbye", displayName);
        expect(hits).toHaveLength(2);
    });

    it("filters by DATE token", () => {
        const hits = filterRelayMessages(messages, "DATE:2026-06-02", displayName);
        expect(hits.every((m) => m.ts >= new Date("2026-06-02").setHours(0, 0, 0, 0))).toBe(true);
        expect(hits.some((m) => m.nick === "bob")).toBe(false);
    });

    it("combines DATE with text terms", () => {
        const hits = filterRelayMessages(messages, "DATE:2026-06-02 hello", displayName);
        expect(hits).toHaveLength(1);
        expect(hits[0].nick).toBe("alice");
    });

    it("parses today date token", () => {
        const todayKey = parseDateSearchToken("today");
        expect(todayKey).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it("filters members by name or hash", () => {
        const members = [
            { hash: "aabbcc", name: "Alice" },
            { hash: "ddeeff", name: "Bob" },
        ];
        expect(filterRelayMembers(members, "ali")).toHaveLength(1);
        expect(filterRelayMembers(members, "dde")).toHaveLength(1);
        expect(filterRelayMembers(members, "")).toHaveLength(2);
    });

    it("parseRelaySearchQuery splits OR", () => {
        const clauses = parseRelaySearchQuery("foo OR bar DATE:2026-01-01");
        expect(clauses).toHaveLength(2);
        expect(clauses[1].dateKey).toBe("2026-01-01");
    });
});

describe("relayMessageTimeline", () => {
    it("inserts date dividers between days", () => {
        const timeline = buildRelayMessageTimeline([
            { kind: "msg", ts: new Date("2026-06-01T10:00:00").getTime(), text: "a" },
            { kind: "msg", ts: new Date("2026-06-02T10:00:00").getTime(), text: "b" },
        ]);
        expect(timeline.filter((e) => e.type === "dateDivider")).toHaveLength(2);
        expect(timeline.filter((e) => e.type === "message")).toHaveLength(2);
    });

    it("relayMessageKey is stable", () => {
        const msg = { kind: "msg", ts: 1, src: "ab", text: "x" };
        expect(relayMessageKey(msg)).toBe(relayMessageKey(msg));
    });
});
