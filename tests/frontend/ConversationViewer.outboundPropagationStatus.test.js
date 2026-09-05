// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    outboundBubbleStatusIconName,
    outboundBubbleStatusTitleKey,
} from "@/js/outboundMessageStatus.js";
import {
    outboundStateIconName,
    outboundStateTitle,
    transferProgressPercent,
} from "@/features/messages/lib/conversationOutboundUi.ts";
import { updateWsMessage } from "@/features/messages/lib/conversationViewerMessages.ts";

describe("ConversationViewer outbound propagation status", () => {
    it("maps delivery method and state to status icons", () => {
        expect(outboundBubbleStatusIconName({ method: "direct", state: "sent" })).toBe("check");
        expect(outboundBubbleStatusIconName({ method: "direct", state: "delivered" })).toBe("check-all");
        expect(outboundBubbleStatusIconName({ method: "propagated", state: "sent" })).toBe("email-outline");
        expect(outboundBubbleStatusIconName({ method: "paper", state: "delivered" })).toBe(
            "note-check-outline"
        );
    });

    it("maps propagation handoff to method-aware copy", () => {
        expect(outboundBubbleStatusTitleKey({ method: "propagated", state: "sent" })).toBe(
            "messages.outbound_on_propagation_node"
        );
        expect(outboundBubbleStatusTitleKey({ method: "direct", state: "delivered" })).toBe(
            "messages.outbound_delivered"
        );
    });

    it("normalizes generic progress and state labels", () => {
        expect(transferProgressPercent(42.5, 100)).toBe(43);
        expect(outboundStateTitle("failed")).toBeTruthy();
        expect(outboundStateIconName("delivered")).toBeTruthy();
    });

    it("preserves existing websocket fields that an update omits", () => {
        const current = [
            {
                type: "lxmf_message",
                is_outbound: true,
                lxmf_message: {
                    hash: "message",
                    state: "outbound",
                    solving_stamps: true,
                    method: "direct",
                },
            },
        ];

        const updated = updateWsMessage(current, {
            hash: "message",
            state: "sent",
            method: "propagated",
        });

        expect(updated[0].lxmf_message).toMatchObject({
            state: "sent",
            method: "propagated",
            solving_stamps: true,
        });
    });
});
