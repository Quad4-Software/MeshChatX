import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    loadVisualiserCache,
    saveVisualiserCache,
    clearVisualiserCache,
    resetVisualiserCacheDbHandle,
} from "@/js/networkVisualiserCache.js";

function mockIndexedDb() {
    const stores = new Map();
    const fakeDb = {
        objectStoreNames: {
            contains: (name) => name === "snapshots",
        },
        transaction(storeNames, mode) {
            const storeName = Array.isArray(storeNames) ? storeNames[0] : storeNames;
            if (!stores.has(storeName)) stores.set(storeName, new Map());
            const data = stores.get(storeName);
            const store = {
                get(key) {
                    const req = {};
                    queueMicrotask(() => {
                        req.result = data.get(key);
                        req.onsuccess?.();
                    });
                    return req;
                },
                put(row) {
                    data.set(row.identityHash, row);
                    const req = {};
                    queueMicrotask(() => req.onsuccess?.());
                    return req;
                },
                delete(key) {
                    data.delete(key);
                    const req = {};
                    queueMicrotask(() => req.onsuccess?.());
                    return req;
                },
            };
            const tx = {
                objectStore: () => store,
                oncomplete: null,
                onerror: null,
            };
            queueMicrotask(() => tx.oncomplete?.());
            return tx;
        },
    };
    const idb = {
        open() {
            const req = {
                result: fakeDb,
                onupgradeneeded: null,
                onsuccess: null,
                onerror: null,
            };
            queueMicrotask(() => {
                req.onupgradeneeded?.({ target: req });
                req.onsuccess?.({ target: req });
            });
            return req;
        },
    };
    return idb;
}

describe("networkVisualiserCache", () => {
    beforeEach(() => {
        resetVisualiserCacheDbHandle();
        vi.stubGlobal("indexedDB", mockIndexedDb());
    });

    afterEach(() => {
        resetVisualiserCacheDbHandle();
        vi.unstubAllGlobals();
    });

    it("round-trips path table announces and positions for one identity", async () => {
        const ok = await saveVisualiserCache({
            identityHash: "abc123",
            pathTable: [{ hash: "n1", hops: 1, interface: "eth0" }],
            announces: { n1: { destination_hash: "n1", aspect: "lxmf.delivery" } },
            positions: { n1: { x: 10, y: 20 } },
        });
        expect(ok).toBe(true);
        const loaded = await loadVisualiserCache("abc123");
        expect(loaded.pathTable).toHaveLength(1);
        expect(loaded.announces.n1.aspect).toBe("lxmf.delivery");
        expect(loaded.positions.n1).toEqual({ x: 10, y: 20 });
    });

    it("isolates cache by identity hash", async () => {
        await saveVisualiserCache({
            identityHash: "id-a",
            pathTable: [{ hash: "a" }],
            announces: {},
            positions: {},
        });
        await saveVisualiserCache({
            identityHash: "id-b",
            pathTable: [{ hash: "b" }],
            announces: {},
            positions: {},
        });
        expect((await loadVisualiserCache("id-a")).pathTable[0].hash).toBe("a");
        expect((await loadVisualiserCache("id-b")).pathTable[0].hash).toBe("b");
    });

    it("clearVisualiserCache removes a snapshot", async () => {
        await saveVisualiserCache({
            identityHash: "gone",
            pathTable: [{ hash: "x" }],
            announces: {},
            positions: {},
        });
        await clearVisualiserCache("gone");
        expect(await loadVisualiserCache("gone")).toBeNull();
    });

    it("returns null when IndexedDB is unavailable", async () => {
        resetVisualiserCacheDbHandle();
        vi.stubGlobal("indexedDB", undefined);
        expect(await loadVisualiserCache("x")).toBeNull();
        expect(await saveVisualiserCache({ identityHash: "x", pathTable: [], announces: {}, positions: {} })).toBe(
            false
        );
    });
});
