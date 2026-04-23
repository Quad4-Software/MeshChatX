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
    });

    it("startCodec2ScriptsBackgroundLoad swallows errors after retries", async () => {
        const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
        vi.spyOn(document.head, "appendChild").mockImplementation((node) => {
            if (node instanceof HTMLScriptElement && node.src) {
                origAppend(node);
                queueMicrotask(() => node.dispatchEvent(new Event("error")));
                return node;
            }
            return origAppend(node);
        });

        await startCodec2ScriptsBackgroundLoad({
            maxAttempts: 2,
            baseDelayMs: 0,
            maxDelayMs: 1,
        });

        expect(warn).toHaveBeenCalled();
        warn.mockRestore();
    });
});
