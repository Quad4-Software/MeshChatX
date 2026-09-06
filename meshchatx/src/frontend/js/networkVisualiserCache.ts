// SPDX-License-Identifier: 0BSD

/**
 * Identity-scoped IndexedDB cache for the network visualiser.
 * Stores path rows, announces, and node positions so reopen can paint quickly
 * and only fetch announces for newly seen destination hashes.
 */

import { openIndexedDb } from "./idbOpen.js";

const DB_NAME = "meshchatx_visualiser_cache";
const DB_VERSION = 1;
const STORE_NAME = "snapshots";
// Bump when layout scale changes so stored x/y from an older spring length
// are not reused as the new compact seed.
const CACHE_VERSION = 2;
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

export type VisualiserCacheSnapshot = {
    identityHash: string;
    savedAt: number;
    pathTable: unknown[];
    announces: Record<string, unknown>;
    positions: Record<string, unknown>;
};

export type VisualiserCacheSaveInput = {
    identityHash: string;
    pathTable: unknown[];
    announces: Record<string, unknown>;
    positions: Record<string, unknown>;
    pathSoftCap?: number;
    announceSoftCap?: number;
};

let dbPromise: Promise<IDBDatabase> | null = null;

function openDb(): Promise<IDBDatabase> {
    if (dbPromise) {
        return dbPromise;
    }
    dbPromise = openIndexedDb(DB_NAME, DB_VERSION, {
        onUpgrade: (db) => {
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: "identityHash" });
            }
        },
    }).catch((err) => {
        dbPromise = null;
        throw err;
    });
    return dbPromise;
}

function clonePlain<T>(value: T): T {
    return JSON.parse(JSON.stringify(value));
}

export async function loadVisualiserCache(
    identityHash: string | null | undefined
): Promise<VisualiserCacheSnapshot | null> {
    if (!identityHash || typeof identityHash !== "string") {
        return null;
    }
    try {
        const db = await openDb();
        const row = await new Promise<Record<string, unknown> | null>((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, "readonly");
            const req = tx.objectStore(STORE_NAME).get(identityHash);
            req.onsuccess = () => resolve((req.result as Record<string, unknown>) || null);
            req.onerror = () => reject(req.error);
        });
        if (!row || row.version !== CACHE_VERSION) {
            return null;
        }
        if (typeof row.savedAt !== "number" || Date.now() - row.savedAt > MAX_AGE_MS) {
            return null;
        }
        if (!Array.isArray(row.pathTable)) {
            return null;
        }
        return {
            identityHash: String(row.identityHash),
            savedAt: row.savedAt,
            pathTable: row.pathTable,
            announces:
                row.announces && typeof row.announces === "object" ? (row.announces as Record<string, unknown>) : {},
            positions:
                row.positions && typeof row.positions === "object" ? (row.positions as Record<string, unknown>) : {},
        };
    } catch {
        return null;
    }
}

export async function saveVisualiserCache(snapshot: VisualiserCacheSaveInput | null | undefined): Promise<boolean> {
    const identityHash = snapshot?.identityHash;
    if (!identityHash || typeof identityHash !== "string") {
        return false;
    }
    try {
        const pathSoftCap = snapshot.pathSoftCap ?? 20_000;
        const announceSoftCap = snapshot.announceSoftCap ?? 10_000;
        let pathTable = Array.isArray(snapshot.pathTable) ? snapshot.pathTable : [];
        if (pathTable.length > pathSoftCap) {
            pathTable = pathTable.slice(0, pathSoftCap);
        }
        const announcesIn = snapshot.announces && typeof snapshot.announces === "object" ? snapshot.announces : {};
        const announceKeys = Object.keys(announcesIn);
        let announces: Record<string, unknown> = announcesIn;
        if (announceKeys.length > announceSoftCap) {
            announces = {};
            for (const key of announceKeys.slice(0, announceSoftCap)) {
                announces[key] = announcesIn[key];
            }
        }
        const positions = snapshot.positions && typeof snapshot.positions === "object" ? snapshot.positions : {};

        const row = {
            identityHash,
            version: CACHE_VERSION,
            savedAt: Date.now(),
            pathTable: clonePlain(pathTable),
            announces: clonePlain(announces),
            positions: clonePlain(positions),
        };

        const db = await openDb();
        await new Promise<void>((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, "readwrite");
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
            tx.objectStore(STORE_NAME).put(row);
        });
        return true;
    } catch {
        return false;
    }
}

export async function clearVisualiserCache(identityHash: string | null | undefined): Promise<boolean> {
    if (!identityHash) {
        return false;
    }
    try {
        const db = await openDb();
        await new Promise<void>((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, "readwrite");
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
            tx.objectStore(STORE_NAME).delete(identityHash);
        });
        return true;
    } catch {
        return false;
    }
}

/** Test helper to reset the open handle between tests. */
export function resetVisualiserCacheDbHandle(): void {
    dbPromise = null;
}
