// SPDX-License-Identifier: 0BSD AND MIT

import { beforeEach, describe, expect, it, vi } from "vitest";
import { applyOutboundComposeEnqueued } from "@/features/messages/lib/conversationListApply.ts";

const PEER = "bb".repeat(16);

describe("MessagesPage outbound compose oracle", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-01-02T03:04:05Z"));
    });

    it("inserts an optimistic conversation before server acknowledgement", () => {
        const conversations = [];

        const result = applyOutboundComposeEnqueued(
            conversations,
            {
                peerHash: PEER,
                previewText: "hello optimistic",
                title: "",
                fields: {},
            },
            {
                myLxmfAddressHash: "aa".repeat(16),
                t: (key) => key,
            }
        );

        expect(result).toBe("created");
        expect(conversations).toHaveLength(1);
        expect(conversations[0]).toMatchObject({
            destination_hash: PEER,
            latest_message_preview: "hello optimistic",
            latest_message_created_at: 1767323045,
        });
    });

    it("updates an existing row without duplicating it", () => {
        const conversations = [
            {
                destination_hash: PEER,
                display_name: "Peer",
                latest_message_preview: "old",
                latest_message_created_at: 1,
                updated_at: new Date(1000).toISOString(),
            },
        ];

        const result = applyOutboundComposeEnqueued(
            conversations,
            {
                peerHash: PEER,
                previewText: "new text",
                title: "title",
                fields: {},
            },
            { myLxmfAddressHash: "aa".repeat(16), t: (key) => key }
        );

        expect(result).toBe("updated");
        expect(conversations).toHaveLength(1);
        expect(conversations[0].latest_message_preview).toBe("new text");
        expect(conversations[0].latest_message_title).toBe("title");
    });

    it("rejects an empty peer hash without creating an orphan row", () => {
        const conversations = [];
        const result = applyOutboundComposeEnqueued(
            conversations,
            { peerHash: "", previewText: "x" },
            { t: (key) => key }
        );

        expect(result).toBeNull();
        expect(conversations).toHaveLength(0);
    });
});
