/**
 * Lazy-load visualiser-wasm (Go) for network visualiser hot paths.
 * Falls back silently when WebAssembly is unavailable or load fails.
 * Artifacts live under /vendor/visualiser-wasm/ (built via task build:visualiser-wasm).
 */

let resolvedPromise: Promise<boolean> | null = null;
let integrityHashes: { wasm?: string; wasmExec?: string } | null = null;

/** Computes SHA-384 hash of ArrayBuffer for SRI verification. */
async function computeSriHash(buf) {
    const hash = await crypto.subtle.digest("SHA-384", buf);
    const base64 = btoa(String.fromCharCode(...new Uint8Array(hash)));
    return `sha384-${base64}`;
}

/** True when WASM artifacts were present at Vite build time. */
export function isVisualiserWasmBundled() {
    if (
        typeof globalThis !== "undefined" &&
        typeof globalThis.__MESHCHATX_TEST_VISUALISER_WASM_BUNDLED__ === "boolean"
    ) {
        return globalThis.__MESHCHATX_TEST_VISUALISER_WASM_BUNDLED__;
    }
    return import.meta.env.VITE_VISUALISER_WASM_BUNDLED === "true";
}

function baseUrl() {
    const root = import.meta.env.BASE_URL || "/";
    return `${root.replace(/\/?$/, "/")}vendor/visualiser-wasm`;
}

async function getIntegrityHashes() {
    if (integrityHashes !== null) {
        return integrityHashes;
    }
    const embeddedWasm = typeof __VISUALISER_WASM_SRI_WASM__ !== "undefined" ? __VISUALISER_WASM_SRI_WASM__ : "";
    const embeddedExec = typeof __VISUALISER_WASM_SRI_EXEC__ !== "undefined" ? __VISUALISER_WASM_SRI_EXEC__ : "";
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

async function verifySri(buf, expectedHash, name) {
    if (!expectedHash) {
        throw new Error(`Visualiser WASM: SRI hash missing for ${name}. Refusing to load untrusted code.`);
    }
    const actualHash = await computeSriHash(buf);
    if (actualHash !== expectedHash) {
        throw new Error(
            `Visualiser WASM: SRI hash mismatch for ${name}. Possible tampering detected. Refusing to execute.`
        );
    }
}

async function injectScript(src, expectedHash) {
    const id = "meshchatx-visualiser-wasm-exec";
    if (document.getElementById(id)) {
        return;
    }
    const res = await fetch(src);
    if (!res.ok) {
        throw new Error(`Visualiser WASM: failed to fetch script ${src} (${res.status})`);
    }
    const buf = await res.arrayBuffer();
    await verifySri(buf, expectedHash, "wasm_exec.js");
    const blob = new Blob([buf], { type: "application/javascript" });
    const blobUrl = URL.createObjectURL(blob);
    return new Promise<void>((resolve, reject) => {
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
            reject(new Error(`Visualiser WASM: failed to load script ${src}`));
        };
        document.head.appendChild(s);
    });
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

function isReady() {
    return (
        typeof globalThis.meshchatxVisualiserBuildPathGraph === "function" &&
        typeof globalThis.meshchatxVisualiserBuildFullGraph === "function" &&
        typeof globalThis.meshchatxVisualiserLayout === "function" &&
        typeof globalThis.meshchatxVisualiserPathHashes === "function" &&
        typeof globalThis.meshchatxVisualiserDedupeIcons === "function"
    );
}

/** True when WASM scene exports for the WebGL renderer are registered. */
export function isVisualiserWebGLSceneReady() {
    return (
        isReady() &&
        typeof globalThis.meshchatxVisualiserSceneSet === "function" &&
        typeof globalThis.meshchatxVisualiserSceneGetDrawBuffers === "function" &&
        typeof globalThis.meshchatxVisualiserSceneTick === "function" &&
        typeof globalThis.meshchatxVisualiserScenePick === "function"
    );
}

async function instantiateOnce() {
    if (typeof WebAssembly === "undefined") {
        throw new Error("Visualiser WASM: WebAssembly is not available");
    }
    const root = baseUrl();
    const integrity = await getIntegrityHashes();
    if (!integrity?.wasmExec) {
        throw new Error("Visualiser WASM: wasm_exec SRI missing (build without WASM vendor files?)");
    }

    if (typeof globalThis.Go === "undefined") {
        await injectScript(`${root}/wasm_exec.js`, integrity.wasmExec);
    }
    if (typeof globalThis.Go === "undefined") {
        throw new Error("Visualiser WASM: Go runtime missing after wasm_exec.js load");
    }
    const go = new globalThis.Go();

    const wasmUrl = `${root}/visualiser.wasm`;
    const res = await fetch(wasmUrl);
    if (!res.ok) {
        throw new Error(`Visualiser WASM: fetch failed (${res.status})`);
    }
    const buf = await res.arrayBuffer();
    await verifySri(buf, integrity?.wasm, "visualiser.wasm");
    await instantiateWasmBuffer(buf, go);

    if (!isReady()) {
        throw new Error("Visualiser WASM: exports were not registered");
    }
}

/**
 * Ensures visualiser WASM is initialized.
 * Resolves true when exports are callable, false when unavailable or failed.
 */
export function preloadVisualiserWasm() {
    if (!isVisualiserWasmBundled()) {
        return Promise.resolve(false);
    }
    if (isReady()) {
        return Promise.resolve(true);
    }
    if (resolvedPromise === null) {
        resolvedPromise = (async () => {
            try {
                await instantiateOnce();
                return isReady();
            } catch (e) {
                console.warn(e);
                resolvedPromise = null;
                return false;
            }
        })();
    }
    return resolvedPromise;
}

export function isVisualiserWasmReady() {
    return isReady();
}

/**
 * Call a WASM JSON export and parse the result string.
 * Returns null on any failure so callers can fall back to JS.
 */
export function callVisualiserWasmJson(fnName, ...args) {
    try {
        const fn = globalThis[fnName];
        if (typeof fn !== "function") {
            return null;
        }
        const raw = fn(...args);
        if (raw == null) {
            return null;
        }
        if (typeof raw === "object" && raw.ok === false) {
            console.warn("Visualiser WASM error:", raw.error);
            return null;
        }
        if (typeof raw !== "string") {
            return null;
        }
        return JSON.parse(raw);
    } catch (e) {
        console.warn("Visualiser WASM call failed:", e);
        return null;
    }
}
