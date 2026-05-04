import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    WASM_FILENAME,
    clearMicronWasmRuntimeOverride,
    computeWasmSriSha384,
    fetchWasmFromGitHubReleaseVerified,
    getMicronWasmRuntimeOverride,
    parseShasums256ForFilename,
    setMicronWasmRuntimeOverride,
    sha256HexOfBuffer,
} from "../../meshchatx/src/frontend/js/MicronWasmRuntimeOverride.js";
import {
    invalidateNomadMicronWasmPreload,
    refreshMicronWasmRuntimeOverrideCache,
} from "../../meshchatx/src/frontend/js/MicronWasmLoader.js";

describe("MicronWasmRuntimeOverride.js", () => {
    beforeEach(async () => {
        await clearMicronWasmRuntimeOverride();
        refreshMicronWasmRuntimeOverrideCache();
        invalidateNomadMicronWasmPreload();
    });

    afterEach(async () => {
        await clearMicronWasmRuntimeOverride();
        refreshMicronWasmRuntimeOverrideCache();
        invalidateNomadMicronWasmPreload();
        vi.restoreAllMocks();
    });

    it("parseShasums256ForFilename reads hex line", () => {
        const text = "c2b0f7de7f241719b54f99b12dc8215e262bdbecb8a5b2a25de3848408aa44cb  micron-parser-go.wasm\n";
        expect(parseShasums256ForFilename(text, WASM_FILENAME)).toBe(
            "c2b0f7de7f241719b54f99b12dc8215e262bdbecb8a5b2a25de3848408aa44cb"
        );
    });

    it("parseShasums256ForFilename supports BSD asterisk prefix", () => {
        const text = "aa".repeat(32) + " *micron-parser-go.wasm\n";
        expect(parseShasums256ForFilename(text, WASM_FILENAME)).toBe("aa".repeat(32));
    });

    it("parseShasums256ForFilename returns null when filename missing", () => {
        expect(parseShasums256ForFilename("abcd".repeat(16) + "  other.bin\n", WASM_FILENAME)).toBe(null);
    });

    it("setMicronWasmRuntimeOverride round-trips via IndexedDB", async () => {
        const wasmBytes = new Uint8Array(5000).fill(7).buffer;
        const wasmSri = await computeWasmSriSha384(wasmBytes);
        await setMicronWasmRuntimeOverride({
            source: "upload",
            releaseTag: "test.wasm",
            wasmSri,
            wasmBytes,
            expectedSha256Hex: null,
        });
        const got = await getMicronWasmRuntimeOverride();
        expect(got).not.toBeNull();
        expect(got.source).toBe("upload");
        expect(got.releaseTag).toBe("test.wasm");
        expect(got.wasmSri).toBe(wasmSri);
        expect(got.wasmBytes.byteLength).toBe(5000);
    });

    it("fetchWasmFromGitHubReleaseVerified rejects hash mismatch", async () => {
        const wasmBytes = new Uint8Array(5000).fill(9).buffer;
        const expectedHex = await sha256HexOfBuffer(wasmBytes);
        const wrongHex = "0".repeat(64);
        const sums = `${wrongHex}  ${WASM_FILENAME}\n`;
        vi.stubGlobal(
            "fetch",
            vi.fn((url) => {
                const u = String(url);
                if (u.includes("micron-parser-go-release") && u.includes("asset=SHASUMS256.txt")) {
                    return Promise.resolve(new Response(sums, { status: 200 }));
                }
                if (u.includes("micron-parser-go-release") && u.includes("asset=micron-parser-go.wasm")) {
                    return Promise.resolve(new Response(wasmBytes, { status: 200 }));
                }
                return Promise.resolve(new Response("", { status: 404 }));
            })
        );
        await expect(fetchWasmFromGitHubReleaseVerified("v9.9.9")).rejects.toThrow(/SHA-256 mismatch/);
    });

    it("fetchWasmFromGitHubReleaseVerified succeeds when SHASUMS matches WASM", async () => {
        const wasmBytes = new Uint8Array(5000).fill(3).buffer;
        const expectedHex = await sha256HexOfBuffer(wasmBytes);
        const sums = `${expectedHex}  ${WASM_FILENAME}\n`;
        vi.stubGlobal(
            "fetch",
            vi.fn((url) => {
                const u = String(url);
                if (u.includes("micron-parser-go-release") && u.includes("asset=SHASUMS256.txt")) {
                    return Promise.resolve(new Response(sums, { status: 200 }));
                }
                if (u.includes("micron-parser-go-release") && u.includes("asset=micron-parser-go.wasm")) {
                    return Promise.resolve(new Response(wasmBytes, { status: 200 }));
                }
                return Promise.resolve(new Response("", { status: 404 }));
            })
        );
        const rec = await fetchWasmFromGitHubReleaseVerified("v1.0.0");
        expect(rec.source).toBe("github");
        expect(rec.releaseTag).toBe("v1.0.0");
        expect(rec.expectedSha256Hex).toBe(expectedHex);
        expect(rec.wasmBytes.byteLength).toBe(5000);
        expect(rec.wasmSri).toMatch(/^sha384-/);
    });

    it("fetchWasmFromGitHubReleaseVerified maps network failure to readable error", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn(() => Promise.reject(new TypeError("Failed to fetch")))
        );
        await expect(fetchWasmFromGitHubReleaseVerified("v1.0.0")).rejects.toThrow(/could not fetch release metadata/i);
    });

    it("fetchWasmFromGitHubReleaseVerified handles missing SHASUMS line", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn((url) => {
                if (String(url).includes("asset=SHASUMS256.txt")) {
                    return Promise.resolve(new Response("deadbeef\n", { status: 200 }));
                }
                return Promise.resolve(new Response("", { status: 404 }));
            })
        );
        await expect(fetchWasmFromGitHubReleaseVerified("v1.0.0")).rejects.toThrow(/not listed/);
    });
});
