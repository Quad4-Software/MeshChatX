const codec2ScriptPaths = [
    "/assets/js/codec2-emscripten/c2enc.js",
    "/assets/js/codec2-emscripten/c2dec.js",
    "/assets/js/codec2-emscripten/sox.js",
    "/assets/js/codec2-emscripten/codec2-lib.js",
    "/assets/js/codec2-emscripten/wav-encoder.js",
    "/assets/js/codec2-emscripten/codec2-microphone-recorder.js",
];

let loadPromise = null;
let resolvedOk = false;
let integrityHashes = null;

/** Computes SHA-384 hash of ArrayBuffer for SRI verification. */
async function computeSriHash(buf) {
    const hash = await crypto.subtle.digest("SHA-384", buf);
    const base64 = btoa(String.fromCharCode(...new Uint8Array(hash)));
    return `sha384-${base64}`;
}

/** Loads integrity.json. Returns null if not available. */
async function loadIntegrityHashes() {
    if (integrityHashes !== null) return integrityHashes;
    try {
        const res = await fetch("/assets/js/codec2-emscripten/integrity.json");
        if (!res.ok) return null;
        const data = await res.json();
        integrityHashes = data.files || {};
        return integrityHashes;
    } catch {
        return null;
    }
}

/** Verifies SRI hash. Throws if mismatch or missing when required. */
async function verifySri(buf, expectedHash, name) {
    if (!expectedHash) {
        throw new Error(`Codec2: SRI hash missing for ${name}. Refusing to load untrusted code.`);
    }
    const actualHash = await computeSriHash(buf);
    if (actualHash !== expectedHash) {
        throw new Error(`Codec2: SRI hash mismatch for ${name}. Possible tampering detected.`);
    }
}

async function injectScript(src) {
    if (typeof document === "undefined") {
        return Promise.resolve();
    }

    const attrName = "data-codec2-src";
    const loadedAttr = "data-codec2-loaded";
    const existing = document.querySelector(`script[${attrName}="${src}"]`);

    if (existing) {
        if (existing.getAttribute(loadedAttr) === "true") {
            return Promise.resolve();
        }
        return new Promise((resolve, reject) => {
            existing.addEventListener("load", () => resolve(), { once: true });
            existing.addEventListener("error", () => reject(new Error(`Failed to load ${src}`)), { once: true });
        });
    }

    // Fetch, verify SRI, then inject as blob
    const integrity = await loadIntegrityHashes();
    const filename = src.split("/").pop();
    const expectedHash = integrity?.[filename];

    const res = await fetch(src);
    if (!res.ok) {
        throw new Error(`Codec2: failed to fetch ${src} (${res.status})`);
    }
    const buf = await res.arrayBuffer();
    await verifySri(buf, expectedHash, filename);

    // Create blob URL for verified content
    const blob = new Blob([buf], { type: "application/javascript" });
    const blobUrl = URL.createObjectURL(blob);

    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = blobUrl;
        script.async = false;
        script.setAttribute(attrName, src);
        script.addEventListener("load", () => {
            URL.revokeObjectURL(blobUrl);
            script.setAttribute(loadedAttr, "true");
            resolve();
        });
        script.addEventListener("error", () => {
            URL.revokeObjectURL(blobUrl);
            script.remove();
            reject(new Error(`Failed to load ${src}`));
        });
        document.head.appendChild(script);
    });
}

function loadChain() {
    return codec2ScriptPaths.reduce((chain, src) => chain.then(() => injectScript(src)), Promise.resolve());
}

/**
 * Run fn until it succeeds or maxAttempts is reached. Waits between failures with capped exponential backoff.
 *
 * @param {() => Promise<void>} fn
 * @param {{ maxAttempts?: number, baseDelayMs?: number, maxDelayMs?: number }} options
 */
export async function withRetries(fn, options = {}) {
    const maxAttempts = options.maxAttempts ?? 12;
    let delayMs = options.baseDelayMs ?? 400;
    const maxDelayMs = options.maxDelayMs ?? 8000;
    let lastErr;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
            await fn();
            return;
        } catch (e) {
            lastErr = e;
            if (attempt === maxAttempts - 1) {
                break;
            }
            await new Promise((r) => setTimeout(r, delayMs));
            delayMs = Math.min(maxDelayMs, Math.floor(delayMs * 1.5));
        }
    }
    throw lastErr;
}

/**
 * Resolves when all Codec2 helper scripts are present. Rejects if any script fails to load.
 * Call from features that require Codec2; use {@link startCodec2ScriptsBackgroundLoad} for startup.
 */
export function ensureCodec2ScriptsLoaded() {
    if (typeof window === "undefined") {
        return Promise.resolve();
    }
    if (resolvedOk) {
        return Promise.resolve();
    }
    if (!loadPromise) {
        loadPromise = loadChain()
            .then(() => {
                resolvedOk = true;
            })
            .catch((err) => {
                loadPromise = null;
                throw err;
            });
    }
    return loadPromise;
}

/**
 * Loads Codec2 scripts in the background with retries (embedded server may not be ready on first paint).
 * Swallows final failure after logging; the rest of the app stays usable without voice-codec scripts.
 *
 * @param {{ maxAttempts?: number, baseDelayMs?: number, maxDelayMs?: number }} options
 */
export async function startCodec2ScriptsBackgroundLoad(options = {}) {
    if (typeof window === "undefined") {
        return;
    }
    try {
        await withRetries(() => ensureCodec2ScriptsLoaded(), {
            maxAttempts: options.maxAttempts ?? 12,
            baseDelayMs: options.baseDelayMs ?? 400,
            maxDelayMs: options.maxDelayMs ?? 8000,
        });
    } catch (e) {
        console.warn("Codec2 scripts failed to load after retries; voice codec features may be unavailable.", e);
    }
}

/** Clears loader state (for unit tests only). */
export function resetCodec2LoaderState() {
    resolvedOk = false;
    loadPromise = null;
}
