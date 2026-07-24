// SPDX-License-Identifier: 0BSD AND MIT
/**
 * Oracle tests for outbound LXMF status icons and titles.
 *
 * Guarantee: UI status glyphs and title keys follow the API state/method
 * strings that backend convert_lxmf_* emits from LXMF.LXMessage. Propagation
 * is method-only. Opportunistic+failed is deferred wait, not a hard fail badge.
 */
import { describe, expect, it } from "vitest";
import {
    isOpportunisticDeferredDelivery,
    outboundBubbleStatusIconName,
    outboundBubbleStatusTitleKey,
} from "@/js/outboundMessageStatus.js";

/** Closed vocabulary aligned with meshchatx/src/backend/lxmf_utils.py converters. */
const API_STATES = [
    "generating",
    "outbound",
    "sending",
    "sent",
    "delivered",
    "rejected",
    "cancelled",
    "failed",
    "unknown",
];

const API_METHODS = ["opportunistic", "direct", "propagated", "paper", "unknown"];

/**
 * Independent UI oracle. Must stay in sync with product intent, not by
 * importing the implementation under test into the expected table.
 */
function oracleIconName({ state, method }) {
    if (state === "delivered") {
        if (method === "propagated") return "email-check-outline";
        if (method === "paper") return "note-check-outline";
        return "check-all";
    }
    if (state === "sent" || state === "propagated" || state === "unknown") {
        if (method === "propagated") return "email-outline";
        if (method === "paper") return "note-outline";
        return "check";
    }
    return "check";
}

function oracleTitleKey({ state, method }) {
    if (state === "delivered") {
        if (method === "propagated") return "messages.outbound_delivered_propagated";
        return "messages.outbound_delivered";
    }
    if (method === "propagated") return "messages.outbound_on_propagation_node";
    return "messages.outbound_sent_network";
}

function oracleDeferred({ state, method }) {
    return method === "opportunistic" && state === "failed";
}

describe("outboundMessageStatus LXMF oracle", () => {
    it("maps every API state x method pair to the independent icon oracle", () => {
        for (const state of API_STATES) {
            for (const method of API_METHODS) {
                const msg = { state, method };
                expect(outboundBubbleStatusIconName(msg)).toBe(oracleIconName(msg));
            }
        }
    });

    it("maps every API state x method pair to the independent title-key oracle", () => {
        for (const state of API_STATES) {
            for (const method of API_METHODS) {
                const msg = { state, method };
                expect(outboundBubbleStatusTitleKey(msg)).toBe(oracleTitleKey(msg));
            }
        }
    });

    it("treats only opportunistic+failed as deferred wait", () => {
        for (const state of API_STATES) {
            for (const method of API_METHODS) {
                const msg = { state, method };
                expect(isOpportunisticDeferredDelivery(msg)).toBe(oracleDeferred(msg));
            }
        }
    });

    it("propagated sent means on-node mailbox icon, not delivered checkmarks", () => {
        const msg = { state: "sent", method: "propagated" };
        expect(outboundBubbleStatusIconName(msg)).toBe("email-outline");
        expect(outboundBubbleStatusTitleKey(msg)).toBe("messages.outbound_on_propagation_node");
        expect(outboundBubbleStatusIconName(msg)).not.toBe("check-all");
        expect(outboundBubbleStatusIconName(msg)).not.toBe("email-check-outline");
    });

    it("propagated delivered means recipient collected mail", () => {
        const msg = { state: "delivered", method: "propagated" };
        expect(outboundBubbleStatusIconName(msg)).toBe("email-check-outline");
        expect(outboundBubbleStatusTitleKey(msg)).toBe("messages.outbound_delivered_propagated");
    });

    it("direct and opportunistic use WhatsApp-style checks for sent/delivered", () => {
        for (const method of ["direct", "opportunistic"]) {
            expect(outboundBubbleStatusIconName({ state: "sent", method })).toBe("check");
            expect(outboundBubbleStatusIconName({ state: "delivered", method })).toBe("check-all");
        }
    });

    it("paper uses note icons for sent and delivered", () => {
        expect(outboundBubbleStatusIconName({ state: "sent", method: "paper" })).toBe("note-outline");
        expect(outboundBubbleStatusIconName({ state: "delivered", method: "paper" })).toBe("note-check-outline");
    });

    it("backend never emits state=propagated but UI still treats it as sent-like", () => {
        expect(outboundBubbleStatusIconName({ state: "propagated", method: "direct" })).toBe("check");
        expect(outboundBubbleStatusIconName({ state: "propagated", method: "propagated" })).toBe("email-outline");
    });

    it("null message has safe defaults", () => {
        expect(outboundBubbleStatusIconName(null)).toBe("check");
        expect(outboundBubbleStatusTitleKey(null)).toBeNull();
        expect(isOpportunisticDeferredDelivery(null)).toBe(false);
    });

    it("sent without delivered is not a hard-fail badge for direct or opportunistic", () => {
        for (const method of ["direct", "opportunistic"]) {
            const sent = { state: "sent", method };
            expect(isOpportunisticDeferredDelivery(sent)).toBe(false);
            expect(outboundBubbleStatusIconName(sent)).toBe("check");
            expect(outboundBubbleStatusIconName(sent)).not.toBe("check-all");
        }
    });

    it("no-receipt stuck at sent still shows single-check network-sent, not delivered", () => {
        const stuck = { state: "sent", method: "opportunistic" };
        expect(outboundBubbleStatusIconName(stuck)).toBe("check");
        expect(outboundBubbleStatusTitleKey(stuck)).toBe("messages.outbound_sent_network");
        expect(isOpportunisticDeferredDelivery(stuck)).toBe(false);
    });

    it("LXMF_STATUS_UI_ORACLE_PROVED", () => {
        let pairs = 0;
        for (const state of API_STATES) {
            for (const method of API_METHODS) {
                const msg = { state, method };
                expect(outboundBubbleStatusIconName(msg)).toBe(oracleIconName(msg));
                expect(outboundBubbleStatusTitleKey(msg)).toBe(oracleTitleKey(msg));
                expect(isOpportunisticDeferredDelivery(msg)).toBe(oracleDeferred(msg));
                pairs += 1;
            }
        }
        expect(pairs).toBe(API_STATES.length * API_METHODS.length);
        console.log("LXMF_STATUS_UI_ORACLE_PROVED");
    });
});
