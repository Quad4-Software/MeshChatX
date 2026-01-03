import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("TileCache.js", () => {
    let TileCache;
    const DB_NAME = "meshchat_map_cache";
    const DB_VERSION = 2;

    beforeEach(async () => {
        vi.resetModules();
        vi.clearAllMocks();

        // Clear all possible indexedDB properties
        delete window.indexedDB;
        delete window.mozIndexedDB;
        delete window.webkitIndexedDB;
        delete window.msIndexedDB;
        delete globalThis.indexedDB;
    });

    it("should support window.indexedDB", async () => {
        const mockRequest = { onsuccess: null, onerror: null };
        const mockOpen = vi.fn().mockReturnValue(mockRequest);
        window.indexedDB = { open: mockOpen };

        // Re-import to trigger constructor and init
        const module = await import("@/js/TileCache");
        const cache = module.default;

        expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
    });

    it("should support vendor prefixes (mozIndexedDB)", async () => {
        const mockRequest = { onsuccess: null, onerror: null };
        const mockOpen = vi.fn().mockReturnValue(mockRequest);
        window.mozIndexedDB = { open: mockOpen };

        const module = await import("@/js/TileCache");
        const cache = module.default;

        expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
    });

    it("should support vendor prefixes (webkitIndexedDB)", async () => {
        const mockRequest = { onsuccess: null, onerror: null };
        const mockOpen = vi.fn().mockReturnValue(mockRequest);
        window.webkitIndexedDB = { open: mockOpen };

        const module = await import("@/js/TileCache");
        const cache = module.default;

        expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
    });

    it("should support vendor prefixes (msIndexedDB)", async () => {
        const mockRequest = { onsuccess: null, onerror: null };
        const mockOpen = vi.fn().mockReturnValue(mockRequest);
        window.msIndexedDB = { open: mockOpen };

        const module = await import("@/js/TileCache");
        const cache = module.default;

        expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
    });

    it("should support globalThis.indexedDB", async () => {
        const mockRequest = { onsuccess: null, onerror: null };
        const mockOpen = vi.fn().mockReturnValue(mockRequest);
        globalThis.indexedDB = { open: mockOpen };

        const module = await import("@/js/TileCache");
        const cache = module.default;

        expect(mockOpen).toHaveBeenCalledWith(DB_NAME, DB_VERSION);
    });

    it("should reject if IndexedDB is not supported", async () => {
        const module = await import("@/js/TileCache");
        const cache = module.default;

        await expect(cache.initPromise).rejects.toBe("IndexedDB not supported");
    });
});
