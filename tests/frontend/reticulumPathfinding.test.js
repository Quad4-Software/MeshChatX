import { describe, it, expect, vi } from "vitest";
import {
    getDestinationPath,
    postRequestPath,
    postDropPath,
    runDestinationPathFinder,
} from "../../meshchatx/src/frontend/js/reticulumPathfinding.js";

describe("reticulumPathfinding", () => {
    it("getDestinationPath uses destination path API", async () => {
        const api = { get: vi.fn().mockResolvedValue({ data: { path: null } }) };
        await getDestinationPath(api, "abcd", { request: "1", timeout: 4 });
        expect(api.get).toHaveBeenCalledWith("/api/v1/destination/abcd/path", {
            params: { request: "1", timeout: 4 },
        });
    });

    it("coerces request true to string", async () => {
        const api = { get: vi.fn().mockResolvedValue({ data: {} }) };
        await getDestinationPath(api, "h1", { request: true });
        expect(api.get).toHaveBeenCalledWith("/api/v1/destination/h1/path", {
            params: { request: "1" },
        });
    });

    it("coerces request false to string", async () => {
        const api = { get: vi.fn().mockResolvedValue({ data: {} }) };
        await getDestinationPath(api, "h2", { request: false });
        expect(api.get).toHaveBeenCalledWith("/api/v1/destination/h2/path", {
            params: { request: "0" },
        });
    });

    it("postRequestPath and postDropPath hit expected routes", async () => {
        const api = { post: vi.fn().mockResolvedValue({ data: {} }) };
        await postRequestPath(api, "aaaabbbbccccddddeeeeffffaaaabbbb");
        expect(api.post).toHaveBeenCalledWith("/api/v1/destination/aaaabbbbccccddddeeeeffffaaaabbbb/request-path");
        await postDropPath(api, "x");
        expect(api.post).toHaveBeenCalledWith("/api/v1/destination/x/drop-path");
    });

    it("runDestinationPathFinder quick posts request-path", async () => {
        const api = { post: vi.fn().mockResolvedValue({ data: {} }) };
        const r = await runDestinationPathFinder(api, "q1", "quick");
        expect(r.ok).toBe(true);
        expect(api.post).toHaveBeenCalledWith("/api/v1/destination/q1/request-path");
    });

    it("runDestinationPathFinder force uses GET with wait", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({ data: { path: { hops: 1 } } }),
        };
        const r = await runDestinationPathFinder(api, "f1", "force", { forceTimeout: 9 });
        expect(r.path.hops).toBe(1);
        expect(api.get).toHaveBeenCalledWith("/api/v1/destination/f1/path", {
            params: { request: "1", timeout: 9 },
        });
    });

    it("runDestinationPathFinder drop_then_request drops then posts", async () => {
        const api = { post: vi.fn().mockResolvedValue({ data: {} }) };
        await runDestinationPathFinder(api, "d1", "drop_then_request");
        expect(api.post).toHaveBeenNthCalledWith(1, "/api/v1/destination/d1/drop-path");
        expect(api.post).toHaveBeenNthCalledWith(2, "/api/v1/destination/d1/request-path");
    });

    it("runDestinationPathFinder drop_then_request continues if drop fails with handler", async () => {
        const onDrop = vi.fn();
        const api = {
            post: vi.fn().mockRejectedValueOnce(new Error("no drop")).mockResolvedValue({ data: {} }),
        };
        await runDestinationPathFinder(api, "d2", "drop_then_request", { onDropPathError: onDrop });
        expect(onDrop).toHaveBeenCalled();
        expect(api.post).toHaveBeenLastCalledWith("/api/v1/destination/d2/request-path");
    });

    it("runDestinationPathFinder rejects unknown mode", async () => {
        const api = { get: vi.fn(), post: vi.fn() };
        await expect(runDestinationPathFinder(api, "z", "invalid")).rejects.toThrow("unknown path finder mode");
    });
});
