// SPDX-License-Identifier: 0BSD
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { isIndexedDbAccessError, openIndexedDb, getIndexedDbFactory } from "../../meshchatx/src/frontend/js/idbOpen.js";

describe("idbOpen.js", () => {
    it("detects SecurityError and InvalidStateError", () => {
        expect(isIndexedDbAccessError(new DOMException("x", "SecurityError"))).toBe(true);
        expect(isIndexedDbAccessError(new DOMException("x", "InvalidStateError"))).toBe(true);
        expect(isIndexedDbAccessError(new Error("other"))).toBe(false);
        expect(isIndexedDbAccessError(null)).toBe(false);
    });

    it("rejects when indexedDB.open throws SecurityError", async () => {
        const saved = globalThis.indexedDB;
        globalThis.indexedDB = {
            open: () => {
                throw new DOMException("denied", "SecurityError");
            },
        };
        try {
            await expect(openIndexedDb("test_db", 1)).rejects.toMatchObject({ name: "SecurityError" });
        } finally {
            globalThis.indexedDB = saved;
        }
    });

    it("getIndexedDbFactory returns null when missing", () => {
        const saved = {
            indexedDB: globalThis.indexedDB,
            mozIndexedDB: globalThis.mozIndexedDB,
            webkitIndexedDB: globalThis.webkitIndexedDB,
            msIndexedDB: globalThis.msIndexedDB,
        };
        delete globalThis.indexedDB;
        delete globalThis.mozIndexedDB;
        delete globalThis.webkitIndexedDB;
        delete globalThis.msIndexedDB;
        try {
            expect(getIndexedDbFactory()).toBeNull();
        } finally {
            Object.assign(globalThis, saved);
        }
    });
});

describe("MicronStorage opaque-origin soft-fail", () => {
    let savedIndexedDb;

    beforeEach(() => {
        savedIndexedDb = globalThis.indexedDB;
        vi.resetModules();
    });

    afterEach(() => {
        globalThis.indexedDB = savedIndexedDb;
    });

    it("import does not open IndexedDB", async () => {
        const mockOpen = vi.fn();
        globalThis.indexedDB = { open: mockOpen };
        await import("../../meshchatx/src/frontend/js/MicronStorage.js");
        expect(mockOpen).not.toHaveBeenCalled();
    });

    it("loadTabs returns [] when open throws SecurityError", async () => {
        globalThis.indexedDB = {
            open: () => {
                throw new DOMException("denied", "SecurityError");
            },
        };
        const { micronStorage } = await import("../../meshchatx/src/frontend/js/MicronStorage.js");
        await expect(micronStorage.loadTabs()).resolves.toEqual([]);
        expect(micronStorage.unavailable).toBe(true);
    });
});
