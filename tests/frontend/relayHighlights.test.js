// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { normalizeHighlightWordInput, relayTextMatchesWords } from "@/js/relay/relayHighlights.js";

describe("relayTextMatchesWords", () => {
    it("matches whole words case-insensitively", () => {
        expect(relayTextMatchesWords("hey uucp fans", ["uucp"])).toBe(true);
        expect(relayTextMatchesWords("hey UUCP fans", ["uucp"])).toBe(true);
    });

    it("does not match inside longer tokens", () => {
        expect(relayTextMatchesWords("uucpd is running", ["uucp"])).toBe(false);
        expect(relayTextMatchesWords("my-uucp-node", ["uucp"])).toBe(true);
        expect(relayTextMatchesWords("uucp2", ["uucp"])).toBe(false);
    });

    it("matches callsigns with digits", () => {
        expect(relayTextMatchesWords("m0oue checking in", ["m0oue"])).toBe(true);
        expect(relayTextMatchesWords("m0oue2 checking in", ["m0oue"])).toBe(false);
    });

    it("matches multi-word phrases", () => {
        expect(relayTextMatchesWords("talking about relay chat today", ["relay chat"])).toBe(true);
    });

    it("escapes regex characters in words", () => {
        expect(relayTextMatchesWords("price is 5.00 now", ["5.00"])).toBe(true);
        expect(relayTextMatchesWords("price is 5x00 now", ["5.00"])).toBe(false);
    });

    it("matches at string boundaries", () => {
        expect(relayTextMatchesWords("uucp", ["uucp"])).toBe(true);
        expect(relayTextMatchesWords("uucp here", ["uucp"])).toBe(true);
        expect(relayTextMatchesWords("see uucp", ["uucp"])).toBe(true);
    });

    it("returns false for empty inputs", () => {
        expect(relayTextMatchesWords("", ["uucp"])).toBe(false);
        expect(relayTextMatchesWords("text", [])).toBe(false);
        expect(relayTextMatchesWords("text", null)).toBe(false);
        expect(relayTextMatchesWords(null, ["uucp"])).toBe(false);
        expect(relayTextMatchesWords("text", ["  ", ""])).toBe(false);
    });

    it("skips blank words", () => {
        expect(relayTextMatchesWords("anything", ["  "])).toBe(false);
    });
});

describe("normalizeHighlightWordInput", () => {
    it("trims and collapses whitespace", () => {
        expect(normalizeHighlightWordInput("  relay   chat ")).toBe("relay chat");
        expect(normalizeHighlightWordInput("")).toBe("");
        expect(normalizeHighlightWordInput(null)).toBe("");
    });
});
