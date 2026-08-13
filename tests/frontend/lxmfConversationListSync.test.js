import { describe, it, expect } from "vitest";
import {
    conversationListSignature,
    countUnreadConversations,
    sortConversationsPinnedFirst,
    syncConversationListInPlace,
} from "../../meshchatx/src/frontend/js/lxmfConversationListSync.js";

describe("lxmfConversationListSync", () => {
    it("builds a stable signature for conversation rows", () => {
        const conversations = [
            {
                destination_hash: "a".repeat(32),
                updated_at: "2026-01-01T00:00:00Z",
                is_unread: true,
                failed_messages_count: 0,
                latest_message_created_at: 1,
                latest_message_preview: "hello",
            },
        ];
        expect(conversationListSignature(conversations)).toBe(conversationListSignature(conversations.slice()));
    });

    it("counts unread conversations", () => {
        expect(countUnreadConversations([{ is_unread: true }, { is_unread: false }, { is_unread: true }])).toBe(2);
    });

    it("syncs updated rows in place while preserving object identity", () => {
        const existing = [
            { destination_hash: "a".repeat(32), display_name: "Alpha", is_unread: true },
            { destination_hash: "b".repeat(32), display_name: "Bravo", is_unread: false },
        ];
        const alphaRef = existing[0];
        const incoming = [
            { destination_hash: "a".repeat(32), display_name: "Alpha", is_unread: false },
            { destination_hash: "b".repeat(32), display_name: "Bravo", is_unread: false },
        ];

        const changed = syncConversationListInPlace(existing, incoming);

        expect(changed).toBe(false);
        expect(existing[0]).toBe(alphaRef);
        expect(existing[0].is_unread).toBe(false);
        expect(existing).toHaveLength(2);
    });

    it("reorders and appends rows when the server order changes", () => {
        const existing = [
            { destination_hash: "a".repeat(32), display_name: "Alpha" },
            { destination_hash: "b".repeat(32), display_name: "Bravo" },
        ];
        const incoming = [
            { destination_hash: "c".repeat(32), display_name: "Charlie" },
            { destination_hash: "a".repeat(32), display_name: "Alpha" },
        ];

        const changed = syncConversationListInPlace(existing, incoming);

        expect(changed).toBe(true);
        expect(existing.map((row) => row.destination_hash)).toEqual(["c".repeat(32), "a".repeat(32)]);
        expect(existing[1].display_name).toBe("Alpha");
    });

    it("returns the same array when nothing is pinned", () => {
        const conversations = [{ destination_hash: "a".repeat(32) }, { destination_hash: "b".repeat(32) }];
        expect(sortConversationsPinnedFirst(conversations, new Set())).toBe(conversations);
        expect(sortConversationsPinnedFirst(conversations, null)).toBe(conversations);
    });

    it("pins selected hashes without changing relative order of the rest", () => {
        const a = "a".repeat(32);
        const b = "b".repeat(32);
        const c = "c".repeat(32);
        const conversations = [
            { destination_hash: a, name: "A" },
            { destination_hash: b, name: "B" },
            { destination_hash: c, name: "C" },
        ];
        const out = sortConversationsPinnedFirst(conversations, new Set([c]));
        expect(out.map((row) => row.destination_hash)).toEqual([c, a, b]);
        expect(conversations[0].destination_hash).toBe(a);
    });
});
