/**
 * Optional runtime override for micron-parser-go WASM (IndexedDB).
 * GitHub releases are verified with SHASUMS256.txt before install.
 */

const DB_NAME = "meshchatx_micron_wasm_override";
const DB_VERSION = 1;
const STORE = "kv";
const KEY = "runtime_override";

/** @typedef {{ source: "github"|"upload", releaseTag: string, wasmSri: string, wasmBytes: ArrayBuffer, expectedSha256Hex: string|null }} MicronWasmRuntimeOverrideRecord */

export const MICRON_PARSER_GO_RELEASE_DOWNLOAD_BASE =
    "https://github.com/Quad4-Software/Micron-Parser-Go/releases/download";

export const WASM_FILENAME = "micron-parser-go.wasm";
export const SHASUMS256_FILENAME = "SHASUMS256.txt";

export const MAX_WASM_OVERRIDE_BYTES = 14 * 1024 * 1024;

/**
 * Same-origin MeshChat API path; server proxies only Quad4-Software/Micron-Parser-Go release assets (CSP).
 * @param {string} tag
 * @param {string} assetName SHASUMS256.txt | micron-parser-go.wasm
 */
export function micronParserGoReleaseProxyUrl(tag, assetName) {
    const params = new URLSearchParams();
    params.set("tag", tag);
    params.set("asset", assetName);
    return `/api/v1/tools/micron-parser-go-release?${params.toString()}`;
}

async function readFetchErrorDetail(res) {
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
        try {
            const j = await res.json();
            if (j && typeof j.error === "string" && j.error) {
                return j.error;
            }
        } catch {
            /* ignore */
        }
    }
    return String(res.status);
}

function openDb() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onerror = () => reject(req.error || new Error("IndexedDB open failed"));
        req.onupgradeneeded = () => {
            const db = req.result;
            if (!db.objectStoreNames.contains(STORE)) {
                db.createObjectStore(STORE);
            }
        };
        req.onsuccess = () => resolve(req.result);
    });
}

/**
 * Parses GNU/BSD shasum output for a single filename.
 * @param {string} text
 * @param {string} filename e.g. micron-parser-go.wasm
 * @returns {string|null} lowercase hex sha256 or null if not found
 */
export function parseShasums256ForFilename(text, filename) {
    if (text == null || filename == null) {
        return null;
    }
    const lines = String(text).split(/\r?\n/);
    for (const raw of lines) {
        const line = raw.trim();
        if (!line || line.startsWith("#")) {
            continue;
        }
        const m = line.match(/^([a-fA-F0-9]{64})\s+\*?(\S+)\s*$/);
        if (!m) {
            continue;
        }
        const name = m[2].trim();
        if (name === filename || name.endsWith(`/${filename}`)) {
            return m[1].toLowerCase();
        }
    }
    return null;
}

/** @param {ArrayBuffer} buf */
export async function sha256HexOfBuffer(buf) {
    const d = await crypto.subtle.digest("SHA-256", buf);
    const bytes = new Uint8Array(d);
    let hex = "";
    for (let i = 0; i < bytes.length; i++) {
        hex += bytes[i].toString(16).padStart(2, "0");
    }
    return hex;
}

/** @param {ArrayBuffer} buf */
export async function computeWasmSriSha384(buf) {
    const hash = await crypto.subtle.digest("SHA-384", buf);
    const base64 = btoa(String.fromCharCode(...new Uint8Array(hash)));
    return `sha384-${base64}`;
}

/**
 * Fetches SHASUMS256.txt and WASM from a GitHub release tag; verifies SHA-256 of WASM.
 * Does not write to storage.
 * @param {string} tag e.g. v1.0.5
 * @param {{ signal?: AbortSignal }} [opts]
 * @returns {Promise<Omit<MicronWasmRuntimeOverrideRecord, never>>}
 */
export async function fetchWasmFromGitHubReleaseVerified(tag, opts = {}) {
    const { signal } = opts;
    const t = String(tag || "").trim();
    if (!t) {
        throw new Error("Micron WASM update: release tag is required");
    }
    let sumsRes;
    try {
        sumsRes = await fetch(micronParserGoReleaseProxyUrl(t, SHASUMS256_FILENAME), { signal, cache: "no-store" });
    } catch (e) {
        const msg = e && e.name === "AbortError" ? "Request aborted" : (e && e.message) || String(e);
        throw new Error(`Micron WASM update: could not fetch release metadata (${msg})`);
    }
    if (!sumsRes.ok) {
        const detail = await readFetchErrorDetail(sumsRes);
        throw new Error(`Micron WASM update: SHASUMS256 fetch failed (${detail}). Check the tag and your network.`);
    }
    let sumsText;
    try {
        sumsText = await sumsRes.text();
    } catch (e) {
        throw new Error(`Micron WASM update: could not read SHASUMS256 (${e && e.message})`);
    }
    const expectedHex = parseShasums256ForFilename(sumsText, WASM_FILENAME);
    if (!expectedHex) {
        throw new Error(`Micron WASM update: ${WASM_FILENAME} not listed in ${SHASUMS256_FILENAME} for this release.`);
    }
    let wasmRes;
    try {
        wasmRes = await fetch(micronParserGoReleaseProxyUrl(t, WASM_FILENAME), { signal, cache: "no-store" });
    } catch (e) {
        const msg = e && e.name === "AbortError" ? "Request aborted" : (e && e.message) || String(e);
        throw new Error(`Micron WASM update: could not download WASM (${msg})`);
    }
    if (!wasmRes.ok) {
        const detail = await readFetchErrorDetail(wasmRes);
        throw new Error(`Micron WASM update: WASM download failed (${detail})`);
    }
    let buf;
    try {
        buf = await wasmRes.arrayBuffer();
    } catch (e) {
        throw new Error(`Micron WASM update: could not read WASM body (${e && e.message})`);
    }
    if (buf.byteLength > MAX_WASM_OVERRIDE_BYTES) {
        throw new Error(`Micron WASM update: WASM exceeds maximum size (${MAX_WASM_OVERRIDE_BYTES} bytes).`);
    }
    if (buf.byteLength < 4096) {
        throw new Error("Micron WASM update: WASM file is too small to be valid.");
    }
    const actualHex = await sha256HexOfBuffer(buf);
    if (actualHex !== expectedHex) {
        throw new Error(
            "Micron WASM update: SHA-256 mismatch after download. Refusing to install (possible tampering or corrupt transfer)."
        );
    }
    const wasmSri = await computeWasmSriSha384(buf);
    return {
        source: "github",
        releaseTag: t,
        wasmSri,
        wasmBytes: buf,
        expectedSha256Hex: expectedHex,
    };
}

function assertSri(wasmSri) {
    if (typeof wasmSri !== "string" || !/^sha384-[A-Za-z0-9+/=]+$/.test(wasmSri)) {
        throw new Error("Micron WASM update: invalid SRI format");
    }
}

/**
 * @param {MicronWasmRuntimeOverrideRecord} record
 */
export async function setMicronWasmRuntimeOverride(record) {
    if (!record || !record.wasmBytes) {
        throw new Error("Micron WASM update: missing WASM data");
    }
    const buf = record.wasmBytes;
    if (!(buf instanceof ArrayBuffer)) {
        throw new Error("Micron WASM update: wasmBytes must be an ArrayBuffer");
    }
    if (buf.byteLength > MAX_WASM_OVERRIDE_BYTES) {
        throw new Error(`Micron WASM update: WASM exceeds maximum size (${MAX_WASM_OVERRIDE_BYTES} bytes).`);
    }
    assertSri(record.wasmSri);
    const source = record.source === "upload" ? "upload" : "github";
    const releaseTag = String(record.releaseTag || "").trim() || (source === "github" ? "unknown" : "upload");
    const expectedSha256Hex = record.expectedSha256Hex == null ? null : String(record.expectedSha256Hex).toLowerCase();
    const db = await openDb();
    try {
        const tx = db.transaction(STORE, "readwrite");
        const st = tx.objectStore(STORE);
        st.put(
            {
                source,
                releaseTag,
                wasmSri: record.wasmSri,
                wasmBytes: buf,
                expectedSha256Hex,
            },
            KEY
        );
        await new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error || new Error("IndexedDB write failed"));
            tx.onabort = () => reject(tx.error || new Error("IndexedDB write aborted"));
        });
    } finally {
        db.close();
    }
}

/** @returns {Promise<MicronWasmRuntimeOverrideRecord|null>} */
export async function getMicronWasmRuntimeOverride() {
    const db = await openDb();
    try {
        const tx = db.transaction(STORE, "readonly");
        const st = tx.objectStore(STORE);
        const raw = await new Promise((resolve, reject) => {
            const r = st.get(KEY);
            r.onsuccess = () => resolve(r.result || null);
            r.onerror = () => reject(r.error || new Error("IndexedDB read failed"));
        });
        if (!raw || !raw.wasmBytes || !raw.wasmSri) {
            return null;
        }
        return {
            source: raw.source === "upload" ? "upload" : "github",
            releaseTag: String(raw.releaseTag || ""),
            wasmSri: String(raw.wasmSri),
            wasmBytes: raw.wasmBytes,
            expectedSha256Hex: raw.expectedSha256Hex == null ? null : String(raw.expectedSha256Hex),
        };
    } finally {
        db.close();
    }
}

export async function clearMicronWasmRuntimeOverride() {
    const db = await openDb();
    try {
        const tx = db.transaction(STORE, "readwrite");
        const st = tx.objectStore(STORE);
        st.delete(KEY);
        await new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error || new Error("IndexedDB delete failed"));
            tx.onabort = () => reject(tx.error || new Error("IndexedDB delete aborted"));
        });
    } finally {
        db.close();
    }
}
