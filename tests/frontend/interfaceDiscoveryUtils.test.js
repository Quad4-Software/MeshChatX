import { describe, it, expect } from "vitest";
import { numOrNull, parseRNodeFrequencyHz } from "../../meshchatx/src/frontend/js/interfaceDiscoveryUtils.js";

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

describe("interfaceDiscoveryUtils parseRNodeFrequencyHz", () => {
    it("normalizes MHz-style decimals to integer Hz", () => {
        expect(parseRNodeFrequencyHz(868.825)).toBe(868825000);
        expect(parseRNodeFrequencyHz("868.825000000")).toBe(868825000);
        expect(parseRNodeFrequencyHz("868.825000000 MHz")).toBe(868825000);
    });

    it("preserves full Hz values", () => {
        expect(parseRNodeFrequencyHz(868825000)).toBe(868825000);
        expect(parseRNodeFrequencyHz("868825000")).toBe(868825000);
    });

    it("maps small integer MHz (433, 868)", () => {
        expect(parseRNodeFrequencyHz(433)).toBe(433000000);
        expect(parseRNodeFrequencyHz(868)).toBe(868000000);
    });

    it("does not scale ambiguous midrange integers", () => {
        expect(parseRNodeFrequencyHz(125000)).toBe(125000);
    });
});
