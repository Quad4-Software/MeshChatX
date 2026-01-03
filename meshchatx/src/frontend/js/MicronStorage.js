const DB_NAME = "micron_editor_db";
const DB_VERSION = 1;
const STORE_NAME = "tabs";

class MicronStorage {
    constructor() {
        this.db = null;
        this.initPromise = this.init();
    }

    async init() {
        return new Promise((resolve, reject) => {
            if (this.db) {
                resolve(this.db);
                return;
            }

            const idb =
                window.indexedDB ||
                window.mozIndexedDB ||
                window.webkitIndexedDB ||
                window.msIndexedDB ||
                globalThis.indexedDB;
            if (!idb) {
                reject("IndexedDB not supported");
                return;
            }

            const request = idb.open(DB_NAME, DB_VERSION);

            request.onerror = (event) => {
                console.error("IndexedDB error:", event.target.errorCode);
                reject("IndexedDB error: " + event.target.errorCode);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve(this.db);
            };
        });
    }

    async saveTabs(tabs) {
        await this.initPromise;
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
        await this.initPromise;
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
        await this.initPromise;
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
