// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    canTrustScrollNearBottomHeuristic,
    isNearBottom,
    shouldLoadPreviousMessages,
} from "@/features/messages/lib/conversationScroll.ts";

function scrollSurface(scrollTop, scrollHeight = 1000, clientHeight = 200) {
    const element = document.createElement("div");
    element.appendChild(document.createElement("div"));
    Object.defineProperty(element, "scrollHeight", { value: scrollHeight });
    Object.defineProperty(element, "clientHeight", { value: clientHeight });
    element.scrollTop = scrollTop;
    return element;
}

describe("ConversationViewer scroll policy", () => {
    it("loads previous messages near the top of normal flow", () => {
        expect(shouldLoadPreviousMessages(scrollSurface(100))).toBe(true);
        expect(shouldLoadPreviousMessages(scrollSurface(700))).toBe(false);
    });

    it("treats only the visual bottom as near bottom", () => {
        expect(isNearBottom(scrollSurface(800))).toBe(true);
        expect(isNearBottom(scrollSurface(100))).toBe(false);
    });

    it("requires rendered content before trusting bottom detection", () => {
        const empty = document.createElement("div");
        expect(canTrustScrollNearBottomHeuristic(empty)).toBe(false);
        empty.appendChild(document.createElement("div"));
        expect(canTrustScrollNearBottomHeuristic(empty)).toBe(true);
    });
});
