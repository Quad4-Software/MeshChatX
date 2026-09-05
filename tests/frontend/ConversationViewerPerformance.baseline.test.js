// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { buildDisplayGroupsNewestFirst } from "@/features/messages/lib/conversationDisplayGroups.ts";
import { displayGroupsOldestFirst } from "@/features/messages/lib/messageListVirtual.ts";
import { visibleConversationItems } from "@/features/messages/lib/conversationViewerMessages.ts";

describe("ConversationViewer performance baseline", () => {
    it("groups and filters one thousand messages within the unit-test budget", () => {
        const peerHash = "aa".repeat(16);
        const myHash = "bb".repeat(16);
        const items = Array.from({ length: 1000 }, (_, index) => ({
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message: {
                id: index,
                hash: `message-${index}`,
                source_hash: peerHash,
                destination_hash: myHash,
                content: `message ${index}`,
                created_at: index,
                fields: {},
            },
        }));

        const started = performance.now();
        const visible = visibleConversationItems(items, peerHash, false);
        const groups = buildDisplayGroupsNewestFirst(visible, () => false);
        const oldestFirst = displayGroupsOldestFirst(groups);
        const elapsed = performance.now() - started;

        expect(visible).toHaveLength(1000);
        expect(oldestFirst.length).toBeGreaterThan(0);
        expect(elapsed).toBeLessThan(250);
    });
});
