const codec2ScriptPaths = [
    "/assets/js/codec2-emscripten/c2enc.js",
    "/assets/js/codec2-emscripten/c2dec.js",
    "/assets/js/codec2-emscripten/sox.js",
    "/assets/js/codec2-emscripten/codec2-lib.js",
    "/assets/js/codec2-emscripten/wav-encoder.js",
    "/assets/js/codec2-emscripten/codec2-microphone-recorder.js",
];

let loadPromise = null;

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

export function ensureCodec2ScriptsLoaded() {
    if (typeof window === "undefined") {
        return Promise.resolve();
    }

    if (!loadPromise) {
        loadPromise = codec2ScriptPaths.reduce((chain, src) => chain.then(() => injectScript(src)), Promise.resolve());
    }

    return loadPromise;
}
