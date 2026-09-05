import { describe, it, expect } from "vitest";
import { isDestinationHash, normalizeDestinationHash } from "@/js/meshValidate.ts";

describe("meshValidate", () => {
    it("accepts exactly 32 hex digits", () => {
        expect(isDestinationHash("a".repeat(32))).toBe(true);
        expect(isDestinationHash("A".repeat(32))).toBe(true);
        expect(isDestinationHash("0123456789abcdef0123456789abcdef")).toBe(true);
    });

    it("rejects short, long, and non-hex", () => {
        expect(isDestinationHash("short")).toBe(false);
        expect(isDestinationHash("a".repeat(31))).toBe(false);
        expect(isDestinationHash("a".repeat(33))).toBe(false);
        expect(isDestinationHash("g".repeat(32))).toBe(false);
        expect(isDestinationHash(null)).toBe(false);
        expect(isDestinationHash(undefined)).toBe(false);
        expect(isDestinationHash(12)).toBe(false);
    });

    it("normalizeDestinationHash strips URI junk then validates", () => {
        const hex = "0123456789abcdef0123456789abcdef";
        expect(normalizeDestinationHash(`lxmf://${hex}`)).toBe(hex);
        expect(normalizeDestinationHash(`LXMF@${hex}`)).toBe(hex);
        expect(normalizeDestinationHash(`${hex}:extra`)).toBe(hex);
        expect(normalizeDestinationHash("not-a-hash")).toBe("");
        expect(normalizeDestinationHash("")).toBe("");
    });
});
