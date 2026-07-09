import { describe, it, expect } from "vitest";
import {
    filterRelayMembers,
    filterRelayMessages,
    parseRelaySearchQuery,
    parseDateSearchToken,
} from "@/js/relayMessageSearch.js";
import {
    buildRelayMessageTimeline,
    mergeRelayMessages,
    relayMessageAlreadyPresent,
    relayMessageKey,
} from "@/js/relayMessageTimeline.js";

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

    it("collapses consecutive join/leave system lines into a presence group", () => {
        const day = new Date("2026-06-02T12:00:00").getTime();
        const timeline = buildRelayMessageTimeline([
            { kind: "msg", ts: day, src: "a", text: "hi", seq: 1 },
            { kind: "system", ts: day + 1, text: "nickie left", seq: 2 },
            { kind: "system", ts: day + 2, text: "jrrz left", seq: 3 },
            { kind: "system", ts: day + 3, text: "jrrz joined", seq: 4 },
            { kind: "msg", ts: day + 4, src: "b", text: "yo", seq: 5 },
            { kind: "system", ts: day + 5, text: "solo joined", seq: 6 },
        ]);
        const types = timeline.filter((e) => e.type !== "dateDivider").map((e) => e.type);
        expect(types).toEqual(["message", "presenceGroup", "message", "message"]);
        const group = timeline.find((e) => e.type === "presenceGroup");
        expect(group.joinedCount).toBe(1);
        expect(group.leftCount).toBe(2);
        expect(group.messages).toHaveLength(3);
        expect(timeline.filter((e) => e.type === "message").at(-1).msg.text).toBe("solo joined");
    });

    it("treats You joined / You rejoined as presence events", () => {
        const day = new Date("2026-06-02T12:00:00").getTime();
        const timeline = buildRelayMessageTimeline([
            { kind: "system", ts: day, text: "You rejoined #lobby", seq: 1 },
            { kind: "system", ts: day + 1, text: "alice joined", seq: 2 },
            { kind: "system", ts: day + 2, text: "You joined #lobby", seq: 3 },
        ]);
        const group = timeline.find((e) => e.type === "presenceGroup");
        expect(group).toBeTruthy();
        expect(group.joinedCount).toBe(3);
        expect(group.leftCount).toBe(0);
    });

    it("collapses connection lost/reconnected lines with presence events", () => {
        const day = new Date("2026-06-02T12:00:00").getTime();
        const timeline = buildRelayMessageTimeline([
            { kind: "system", ts: day, text: "Connection lost", seq: 1 },
            { kind: "system", ts: day + 1, text: "Reconnected to hub", seq: 2 },
            { kind: "system", ts: day + 2, text: "You rejoined #lobby", seq: 3 },
        ]);
        const group = timeline.find((e) => e.type === "presenceGroup");
        expect(group).toBeTruthy();
        expect(group.connectionCount).toBe(2);
        expect(group.joinedCount).toBe(1);
    });

    it("relayMessageKey is stable", () => {
        const msg = { kind: "msg", ts: 1, src: "ab", text: "x" };
        expect(relayMessageKey(msg)).toBe(relayMessageKey(msg));
    });

    it("relayMessageKey prefers seq when present", () => {
        const msg = { kind: "msg", ts: 1, src: "ab", text: "x", seq: 42 };
        expect(relayMessageKey(msg)).toBe("seq-42");
    });

    it("relayMessageAlreadyPresent matches by seq", () => {
        const messages = [{ kind: "msg", ts: 1, src: "ab", text: "x", seq: 7 }];
        expect(relayMessageAlreadyPresent(messages, { kind: "msg", ts: 99, src: "cd", text: "y", seq: 7 })).toBe(true);
        expect(relayMessageAlreadyPresent(messages, { kind: "msg", ts: 1, src: "ab", text: "x", seq: 8 })).toBe(false);
    });

    it("relayMessageAlreadyPresent falls back when seq is missing", () => {
        const messages = [{ kind: "msg", ts: 1, src: "ab", text: "hello" }];
        expect(relayMessageAlreadyPresent(messages, { kind: "msg", ts: 1, src: "ab", text: "hello" })).toBe(true);
        expect(relayMessageAlreadyPresent(messages, { kind: "msg", ts: 1, src: "ab", text: "other" })).toBe(false);
    });

    it("mergeRelayMessages keeps websocket arrivals not in the loaded page", () => {
        const loaded = [
            { kind: "msg", ts: 1, src: "ab", text: "a", seq: 1 },
            { kind: "msg", ts: 2, src: "ab", text: "b", seq: 2 },
        ];
        const live = [
            { kind: "msg", ts: 2, src: "ab", text: "b", seq: 2 },
            { kind: "msg", ts: 3, src: "cd", text: "c", seq: 3 },
        ];
        const merged = mergeRelayMessages(loaded, live);
        expect(merged.map((m) => m.seq)).toEqual([1, 2, 3]);
    });
});
