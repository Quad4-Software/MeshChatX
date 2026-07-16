import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    isVisualiserWasmBundled,
    preloadVisualiserWasm,
    isVisualiserWasmReady,
    callVisualiserWasmJson,
} from "@/js/VisualiserWasmLoader.js";

describe("VisualiserWasmLoader", () => {
    beforeEach(() => {
        document.getElementById("meshchatx-visualiser-wasm-exec")?.remove();
        delete globalThis.__MESHCHATX_TEST_VISUALISER_WASM_BUNDLED__;
        delete globalThis.meshchatxVisualiserBuildPathGraph;
        delete globalThis.meshchatxVisualiserPathHashes;
        delete globalThis.meshchatxVisualiserDedupeIcons;
        delete globalThis.Go;
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
        document.getElementById("meshchatx-visualiser-wasm-exec")?.remove();
    });

    it("reports bundled flag from test override", () => {
        globalThis.__MESHCHATX_TEST_VISUALISER_WASM_BUNDLED__ = false;
        expect(isVisualiserWasmBundled()).toBe(false);
        globalThis.__MESHCHATX_TEST_VISUALISER_WASM_BUNDLED__ = true;
        expect(isVisualiserWasmBundled()).toBe(true);
    });

    it("preloadVisualiserWasm resolves false when not bundled", async () => {
        globalThis.__MESHCHATX_TEST_VISUALISER_WASM_BUNDLED__ = false;
        await expect(preloadVisualiserWasm()).resolves.toBe(false);
    });

    it("preloadVisualiserWasm resolves false when WebAssembly is unavailable", async () => {
        globalThis.__MESHCHATX_TEST_VISUALISER_WASM_BUNDLED__ = true;
        vi.stubGlobal("WebAssembly", undefined);
        await expect(preloadVisualiserWasm()).resolves.toBe(false);
        expect(isVisualiserWasmReady()).toBe(false);
    });

    it("callVisualiserWasmJson returns null when export missing", () => {
        expect(callVisualiserWasmJson("meshchatxVisualiserBuildPathGraph", "{}")).toBeNull();
    });

    it("callVisualiserWasmJson parses JSON string results", () => {
        globalThis.meshchatxVisualiserPathHashes = () => JSON.stringify(["aa", "bb"]);
        expect(callVisualiserWasmJson("meshchatxVisualiserPathHashes", "[]", 4)).toEqual(["aa", "bb"]);
    });

    it("callVisualiserWasmJson returns null on export error object", () => {
        globalThis.meshchatxVisualiserPathHashes = () => ({ ok: false, error: "bad" });
        expect(callVisualiserWasmJson("meshchatxVisualiserPathHashes", "[]")).toBeNull();
    });
});
