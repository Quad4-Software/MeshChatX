import { describe, it, expect } from "vitest";
import { gzipSync } from "node:zlib";
import { decodeTgsBuffer } from "@/js/tgsDecode.js";

describe("tgsDecode", () => {
    it("decodes gzip-wrapped Lottie JSON", async () => {
        const json = JSON.stringify({ v: "5", fr: 30, ip: 0, op: 10, w: 100, h: 100, layers: [] });
        const gz = gzipSync(Buffer.from(json, "utf8"));
        const buf = gz.buffer.slice(gz.byteOffset, gz.byteOffset + gz.byteLength);
        const data = await decodeTgsBuffer(buf);
        expect(data.w).toBe(100);
        expect(data.h).toBe(100);
    });

    it("decodes raw JSON without gzip header", async () => {
        const json = '{"a":1}';
        const enc = new TextEncoder();
        const data = await decodeTgsBuffer(enc.encode(json).buffer);
        expect(data.a).toBe(1);
    });

    it("rejects invalid JSON after gzip", async () => {
        const gz = gzipSync(Buffer.from("not-json{{{", "utf8"));
        const buf = gz.buffer.slice(gz.byteOffset, gz.byteOffset + gz.byteLength);
        await expect(decodeTgsBuffer(buf)).rejects.toThrow();
    });
});
