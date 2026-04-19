import { gzipSync } from "node:zlib";
import { describe, it, expect, beforeAll } from "vitest";
import { decodeTgsBuffer } from "@/js/tgsDecode.js";

beforeAll(() => {
    const ctx = {
        fillStyle: "",
        strokeStyle: "",
        fillRect: vi.fn(),
        clearRect: vi.fn(),
        save: vi.fn(),
        restore: vi.fn(),
        translate: vi.fn(),
        scale: vi.fn(),
        rotate: vi.fn(),
        beginPath: vi.fn(),
        closePath: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        arc: vi.fn(),
        fill: vi.fn(),
        stroke: vi.fn(),
        setTransform: vi.fn(),
        drawImage: vi.fn(),
        measureText: vi.fn(() => ({ width: 0 })),
        createLinearGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
        createRadialGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
    };
    HTMLCanvasElement.prototype.getContext = vi.fn(() => ctx);
});

function randomUint8Array(n) {
    const u = new Uint8Array(n);
    crypto.getRandomValues(u);
    return u;
}

function randomJsonValue(depth) {
    if (depth <= 0) {
        return null;
    }
    const r = Math.random();
    if (r < 0.2) {
        return null;
    }
    if (r < 0.4) {
        return Math.floor(Math.random() * 1_000_000);
    }
    if (r < 0.55) {
        return String.fromCharCode(32 + Math.floor(Math.random() * 80));
    }
    if (r < 0.75) {
        const n = Math.floor(Math.random() * 8);
        return Array.from({ length: n }, () => randomJsonValue(depth - 1));
    }
    const n = Math.floor(Math.random() * 6);
    const o = {};
    for (let i = 0; i < n; i++) {
        o[`k${i}`] = randomJsonValue(depth - 1);
    }
    return o;
}

describe("fuzzing: TGS decode", () => {
    it("fuzzing: decodeTgsBuffer handles random buffers without unhandled rejection", async () => {
        for (let i = 0; i < 2000; i++) {
            const len = Math.floor(Math.random() * 6144);
            const buf = randomUint8Array(len).buffer;
            try {
                await decodeTgsBuffer(buf);
            } catch {
                /* JSON.parse, gzip, or missing DecompressionStream */
            }
        }
        expect(true).toBe(true);
    });

    it("fuzzing: decodeTgsBuffer handles gzip-compressed random JSON", async () => {
        for (let i = 0; i < 400; i++) {
            const payload = JSON.stringify(randomJsonValue(6));
            const gz = gzipSync(Buffer.from(payload, "utf8"));
            const ab = gz.buffer.slice(gz.byteOffset, gz.byteOffset + gz.byteLength);
            try {
                await decodeTgsBuffer(ab);
            } catch {
                /* invalid JSON after decompress */
            }
        }
        expect(true).toBe(true);
    });

});
