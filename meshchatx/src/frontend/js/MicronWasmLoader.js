/**
 * Lazy-load micron-parser-go WASM (see https://github.com/Quad4-Software/Micron-Parser-Go ).
 * Requires wasm_exec.js from Go and micron-parser-go.wasm under /vendor/micron-parser-go/,
 * or a runtime WASM override from IndexedDB (see MicronWasmRuntimeOverride.js).
 * Build-time fetch: scripts/fetch-micron-wasm.mjs; omitted builds set VITE_MICRON_WASM_BUNDLED=false.
 */

import { getMicronWasmRuntimeOverride } from "./MicronWasmRuntimeOverride.js";

let resolvedPromise = null;
let integrityHashes = null;

let resolvedOverridePromise = null;
function readRuntimeOverrideCached() {
    if (resolvedOverridePromise) {
        return resolvedOverridePromise;
    }
    if (typeof globalThis !== "undefined" && globalThis.__MESHCHATX_TEST_MICRON_WASM_OVERRIDE__ !== undefined) {
        const v = globalThis.__MESHCHATX_TEST_MICRON_WASM_OVERRIDE__;
        resolvedOverridePromise = Promise.resolve(v === false ? null : v);
        return resolvedOverridePromise;
    }
    resolvedOverridePromise = (async () => {
        try {
            return await getMicronWasmRuntimeOverride();
        } catch (e) {
            console.warn("Micron WASM: could not read runtime override", e);
            return null;
        }
    })();
    return resolvedOverridePromise;
}

/** Computes SHA-384 hash of ArrayBuffer for SRI verification. */
async function computeSriHash(buf) {
    const hash = await crypto.subtle.digest("SHA-384", buf);
    const base64 = btoa(String.fromCharCode(...new Uint8Array(hash)));
    return `sha384-${base64}`;
}

/** Injects CSS required for ForceMonospace mode when using WASM. Safe to call multiple times. */
function injectMicronWasmStyles() {
    if (document.getElementById("micron-wasm-monospace-styles")) {
        return;
    }
    const styleEl = document.createElement("style");
    styleEl.id = "micron-wasm-monospace-styles";
    styleEl.textContent = `
        .Mu-nl {
            cursor: pointer;
        }
        .Mu-mnt {
            display: inline-block;
            min-width: 1ch;
            text-align: center;
            white-space: pre;
            text-decoration: inherit;
            font-variant-numeric: tabular-nums;
        }
        .Mu-mws {
            text-decoration: inherit;
            display: inline;
        }
    `;
    document.head.appendChild(styleEl);
}

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

/** Returns SRI hashes embedded at build time (primary) or fetched from integrity.json (fallback). */
async function getIntegrityHashes() {
    if (integrityHashes !== null) {
        return integrityHashes;
    }
    const embeddedWasm = typeof __MICRON_WASM_SRI_WASM__ !== "undefined" ? __MICRON_WASM_SRI_WASM__ : "";
    const embeddedExec = typeof __MICRON_WASM_SRI_EXEC__ !== "undefined" ? __MICRON_WASM_SRI_EXEC__ : "";
    if (embeddedWasm && embeddedExec) {
        integrityHashes = { wasm: embeddedWasm, wasmExec: embeddedExec };
        return integrityHashes;
    }
    try {
        const res = await fetch(`${baseUrl()}/integrity.json`);
        if (!res.ok) return null;
        integrityHashes = await res.json();
        return integrityHashes;
    } catch {
        return null;
    }
}

/** Verifies SRI hash of buffer against expected hash. Throws if mismatch or no hash provided. */
async function verifySri(buf, expectedHash, name) {
    if (!expectedHash) {
        throw new Error(`Micron WASM: SRI hash missing for ${name}. Refusing to load untrusted code.`);
    }
    const actualHash = await computeSriHash(buf);
    if (actualHash !== expectedHash) {
        throw new Error(
            `Micron WASM: SRI hash mismatch for ${name}. Possible tampering detected. Refusing to execute.`
        );
    }
}

async function injectScript(src, expectedHash) {
    const id = "meshchatx-micron-wasm-exec";
    if (document.getElementById(id)) {
        return;
    }
    const res = await fetch(src);
    if (!res.ok) {
        throw new Error(`Micron WASM: failed to fetch script ${src} (${res.status})`);
    }
    const buf = await res.arrayBuffer();
    await verifySri(buf, expectedHash, "wasm_exec.js");
    const blob = new Blob([buf], { type: "application/javascript" });
    const blobUrl = URL.createObjectURL(blob);
    return new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.id = id;
        s.async = true;
        s.src = blobUrl;
        s.onload = () => {
            URL.revokeObjectURL(blobUrl);
            resolve();
        };
        s.onerror = () => {
            URL.revokeObjectURL(blobUrl);
            reject(new Error(`Micron WASM: failed to load script ${src}`));
        };
        document.head.appendChild(s);
    });
}

/**
 * Tears down wasm_exec script tag and globals so WASM can be reloaded (e.g. after override change).
 */
export function teardownNomadMicronWasmRuntime() {
    document.getElementById("meshchatx-micron-wasm-exec")?.remove();
    try {
        delete globalThis.micronConvert;
    } catch {
        globalThis.micronConvert = undefined;
    }
    try {
        delete globalThis.Go;
    } catch {
        globalThis.Go = undefined;
    }
}

/**
 * Restricts the exported Go function to string/boolean inputs and string output for the Micron HTML path.
 * Full process isolation is not available in-browser; output is still sanitized by MicronParser.
 */
function wrapMicronConvertForNarrowJsSurface() {
    const inner = globalThis.micronConvert;
    if (typeof inner !== "function" || inner.__meshchatxMicronWasmWrapped) {
        return;
    }
    const wrapped = function (markup, darkTheme, forceMonospace) {
        return inner(String(markup ?? ""), darkTheme === true, forceMonospace === true);
    };
    wrapped.__meshchatxMicronWasmWrapped = true;
    globalThis.micronConvert = wrapped;
}

async function instantiateWasmBuffer(buf, go) {
    let result;
    try {
        result = await WebAssembly.instantiateStreaming(
            new Response(buf, { headers: { "content-type": "application/wasm" } }),
            go.importObject
        );
    } catch {
        result = await WebAssembly.instantiate(buf, go.importObject);
    }
    go.run(result.instance);
}

async function instantiateOnce() {
    if (typeof WebAssembly === "undefined") {
        throw new Error("Micron WASM: WebAssembly is not available");
    }
    const root = baseUrl();
    const override = await readRuntimeOverrideCached();
    const integrity = await getIntegrityHashes();

    if (!integrity?.wasmExec) {
        throw new Error("Micron WASM: wasm_exec SRI missing (build without WASM vendor files?)");
    }

    await injectScript(`${root}/wasm_exec.js`, integrity.wasmExec);
    if (typeof globalThis.Go === "undefined") {
        throw new Error("Micron WASM: Go runtime missing after wasm_exec.js load");
    }
    const go = new globalThis.Go();

    if (override && override.wasmBytes && override.wasmSri) {
        await verifySri(override.wasmBytes, override.wasmSri, "micron-parser-go.wasm (runtime override)");
        await instantiateWasmBuffer(override.wasmBytes, go);
    } else {
        const wasmUrl = `${root}/micron-parser-go.wasm`;
        const res = await fetch(wasmUrl);
        if (!res.ok) {
            throw new Error(`Micron WASM: fetch failed (${res.status})`);
        }
        const buf = await res.arrayBuffer();
        await verifySri(buf, integrity?.wasm, "micron-parser-go.wasm");
        await instantiateWasmBuffer(buf, go);
    }

    if (typeof globalThis.micronConvert !== "function") {
        throw new Error("Micron WASM: micronConvert was not registered");
    }
    wrapMicronConvertForNarrowJsSurface();
}

export function invalidateNomadMicronWasmPreload() {
    resolvedPromise = null;
    integrityHashes = null;
    resolvedOverridePromise = null;
    teardownNomadMicronWasmRuntime();
}

/**
 * Call after installing or clearing a runtime WASM override so the next preload re-reads IndexedDB.
 */
export function refreshMicronWasmRuntimeOverrideCache() {
    resolvedOverridePromise = null;
}

/**
 * Ensures micron-parser-go WASM is initialized; resolves true when micronConvert is callable.
 */
export function preloadNomadMicronWasm() {
    if (!isMicronWasmBundled()) {
        return Promise.resolve(false);
    }
    if (typeof globalThis.micronConvert === "function") {
        injectMicronWasmStyles();
        return Promise.resolve(true);
    }
    if (resolvedPromise === null) {
        resolvedPromise = (async () => {
            try {
                await instantiateOnce();
                const ok = typeof globalThis.micronConvert === "function";
                if (ok) injectMicronWasmStyles();
                return ok;
            } catch (e) {
                console.warn(e);
                resolvedPromise = null;
                return false;
            }
        })();
    }
    return resolvedPromise;
}
