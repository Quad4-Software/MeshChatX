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

function injectScript(src) {
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

    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.async = false;
        script.setAttribute(attrName, src);
        script.addEventListener("load", () => {
            script.setAttribute(loadedAttr, "true");
            resolve();
        });
        script.addEventListener("error", () => {
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
