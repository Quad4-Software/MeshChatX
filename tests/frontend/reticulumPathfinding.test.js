// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi } from "vitest";
import {
    getDestinationPath,
    postRequestPath,
    postDropPath,
    runDestinationPathFinder,
    normalizePathSnapshot,
    pathNeedsRefresh,
    pathIsReady,
    warmPathIfNeeded,
} from "../../meshchatx/src/frontend/js/reticulumPathfinding.js";

describe("reticulumPathfinding.js", () => {
    it("getDestinationPath builds expected URL and forwards params", () => {
        const api = { get: vi.fn().mockResolvedValue({ data: { path: null } }) };
        getDestinationPath(api, "deadbeef", { request: true, timeout: 12 });
        expect(api.get).toHaveBeenCalledWith("/api/v1/destination/deadbeef/path", {
            params: { request: "1", timeout: 12 },
        });
    });

    it("getDestinationPath uses raw hash segment (caller must validate)", () => {
        const api = { get: vi.fn().mockResolvedValue({ data: {} }) };
        getDestinationPath(api, "not/a/hex", {});
        expect(api.get).toHaveBeenCalledWith("/api/v1/destination/not/a/hex/path", expect.any(Object));
    });

    it("postRequestPath and postDropPath hit destination endpoints", () => {
        const api = { post: vi.fn().mockResolvedValue({}) };
        postRequestPath(api, "ab");
        postDropPath(api, "ab");
        expect(api.post).toHaveBeenCalledWith("/api/v1/destination/ab/request-path");
        expect(api.post).toHaveBeenCalledWith("/api/v1/destination/ab/drop-path");
    });

    it("runDestinationPathFinder quick only posts request-path", async () => {
        const api = { post: vi.fn().mockResolvedValue({}) };
        const r = await runDestinationPathFinder(api, "h", "quick");
        expect(r).toEqual({ ok: true, path: null });
        expect(api.post).toHaveBeenCalledTimes(1);
    });

    it("runDestinationPathFinder rejects unknown mode", async () => {
        const api = { get: vi.fn(), post: vi.fn() };
        await expect(runDestinationPathFinder(api, "h", "invalid-mode")).rejects.toThrow("unknown path finder mode");
    });

    it("normalizePathSnapshot defaults missing metadata to stale", () => {
        expect(normalizePathSnapshot({ path: null })).toEqual({
            path: null,
            path_stale: true,
            path_unresponsive: false,
        });
        expect(normalizePathSnapshot(null)).toEqual({
            path: null,
            path_stale: true,
            path_unresponsive: false,
        });
    });

    it("pathNeedsRefresh respects stale and unresponsive flags", () => {
        const fresh = { path: { hops: 1 }, path_stale: false, path_unresponsive: false };
        expect(pathNeedsRefresh(fresh)).toBe(false);
        expect(pathIsReady(fresh)).toBe(true);
        expect(pathNeedsRefresh({ ...fresh, path_stale: true })).toBe(true);
        expect(pathNeedsRefresh({ ...fresh, path_unresponsive: true })).toBe(true);
        expect(pathNeedsRefresh({ path: null, path_stale: true, path_unresponsive: false })).toBe(true);
    });

    it("warmPathIfNeeded skips request when path is ready", async () => {
        const api = { post: vi.fn() };
        const snapshot = { path: { hops: 1 }, path_stale: false, path_unresponsive: false };
        const r = await warmPathIfNeeded(api, "abc", snapshot);
        expect(r).toEqual({ requested: false });
        expect(api.post).not.toHaveBeenCalled();
    });

    it("warmPathIfNeeded posts when path is missing or stale", async () => {
        const api = { post: vi.fn().mockResolvedValue({}) };
        await warmPathIfNeeded(api, "abc", { path: null, path_stale: true, path_unresponsive: false });
        expect(api.post).toHaveBeenCalledWith("/api/v1/destination/abc/request-path");
    });
});
