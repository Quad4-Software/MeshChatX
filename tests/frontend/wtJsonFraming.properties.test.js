// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import {
    encodeWtJsonLine,
    feedWtJsonLines,
    WT_MAX_FRAME_CHARS,
} from "../../meshchatx/src/frontend/js/wtJsonFraming.js";

function mulberry32(seed) {
    let a = seed >>> 0;
    return () => {
        a |= 0;
        a = (a + 0x6d2b79f5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

describe("wtJsonFraming properties", () => {
    it("encode/feed roundtrips arbitrary objects", () => {
        const rnd = mulberry32(5);
        for (let i = 0; i < 200; i++) {
            const obj = {
                n: Math.floor(rnd() * 1e9),
                s: `x${Math.floor(rnd() * 1e6)}\nembedded newline in string`,
                arr: [1, "two", null, { deep: true }],
            };
            const { objects, errors, buffer } = feedWtJsonLines("", encodeWtJsonLine(obj));
            expect(errors).toEqual([]);
            expect(buffer).toBe("");
            expect(objects).toEqual([obj]);
        }
    });

    it("chunk-split invariance: any split of a stream yields identical objects", () => {
        const rnd = mulberry32(17);
        for (let trial = 0; trial < 100; trial++) {
            const objs = Array.from({ length: 1 + Math.floor(rnd() * 8) }, () => ({
                id: Math.floor(rnd() * 1e6),
            }));
            const stream = objs.map(encodeWtJsonLine).join("");
            const splitAt = Math.floor(rnd() * (stream.length + 1));
            const whole = feedWtJsonLines("", stream);
            let state = { objects: [], buffer: "", errors: [] };
            const r1 = feedWtJsonLines("", stream.slice(0, splitAt));
            const r2 = feedWtJsonLines(r1.buffer, stream.slice(splitAt));
            expect([...r1.objects, ...r2.objects]).toEqual(whole.objects);
            expect(r2.buffer).toBe(whole.buffer);
        }
    });

    it("never throws on arbitrary chunks", () => {
        const rnd = mulberry32(23);
        for (let i = 0; i < 300; i++) {
            const len = Math.floor(rnd() * 200);
            let chunk = "";
            for (let j = 0; j < len; j++) {
                chunk += String.fromCharCode(Math.floor(rnd() * 128));
            }
            const out = feedWtJsonLines("", chunk);
            expect(out).toHaveProperty("objects");
            expect(out).toHaveProperty("buffer");
            expect(out).toHaveProperty("errors");
        }
    });

    it("oversized buffered content trips overflow and resets", () => {
        const huge = "x".repeat(WT_MAX_FRAME_CHARS * 2 + 1);
        const out = feedWtJsonLines("", huge);
        expect(out.errors).toContain("frame_overflow");
        expect(out.buffer).toBe("");
    });

    it("non-object JSON lines report errors, not objects", () => {
        const out = feedWtJsonLines("", 'null\n5\n"str"\n[1,2]\n{}\n');
        // Arrays are typeof "object" so they pass through as objects.
        expect(out.objects).toEqual([[1, 2], {}]);
        expect(out.errors).toEqual(["not_object", "not_object", "not_object"]);
    });
});
