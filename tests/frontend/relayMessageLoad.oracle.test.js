// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    buildRelayMessageTimeline,
    filterUniqueOlderRelayMessages,
    prependRelayMessageTimeline,
    relayMessageTimelineSignature,
    RELAY_MESSAGES_INITIAL_PAGE_SIZE,
    RELAY_MESSAGES_PREVIOUS_PAGE_SIZE,
} from "@/js/relayMessageTimeline.js";

function msg(seq, text = "hi") {
    return { kind: "msg", seq, text, ts: seq * 1000, src: "aa".repeat(16), nick: "n" };
}

describe("relay message load oracle", () => {
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

    it("timeline signature changes when seq range grows", () => {
        const a = relayMessageTimelineSignature([msg(10), msg(11)]);
        const b = relayMessageTimelineSignature([msg(8), msg(10), msg(11)]);
        expect(a).not.toBe(b);
    });

    it("duplicate-only older page yields empty unique list", () => {
        const existing = Array.from({ length: 50 }, (_, i) => msg(100 + i));
        const older = Array.from({ length: 50 }, (_, i) => msg(100 + i));
        expect(filterUniqueOlderRelayMessages(older, existing)).toHaveLength(0);
    });
});
