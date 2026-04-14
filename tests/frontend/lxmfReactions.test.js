import { describe, expect, it } from "vitest";
import { mergeLxmfReactionRowsIntoMessages } from "../../meshchatx/src/frontend/js/lxmfReactions";

describe("mergeLxmfReactionRowsIntoMessages", () => {
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
});
