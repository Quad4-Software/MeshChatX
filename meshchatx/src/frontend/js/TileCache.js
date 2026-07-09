const DB_NAME = "meshchat_map_cache";
const DB_VERSION = 3;
const STORE_NAME = "tiles";
const STATE_STORE = "map_state";
const META_STORE = "tile_meta";

const MAX_TILES = 5000;
const MAX_BYTES = 256 * 1024 * 1024;
const TILE_TTL_MS = 30 * 24 * 60 * 60 * 1000;

class TileCache {
    constructor() {
        this.db = null;
        this.initPromise = this.init();
    }

    async init() {
        return new Promise((resolve, reject) => {
            const idb =
                window.indexedDB ||
                window.mozIndexedDB ||
                window.webkitIndexedDB ||
                window.msIndexedDB ||
                globalThis.indexedDB;

            if (!idb) {
                console.warn("IndexedDB not supported, map caching will be disabled");
                reject("IndexedDB not supported");
                return;
            }

            const request = idb.open(DB_NAME, DB_VERSION);

            request.onerror = (event) => reject("IndexedDB error: " + event.target.errorCode);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME);
                }
                if (!db.objectStoreNames.contains(STATE_STORE)) {
                    db.createObjectStore(STATE_STORE);
                }
                if (!db.objectStoreNames.contains(META_STORE)) {
                    db.createObjectStore(META_STORE);
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve();
            };
        });
    }

    _blobSize(data) {
        if (!data) return 0;
        if (typeof data.size === "number") return data.size;
        if (data.byteLength != null) return data.byteLength;
        if (typeof data === "string") return data.length;
        return 0;
    }

    async getTile(key) {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME, META_STORE], "readwrite");
            const store = transaction.objectStore(STORE_NAME);
            const metaStore = transaction.objectStore(META_STORE);
            const request = store.get(key);

            request.onsuccess = () => {
                const value = request.result;
                if (value != null) {
                    const metaReq = metaStore.get(key);
                    metaReq.onsuccess = () => {
                        const prev = metaReq.result || {};
                        metaStore.put(
                            {
                                ...prev,
                                lastAccess: Date.now(),
                                size: prev.size ?? this._blobSize(value),
                            },
                            key
                        );
                    };
                }
                resolve(value);
            };
            request.onerror = () => reject(request.error);
        });
    }

    async setTile(key, data) {
        await this.initPromise;
        await this._evictIfNeeded(this._blobSize(data));
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME, META_STORE], "readwrite");
            const store = transaction.objectStore(STORE_NAME);
            const metaStore = transaction.objectStore(META_STORE);
            store.put(data, key);
            metaStore.put(
                {
                    lastAccess: Date.now(),
                    size: this._blobSize(data),
                },
                key
            );

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
        });
    }

    async _readAllMeta() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([META_STORE], "readonly");
            const store = transaction.objectStore(META_STORE);
            const request = store.openCursor();
            const rows = [];
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (!cursor) {
                    resolve(rows);
                    return;
                }
                rows.push({ key: cursor.key, ...(cursor.value || {}) });
                cursor.continue();
            };
            request.onerror = () => reject(request.error);
        });
    }

    async _evictIfNeeded(incomingBytes = 0) {
        let meta;
        try {
            meta = await this._readAllMeta();
        } catch {
            return;
        }
        const now = Date.now();
        const expired = meta.filter((m) => m.lastAccess && now - m.lastAccess > TILE_TTL_MS);
        if (expired.length > 0) {
            await this._deleteKeys(expired.map((m) => m.key));
            meta = meta.filter((m) => !expired.some((e) => e.key === m.key));
        }

        let totalBytes = meta.reduce((sum, m) => sum + (m.size || 0), 0) + incomingBytes;
        let count = meta.length + (incomingBytes > 0 ? 1 : 0);
        if (count <= MAX_TILES && totalBytes <= MAX_BYTES) {
            return;
        }

        const ordered = meta.slice().sort((a, b) => (a.lastAccess || 0) - (b.lastAccess || 0));
        const toDelete = [];
        for (const row of ordered) {
            if (count <= MAX_TILES && totalBytes <= MAX_BYTES) {
                break;
            }
            toDelete.push(row.key);
            totalBytes -= row.size || 0;
            count -= 1;
        }
        if (toDelete.length > 0) {
            await this._deleteKeys(toDelete);
        }
    }

    async _deleteKeys(keys) {
        if (!keys.length) return;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME, META_STORE], "readwrite");
            const store = transaction.objectStore(STORE_NAME);
            const metaStore = transaction.objectStore(META_STORE);
            for (const key of keys) {
                store.delete(key);
                metaStore.delete(key);
            }
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
        });
    }

    async getMapState(key) {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STATE_STORE], "readonly");
            const store = transaction.objectStore(STATE_STORE);
            const request = store.get(key);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async setMapState(key, data) {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STATE_STORE], "readwrite");
            const store = transaction.objectStore(STATE_STORE);
            store.put(data, key);

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
        });
    }

    async clear() {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const stores = [STORE_NAME, STATE_STORE];
            if (this.db.objectStoreNames.contains(META_STORE)) {
                stores.push(META_STORE);
            }
            const transaction = this.db.transaction(stores, "readwrite");
            for (const name of stores) {
                transaction.objectStore(name).clear();
            }

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        });
    }
}

export default new TileCache();
