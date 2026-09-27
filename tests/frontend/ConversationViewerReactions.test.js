// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { applyWsMessage } from "@/features/messages/lib/conversationViewerMessages.ts";
import { mergeLxmfReactionRowsIntoMessages } from "@/js/lxmfReactions.js";

const peerHash = "aa".repeat(16);
const myHash = "bb".repeat(16);

function parent() {
    return {
        hash: "message",
        content: "hello",
        source_hash: peerHash,
        destination_hash: myHash,
        fields: {},
        reactions: [],
    };
}

describe("ConversationViewer reactions", () => {
    it("merges a reaction row into its parent without rendering a second bubble", () => {
        const messages = mergeLxmfReactionRowsIntoMessages([
            parent(),
            {
                hash: "reaction",
                is_reaction: true,
                reaction_to: "message",
                reaction_emoji: "like",
                reaction_sender: peerHash,
                source_hash: peerHash,
                destination_hash: myHash,
            },
        ]);

        expect(messages).toHaveLength(1);
        expect(messages[0].reactions).toEqual([
            expect.objectContaining({
                emoji: "like",
                sender: peerHash,
                reactionHash: "reaction",
            }),
        ]);
    });

    it("applies incoming reactions case-insensitively", () => {
        const current = [
            {
                type: "lxmf_message",
                is_outbound: false,
                lxmf_message: { ...parent(), hash: "AaBb" },
            },
        ];

        const result = applyWsMessage(
            current,
            {
                hash: "server-reaction",
                is_reaction: true,
                reaction_to: "aabb",
                reaction_emoji: "heart",
                reaction_sender: peerHash,
                source_hash: peerHash,
                destination_hash: myHash,
            },
            peerHash,
            myHash
        );

        expect(result.changed).toBe(true);
        expect(result.items).toHaveLength(1);
        expect(result.items[0].lxmf_message.reactions[0]).toMatchObject({
            emoji: "heart",
            reactionHash: "server-reaction",
        });
    });

    it("ignores reactions for another conversation", () => {
        const current = [{ type: "lxmf_message", is_outbound: false, lxmf_message: parent() }];
        const result = applyWsMessage(
            current,
            {
                hash: "reaction",
                is_reaction: true,
                reaction_to: "message",
                source_hash: "cc".repeat(16),
                destination_hash: "dd".repeat(16),
            },
            peerHash,
            myHash
        );

        expect(result).toEqual({ items: current, changed: false, incoming: false });
    });

    it("removes only the pending placeholder matching a delivered outbound message", () => {
        const current = [
            {
                type: "lxmf_message",
                is_outbound: true,
                lxmf_message: {
                    hash: "pending-1",
                    content: "first",
                    destination_hash: peerHash,
                    source_hash: myHash,
                },
            },
            {
                type: "lxmf_message",
                is_outbound: true,
                lxmf_message: {
                    hash: "pending-2",
                    content: "second",
                    destination_hash: peerHash,
                    source_hash: myHash,
                },
            },
        ];

        const result = applyWsMessage(
            current,
            {
                hash: "real-1",
                content: "first",
                destination_hash: peerHash,
                source_hash: myHash,
            },
            peerHash,
            myHash
        );

        const hashes = result.items.map((item) => item.lxmf_message.hash);
        expect(hashes).toContain("real-1");
        // The other in-flight send keeps its bubble so a later failure can
        // still mark it failed and offer retry.
        expect(hashes).toContain("pending-2");
        expect(hashes).not.toContain("pending-1");
    });
});
