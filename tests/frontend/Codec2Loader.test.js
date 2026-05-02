import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    withRetries,
    resetCodec2LoaderState,
    ensureCodec2ScriptsLoaded,
    startCodec2ScriptsBackgroundLoad,
} from "../../meshchatx/src/frontend/js/Codec2Loader.js";

describe("withRetries", () => {
    it("succeeds on first attempt", async () => {
        const fn = vi.fn().mockResolvedValue(undefined);
        await withRetries(fn, { maxAttempts: 4, baseDelayMs: 1, maxDelayMs: 5 });
        expect(fn).toHaveBeenCalledTimes(1);
    });

    it("retries with backoff until success", async () => {
        const fn = vi
            .fn()
            .mockRejectedValueOnce(new Error("a"))
            .mockRejectedValueOnce(new Error("b"))
            .mockResolvedValue(undefined);
        await withRetries(fn, { maxAttempts: 6, baseDelayMs: 1, maxDelayMs: 5 });
        expect(fn).toHaveBeenCalledTimes(3);
    });

    it("throws after maxAttempts failures", async () => {
        const fn = vi.fn().mockRejectedValue(new Error("always"));
        await expect(withRetries(fn, { maxAttempts: 3, baseDelayMs: 1, maxDelayMs: 5 })).rejects.toThrow("always");
        expect(fn).toHaveBeenCalledTimes(3);
    });

    it("performance: completes quickly with tiny delays", async () => {
        const fn = vi.fn().mockResolvedValue(undefined);
        const t0 = performance.now();
        await withRetries(fn, { maxAttempts: 8, baseDelayMs: 0, maxDelayMs: 1 });
        expect(performance.now() - t0).toBeLessThan(500);
    });
});

describe("Codec2Loader integration (jsdom)", () => {
    const origAppend = document.head.appendChild.bind(document.head);

    beforeEach(() => {
        resetCodec2LoaderState();
        vi.restoreAllMocks();
    });

    afterEach(() => {
        resetCodec2LoaderState();
        document.head.appendChild = origAppend;
        document.querySelectorAll("script[data-codec2-src]").forEach((el) => el.remove());
    });

    it("ensureCodec2ScriptsLoaded resolves when script tags load", async () => {
        // Mock crypto.subtle.digest first
        const mockHashBytes = new Uint8Array(48);
        for (let i = 0; i < 48; i++) mockHashBytes[i] = i;
        const mockHashB64 = btoa(String.fromCharCode(...mockHashBytes));

        vi.stubGlobal("crypto", {
            subtle: {
                digest: vi.fn(async () => mockHashBytes.buffer),
            },
        });

        // Mock fetch to return integrity.json and script content
        const mockIntegrity = {
            files: {
                "c2enc.js": `sha384-${mockHashB64}`,
                "c2dec.js": `sha384-${mockHashB64}`,
                "sox.js": `sha384-${mockHashB64}`,
                "codec2-lib.js": `sha384-${mockHashB64}`,
                "wav-encoder.js": `sha384-${mockHashB64}`,
                "codec2-microphone-recorder.js": `sha384-${mockHashB64}`,
            },
        };

        vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
            if (url.includes("integrity.json")) {
                return Promise.resolve({
                    ok: true,
                    json: async () => mockIntegrity,
                });
            }
            // Return mock script content for any script request
            const content = "// mock script";
            return Promise.resolve({
                ok: true,
                arrayBuffer: async () => new TextEncoder().encode(content).buffer,
            });
        });

        vi.spyOn(document.head, "appendChild").mockImplementation((node) => {
            if (node instanceof HTMLScriptElement && node.src) {
                origAppend(node);
                queueMicrotask(() => node.dispatchEvent(new Event("load")));
                return node;
            }
            return origAppend(node);
        });

        await ensureCodec2ScriptsLoaded();
        await expect(ensureCodec2ScriptsLoaded()).resolves.toBeUndefined();
        expect(document.querySelectorAll("script[data-codec2-src]").length).toBe(6);

        vi.unstubAllGlobals();
    });

    it("startCodec2ScriptsBackgroundLoad swallows errors after retries", async () => {
        const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

        // Mock crypto
        vi.stubGlobal("crypto", {
            subtle: {
                digest: vi.fn(async () => new ArrayBuffer(48)),
            },
        });

        // Mock fetch to fail (simulate network/SRI failure)
        vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network error"));

        await startCodec2ScriptsBackgroundLoad({
            maxAttempts: 2,
            baseDelayMs: 0,
            maxDelayMs: 1,
        });

        expect(warn).toHaveBeenCalled();
        warn.mockRestore();
        vi.unstubAllGlobals();
    });
});
