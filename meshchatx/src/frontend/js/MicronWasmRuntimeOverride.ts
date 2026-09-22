/**
 * Optional runtime override for micron-parser-go WASM (IndexedDB).
 * Install via local .wasm upload only. Build ships bundled WASM under /vendor/.
 */

import { openIndexedDb } from "./idbOpen.js";

const DB_NAME = "meshchatx_micron_wasm_override";
const DB_VERSION = 1;
const STORE = "kv";
const KEY = "runtime_override";

export type MicronWasmRuntimeOverrideRecord = {
    source: "upload";
    releaseTag: string;
    wasmSri: string;
    wasmBytes: ArrayBuffer;
    expectedSha256Hex: string | null;
};

export const WASM_FILENAME = "micron-parser-go.wasm";

export const MAX_WASM_OVERRIDE_BYTES = 14 * 1024 * 1024;

function openDb() {
    return openIndexedDb(DB_NAME, DB_VERSION, {
        onUpgrade: (db) => {
            if (!db.objectStoreNames.contains(STORE)) {
                db.createObjectStore(STORE);
            }
        },
    });
}

export async function sha256HexOfBuffer(buf: ArrayBuffer): Promise<string> {
    const d = await crypto.subtle.digest("SHA-256", buf);
    const bytes = new Uint8Array(d);
    let hex = "";
    for (let i = 0; i < bytes.length; i++) {
        hex += bytes[i].toString(16).padStart(2, "0");
    }
    return hex;
}

export async function computeWasmSriSha384(buf: ArrayBuffer): Promise<string> {
    const hash = await crypto.subtle.digest("SHA-384", buf);
    const base64 = btoa(String.fromCharCode(...new Uint8Array(hash)));
    return `sha384-${base64}`;
}

function assertSri(wasmSri: unknown): asserts wasmSri is string {
    if (typeof wasmSri !== "string" || !/^sha384-[A-Za-z0-9+/=]+$/.test(wasmSri)) {
        throw new Error("Micron WASM update: invalid SRI format");
    }
}

export async function setMicronWasmRuntimeOverride(record: MicronWasmRuntimeOverrideRecord): Promise<void> {
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
    const releaseTag = String(record.releaseTag || "").trim() || "upload";
    const expectedSha256Hex = record.expectedSha256Hex == null ? null : String(record.expectedSha256Hex).toLowerCase();
    const db = await openDb();
    try {
        const tx = db.transaction(STORE, "readwrite");
        const st = tx.objectStore(STORE);
        st.put(
            {
                source: "upload",
                releaseTag,
                wasmSri: record.wasmSri,
                wasmBytes: buf,
                expectedSha256Hex,
            },
            KEY
        );
        await new Promise<void>((resolve, reject) => {
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error || new Error("IndexedDB write failed"));
            tx.onabort = () => reject(tx.error || new Error("IndexedDB write aborted"));
        });
    } finally {
        db.close();
    }
}

export async function getMicronWasmRuntimeOverride(): Promise<MicronWasmRuntimeOverrideRecord | null> {
    const db = await openDb();
    try {
        const tx = db.transaction(STORE, "readonly");
        const st = tx.objectStore(STORE);
        const raw = await new Promise<MicronWasmRuntimeOverrideRecord | null>((resolve, reject) => {
            const r = st.get(KEY);
            r.onsuccess = () => resolve((r.result as MicronWasmRuntimeOverrideRecord | undefined) || null);
            r.onerror = () => reject(r.error || new Error("IndexedDB read failed"));
        });
        if (!raw || !raw.wasmBytes || !raw.wasmSri) {
            return null;
        }
        return {
            source: "upload",
            releaseTag: String(raw.releaseTag || ""),
            wasmSri: String(raw.wasmSri),
            wasmBytes: raw.wasmBytes,
            expectedSha256Hex: raw.expectedSha256Hex == null ? null : String(raw.expectedSha256Hex),
        };
    } finally {
        db.close();
    }
}

export async function clearMicronWasmRuntimeOverride(): Promise<void> {
    const db = await openDb();
    try {
        const tx = db.transaction(STORE, "readwrite");
        const st = tx.objectStore(STORE);
        st.delete(KEY);
        await new Promise<void>((resolve, reject) => {
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error || new Error("IndexedDB delete failed"));
            tx.onabort = () => reject(tx.error || new Error("IndexedDB delete aborted"));
        });
    } finally {
        db.close();
    }
}
