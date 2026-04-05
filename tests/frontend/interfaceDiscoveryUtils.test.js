import { describe, it, expect } from "vitest";
import { numOrNull } from "../../meshchatx/src/frontend/js/interfaceDiscoveryUtils.js";

describe("interfaceDiscoveryUtils numOrNull", () => {
    it("treats empty and invalid as null", () => {
        expect(numOrNull(null)).toBe(null);
        expect(numOrNull(undefined)).toBe(null);
        expect(numOrNull("")).toBe(null);
        expect(numOrNull("   ")).toBe(null);
        expect(numOrNull(Number.NaN)).toBe(null);
        expect(numOrNull(Number.POSITIVE_INFINITY)).toBe(null);
        expect(numOrNull("not-a-number")).toBe(null);
    });

    it("accepts finite numbers and numeric strings", () => {
        expect(numOrNull(0)).toBe(0);
        expect(numOrNull(-12.5)).toBe(-12.5);
        expect(numOrNull("0")).toBe(0);
        expect(numOrNull(" 42.25 ")).toBe(42.25);
    });

    it("fuzz: random finite doubles round-trip", () => {
        for (let i = 0; i < 200; i++) {
            const x = (Math.random() - 0.5) * 360;
            expect(numOrNull(x)).toBeCloseTo(x, 10);
        }
    });
});
