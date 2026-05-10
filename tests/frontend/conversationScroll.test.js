import { describe, it, expect } from "vitest";
import {
    SCROLL_BOTTOM_EPS_PX,
    canTrustScrollNearBottomHeuristic,
    isNearBottom,
    isScrollColumnReverse,
    maxScrollTop,
    resetMessagesScrollSurface,
    scrollContainerToBottom,
    shouldLoadPreviousMessages,
} from "@/components/messages/conversationScroll.js";

function makeScrollContainer({ reverse, scrollTop, scrollHeight, clientHeight }) {
    const outer = document.createElement("div");
    const inner = document.createElement("div");
    if (reverse) {
        inner.style.flexDirection = "column-reverse";
    } else {
        inner.style.flexDirection = "column";
    }
    outer.appendChild(inner);
    document.body.appendChild(outer);
    Object.defineProperty(outer, "scrollHeight", { value: scrollHeight, configurable: true });
    Object.defineProperty(outer, "clientHeight", { value: clientHeight, configurable: true });
    outer.scrollTop = scrollTop;
    return outer;
}

describe("conversationScroll.js", () => {
    it("maxScrollTop uses clientHeight", () => {
        const el = document.createElement("div");
        Object.defineProperty(el, "scrollHeight", { value: 500, configurable: true });
        Object.defineProperty(el, "clientHeight", { value: 100, configurable: true });
        expect(maxScrollTop(el)).toBe(400);
    });

    it("isNearBottom for column-reverse uses small scrollTop", () => {
        const el = makeScrollContainer({
            reverse: true,
            scrollTop: 3,
            scrollHeight: 5000,
            clientHeight: 100,
        });
        expect(isScrollColumnReverse(el)).toBe(true);
        expect(isNearBottom(el, SCROLL_BOTTOM_EPS_PX)).toBe(true);
        el.scrollTop = 2000;
        expect(isNearBottom(el, SCROLL_BOTTOM_EPS_PX)).toBe(false);
        el.remove();
    });

    it("isNearBottom for normal column uses distance from max scrollTop", () => {
        const el = makeScrollContainer({
            reverse: false,
            scrollTop: 392,
            scrollHeight: 500,
            clientHeight: 100,
        });
        expect(isScrollColumnReverse(el)).toBe(false);
        expect(isNearBottom(el, SCROLL_BOTTOM_EPS_PX)).toBe(true);
        el.scrollTop = 0;
        expect(isNearBottom(el, SCROLL_BOTTOM_EPS_PX)).toBe(false);
        el.remove();
    });

    it("isNearBottom tolerates fractional scroll metrics (normal column)", () => {
        const el = document.createElement("div");
        const inner = document.createElement("div");
        inner.style.flexDirection = "column";
        el.appendChild(inner);
        document.body.appendChild(el);
        Object.defineProperty(el, "scrollHeight", { value: 500.4, configurable: true });
        Object.defineProperty(el, "clientHeight", { value: 100.2, configurable: true });
        el.scrollTop = 400.19;
        expect(isNearBottom(el, SCROLL_BOTTOM_EPS_PX)).toBe(true);
        el.remove();
    });

    it("scrollContainerToBottom sets scrollTop for column-reverse", () => {
        const el = makeScrollContainer({
            reverse: true,
            scrollTop: 300,
            scrollHeight: 800,
            clientHeight: 100,
        });
        scrollContainerToBottom(el);
        expect(el.scrollTop).toBe(0);
        el.remove();
    });

    it("scrollContainerToBottom sets scrollTop to max for normal column", () => {
        const el = makeScrollContainer({
            reverse: false,
            scrollTop: 0,
            scrollHeight: 600,
            clientHeight: 100,
        });
        scrollContainerToBottom(el);
        expect(el.scrollTop).toBe(500);
        el.remove();
    });

    it("shouldLoadPreviousMessages mirrors edge for column-reverse", () => {
        const el = makeScrollContainer({
            reverse: true,
            scrollTop: 4450,
            scrollHeight: 5000,
            clientHeight: 100,
        });
        expect(shouldLoadPreviousMessages(el)).toBe(true);
        el.scrollTop = 0;
        expect(shouldLoadPreviousMessages(el)).toBe(false);
        el.remove();
    });

    it("shouldLoadPreviousMessages is false at visual bottom for short column-reverse threads", () => {
        const el = makeScrollContainer({
            reverse: true,
            scrollTop: 0,
            scrollHeight: 300,
            clientHeight: 100,
        });
        expect(maxScrollTop(el)).toBe(200);
        expect(shouldLoadPreviousMessages(el)).toBe(false);
        el.remove();
    });

    it("shouldLoadPreviousMessages uses scrollTop for normal column", () => {
        const el = makeScrollContainer({
            reverse: false,
            scrollTop: 100,
            scrollHeight: 5000,
            clientHeight: 100,
        });
        expect(shouldLoadPreviousMessages(el)).toBe(true);
        el.scrollTop = 2000;
        expect(shouldLoadPreviousMessages(el)).toBe(false);
        el.remove();
    });

    it("resetMessagesScrollSurface forces scrollTop to 0", () => {
        const el = makeScrollContainer({
            reverse: false,
            scrollTop: 400,
            scrollHeight: 900,
            clientHeight: 100,
        });
        resetMessagesScrollSurface(el);
        expect(el.scrollTop).toBe(0);
        el.remove();
    });

    it("canTrustScrollNearBottomHeuristic requires an inner child", () => {
        const outer = document.createElement("div");
        document.body.appendChild(outer);
        expect(canTrustScrollNearBottomHeuristic(outer)).toBe(false);
        const inner = document.createElement("div");
        outer.appendChild(inner);
        expect(canTrustScrollNearBottomHeuristic(outer)).toBe(true);
        outer.remove();
    });

    it("isNearBottom is misleading on empty container without inner (trust heuristic false)", () => {
        const el = document.createElement("div");
        document.body.appendChild(el);
        Object.defineProperty(el, "scrollHeight", { value: 400, configurable: true });
        Object.defineProperty(el, "clientHeight", { value: 400, configurable: true });
        el.scrollTop = 0;
        expect(isScrollColumnReverse(el)).toBe(false);
        expect(isNearBottom(el, SCROLL_BOTTOM_EPS_PX)).toBe(true);
        expect(canTrustScrollNearBottomHeuristic(el)).toBe(false);
        el.remove();
    });
});
