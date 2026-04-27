import { describe, it, expect } from "vitest";
import {
    MESSAGE_BODY_MAX_DISPLAY_CHARS,
    isStringTooLargeForInlineDisplay,
} from "../../meshchatx/src/frontend/js/messageDisplayLimits.js";

describe("messageDisplayLimits", () => {
    it("isStringTooLargeForInlineDisplay is false at limit", () => {
        const s = "a".repeat(MESSAGE_BODY_MAX_DISPLAY_CHARS);
        expect(isStringTooLargeForInlineDisplay(s)).toBe(false);
    });

    it("isStringTooLargeForInlineDisplay is true above limit", () => {
        const s = "a".repeat(MESSAGE_BODY_MAX_DISPLAY_CHARS + 1);
        expect(isStringTooLargeForInlineDisplay(s)).toBe(true);
    });

    it("isStringTooLargeForInlineDisplay is false for non-strings", () => {
        expect(isStringTooLargeForInlineDisplay(null)).toBe(false);
        expect(isStringTooLargeForInlineDisplay(undefined)).toBe(false);
        expect(isStringTooLargeForInlineDisplay(123)).toBe(false);
    });
});
