import { describe, it, expect, vi, afterEach } from "vitest";
import {
    ensureAudioContextRunning,
    decodeAudioDataCompat,
    decodeAudioArrayBuffer,
} from "../../meshchatx/src/frontend/js/audioContextUtils.js";

const makeCtx = (state = "suspended") => ({
    state,
    resume: vi.fn(function () {
        this.state = "running";
        return Promise.resolve();
    }),
    decodeAudioData: vi.fn(() => Promise.resolve({ decoded: true })),
    close: vi.fn(() => Promise.resolve()),
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("ensureAudioContextRunning", () => {
    it("returns a running context without calling resume", async () => {
        const ctx = makeCtx("running");
        await expect(ensureAudioContextRunning(ctx)).resolves.toBe(ctx);
        expect(ctx.resume).not.toHaveBeenCalled();
    });

    it("resumes a suspended context and returns it once running", async () => {
        const ctx = makeCtx("suspended");
        await expect(ensureAudioContextRunning(ctx)).resolves.toBe(ctx);
        expect(ctx.resume).toHaveBeenCalledTimes(1);
        expect(ctx.state).toBe("running");
    });

    it("treats interrupted like suspended", async () => {
        const ctx = makeCtx("interrupted");
        await expect(ensureAudioContextRunning(ctx)).resolves.toBe(ctx);
        expect(ctx.resume).toHaveBeenCalledTimes(1);
    });

    it("returns null when resume resolves but state stays suspended", async () => {
        const ctx = makeCtx("suspended");
        ctx.resume = vi.fn(() => Promise.resolve());
        await expect(ensureAudioContextRunning(ctx)).resolves.toBe(null);
    });

    it("returns null when resume rejects", async () => {
        const ctx = makeCtx("suspended");
        ctx.resume = vi.fn(() => Promise.reject(new Error("no gesture")));
        await expect(ensureAudioContextRunning(ctx)).resolves.toBe(null);
    });

    it("returns null for missing context or missing resume", async () => {
        await expect(ensureAudioContextRunning(null)).resolves.toBe(null);
        await expect(ensureAudioContextRunning({ state: "suspended" })).resolves.toBe(null);
    });

    it("gives up when resume never settles", async () => {
        const ctx = makeCtx("suspended");
        ctx.resume = vi.fn(() => new Promise(() => {}));
        await expect(ensureAudioContextRunning(ctx, 10)).resolves.toBe(null);
    });
});

describe("decodeAudioDataCompat", () => {
    it("uses the promise form when available", async () => {
        const buffer = { duration: 1 };
        const ctx = { decodeAudioData: vi.fn(() => Promise.resolve(buffer)) };
        await expect(decodeAudioDataCompat(ctx, new ArrayBuffer(4))).resolves.toBe(buffer);
        expect(ctx.decodeAudioData).toHaveBeenCalledWith(expect.any(ArrayBuffer));
    });

    it("falls back to the callback form on older WebKit", async () => {
        const buffer = { duration: 2 };
        const ctx = {
            decodeAudioData(data, ok, err) {
                ok(buffer);
            },
        };
        await expect(decodeAudioDataCompat(ctx, new ArrayBuffer(4))).resolves.toBe(buffer);
    });

    it("rejects when decodeAudioData is unavailable", async () => {
        await expect(decodeAudioDataCompat({}, new ArrayBuffer(4))).rejects.toThrow("decodeAudioData unavailable");
    });
});

describe("decodeAudioArrayBuffer", () => {
    it("prefers OfflineAudioContext so no live context is needed", async () => {
        const buffer = { duration: 3 };
        const calls = [];
        class FakeOfflineAudioContext {
            constructor(channels, length, sampleRate) {
                calls.push([channels, length, sampleRate]);
                this.decodeAudioData = vi.fn(() => Promise.resolve(buffer));
            }
        }
        vi.stubGlobal("OfflineAudioContext", FakeOfflineAudioContext);
        const AudioContextSpy = vi.fn();
        vi.stubGlobal("AudioContext", AudioContextSpy);

        await expect(decodeAudioArrayBuffer(new ArrayBuffer(4))).resolves.toBe(buffer);
        expect(calls).toEqual([[1, 1, 44100]]);
        expect(AudioContextSpy).not.toHaveBeenCalled();
    });

    it("falls back to a throwaway AudioContext that gets closed", async () => {
        const buffer = { duration: 4 };
        const ctx = {
            decodeAudioData: vi.fn(() => Promise.resolve(buffer)),
            close: vi.fn(() => Promise.resolve()),
        };
        vi.stubGlobal(
            "AudioContext",
            vi.fn(function () {
                return ctx;
            })
        );
        vi.stubGlobal("webkitAudioContext", undefined);

        await expect(decodeAudioArrayBuffer(new ArrayBuffer(4))).resolves.toBe(buffer);
        expect(ctx.decodeAudioData).toHaveBeenCalled();
        expect(ctx.close).toHaveBeenCalled();
    });

    it("rejects when no Web Audio implementation exists", async () => {
        vi.stubGlobal("AudioContext", undefined);
        vi.stubGlobal("webkitAudioContext", undefined);
        await expect(decodeAudioArrayBuffer(new ArrayBuffer(4))).rejects.toThrow("Web Audio unavailable");
    });
});
