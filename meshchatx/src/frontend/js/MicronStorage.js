// SPDX-License-Identifier: 0BSD
import { isIndexedDbAccessError, openIndexedDb } from "./idbOpen.js";

const DB_NAME = "micron_editor_db";
const DB_VERSION = 1;
const STORE_NAME = "tabs";

class MicronStorage {
    constructor() {
        this.db = null;
        this.initPromise = null;
        this.unavailable = false;
    }

    _ensureInit() {
        if (this.initPromise) {
            return this.initPromise;
        }
        this.initPromise = this.init().catch((err) => {
            if (isIndexedDbAccessError(err) || err === "IndexedDB not supported") {
                this.unavailable = true;
                this.db = null;
                return null;
            }
            this.unavailable = true;
            this.db = null;
            console.warn("MicronStorage: IndexedDB init failed", err);
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
                    db.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
                }
            },
        });
        return this.db;
    }

    async saveTabs(tabs) {
        await this._ensureInit();
        if (!this.db) {
            return;
        }
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME], "readwrite");
            const store = transaction.objectStore(STORE_NAME);

            // Clear existing tabs before saving new ones to maintain order and structure
            const clearRequest = store.clear();

            clearRequest.onsuccess = () => {
                if (tabs.length === 0) {
                    return;
                }

                // Ensure we are storing plain objects, not Vue proxies or other non-cloneable objects.
                // JSON.parse/stringify is a safe way to strip proxies and ensure serializability
                // for these simple tab objects.
                const plainTabs = JSON.parse(JSON.stringify(tabs));

                plainTabs.forEach((tab) => {
                    store.add(tab);
                });
            };

            transaction.oncomplete = () => resolve();
            transaction.onerror = (event) => reject(event.target.error);
        });
    }

    async loadTabs() {
        await this._ensureInit();
        if (!this.db) {
            return [];
        }
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME], "readonly");
            const store = transaction.objectStore(STORE_NAME);
            const request = store.getAll();

            request.onsuccess = () => {
                resolve(request.result);
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    async clearAll() {
        await this._ensureInit();
        if (!this.db) {
            return;
        }
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME], "readwrite");
            const store = transaction.objectStore(STORE_NAME);
            const request = store.clear();

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }
}

export const micronStorage = new MicronStorage();
