/**
 * Lazy-load micron-parser-go WASM (see https://github.com/Quad4-Software/Micron-Parser-Go ).
 * Requires wasm_exec.js from Go and micron-parser-go.wasm under /vendor/micron-parser-go/.
 * Files are fetched at production build time (scripts/fetch-micron-wasm.mjs); omitted builds set VITE_MICRON_WASM_BUNDLED=false.
 */

let resolvedPromise = null;

/** True when WASM artifacts were present at Vite build time (not runtime probing). */
export function isMicronWasmBundled() {
    if (typeof globalThis !== "undefined" && typeof globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__ === "boolean") {
        return globalThis.__MESHCHATX_TEST_MICRON_WASM_BUNDLED__;
    }
    return import.meta.env.VITE_MICRON_WASM_BUNDLED === "true";
}

function baseUrl() {
    const root = import.meta.env.BASE_URL || "/";
    return `${root.replace(/\/?$/, "/")}vendor/micron-parser-go`;
}

function injectScript(src) {
    const id = "meshchatx-micron-wasm-exec";
    if (document.getElementById(id)) {
        return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.id = id;
        s.async = true;
        s.src = src;
        s.onload = () => resolve();
        s.onerror = () => reject(new Error(`Micron WASM: failed to load script ${src}`));
        document.head.appendChild(s);
    });
}

async function instantiateOnce() {
    if (typeof WebAssembly === "undefined") {
        throw new Error("Micron WASM: WebAssembly is not available");
    }
    const root = baseUrl();
    await injectScript(`${root}/wasm_exec.js`);
    if (typeof globalThis.Go === "undefined") {
        throw new Error("Micron WASM: Go runtime missing after wasm_exec.js load");
    }
    const wasmUrl = `${root}/micron-parser-go.wasm`;
    const go = new globalThis.Go();
    let result;
    try {
        result = await WebAssembly.instantiateStreaming(fetch(wasmUrl), go.importObject);
    } catch {
        const buf = await fetch(wasmUrl).then((r) => {
            if (!r.ok) {
                throw new Error(`Micron WASM: fetch failed (${r.status})`);
            }
            return r.arrayBuffer();
        });
        result = await WebAssembly.instantiate(buf, go.importObject);
    }
    go.run(result.instance);
    if (typeof globalThis.micronConvert !== "function") {
        throw new Error("Micron WASM: micronConvert was not registered");
    }
}

export function invalidateNomadMicronWasmPreload() {
    resolvedPromise = null;
}

/**
 * Ensures micron-parser-go WASM is initialized; resolves true when micronConvert is callable.
 */
export function preloadNomadMicronWasm() {
    if (!isMicronWasmBundled()) {
        return Promise.resolve(false);
    }
    if (typeof globalThis.micronConvert === "function") {
        return Promise.resolve(true);
    }
    if (resolvedPromise === null) {
        resolvedPromise = (async () => {
            try {
                await instantiateOnce();
                return typeof globalThis.micronConvert === "function";
            } catch (e) {
                console.warn(e);
                resolvedPromise = null;
                return false;
            }
        })();
    }
    return resolvedPromise;
}
