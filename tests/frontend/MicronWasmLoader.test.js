import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    invalidateNomadMicronWasmPreload,
    isMicronWasmBundled,
    preloadNomadMicronWasm,
} from "../../meshchatx/src/frontend/js/MicronWasmLoader.js";

describe("MicronWasmLoader.js", () => {
    let origBundledFlag;

    beforeEach(() => {
        origBundledFlag = globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__;
        invalidateNomadMicronWasmPreload();
        delete globalThis.micronConvert;
        delete globalThis.Go;
        document.getElementById("meshchatx-micron-wasm-exec")?.remove();
    });

    afterEach(() => {
        invalidateNomadMicronWasmPreload();
        delete globalThis.micronConvert;
        delete globalThis.Go;
        document.getElementById("meshchatx-micron-wasm-exec")?.remove();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
        if (origBundledFlag === undefined) {
            delete globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__;
        } else {
            globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = origBundledFlag;
        }
    });

    it("isMicronWasmBundled honors __MESHCHATX_TEST_MICRON_WASM_BUNDLED__", () => {
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = true;
        expect(isMicronWasmBundled()).toBe(true);
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = false;
        expect(isMicronWasmBundled()).toBe(false);
    });

    it("preloadNomadMicronWasm resolves false without bundling and does not fetch", async () => {
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = false;
        const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response());
        const ok = await preloadNomadMicronWasm();
        expect(ok).toBe(false);
        expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("preloadNomadMicronWasm resolves false when WebAssembly is unavailable", async () => {
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = true;
        vi.stubGlobal("WebAssembly", undefined);
        const ok = await preloadNomadMicronWasm();
        expect(ok).toBe(false);
    });

    it("preloadNomadMicronWasm resolves false when wasm_exec script fails to load", async () => {
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = true;
        const appendSpy = vi.spyOn(document.head, "appendChild").mockImplementation((node) => {
            if (node?.tagName === "SCRIPT" && typeof node.onerror === "function") {
                queueMicrotask(() => node.onerror());
            }
            return node;
        });
        try {
            const ok = await preloadNomadMicronWasm();
            expect(ok).toBe(false);
        } finally {
            appendSpy.mockRestore();
        }
    });

    it("preloadNomadMicronWasm resolves false when wasm_exec loads but Go is missing", async () => {
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = true;
        const appendSpy = vi.spyOn(document.head, "appendChild").mockImplementation((node) => {
            if (node?.tagName === "SCRIPT" && typeof node.onload === "function") {
                queueMicrotask(() => node.onload());
            }
            return node;
        });
        try {
            const ok = await preloadNomadMicronWasm();
            expect(ok).toBe(false);
        } finally {
            appendSpy.mockRestore();
        }
    });

    it("preloadNomadMicronWasm resolves false when WASM instantiation fails", async () => {
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = true;
        globalThis.Go = class {
            constructor() {
                this.importObject = {};
                this.run = vi.fn();
            }
        };

        const appendSpy = vi.spyOn(document.head, "appendChild").mockImplementation((node) => {
            if (node?.tagName === "SCRIPT" && typeof node.onload === "function") {
                queueMicrotask(() => node.onload());
            }
            return node;
        });

        vi.spyOn(globalThis, "fetch").mockResolvedValue({
            ok: true,
            arrayBuffer: async () => new ArrayBuffer(16),
            headers: new Headers({ "content-type": "application/wasm" }),
        });

        const streaming = vi
            .spyOn(WebAssembly, "instantiateStreaming")
            .mockRejectedValue(new Error("streaming failed"));
        const instantiate = vi.spyOn(WebAssembly, "instantiate").mockRejectedValue(new Error("bad wasm"));

        try {
            const ok = await preloadNomadMicronWasm();
            expect(ok).toBe(false);
            expect(streaming).toHaveBeenCalled();
            expect(instantiate).toHaveBeenCalled();
        } finally {
            appendSpy.mockRestore();
        }
    });

    it("preloadNomadMicronWasm can retry after invalidateNomadMicronWasmPreload", async () => {
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = true;
        globalThis.Go = class {
            constructor() {
                this.importObject = {};
                this.run = vi.fn();
            }
        };

        const appendSpy = vi.spyOn(document.head, "appendChild").mockImplementation((node) => {
            if (node?.tagName === "SCRIPT" && typeof node.onload === "function") {
                queueMicrotask(() => node.onload());
            }
            return node;
        });

        vi.spyOn(globalThis, "fetch").mockResolvedValue({
            ok: true,
            arrayBuffer: async () => new ArrayBuffer(16),
            headers: new Headers({ "content-type": "application/wasm" }),
        });

        vi.spyOn(WebAssembly, "instantiateStreaming").mockRejectedValue(new Error("streaming failed"));
        const instantiate = vi
            .spyOn(WebAssembly, "instantiate")
            .mockRejectedValueOnce(new Error("first"))
            .mockRejectedValueOnce(new Error("second"));

        try {
            expect(await preloadNomadMicronWasm()).toBe(false);
            invalidateNomadMicronWasmPreload();
            expect(await preloadNomadMicronWasm()).toBe(false);
            expect(instantiate).toHaveBeenCalledTimes(2);
        } finally {
            appendSpy.mockRestore();
        }
    });

    it("preloadNomadMicronWasm resolves true when micronConvert is already defined", async () => {
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = true;
        globalThis.micronConvert = vi.fn(() => "");
        expect(await preloadNomadMicronWasm()).toBe(true);
    });
});
