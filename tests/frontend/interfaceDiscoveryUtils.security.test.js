// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import { numOrNull } from "@/js/interfaceDiscoveryUtils.js";

describe("interfaceDiscoveryUtils security-oriented inputs", () => {
    it("numOrNull rejects object and array coercion traps", () => {
        expect(numOrNull({ valueOf: () => "42" })).toBe(null);
        expect(numOrNull([])).toBe(null);
        expect(numOrNull(["1"])).toBe(null);
    });

    it("numOrNull handles long digit strings without throwing", () => {
        const s = "1".repeat(400);
        expect(numOrNull(s)).toBe(null);
    });

    it("numOrNull handles unicode and RTL marks in strings", () => {
        expect(numOrNull("\u202e12\u202c")).toBe(null);
        expect(numOrNull("12\u200b34")).toBe(null);
    });

    it("fuzz numOrNull with random strings", () => {
        for (let i = 0; i < 300; i++) {
            const s = String.fromCodePoint(...Array.from({ length: 8 }, () => Math.floor(Math.random() * 0x10ffff)));
            expect(() => numOrNull(s)).not.toThrow();
        }
    });
});
