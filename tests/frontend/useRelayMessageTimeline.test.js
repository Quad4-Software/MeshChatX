// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { nextTick } from "vue";
import { useRelayMessageTimeline } from "../../meshchatx/src/frontend/js/relay/useRelayMessageTimeline.js";
import { RELAY_MESSAGES_PREVIOUS_PAGE_SIZE } from "../../meshchatx/src/frontend/js/relayMessageTimeline.js";

const HUB_HASH = "00112233445566778899aabbccddeeff";

function msg(seq, text = "hi", overrides = {}) {
    return { kind: "msg", seq, text, ts: seq * 1000, src: "aa".repeat(16), nick: "n", ...overrides };
}

function makeTimeline(overrides = {}) {
    return useRelayMessageTimeline({
        getSelectedHubHash: () => HUB_HASH,
        getSelectedRoom: () => "lobby",
        getMessagesScrollElement: () => null,
        encodeRoom: (room) => encodeURIComponent(room),
        t: (key, params) => `${key}:${params?.count ?? ""}`,
        ...overrides,
    });
}

describe("useRelayMessageTimeline", () => {
    beforeEach(() => {
        window.api = { get: vi.fn().mockResolvedValue({ data: {} }) };
    });

    afterEach(() => {
        delete window.api;
        vi.restoreAllMocks();
    });

    it("builds a timeline cache from messages via the immediate watcher", async () => {
        const tl = makeTimeline();
        expect(tl.messageTimeline.value).toEqual([]);
        tl.messages.value = [msg(1, "a"), msg(2, "b")];
        await nextTick();
        const entries = tl.messageTimeline.value;
        expect(entries.filter((e) => e.type === "message").map((e) => e.msg.seq)).toEqual([1, 2]);
        expect(tl.messageTimelineCache.value).not.toBeNull();
    });

    it("a cold cache falls back to building the timeline on read", async () => {
        const tl = makeTimeline();
        tl.messages.value = [msg(1)];
        await nextTick();
        expect(tl.messageTimelineCache.value).not.toBeNull();
        tl.messageTimelineCache.value = null;
        expect(tl.messageTimeline.value.filter((e) => e.type === "message")).toHaveLength(1);
    });

    it("oldestLoadedSeq tracks the smallest numeric seq", () => {
        const tl = makeTimeline();
        tl.messages.value = [msg(5), { kind: "system", text: "no seq" }, msg(3), msg(9)];
        expect(tl.oldestLoadedSeq.value).toBe(3);
        tl.messages.value = [];
        expect(tl.oldestLoadedSeq.value).toBeNull();
    });

    it("loadPreviousMessages prepends unique older messages and keeps scroll position", async () => {
        const scrollEl = { scrollHeight: 1000, scrollTop: 120 };
        const prependTimelineCache = vi.fn();
        window.api.get.mockResolvedValue({
            data: { messages: [msg(1), msg(2), msg(3)], has_more: true },
        });
        const tl = makeTimeline({ getMessagesScrollElement: () => scrollEl, prependTimelineCache });
        tl.messages.value = [msg(3), msg(4)];
        tl.hasMorePrevious.value = true;
        await tl.loadPreviousMessages();
        expect(tl.messages.value.map((m) => m.seq)).toEqual([1, 2, 3, 4]);
        expect(prependTimelineCache).toHaveBeenCalledWith([msg(1), msg(2)]);
        expect(tl.hasMorePrevious.value).toBe(true);
        expect(tl.isLoadingPrevious.value).toBe(false);
        expect(window.api.get).toHaveBeenCalledWith(
            `/api/v1/rrc/hubs/${HUB_HASH}/rooms/lobby/messages`,
            { params: { limit: RELAY_MESSAGES_PREVIOUS_PAGE_SIZE, before_seq: 3 } }
        );
        // Simulate the DOM growing after the prepend, then the nextTick
        // callback restores scrollTop by the height delta.
        scrollEl.scrollHeight = 1500;
        await nextTick();
        expect(scrollEl.scrollTop).toBe(120 + (1500 - 1000));
    });

    it("loadPreviousMessages sets hasMorePrevious false when the page is a duplicate", async () => {
        window.api.get.mockResolvedValue({
            data: { messages: [msg(3), msg(4)], has_more: true },
        });
        const tl = makeTimeline();
        tl.messages.value = [msg(3), msg(4)];
        tl.hasMorePrevious.value = true;
        await tl.loadPreviousMessages();
        expect(tl.messages.value.map((m) => m.seq)).toEqual([3, 4]);
        expect(tl.hasMorePrevious.value).toBe(false);
    });

    it("loadPreviousMessages bails without a room selection or more pages", async () => {
        const tl = makeTimeline({ getSelectedRoom: () => null });
        tl.messages.value = [msg(1)];
        tl.hasMorePrevious.value = true;
        await tl.loadPreviousMessages();
        expect(window.api.get).not.toHaveBeenCalled();

        const tl2 = makeTimeline();
        tl2.messages.value = [msg(1)];
        tl2.hasMorePrevious.value = false;
        await tl2.loadPreviousMessages();
        expect(window.api.get).not.toHaveBeenCalled();
    });

    it("loadPreviousMessages clears hasMorePrevious when no seq is loaded", async () => {
        const tl = makeTimeline();
        tl.messages.value = [{ kind: "system", text: "join" }];
        tl.hasMorePrevious.value = true;
        await tl.loadPreviousMessages();
        expect(tl.hasMorePrevious.value).toBe(false);
        expect(window.api.get).not.toHaveBeenCalled();
    });

    it("loadPreviousMessages discards the response when the room changed mid-flight", async () => {
        let resolveGet;
        window.api.get.mockImplementation(() => new Promise((r) => (resolveGet = r)));
        let room = "lobby";
        const tl = makeTimeline({ getSelectedRoom: () => room });
        tl.messages.value = [msg(5)];
        tl.hasMorePrevious.value = true;
        const pending = tl.loadPreviousMessages();
        room = "other";
        resolveGet({ data: { messages: [msg(1)], has_more: true } });
        await pending;
        expect(tl.messages.value.map((m) => m.seq)).toEqual([5]);
        expect(tl.isLoadingPrevious.value).toBe(false);
    });

    it("loadPreviousMessages resets flags after a request failure", async () => {
        window.api.get.mockRejectedValue(new Error("boom"));
        const tl = makeTimeline();
        tl.messages.value = [msg(5)];
        tl.hasMorePrevious.value = true;
        await tl.loadPreviousMessages();
        expect(tl.hasMorePrevious.value).toBe(false);
        expect(tl.isLoadingPrevious.value).toBe(false);
        expect(tl.loadPreviousInFlight.value).toBe(0);
    });

    it("onMessagesScroll loads older pages only near the top edge", () => {
        const tl = makeTimeline();
        tl.messages.value = [msg(5)];
        tl.hasMorePrevious.value = true;
        tl.onMessagesScroll({ target: { scrollTop: 500 } });
        expect(window.api.get).not.toHaveBeenCalled();
        tl.onMessagesScroll({ target: { scrollTop: 100 } });
        expect(window.api.get).toHaveBeenCalledTimes(1);
    });

    it("onMessagesScroll is a no-op while a load is in flight", async () => {
        let resolveGet;
        window.api.get.mockImplementation(() => new Promise((r) => (resolveGet = r)));
        const tl = makeTimeline();
        tl.messages.value = [msg(5)];
        tl.hasMorePrevious.value = true;
        const pending = tl.loadPreviousMessages();
        tl.onMessagesScroll({ target: { scrollTop: 0 } });
        expect(window.api.get).toHaveBeenCalledTimes(1);
        resolveGet({ data: { messages: [], has_more: false } });
        await pending;
    });

    it("timelineEntryKey formats divider, presence group, and message keys", () => {
        const tl = makeTimeline();
        expect(tl.timelineEntryKey({ type: "dateDivider", dayKey: "2026-01-02" }, 3)).toBe("date-2026-01-02-3");
        expect(tl.timelineEntryKey({ type: "presenceGroup", id: "pg1" }, 0)).toBe("presence-pg1-0");
        expect(tl.timelineEntryKey({ type: "message", msg: msg(7) }, 2)).toBe("seq-7-2");
        expect(tl.timelineEntryKey({ type: "message", msg: null }, 4)).toBe("idx-4");
    });

    it("presence groups toggle open and closed", () => {
        const tl = makeTimeline();
        expect(tl.isPresenceGroupExpanded("g1")).toBe(false);
        tl.togglePresenceGroup("g1");
        expect(tl.isPresenceGroupExpanded("g1")).toBe(true);
        tl.togglePresenceGroup("g1");
        expect(tl.isPresenceGroupExpanded("g1")).toBe(false);
        tl.togglePresenceGroup(null);
        expect(tl.expandedPresenceGroups.value).toEqual({ g1: false });
    });

    it("formatPresenceGroupSummary joins counts and falls back to event count", () => {
        const tl = makeTimeline();
        expect(tl.formatPresenceGroupSummary({ joinedCount: 2, leftCount: 1, connectionCount: 0 })).toBe(
            "relay_chat.presence_joined:2 · relay_chat.presence_left:1"
        );
        expect(tl.formatPresenceGroupSummary({ messages: [msg(1), msg(2), msg(3)] })).toBe(
            "relay_chat.presence_events:3"
        );
    });
});
