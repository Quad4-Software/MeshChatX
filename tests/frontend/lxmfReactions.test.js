import { describe, expect, it } from "vitest";
import { mergeLxmfReactionRowsIntoMessages } from "../../meshchatx/src/frontend/js/lxmfReactions";

describe("mergeLxmfReactionRowsIntoMessages", () => {
    it("returns an empty array when input is not an array", () => {
        expect(mergeLxmfReactionRowsIntoMessages(undefined)).toEqual([]);
        expect(mergeLxmfReactionRowsIntoMessages(null)).toEqual([]);
    });

    it("merges reaction rows onto parents and drops reaction-only rows", () => {
        const parentHash = "a".repeat(32);
        const incoming = [
            {
                hash: parentHash,
                source_hash: "b".repeat(32),
                content: "hello",
                is_reaction: false,
            },
            {
                hash: "c".repeat(32),
                source_hash: "d".repeat(32),
                content: "",
                is_reaction: true,
                reaction_to: parentHash,
                reaction_emoji: "\u{1F44D}",
                reaction_sender: "e".repeat(32),
            },
        ];
        const out = mergeLxmfReactionRowsIntoMessages(incoming);
        expect(out).toHaveLength(1);
        expect(out[0].hash).toBe(parentHash);
        expect(out[0].reactions).toHaveLength(1);
        expect(out[0].reactions[0].emoji).toBe("\u{1F44D}");
        expect(out[0].reactions[0].sender).toBe("e".repeat(32));
    });

    it("matches reaction_to to parent hash case-insensitively", () => {
        const parentHash = "Aa".repeat(16);
        const incoming = [
            { hash: parentHash, content: "hi", is_reaction: false },
            {
                hash: "c".repeat(32),
                is_reaction: true,
                reaction_to: parentHash.toLowerCase(),
                reaction_emoji: "\u{1F44D}",
                reaction_sender: "e".repeat(32),
            },
        ];
        const out = mergeLxmfReactionRowsIntoMessages(incoming);
        expect(out[0].reactions).toHaveLength(1);
    });

    it("dedupes same sender and emoji", () => {
        const parentHash = "a".repeat(32);
        const sender = "e".repeat(32);
        const incoming = [
            { hash: parentHash, content: "x", is_reaction: false },
            {
                hash: "r1",
                is_reaction: true,
                reaction_to: parentHash,
                reaction_emoji: "\u{1F44D}",
                reaction_sender: sender,
            },
            {
                hash: "r2",
                is_reaction: true,
                reaction_to: parentHash,
                reaction_emoji: "\u{1F44D}",
                reaction_sender: sender,
            },
        ];
        const out = mergeLxmfReactionRowsIntoMessages(incoming);
        expect(out[0].reactions).toHaveLength(1);
    });

    it("preserves XSS-like emoji strings as opaque data for UI escaping", () => {
        const parentHash = "a".repeat(32);
        const emoji = "<img src=x onerror=1>";
        const incoming = [
            { hash: parentHash, content: "x", is_reaction: false },
            {
                hash: "r1",
                is_reaction: true,
                reaction_to: parentHash,
                reaction_emoji: emoji,
                reaction_sender: "e".repeat(32),
            },
        ];
        const out = mergeLxmfReactionRowsIntoMessages(incoming);
        expect(out[0].reactions[0].emoji).toBe(emoji);
    });

    it("ignores reactions with missing parent or reaction_to", () => {
        const incoming = [
            { hash: "a".repeat(32), content: "x", is_reaction: false },
            {
                hash: "r1",
                is_reaction: true,
                reaction_to: "no_such_parent_hash_xxxxxxxxxxxxxx",
                reaction_emoji: "\u{1F44D}",
                reaction_sender: "e".repeat(32),
            },
            {
                hash: "r2",
                is_reaction: true,
                reaction_emoji: "\u{1F602}",
                reaction_sender: "f".repeat(32),
            },
        ];
        const out = mergeLxmfReactionRowsIntoMessages(incoming);
        expect(out[0].reactions).toHaveLength(0);
    });

    it("handles many reactions without throwing", () => {
        const parentHash = "a".repeat(32);
        const incoming = [{ hash: parentHash, content: "x", is_reaction: false }];
        for (let i = 0; i < 200; i++) {
            incoming.push({
                hash: `r${i}`.padEnd(32, "0"),
                is_reaction: true,
                reaction_to: parentHash,
                reaction_emoji: String.fromCodePoint(0x1f600 + (i % 16)),
                reaction_sender: `${i.toString(16)}`.padStart(32, "0"),
            });
        }
        const out = mergeLxmfReactionRowsIntoMessages(incoming);
        expect(out[0].reactions.length).toBe(200);
    });
});
