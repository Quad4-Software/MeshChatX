// SPDX-License-Identifier: 0BSD
/**
 * Safe IndexedDB open helpers.
 *
 * Opaque origins (Nomad crash-tab iframe with sandbox="allow-scripts" and no
 * allow-same-origin) throw SecurityError on indexedDB.open. Keep that denial
 * from becoming an uncaught rejection when a shared chunk evaluates.
 */

type IndexedDbGlobal = typeof globalThis & {
    indexedDB?: IDBFactory;
    mozIndexedDB?: IDBFactory;
    webkitIndexedDB?: IDBFactory;
    msIndexedDB?: IDBFactory;
};

export type OpenIndexedDbOptions = {
    onUpgrade?: (db: IDBDatabase, event: IDBVersionChangeEvent) => void;
};

export function isIndexedDbAccessError(err: unknown): boolean {
    if (!err || typeof err !== "object") {
        return false;
    }
    const name = (err as { name?: string }).name;
    return name === "SecurityError" || name === "InvalidStateError";
}

export function getIndexedDbFactory(): IDBFactory | null {
    const g = globalThis as IndexedDbGlobal;
    return g.indexedDB || g.mozIndexedDB || g.webkitIndexedDB || g.msIndexedDB || null;
}

export function openIndexedDb(name: string, version: number, opts: OpenIndexedDbOptions = {}): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
        const idb = getIndexedDbFactory();
        if (!idb) {
            reject(new Error("IndexedDB unavailable"));
            return;
        }
        let request: IDBOpenDBRequest;
        try {
            request = idb.open(name, version);
        } catch (err) {
            reject(err);
            return;
        }
        request.onerror = () => {
            reject(request.error || new Error("IndexedDB open failed"));
        };
        request.onupgradeneeded = (event) => {
            if (typeof opts.onUpgrade === "function") {
                opts.onUpgrade(request.result, event);
            }
        };
        request.onsuccess = () => resolve(request.result);
    });
}
