// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    estimateRelayEntryHeight,
    relayVirtualEntryKey,
    MIN_VIRTUAL_RELAY_ENTRIES,
} from "@/components/relay/relayMessageListVirtual.js";
import { relayMessageKey } from "@/js/relayMessageTimeline.js";

const keyFn = (msg) => relayMessageKey(msg);

describe("relayVirtualEntryKey", () => {
    it("keys message entries by the message key, not the index", () => {
        const entry = { type: "message", msg: { kind: "msg", seq: 42, text: "hi" } };
        expect(relayVirtualEntryKey(entry, keyFn)).toBe("seq-42");
    });

    it("returns the same key after the entry moves position in the list", () => {
        const older = { type: "message", msg: { kind: "msg", seq: 5, text: "a" } };
        const newer = { type: "message", msg: { kind: "msg", seq: 6, text: "b" } };
        const list = [older, newer];
        const olderKey = relayVirtualEntryKey(list[0], keyFn);
        const prepended = [{ type: "message", msg: { kind: "msg", seq: 1, text: "x" } }, older, newer];
        // Index 0 now holds a different entry; the moved entry keeps its key.
        expect(relayVirtualEntryKey(prepended[0], keyFn)).not.toBe(olderKey);
        expect(relayVirtualEntryKey(prepended[1], keyFn)).toBe(olderKey);
    });

    it("keys date dividers by dayKey", () => {
        expect(relayVirtualEntryKey({ type: "dateDivider", dayKey: "2026-01-02" }, keyFn)).toBe("date-2026-01-02");
    });

    it("keys presence groups by id", () => {
        expect(relayVirtualEntryKey({ type: "presenceGroup", id: "seq-9" }, keyFn)).toBe("presence-seq-9");
    });

    it("keys the unread divider", () => {
        expect(relayVirtualEntryKey({ type: "unreadDivider" }, keyFn)).toBe("unread-divider");
    });

    it("returns an empty string when no key can be derived", () => {
        expect(relayVirtualEntryKey(null, keyFn)).toBe("");
        expect(relayVirtualEntryKey(undefined, keyFn)).toBe("");
        expect(relayVirtualEntryKey({ type: "dateDivider" }, keyFn)).toBe("");
        expect(relayVirtualEntryKey({ type: "presenceGroup", id: "" }, keyFn)).toBe("");
        expect(relayVirtualEntryKey({ type: "message", msg: null }, keyFn)).toBe("");
        expect(relayVirtualEntryKey({ type: "message", msg: {} }, () => "")).toBe("");
        expect(relayVirtualEntryKey({ type: "other" }, keyFn)).toBe("");
    });
});

describe("estimateRelayEntryHeight", () => {
    it("estimates dividers and messages distinctly", () => {
        expect(estimateRelayEntryHeight({ type: "dateDivider" })).toBe(44);
        expect(estimateRelayEntryHeight({ type: "presenceGroup" })).toBe(28);
        expect(estimateRelayEntryHeight({ type: "message", msg: { text: "hi" } })).toBe(32);
        expect(estimateRelayEntryHeight(null)).toBe(28);
    });
});

describe("virtual list threshold", () => {
    it("keeps the minimum entry count export", () => {
        expect(MIN_VIRTUAL_RELAY_ENTRIES).toBe(150);
    });
});
