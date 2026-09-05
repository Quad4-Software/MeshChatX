// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    applyFailedCountFromStateUpdate,
    applyOutboundMessageStateUpdated,
    nextFailedMessagesCount,
} from "@/features/messages/lib/conversationListApply.ts";
import { optimisticMessage } from "@/features/messages/lib/conversationViewerSend.ts";
import { peerPathNeedsRefresh } from "@/features/messages/lib/conversationViewerPath.ts";

describe("message sending failure contracts", () => {
    it("increments and clears failed counts only on state transitions", () => {
        expect(nextFailedMessagesCount(0, "sending", "failed")).toBe(1);
        expect(nextFailedMessagesCount(1, "failed", "failed")).toBe(1);
        expect(nextFailedMessagesCount(1, "failed", "delivered")).toBe(0);
    });

    it("applies failure state to the matching conversation", () => {
        const peerHash = "aa".repeat(16);
        const conversations = [{ destination_hash: peerHash, failed_messages_count: 0 }];

        expect(
            applyOutboundMessageStateUpdated(conversations, {
                destination_hash: peerHash,
                is_incoming: false,
                state: "failed",
            })
        ).toBe(true);
        expect(conversations[0].failed_messages_count).toBe(1);
        expect(
            applyFailedCountFromStateUpdate(conversations[0], {
                destination_hash: peerHash,
                state: "delivered",
            })
        ).toBe(true);
        expect(conversations[0].failed_messages_count).toBe(0);
    });

    it("marks optimistic direct sends as waiting when a path is missing", () => {
        const message = optimisticMessage(
            {
                destinationHash: "bb".repeat(16),
                myLxmfAddressHash: "cc".repeat(16),
                text: "hello",
                fields: {},
                images: [],
                deliveryMethod: "direct",
                replyToHash: null,
                replyQuotedContent: null,
                pendingHash: null,
            },
            true
        );

        expect(message.destination_hash).toBe("bb".repeat(16));
        expect(message.state).toBe("sending");
        expect(message._pendingPathfinding).toBe(true);
    });

    it("requests path refresh for missing, stale, or unresponsive paths", () => {
        expect(peerPathNeedsRefresh(null)).toBe(true);
        expect(peerPathNeedsRefresh({ path: null, path_stale: false, path_unresponsive: false })).toBe(true);
        expect(peerPathNeedsRefresh({ path: { hops: 1 }, path_stale: true, path_unresponsive: false })).toBe(true);
        expect(peerPathNeedsRefresh({ path: { hops: 1 }, path_stale: false, path_unresponsive: false })).toBe(false);
    });
});
