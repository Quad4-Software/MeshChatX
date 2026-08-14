import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
    clearMicronWasmRuntimeOverride,
    computeWasmSriSha384,
    getMicronWasmRuntimeOverride,
    setMicronWasmRuntimeOverride,
} from "../../meshchatx/src/frontend/js/MicronWasmRuntimeOverride.js";
import { refreshMicronWasmRuntimeOverrideCache } from "../../meshchatx/src/frontend/js/MicronWasmLoader.js";

describe("MicronWasmRuntimeOverride.js", () => {
    beforeEach(async () => {
        await clearMicronWasmRuntimeOverride();
        refreshMicronWasmRuntimeOverrideCache();
    });

    afterEach(async () => {
        await clearMicronWasmRuntimeOverride();
        refreshMicronWasmRuntimeOverrideCache();
    });

    it("setMicronWasmRuntimeOverride round-trips via IndexedDB", async () => {
        const wasmBytes = new Uint8Array(4096).fill(7).buffer;
        const wasmSri = await computeWasmSriSha384(wasmBytes);
        await setMicronWasmRuntimeOverride({
            source: "upload",
            releaseTag: "custom.wasm",
            wasmSri,
            wasmBytes,
            expectedSha256Hex: null,
        });
        const got = await getMicronWasmRuntimeOverride();
        expect(got).not.toBeNull();
        expect(got.releaseTag).toBe("custom.wasm");
        expect(got.wasmSri).toBe(wasmSri);
        expect(got.wasmBytes.byteLength).toBe(4096);
    });
});
