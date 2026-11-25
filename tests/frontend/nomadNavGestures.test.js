// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import {
    NAV_SWIPE_EDGE_PX,
    NAV_SWIPE_BACK_TRIGGER_PX,
    NAV_PULL_TRIGGER_PX,
    NAV_SWIPE_BACK_MAX_PX,
    NAV_PULL_MAX_PX,
    isNavSwipeBackMotion,
    isNavPullMotion,
    canArmNavSwipeBack,
    computeNavSwipeBackDistance,
    computeNavPullDistance,
} from "../../meshchatx/src/frontend/js/nomadNavGestures.js";

describe("nomadNavGestures", () => {
    it("keeps the documented thresholds", () => {
        expect(NAV_SWIPE_EDGE_PX).toBe(40);
        expect(NAV_SWIPE_BACK_TRIGGER_PX).toBe(64);
        expect(NAV_PULL_TRIGGER_PX).toBe(72);
        expect(NAV_SWIPE_BACK_MAX_PX).toBe(140);
        expect(NAV_PULL_MAX_PX).toBe(160);
    });

    it("arms the edge swipe only inside the edge zone", () => {
        expect(canArmNavSwipeBack(0, 0)).toBe(true);
        expect(canArmNavSwipeBack(NAV_SWIPE_EDGE_PX, 0)).toBe(true);
        expect(canArmNavSwipeBack(NAV_SWIPE_EDGE_PX + 1, 0)).toBe(false);
    });

    it("does not arm the edge swipe when the scroller can pan right", () => {
        // scrollLeft > 0: a rightward drag pans the content back natively,
        // so forwarding it as swipe-back would hijack the pan.
        expect(canArmNavSwipeBack(10, 1)).toBe(false);
        expect(canArmNavSwipeBack(10, 200)).toBe(false);
        expect(canArmNavSwipeBack(10, 0)).toBe(true);
    });

    it("swipe-back motion must be rightward and horizontal-dominant", () => {
        expect(isNavSwipeBackMotion(30, 0)).toBe(true);
        expect(isNavSwipeBackMotion(30, 29)).toBe(true);
        expect(isNavSwipeBackMotion(30, 30)).toBe(false);
        expect(isNavSwipeBackMotion(30, -29)).toBe(true);
        expect(isNavSwipeBackMotion(0, 0)).toBe(false);
        expect(isNavSwipeBackMotion(-30, 0)).toBe(false);
        expect(isNavSwipeBackMotion(10, 40)).toBe(false);
    });

    it("pull motion must be downward and vertical-dominant", () => {
        expect(isNavPullMotion(0, 30)).toBe(true);
        expect(isNavPullMotion(29, 30)).toBe(true);
        expect(isNavPullMotion(30, 30)).toBe(false);
        expect(isNavPullMotion(0, 0)).toBe(false);
        expect(isNavPullMotion(0, -30)).toBe(false);
        expect(isNavPullMotion(40, 10)).toBe(false);
    });

    it("caps the swipe-back distance and cancels on reversal", () => {
        expect(computeNavSwipeBackDistance(100, 0)).toBe(100);
        expect(computeNavSwipeBackDistance(200, 0)).toBe(NAV_SWIPE_BACK_MAX_PX);
        // direction reversed mid-gesture: the armed distance must not survive
        expect(computeNavSwipeBackDistance(-20, 0)).toBe(0);
        expect(computeNavSwipeBackDistance(20, -40)).toBe(0);
    });

    it("caps the pull distance and cancels on reversal", () => {
        expect(computeNavPullDistance(0, 120, 0, 0)).toBe(120);
        expect(computeNavPullDistance(0, 220, 0, 0)).toBe(NAV_PULL_MAX_PX);
        expect(computeNavPullDistance(0, -20, 0, 0)).toBe(0);
        expect(computeNavPullDistance(-40, 20, 0, 0)).toBe(0);
    });

    it("pull stays zero when the scroller started or moved away from the top", () => {
        expect(computeNavPullDistance(0, 120, 5, 0)).toBe(0);
        expect(computeNavPullDistance(0, 120, 0, 5)).toBe(0);
        expect(computeNavPullDistance(0, 120, 0, 0)).toBe(120);
    });

    it("swipe-back and pull dominance are mutually exclusive", () => {
        // For any displacement at most one gesture can report a distance.
        for (const [dx, dy] of [
            [50, 0],
            [0, 50],
            [50, 50],
            [-50, 50],
            [50, -50],
            [30, 60],
            [60, 30],
        ]) {
            const swipe = computeNavSwipeBackDistance(dx, dy);
            const pull = computeNavPullDistance(dx, dy, 0, 0);
            expect(swipe === 0 || pull === 0).toBe(true);
        }
    });
});
