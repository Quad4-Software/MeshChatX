/**
 * Lazy-load geo-wasm (Go MGRS/UTM/OLC) for map coordinate formats.
 * Falls back silently when WebAssembly is unavailable or load fails.
 */

let resolvedPromise = null;
let integrityHashes = null;

async function computeSriHash(buf) {
    const hash = await crypto.subtle.digest("SHA-384", buf);
    const base64 = btoa(String.fromCharCode(...new Uint8Array(hash)));
    return `sha384-${base64}`;
}

/** True when WASM artifacts were present at Vite build time. */
export function isGeoWasmBundled() {
    if (typeof globalThis !== "undefined" && typeof globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ === "boolean") {
        return globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__;
    }
    return import.meta.env.VITE_GEO_WASM_BUNDLED === "true";
}

/** Reset loader state between tests. */
export function resetGeoWasmLoaderForTests() {
    resolvedPromise = null;
    integrityHashes = null;
    if (typeof document !== "undefined") {
        document.getElementById("meshchatx-geo-wasm-exec")?.remove();
    }
    delete globalThis.meshchatxGeoFormat;
    delete globalThis.meshchatxGeoParse;
    delete globalThis.meshchatxGeoLatLonToGrid;
    delete globalThis.Go;
}

function baseUrl() {
    const root = import.meta.env.BASE_URL || "/";
    return `${root.replace(/\/?$/, "/")}vendor/geo-wasm`;
}

async function getIntegrityHashes() {
    if (integrityHashes !== null) {
        return integrityHashes;
    }
    const embeddedWasm = typeof __GEO_WASM_SRI_WASM__ !== "undefined" ? __GEO_WASM_SRI_WASM__ : "";
    const embeddedExec = typeof __GEO_WASM_SRI_EXEC__ !== "undefined" ? __GEO_WASM_SRI_EXEC__ : "";
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
        throw new Error(`Geo WASM: SRI hash missing for ${name}. Refusing to load untrusted code.`);
    }
    const actualHash = await computeSriHash(buf);
    if (actualHash !== expectedHash) {
        throw new Error(`Geo WASM: SRI hash mismatch for ${name}. Possible tampering detected. Refusing to execute.`);
    }
}

async function injectScript(src, expectedHash) {
    const id = "meshchatx-geo-wasm-exec";
    const existing = document.getElementById(id);
    if (existing) {
        // Stale tag without Go (partial/failed prior load) must be replaced so retry works.
        if (typeof globalThis.Go !== "undefined") {
            return;
        }
        existing.remove();
    }
    const res = await fetch(src);
    if (!res.ok) {
        throw new Error(`Geo WASM: failed to fetch script ${src} (${res.status})`);
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
            s.remove();
            reject(new Error(`Geo WASM: failed to load script ${src}`));
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
        typeof globalThis.meshchatxGeoFormat === "function" &&
        typeof globalThis.meshchatxGeoParse === "function" &&
        typeof globalThis.meshchatxGeoLatLonToGrid === "function"
    );
}

async function instantiateOnce() {
    if (typeof WebAssembly === "undefined") {
        throw new Error("Geo WASM: WebAssembly is not available");
    }
    const root = baseUrl();
    const integrity = await getIntegrityHashes();
    if (!integrity?.wasmExec) {
        throw new Error("Geo WASM: wasm_exec SRI missing (build without WASM vendor files?)");
    }

    if (typeof globalThis.Go === "undefined") {
        await injectScript(`${root}/wasm_exec.js`, integrity.wasmExec);
    }
    if (typeof globalThis.Go === "undefined") {
        throw new Error("Geo WASM: Go runtime missing after wasm_exec.js load");
    }
    const go = new globalThis.Go();

    const res = await fetch(`${root}/geo.wasm`);
    if (!res.ok) {
        throw new Error(`Geo WASM: fetch failed (${res.status})`);
    }
    const buf = await res.arrayBuffer();
    await verifySri(buf, integrity?.wasm, "geo.wasm");
    await instantiateWasmBuffer(buf, go);

    if (!isReady()) {
        throw new Error("Geo WASM: exports were not registered");
    }
}

/**
 * Ensures geo WASM is initialized.
 * Resolves true when exports are callable, false when unavailable or failed.
 */
export function preloadGeoWasm() {
    if (!isGeoWasmBundled()) {
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

export function isGeoWasmReady() {
    return isReady();
}

/**
 * Call a WASM JSON export and parse the result string.
 * Returns null on any failure so callers can fall back.
 */
export function callGeoWasmJson(fnName, payload) {
    try {
        const fn = globalThis[fnName];
        if (typeof fn !== "function") {
            return null;
        }
        const raw = fn(JSON.stringify(payload ?? {}));
        if (raw == null) {
            return null;
        }
        if (typeof raw === "object" && raw.ok === false) {
            return raw;
        }
        if (typeof raw !== "string") {
            return null;
        }
        return JSON.parse(raw);
    } catch (e) {
        console.warn("Geo WASM call failed:", e);
        return null;
    }
}
