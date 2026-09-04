import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    isGeoWasmBundled,
    preloadGeoWasm,
    isGeoWasmReady,
    callGeoWasmJson,
    resetGeoWasmLoaderForTests,
} from "../../meshchatx/src/frontend/js/GeoWasmLoader.js";

describe("GeoWasmLoader", () => {
    beforeEach(() => {
        resetGeoWasmLoaderForTests();
        delete globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__;
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
        resetGeoWasmLoaderForTests();
    });

    it("reports bundled flag from test override", () => {
        globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ = false;
        expect(isGeoWasmBundled()).toBe(false);
        globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ = true;
        expect(isGeoWasmBundled()).toBe(true);
    });

    it("preloadGeoWasm resolves false when not bundled", async () => {
        globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ = false;
        await expect(preloadGeoWasm()).resolves.toBe(false);
    });

    it("preloadGeoWasm resolves false when WebAssembly is unavailable", async () => {
        globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ = true;
        vi.stubGlobal("WebAssembly", undefined);
        await expect(preloadGeoWasm()).resolves.toBe(false);
        expect(isGeoWasmReady()).toBe(false);
    });

    it("dedupes concurrent preloadGeoWasm into one load attempt (race)", async () => {
        globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ = true;
        let fetchCalls = 0;
        globalThis.fetch = vi.fn(async () => {
            fetchCalls += 1;
            await new Promise((r) => setTimeout(r, 20));
            return { ok: false, status: 404 };
        });

        const [a, b, c] = await Promise.all([preloadGeoWasm(), preloadGeoWasm(), preloadGeoWasm()]);
        expect(a).toBe(false);
        expect(b).toBe(false);
        expect(c).toBe(false);
        // One shared instantiate path: integrity.json then abort, not 3x full fan-out.
        expect(fetchCalls).toBeLessThanOrEqual(2);
        expect(fetchCalls).toBeGreaterThanOrEqual(1);
    });

    it("callGeoWasmJson returns null when export missing", () => {
        expect(callGeoWasmJson("meshchatxGeoParse", { text: "1,2" })).toBeNull();
    });

    it("callGeoWasmJson parses JSON string results", () => {
        globalThis.meshchatxGeoParse = () => JSON.stringify({ ok: true, lat: 1, lon: 2, kind: "wgs84" });
        expect(callGeoWasmJson("meshchatxGeoParse", { text: "1,2" })).toEqual({
            ok: true,
            lat: 1,
            lon: 2,
            kind: "wgs84",
        });
    });

    it("callGeoWasmJson returns error object from WASM ok:false", () => {
        globalThis.meshchatxGeoParse = () => ({ ok: false, error: "bad" });
        expect(callGeoWasmJson("meshchatxGeoParse", { text: "x" })).toEqual({ ok: false, error: "bad" });
    });

    it("removes stale wasm_exec script tag when Go is missing so retry can reinject", async () => {
        globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ = true;
        const stale = document.createElement("script");
        stale.id = "meshchatx-geo-wasm-exec";
        document.head.appendChild(stale);
        delete globalThis.Go;

        let sawExecFetch = false;
        globalThis.fetch = vi.fn(async (url) => {
            const u = String(url);
            if (u.includes("integrity.json")) {
                return {
                    ok: true,
                    json: async () => ({
                        wasm: "sha384-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        wasmExec:
                            "sha384-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    }),
                };
            }
            if (u.includes("wasm_exec.js")) {
                sawExecFetch = true;
                // Fail after proving we attempted reinject (SRI will fail or we abort).
                return { ok: false, status: 404 };
            }
            return { ok: false, status: 404 };
        });

        await expect(preloadGeoWasm()).resolves.toBe(false);
        expect(sawExecFetch).toBe(true);
        // Stale node was removed; failed inject should not leave a blocking tag without Go.
        const leftover = document.getElementById("meshchatx-geo-wasm-exec");
        expect(leftover === null || typeof globalThis.Go !== "undefined").toBe(true);
    });
});
