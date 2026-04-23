import { describe, it, expect, vi } from "vitest";
import {
    buildNominatimSearchUrl,
    normalizeHttpBaseUrl,
    fetchTileBlobWithRetry,
    fetchJsonWithRetry,
    TILE_FETCH_TIMEOUT_MS,
} from "@/js/mapTileNetwork";

describe("mapTileNetwork", () => {
    describe("normalizeHttpBaseUrl", () => {
        it("strips trailing slash", () => {
            expect(normalizeHttpBaseUrl("http://127.0.0.1:8080/nominatim/")).toBe("http://127.0.0.1:8080/nominatim");
        });
    });

    describe("buildNominatimSearchUrl", () => {
        it("builds search URL for public nominatim", () => {
            const u = buildNominatimSearchUrl("https://nominatim.openstreetmap.org", "Paris", 5);
            expect(u).toBe("https://nominatim.openstreetmap.org/search?format=json&q=Paris&limit=5&addressdetails=1");
        });

        it("supports custom local mesh nominatim base", () => {
            const u = buildNominatimSearchUrl("http://192.168.44.1:3000/", "camp", 10);
            expect(u.startsWith("http://192.168.44.1:3000/search?")).toBe(true);
            expect(u).toContain(encodeURIComponent("camp"));
        });

        it("encodes query parameters safely", () => {
            const u = buildNominatimSearchUrl("http://localhost/nom", "a&b=c", 10);
            expect(u).toContain(encodeURIComponent("a&b=c"));
            expect(u).not.toContain("a&b=c&");
        });
    });

    describe("fetchTileBlobWithRetry", () => {
        it("returns blob on first successful response", async () => {
            const blob = new Blob([new Uint8Array([1, 2, 3])], { type: "image/png" });
            global.fetch = vi.fn().mockResolvedValue({
                ok: true,
                blob: () => Promise.resolve(blob),
            });
            const r = await fetchTileBlobWithRetry("https://tile.example/0/0/0.png", {}, { retries: 0 });
            expect(r.ok).toBe(true);
            expect(r.blob).toBe(blob);
            expect(global.fetch).toHaveBeenCalledTimes(1);
            delete global.fetch;
        });

        it("retries after failure then succeeds", async () => {
            const blob = new Blob([], { type: "image/png" });
            global.fetch = vi
                .fn()
                .mockRejectedValueOnce(new TypeError("Failed to fetch"))
                .mockResolvedValueOnce({
                    ok: true,
                    blob: () => Promise.resolve(blob),
                });
            const r = await fetchTileBlobWithRetry(
                "https://tile.example/1/1/1.png",
                {},
                { retries: 2, retryBaseDelayMs: 0 }
            );
            expect(r.ok).toBe(true);
            expect(global.fetch).toHaveBeenCalledTimes(2);
            delete global.fetch;
        });

        it("returns ok false after exhausting retries", async () => {
            global.fetch = vi.fn().mockRejectedValue(new TypeError("network"));
            const r = await fetchTileBlobWithRetry(
                "https://tile.example/z/x/y.png",
                {},
                { retries: 1, retryBaseDelayMs: 0, timeoutMs: TILE_FETCH_TIMEOUT_MS }
            );
            expect(r.ok).toBe(false);
            expect(r.error).toBeDefined();
            delete global.fetch;
        });
    });

    describe("fetchJsonWithRetry", () => {
        it("returns response on HTTP 200", async () => {
            global.fetch = vi.fn().mockResolvedValue({
                ok: true,
                json: () => Promise.resolve([]),
            });
            const r = await fetchJsonWithRetry("http://127.0.0.1:9999/search?q=x", {}, { retries: 0 });
            expect(r.ok).toBe(true);
            expect(r.response.ok).toBe(true);
            delete global.fetch;
        });

        it("does not retry on HTTP 404", async () => {
            global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 });
            const r = await fetchJsonWithRetry("http://localhost/n/search", {}, { retries: 2, retryBaseDelayMs: 0 });
            expect(r.ok).toBe(false);
            expect(r.status).toBe(404);
            expect(global.fetch).toHaveBeenCalledTimes(1);
            delete global.fetch;
        });
    });
});
