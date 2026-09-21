// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi } from "vitest";
import { CONVERSATION_MESSAGES_PAGE_SIZE } from "@/features/messages/lib/conversationDisplayGroups.ts";
import {
    fetchConversationPage,
    oldestMessageId,
    prependConversationPage,
} from "@/features/messages/lib/conversationViewerMessages.ts";

const peerHash = "ab".repeat(16);
const myHash = "cd".repeat(16);

function message(id, overrides = {}) {
    return {
        id,
        hash: `hash-${id}`,
        source_hash: peerHash,
        destination_hash: myHash,
        content: `message-${id}`,
        fields: {},
        ...overrides,
    };
}

describe("conversation incremental load oracle", () => {
    it("requests one descending page at the configured size", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({ data: { lxmf_messages: [message(2), message(1)] } }),
        };

        const page = await fetchConversationPage(api, peerHash, myHash, null);

        expect(api.get).toHaveBeenCalledWith(`/api/v1/lxmf-messages/conversation/${peerHash}`, {
            params: {
                count: CONVERSATION_MESSAGES_PAGE_SIZE,
                order: "desc",
                after_id: null,
            },
        });
        expect(page.items.map((item) => item.lxmf_message.id)).toEqual([1, 2]);
        expect(page.hasMore).toBe(false);
    });

    it("prepends only unseen older messages", () => {
        const current = [message(3), message(4)].map((lxmf_message) => ({
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message,
        }));
        const page = [message(1), message(2), message(3)].map((lxmf_message) => ({
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message,
        }));

        const result = prependConversationPage(current, page);

        expect(result.added).toBe(2);
        expect(result.items.map((item) => item.lxmf_message.id)).toEqual([1, 2, 3, 4]);
    });

    it("stops pagination when a full page contributes no unseen rows", () => {
        const current = Array.from({ length: CONVERSATION_MESSAGES_PAGE_SIZE }, (_, index) => ({
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message: message(index + 1),
        }));

        const result = prependConversationPage(current, current);
        expect(result.added).toBe(0);
    });

    it("finds the oldest message id for the selected peer only", () => {
        const items = [
            {
                type: "lxmf_message",
                is_outbound: false,
                lxmf_message: message(8),
            },
            {
                type: "lxmf_message",
                is_outbound: false,
                lxmf_message: message(3),
            },
            {
                type: "lxmf_message",
                is_outbound: false,
                lxmf_message: message(1, { source_hash: "ef".repeat(16), destination_hash: myHash }),
            },
        ];

        expect(oldestMessageId(items, peerHash)).toBe(3);
    });
});
