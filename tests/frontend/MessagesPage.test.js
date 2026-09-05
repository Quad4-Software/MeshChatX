// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, waitFor } from "@testing-library/svelte";
import MessagesPage from "@/features/messages/MessagesPage.svelte";
import {
    applyOutboundMessageCreated,
    applyOutboundMessageStateUpdated,
} from "@/features/messages/lib/conversationListApply.ts";
import { buildConversationQueryParams } from "@/features/messages/lib/conversationQuery.ts";
import {
    applyOptimisticUnreadClear,
    destinationsNeedingUnreadDismiss,
    nextUnreadConversationsCount,
} from "@/features/messages/lib/unreadDismiss.ts";

vi.mock("@/js/identityHttpReady.js", () => ({
    runWhenIdentityHttpReady: (callback) => {
        callback();
        return () => {};
    },
}));

function mediaQuery(matches = false) {
    return {
        matches,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
    };
}

describe("MessagesPage.svelte", () => {
    let api;

    beforeEach(() => {
        localStorage.clear();
        window.matchMedia = vi.fn(() => mediaQuery(false));
        api = {
            get: vi.fn((url) => {
                if (url === "/api/v1/config") {
                    return Promise.resolve({ data: { config: { lxmf_address_hash: "a".repeat(32) } } });
                }
                if (url === "/api/v1/lxmf/conversations") {
                    return Promise.resolve({ data: { conversations: [] } });
                }
                if (url === "/api/v1/lxmf/conversation-pins") {
                    return Promise.resolve({ data: { peer_hashes: [] } });
                }
                if (url === "/api/v1/lxmf/folders") {
                    return Promise.resolve({ data: [] });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
            isCancel: vi.fn(() => false),
        };
        window.api = api;
    });

    afterEach(() => {
        cleanup();
        vi.useRealTimers();
        delete window.api;
    });

    it("loads configuration, conversations, pins, and folders on mount", async () => {
        render(MessagesPage, { destinationHash: "" });

        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith("/api/v1/config");
            expect(api.get).toHaveBeenCalledWith("/api/v1/lxmf/conversations", expect.any(Object));
            expect(api.get).toHaveBeenCalledWith("/api/v1/lxmf/conversation-pins");
            expect(api.get).toHaveBeenCalledWith("/api/v1/lxmf/folders");
        });
    });

    it("builds filtered conversation query parameters without component internals", () => {
        expect(
            buildConversationQueryParams({
                conversationSearchTerm: " findme ",
                filterUnreadOnly: true,
                filterFailedOnly: true,
                filterHasAttachmentsOnly: true,
                selectedFolderId: 7,
            })
        ).toEqual({
            search: "findme",
            filter_unread: true,
            filter_failed: true,
            filter_has_attachments: true,
            folder_id: 7,
        });
    });

    it("applies websocket-created previews without reloading the list", () => {
        const peerHash = "b".repeat(32);
        const conversations = [{ destination_hash: peerHash, latest_message_preview: "old" }];

        const result = applyOutboundMessageCreated(
            conversations,
            {
                hash: "message",
                destination_hash: peerHash,
                is_incoming: false,
                content: "new message",
                timestamp: 1700000000,
            },
            { myLxmfAddressHash: "a".repeat(32), t: (key) => key }
        );

        expect(result).toBe("updated");
        expect(conversations[0].latest_message_preview).toBe("new message");
    });

    it("tracks failed outbound state transitions exactly once", () => {
        const peerHash = "c".repeat(32);
        const conversations = [{ destination_hash: peerHash, failed_messages_count: 0 }];
        const message = { destination_hash: peerHash, is_incoming: false, state: "failed" };

        expect(applyOutboundMessageStateUpdated(conversations, message)).toBe(true);
        expect(conversations[0].failed_messages_count).toBe(1);
        expect(applyOutboundMessageStateUpdated(conversations, message)).toBe(true);
        expect(conversations[0].failed_messages_count).toBe(1);
    });

    it("collects visible unread panes and clears counts optimistically", () => {
        const hash = "d".repeat(32);
        const conversation = { destination_hash: hash, is_unread: true };
        const panes = [{ id: 1, peer: { destination_hash: hash } }];

        expect(destinationsNeedingUnreadDismiss(panes, [conversation])).toEqual([hash]);
        expect(applyOptimisticUnreadClear(conversation)).toBe(true);
        expect(conversation.is_unread).toBe(false);
        expect(nextUnreadConversationsCount(3, true)).toBe(2);
    });
});
