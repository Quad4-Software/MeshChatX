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

        // Mock crypto.subtle.digest to return hash matching embedded SRI for test data
        const mockWasmHash = __MICRON_WASM_SRI_WASM__?.replace("sha384-", "") || "";
        const mockExecHash = __MICRON_WASM_SRI_EXEC__?.replace("sha384-", "") || "";
        vi.stubGlobal("crypto", {
            subtle: {
                digest: vi.fn(async (algo, buf) => {
                    // Return different hash based on buffer size to distinguish wasm_exec.js vs wasm
                    const hash =
                        buf.byteLength < 1000
                            ? mockExecHash // wasm_exec.js is smaller
                            : mockWasmHash; // wasm is larger
                    // Convert base64 to ArrayBuffer
                    const binary = atob(hash);
                    const bytes = new Uint8Array(binary.length);
                    for (let i = 0; i < binary.length; i++) {
                        bytes[i] = binary.charCodeAt(i);
                    }
                    return bytes.buffer;
                }),
            },
        });

        vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
            const isWasm = url.includes(".wasm");
            return Promise.resolve({
                ok: true,
                arrayBuffer: async () => (isWasm ? new ArrayBuffer(4096) : new ArrayBuffer(500)),
                headers: new Headers({ "content-type": isWasm ? "application/wasm" : "application/javascript" }),
            });
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
            vi.unstubAllGlobals();
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

        // Mock crypto.subtle.digest to return hash matching embedded SRI for test data
        const mockWasmHash = __MICRON_WASM_SRI_WASM__?.replace("sha384-", "") || "";
        const mockExecHash = __MICRON_WASM_SRI_EXEC__?.replace("sha384-", "") || "";
        vi.stubGlobal("crypto", {
            subtle: {
                digest: vi.fn(async (algo, buf) => {
                    const hash = buf.byteLength < 1000 ? mockExecHash : mockWasmHash;
                    const binary = atob(hash);
                    const bytes = new Uint8Array(binary.length);
                    for (let i = 0; i < binary.length; i++) {
                        bytes[i] = binary.charCodeAt(i);
                    }
                    return bytes.buffer;
                }),
            },
        });

        vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
            const isWasm = url.includes(".wasm");
            return Promise.resolve({
                ok: true,
                arrayBuffer: async () => (isWasm ? new ArrayBuffer(4096) : new ArrayBuffer(500)),
                headers: new Headers({ "content-type": isWasm ? "application/wasm" : "application/javascript" }),
            });
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
            vi.unstubAllGlobals();
        }
    });

    it("preloadNomadMicronWasm resolves true when micronConvert is already defined", async () => {
        globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ = true;
        globalThis.micronConvert = vi.fn(() => "");
        expect(await preloadNomadMicronWasm()).toBe(true);
    });
});
