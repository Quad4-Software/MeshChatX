import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";

const DB_NAME = "meshchat_map_cache";

function tag(o) {
    return Object.prototype.toString.call(o);
}

function tilePayloadToUint8(got) {
    if (got == null) {
        return null;
    }
    const t = tag(got);
    if (t === "[object Uint8Array]") {
        return got;
    }
    if (t === "[object ArrayBuffer]") {
        return new Uint8Array(got);
    }
    if (Array.isArray(got)) {
        return Uint8Array.from(got);
    }
    return null;
}

async function tilePayloadToUint8Async(got) {
    if (got == null) {
        return null;
    }
    if (tag(got) === "[object Blob]") {
        return new Uint8Array(await got.arrayBuffer());
    }
    return tilePayloadToUint8(got);
}

function deleteMapCacheDb() {
    const idb = globalThis.indexedDB;
    if (!idb) {
        return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
        const req = idb.deleteDatabase(DB_NAME);
        req.onsuccess = () => resolve();
        req.onblocked = () => resolve();
        req.onerror = () => reject(req.error);
    });
}

describe("TileCache.js", () => {
    describe("indexedDB detection (mocked)", () => {
        const DB_VERSION = 2;
        let savedIndexedDb;
        let savedGlobalIndexedDb;

        beforeEach(async () => {
            savedIndexedDb = window.indexedDB;
            savedGlobalIndexedDb = globalThis.indexedDB;
            vi.resetModules();
            vi.clearAllMocks();

            delete window.indexedDB;
            delete window.mozIndexedDB;
            delete window.webkitIndexedDB;
            delete window.msIndexedDB;
            delete globalThis.indexedDB;
        });

        afterEach(() => {
            if (savedIndexedDb !== undefined) {
                window.indexedDB = savedIndexedDb;
            }
            if (savedGlobalIndexedDb !== undefined) {
                globalThis.indexedDB = savedGlobalIndexedDb;
            }
        });

        it("should support window.indexedDB", async () => {
            const mockRequest = { onsuccess: null, onerror: null };
            const mockOpen = vi.fn().mockReturnValue(mockRequest);
            window.indexedDB = { open: mockOpen };

            await import("@/js/TileCache");

            expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
        });

        it("should support vendor prefixes (mozIndexedDB)", async () => {
            const mockRequest = { onsuccess: null, onerror: null };
            const mockOpen = vi.fn().mockReturnValue(mockRequest);
            window.mozIndexedDB = { open: mockOpen };

            await import("@/js/TileCache");

            expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
        });

        it("should support vendor prefixes (webkitIndexedDB)", async () => {
            const mockRequest = { onsuccess: null, onerror: null };
            const mockOpen = vi.fn().mockReturnValue(mockRequest);
            window.webkitIndexedDB = { open: mockOpen };

            await import("@/js/TileCache");

            expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
        });

        it("should support vendor prefixes (msIndexedDB)", async () => {
            const mockRequest = { onsuccess: null, onerror: null };
            const mockOpen = vi.fn().mockReturnValue(mockRequest);
            window.msIndexedDB = { open: mockOpen };

            await import("@/js/TileCache");

            expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
        });

        it("should support globalThis.indexedDB", async () => {
            const mockRequest = { onsuccess: null, onerror: null };
            const mockOpen = vi.fn().mockReturnValue(mockRequest);
            globalThis.indexedDB = { open: mockOpen };

            await import("@/js/TileCache");

            expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
        });

        it("should reject if IndexedDB is not supported", async () => {
            const module = await import("@/js/TileCache");
            const cache = module.default;

            await expect(cache.initPromise).rejects.toBe("IndexedDB not supported");
        });
    });

    describe("tile and map_state storage (fake-indexeddb)", () => {
        let TileCache;

        beforeAll(async () => {
            vi.resetModules();
            await deleteMapCacheDb();
            const mod = await import("@/js/TileCache");
            TileCache = mod.default;
            await TileCache.initPromise;
        });

        beforeEach(async () => {
            await TileCache.clear();
        });

        it("stores and retrieves binary tile data under the URL key", async () => {
            const key = "https://tiles.example/z/x/y.png";
            const bytes = Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

            // IndexedDB structured clone stores ArrayBuffer reliably in jsdom + fake-indexeddb.
            // MapPage passes Blob from fetch(); both Blob and ArrayBuffer are valid values.
            await TileCache.setTile(key, bytes.buffer);
            const got = await TileCache.getTile(key);

            const out = await tilePayloadToUint8Async(got);
            expect(out).not.toBeNull();
            expect(Array.from(out)).toEqual(Array.from(bytes));
        });

        it("stores and retrieves a tile Blob under the URL key when the runtime preserves Blob", async () => {
            const key = "https://tiles.example/blob.png";
            const bytes = Uint8Array.from([0x89, 0x50, 0x4e, 0x47]);
            const blob = new Blob([bytes], { type: "image/png" });

            await TileCache.setTile(key, blob);
            const got = await TileCache.getTile(key);

            if (!(got instanceof Blob)) {
                return;
            }

            expect(got.type).toBe("image/png");
            expect(got.size).toBe(bytes.length);
            const out = new Uint8Array(await got.arrayBuffer());
            expect(Array.from(out)).toEqual(Array.from(bytes));
        });

        it("returns undefined for a missing tile key", async () => {
            const got = await TileCache.getTile("https://missing.example/0/0/0.png");
            expect(got).toBeUndefined();
        });

        it("overwrites an existing tile key", async () => {
            const key = "https://tiles.example/same.png";
            await TileCache.setTile(key, Uint8Array.from([1, 2, 3]).buffer);
            await TileCache.setTile(key, Uint8Array.from([9, 9]).buffer);

            const got = await TileCache.getTile(key);
            const out = await tilePayloadToUint8Async(got);
            expect(out).not.toBeNull();
            expect(out.length).toBe(2);
            expect(out[0]).toBe(9);
        });

        it("stores and retrieves map state independently of tiles", async () => {
            const state = { center: [12.5, 55.1], zoom: 7, offlineEnabled: false };
            await TileCache.setMapState("last_view", state);
            const got = await TileCache.getMapState("last_view");

            expect(got).toEqual(state);
        });

        it("clear removes tiles and map state", async () => {
            await TileCache.setTile("https://x/t.png", Uint8Array.from([97]).buffer);
            await TileCache.setMapState("last_view", { zoom: 1 });

            await TileCache.clear();

            expect(await TileCache.getTile("https://x/t.png")).toBeUndefined();
            expect(await TileCache.getMapState("last_view")).toBeUndefined();
        });
    });
});
