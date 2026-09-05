// SPDX-License-Identifier: 0BSD
import { isIndexedDbAccessError, openIndexedDb } from "./idbOpen.js";

const DB_NAME = "meshchat_map_cache";
const DB_VERSION = 3;
const STORE_NAME = "tiles";
const STATE_STORE = "map_state";
const META_STORE = "tile_meta";

const MAX_TILES = 5000;
const MAX_BYTES = 256 * 1024 * 1024;
const TILE_TTL_MS = 30 * 24 * 60 * 60 * 1000;
const MEM_MAX_ENTRIES = 128;
const ACCESS_FLUSH_HITS = 32;
const ACCESS_FLUSH_MS = 5000;

class TileCache {
    declare _accessFlushTimer: any;
    declare _memCache: Map<any, any>;
    declare _pendingAccess: Map<any, any>;
    declare db: any;
    declare initPromise: any;
    declare unavailable: boolean;
    constructor() {
        this.db = null;
        this._memCache = new Map();
        this._pendingAccess = new Map();
        this._accessFlushTimer = null;
        this.initPromise = null;
        this.unavailable = false;
    }

    _ensureInit() {
        if (this.initPromise) {
            return this.initPromise;
        }
        this.initPromise = this.init().catch((err) => {
            if (isIndexedDbAccessError(err) || String(err).includes("IndexedDB")) {
                this.unavailable = true;
                this.db = null;
                return null;
            }
            this.unavailable = true;
            this.db = null;
            console.warn("TileCache: IndexedDB init failed", err);
            return null;
        });
        return this.initPromise;
    }

    async init() {
        if (this.db) {
            return this.db;
        }
        this.db = await openIndexedDb(DB_NAME, DB_VERSION, {
            onUpgrade: (db) => {
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME);
                }
                if (!db.objectStoreNames.contains(STATE_STORE)) {
                    db.createObjectStore(STATE_STORE);
                }
                if (!db.objectStoreNames.contains(META_STORE)) {
                    db.createObjectStore(META_STORE);
                }
            },
        });
        return this.db;
    }

    _blobSize(data) {
        if (!data) return 0;
        if (typeof data.size === "number") return data.size;
        if (data.byteLength != null) return data.byteLength;
        if (typeof data === "string") return data.length;
        return 0;
    }

    _memGet(key) {
        const hit = this._memCache.get(key);
        if (!hit) {
            return undefined;
        }
        this._memCache.delete(key);
        this._memCache.set(key, hit);
        return hit.data;
    }

    _memPut(key, data) {
        if (this._memCache.has(key)) {
            this._memCache.delete(key);
        }
        this._memCache.set(key, { data, size: this._blobSize(data) });
        while (this._memCache.size > MEM_MAX_ENTRIES) {
            const oldest = this._memCache.keys().next().value;
            this._memCache.delete(oldest);
        }
    }

    _queueAccess(key) {
        this._pendingAccess.set(key, Date.now());
        if (this._pendingAccess.size >= ACCESS_FLUSH_HITS) {
            this._flushAccess();
            return;
        }
        if (this._accessFlushTimer == null) {
            this._accessFlushTimer = setTimeout(() => {
                this._accessFlushTimer = null;
                this._flushAccess();
            }, ACCESS_FLUSH_MS);
        }
    }

    async _flushAccess() {
        if (this._accessFlushTimer != null) {
            clearTimeout(this._accessFlushTimer);
            this._accessFlushTimer = null;
        }
        const pending = this._pendingAccess;
        this._pendingAccess = new Map();
        if (!pending.size || !this.db) {
            return;
        }
        try {
            await this._ensureInit();
            if (!this.db) {
                return;
            }
            await new Promise<void>((resolve, reject) => {
                const transaction = this.db.transaction([META_STORE], "readwrite");
                const metaStore = transaction.objectStore(META_STORE);
                for (const [key, ts] of pending.entries()) {
                    const req = metaStore.get(key);
                    req.onsuccess = () => {
                        const prev = req.result || {};
                        metaStore.put(
                            {
                                ...prev,
                                lastAccess: ts,
                                size: prev.size ?? 0,
                            },
                            key
                        );
                    };
                }
                transaction.oncomplete = () => resolve();
                transaction.onerror = () => reject(transaction.error);
                transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
            });
        } catch {
            /* ignore idle flush errors */
        }
    }

    async getTile(key) {
        await this._ensureInit();
        if (!this.db) {
            return undefined;
        }
        const mem = this._memGet(key);
        if (mem !== undefined) {
            this._queueAccess(key);
            return mem;
        }
        return new Promise<any>((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME], "readonly");
            const store = transaction.objectStore(STORE_NAME);
            const request = store.get(key);

            request.onsuccess = () => {
                const value = request.result;
                if (value != null) {
                    this._memPut(key, value);
                    this._queueAccess(key);
                }
                resolve(value);
            };
            request.onerror = () => reject(request.error);
        });
    }

    async setTile(key, data) {
        await this._ensureInit();
        if (!this.db) {
            this._memPut(key, data);
            return;
        }
        await this._evictIfNeeded(this._blobSize(data));
        return new Promise<void>((resolve, reject) => {
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
            this._memPut(key, data);

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
        });
    }

    async _readAllMeta() {
        return new Promise<any>((resolve, reject) => {
            const transaction = this.db.transaction([META_STORE], "readonly");
            const store = transaction.objectStore(META_STORE);
            const request = store.openCursor();
            const rows: any[] = [];
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
        const toDelete: any[] = [];
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
        return new Promise<void>((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME, META_STORE], "readwrite");
            const store = transaction.objectStore(STORE_NAME);
            const metaStore = transaction.objectStore(META_STORE);
            for (const key of keys) {
                store.delete(key);
                metaStore.delete(key);
                this._memCache.delete(key);
                this._pendingAccess.delete(key);
            }
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
        });
    }

    async getMapState(key) {
        await this._ensureInit();
        if (!this.db) {
            return undefined;
        }
        return new Promise<any>((resolve, reject) => {
            const transaction = this.db.transaction([STATE_STORE], "readonly");
            const store = transaction.objectStore(STATE_STORE);
            const request = store.get(key);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async setMapState(key, data) {
        await this._ensureInit();
        if (!this.db) {
            return;
        }
        return new Promise<void>((resolve, reject) => {
            const transaction = this.db.transaction([STATE_STORE], "readwrite");
            const store = transaction.objectStore(STATE_STORE);
            store.put(data, key);

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
        });
    }

    async clear() {
        await this._ensureInit();
        this._memCache.clear();
        this._pendingAccess.clear();
        if (!this.db) {
            return;
        }
        return new Promise<void>((resolve, reject) => {
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

export { TileCache };
export default new TileCache();
