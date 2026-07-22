// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import { shouldWarnMultiSession, shouldShowMultiSessionToast } from "../../meshchatx/src/frontend/js/activeSessions.js";

describe("activeSessions oracles", () => {
    it("warns only when count is at least two and setting is on", () => {
        expect(shouldWarnMultiSession(0, true)).toBe(false);
        expect(shouldWarnMultiSession(1, true)).toBe(false);
        expect(shouldWarnMultiSession(2, true)).toBe(true);
        expect(shouldWarnMultiSession(5, true)).toBe(true);
        expect(shouldWarnMultiSession(2, false)).toBe(false);
        expect(shouldWarnMultiSession(2, undefined)).toBe(true);
        expect(shouldWarnMultiSession(Number.NaN, true)).toBe(false);
    });

    it("toasts once per multi-session episode", () => {
        expect(shouldShowMultiSessionToast(1, true, false)).toEqual({
            show: false,
            warned: false,
        });
        expect(shouldShowMultiSessionToast(2, true, false)).toEqual({
            show: true,
            warned: true,
        });
        expect(shouldShowMultiSessionToast(3, true, true)).toEqual({
            show: false,
            warned: true,
        });
        expect(shouldShowMultiSessionToast(1, true, true)).toEqual({
            show: false,
            warned: false,
        });
        expect(shouldShowMultiSessionToast(2, false, false)).toEqual({
            show: false,
            warned: false,
        });
    });
});
