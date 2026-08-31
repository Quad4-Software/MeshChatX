// SPDX-License-Identifier: 0BSD
/**
 * Safe IndexedDB open helpers.
 *
 * Opaque origins (Nomad crash-tab iframe with sandbox="allow-scripts" and no
 * allow-same-origin) throw SecurityError on indexedDB.open. Keep that denial
 * from becoming an uncaught rejection when a shared chunk evaluates.
 */

/**
 * @param {unknown} err
 * @returns {boolean}
 */
export function isIndexedDbAccessError(err) {
    if (!err || typeof err !== "object") {
        return false;
    }
    const name = /** @type {{ name?: string }} */ (err).name;
    return name === "SecurityError" || name === "InvalidStateError";
}

/**
 * @returns {IDBFactory | null}
 */
export function getIndexedDbFactory() {
    const g = globalThis;
    return g.indexedDB || g.mozIndexedDB || g.webkitIndexedDB || g.msIndexedDB || null;
}

/**
 * @param {string} name
 * @param {number} version
 * @param {{ onUpgrade?: (db: IDBDatabase, event: IDBVersionChangeEvent) => void }} [opts]
 * @returns {Promise<IDBDatabase>}
 */
export function openIndexedDb(name, version, opts = {}) {
    return new Promise((resolve, reject) => {
        const idb = getIndexedDbFactory();
        if (!idb) {
            reject(new Error("IndexedDB unavailable"));
            return;
        }
        let request;
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
