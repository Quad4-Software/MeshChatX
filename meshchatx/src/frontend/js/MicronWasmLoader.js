/**
 * Lazy-load micron-parser-go WASM (see https://github.com/Quad4-Software/Micron-Parser-Go ).
 * Requires wasm_exec.js from Go and micron-parser-go.wasm under /vendor/micron-parser-go/.
 * Files are fetched at production build time (scripts/fetch-micron-wasm.mjs); omitted builds set VITE_MICRON_WASM_BUNDLED=false.
 */

let resolvedPromise = null;
let integrityHashes = null;

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
    // Use build-time embedded hashes as primary trusted source (tamper-proof)
    const embeddedWasm = typeof __MICRON_WASM_SRI_WASM__ !== "undefined" ? __MICRON_WASM_SRI_WASM__ : "";
    const embeddedExec = typeof __MICRON_WASM_SRI_EXEC__ !== "undefined" ? __MICRON_WASM_SRI_EXEC__ : "";
    if (embeddedWasm && embeddedExec) {
        integrityHashes = { wasm: embeddedWasm, wasmExec: embeddedExec };
        return integrityHashes;
    }
    // Fallback: fetch from server (less secure, but allows development builds)
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
    // Fetch and verify SRI before injecting
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

async function instantiateOnce() {
    if (typeof WebAssembly === "undefined") {
        throw new Error("Micron WASM: WebAssembly is not available");
    }
    const root = baseUrl();
    const integrity = await getIntegrityHashes();

    await injectScript(`${root}/wasm_exec.js`, integrity?.wasmExec);
    if (typeof globalThis.Go === "undefined") {
        throw new Error("Micron WASM: Go runtime missing after wasm_exec.js load");
    }
    const wasmUrl = `${root}/micron-parser-go.wasm`;
    const go = new globalThis.Go();
    let result;
    try {
        // Try streaming first
        const res = await fetch(wasmUrl);
        if (!res.ok) {
            throw new Error(`Micron WASM: fetch failed (${res.status})`);
        }
        const buf = await res.arrayBuffer();
        await verifySri(buf, integrity?.wasm, "micron-parser-go.wasm");
        result = await WebAssembly.instantiateStreaming(
            new Response(buf, { headers: { "content-type": "application/wasm" } }),
            go.importObject
        );
    } catch {
        // Fallback to buffer instantiation
        const buf = await fetch(wasmUrl).then((r) => {
            if (!r.ok) {
                throw new Error(`Micron WASM: fetch failed (${r.status})`);
            }
            return r.arrayBuffer();
        });
        await verifySri(buf, integrity?.wasm, "micron-parser-go.wasm");
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
