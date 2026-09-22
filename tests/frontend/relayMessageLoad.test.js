// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    buildRelayMessageTimeline,
    filterUniqueOlderRelayMessages,
    mergeRelayMessages,
    prependRelayMessageTimeline,
    relayMessageTimelineSignature,
    RELAY_MESSAGES_INITIAL_PAGE_SIZE,
    RELAY_MESSAGES_PREVIOUS_PAGE_SIZE,
} from "@/js/relayMessageTimeline.js";

function msg(seq, text = "hi") {
    return { kind: "msg", seq, text, ts: seq * 1000, src: "aa".repeat(16), nick: "n" };
}

function presence(seq, event = "join") {
    return {
        kind: "system",
        seq,
        event,
        text: `peer ${event === "join" ? "joined" : "left"}`,
        ts: seq * 1000,
        src: "bb".repeat(16),
    };
}

describe("relay message load reference", () => {
    it("exports stable page sizes", () => {
        expect(RELAY_MESSAGES_INITIAL_PAGE_SIZE).toBeGreaterThanOrEqual(100);
        expect(RELAY_MESSAGES_PREVIOUS_PAGE_SIZE).toBeGreaterThanOrEqual(50);
    });

    it("filterUniqueOlderRelayMessages dedupes by seq in O(n)", () => {
        const existing = [msg(50), msg(51)];
        const older = [msg(48), msg(49), msg(50), msg(51)];
        const unique = filterUniqueOlderRelayMessages(older, existing);
        expect(unique.map((m) => m.seq)).toEqual([48, 49]);
    });

    it("prependRelayMessageTimeline matches full rebuild", () => {
        const older = [msg(1, "a"), msg(2, "b")];
        const newer = [msg(3, "c"), msg(4, "d")];
        const all = older.concat(newer);
        const full = buildRelayMessageTimeline(all);
        const base = buildRelayMessageTimeline(newer);
        const inc = prependRelayMessageTimeline(base, older);
        const seqs = (timeline) => timeline.filter((e) => e.type === "message").map((e) => e.msg.seq);
        expect(seqs(inc)).toEqual(seqs(full));
    });

    it("prependRelayMessageTimeline merges a presence run split across the page boundary", () => {
        const older = [msg(1), presence(2), presence(3)];
        const newer = [presence(4), presence(5), msg(6)];
        const base = buildRelayMessageTimeline(newer);
        const inc = prependRelayMessageTimeline(base, older);
        const groups = inc.filter((e) => e.type === "presenceGroup");
        expect(groups).toHaveLength(1);
        expect(groups[0].messages.map((m) => m.seq)).toEqual([2, 3, 4, 5]);
    });

    it("prependRelayMessageTimeline keeps the rendered group id across a boundary merge", () => {
        const older = [presence(2), presence(3)];
        const newer = [presence(4), presence(5), msg(6)];
        const base = buildRelayMessageTimeline(newer);
        const baseGroup = base.find((e) => e.type === "presenceGroup");
        const inc = prependRelayMessageTimeline(base, older);
        const groups = inc.filter((e) => e.type === "presenceGroup");
        expect(groups).toHaveLength(1);
        // Expansion state is keyed by the group id; a fresh id would
        // collapse the open group when older history is prepended.
        expect(groups[0].id).toBe(baseGroup.id);
    });

    it("mergeRelayMessages inserts extras in seq order instead of appending", () => {
        const base = [msg(5), msg(6)];
        const extras = [msg(2), msg(6), msg(9)];
        const merged = mergeRelayMessages(base, extras);
        // Older history merged late must not land below newer arrivals.
        expect(merged.map((m) => m.seq)).toEqual([2, 5, 6, 9]);
    });

    it("prependRelayMessageTimeline does not merge presence across a chat message", () => {
        const older = [presence(1), presence(2), msg(3)];
        const newer = [msg(4), presence(5), presence(6)];
        const base = buildRelayMessageTimeline(newer);
        const inc = prependRelayMessageTimeline(base, older);
        const groups = inc.filter((e) => e.type === "presenceGroup");
        expect(groups).toHaveLength(2);
        expect(groups[0].messages.map((m) => m.seq)).toEqual([1, 2]);
        expect(groups[1].messages.map((m) => m.seq)).toEqual([5, 6]);
    });

    it("timeline signature changes when seq range grows", () => {
        const a = relayMessageTimelineSignature([msg(10), msg(11)]);
        const b = relayMessageTimelineSignature([msg(8), msg(10), msg(11)]);
        expect(a).not.toBe(b);
    });

    it("timeline signature catches in-place edits", () => {
        const before = relayMessageTimelineSignature([msg(10), msg(11)]);
        const edited = relayMessageTimelineSignature([msg(10), { ...msg(11), highlighted: true }]);
        const retext = relayMessageTimelineSignature([msg(10), msg(11, "a much longer body")]);
        expect(edited).not.toBe(before);
        expect(retext).not.toBe(before);
    });

    it("duplicate-only older page yields empty unique list", () => {
        const existing = Array.from({ length: 50 }, (_, i) => msg(100 + i));
        const older = Array.from({ length: 50 }, (_, i) => msg(100 + i));
        expect(filterUniqueOlderRelayMessages(older, existing)).toHaveLength(0);
    });
});
