import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
    CachedPmtilesSource,
    resetCachedPmtilesSourcesForTests,
    getCachedPmtilesSource,
} from "../../meshchatx/src/frontend/js/pmtilesCacheSource.js";

const ARCHIVE = "https://tiles.example/planet.pmtiles";

function bytes(n, fill = 0) {
    const b = new Uint8Array(n);
    for (let i = 0; i < n; i++) b[i] = (fill + i) % 256;
    return b.buffer;
}

function makeResp(data, status = 206, headers = {}) {
    return {
        status,
        ok: status < 300,
        headers: new Headers(headers),
        body: { cancel: vi.fn() },
        arrayBuffer: () => Promise.resolve(data),
    };
}

let fetchImpl;
beforeEach(() => {
    resetCachedPmtilesSourcesForTests();
    fetchImpl = vi.fn(async (url, opts) => {
        const range = /bytes=(\d+)-(\d+)/.exec(new Headers(opts.headers).get("range"));
        const off = +range[1];
        const end = +range[2];
        return makeResp(bytes(end - off + 1, off & 0xff), 206, {
            "content-range": `bytes ${off}-${end}/1000000`,
            "cache-control": "public, max-age=3600",
            "last-modified": "Wed, 01 Jan 2025 00:00:00 GMT",
        });
    });
    vi.stubGlobal("fetch", (...args) => fetchImpl(...args));
});
afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe("CachedPmtilesSource", () => {
    it("fetches a range once and serves repeat reads from memory", async () => {
        const src = new CachedPmtilesSource(ARCHIVE);
        const a = await src.getBytes(100, 50);
        const b = await src.getBytes(100, 50);
        expect(fetchImpl.mock.calls.length).toBe(2); // meta probe + range
        expect(new Uint8Array(a.data).length).toBe(50);
        expect(new Uint8Array(b.data).length).toBe(50);
    });

    it("dedupes identical in-flight range requests", async () => {
        const src = new CachedPmtilesSource(ARCHIVE);
        await src._meta();
        const callsBefore = fetchImpl.mock.calls.length;
        const [a, b, c] = await Promise.all([src.getBytes(0, 10), src.getBytes(0, 10), src.getBytes(0, 10)]);
        expect(fetchImpl.mock.calls.length - callsBefore).toBe(1);
        expect(new Uint8Array(a.data)).toEqual(new Uint8Array(b.data));
        expect(new Uint8Array(b.data)).toEqual(new Uint8Array(c.data));
    });

    it("aborts the shared fetch when every waiter cancels", async () => {
        let sawAbort = false;
        fetchImpl = vi.fn(async (url, opts) => {
            opts.signal?.addEventListener("abort", () => {
                sawAbort = true;
            });
            const range = /bytes=(\d+)-(\d+)/.exec(new Headers(opts.headers).get("range"));
            return makeResp(bytes(+range[2] - +range[1] + 1));
        });
        const src = new CachedPmtilesSource(ARCHIVE);
        await src._meta();
        const c1 = new AbortController();
        const c2 = new AbortController();
        const p1 = src.getBytes(0, 10, c1.signal);
        const p2 = src.getBytes(0, 10, c2.signal);
        p1.catch(() => {});
        p2.catch(() => {});
        c1.abort();
        c2.abort();
        await Promise.allSettled([p1, p2]);
        expect(sawAbort).toBe(true);
    });

    it("invalidates entries when the archive fingerprint changes", async () => {
        let stamp = "Wed, 01 Jan 2025 00:00:00 GMT";
        let content = 7;
        fetchImpl = vi.fn(async (url, opts) => {
            const range = /bytes=(\d+)-(\d+)/.exec(new Headers(opts.headers).get("range"));
            const off = +range[1];
            const end = +range[2];
            return makeResp(bytes(end - off + 1, content), 206, {
                "content-range": `bytes ${off}-${end}/1000000`,
                "cache-control": "public, max-age=0",
                "last-modified": stamp,
            });
        });
        const src = new CachedPmtilesSource(ARCHIVE);
        await src.getBytes(0, 10);
        const meta = await src._meta();
        meta.fetchedAt = Date.now() - 5000;
        const calls1 = fetchImpl.mock.calls.length;
        await src.getBytes(0, 10); // revalidates, unchanged fingerprint
        expect(fetchImpl.mock.calls.length).toBeGreaterThan(calls1); // probe ran
        const readsAfterProbe = fetchImpl.mock.calls.length;
        // Simulate archive rebuild: new last-modified and new bytes.
        stamp = "Thu, 02 Jan 2025 00:00:00 GMT";
        content = 99;
        meta.fetchedAt = Date.now() - 25 * 3600 * 1000; // beyond grace: hard revalidate
        await src.getBytes(0, 10);
        const rangeCalls = fetchImpl.mock.calls
            .slice(readsAfterProbe)
            .filter((c) => /bytes=0-9\b/.test(new Headers(c[1].headers).get("range")));
        expect(rangeCalls.length).toBe(1); // refetched after invalidation
    });

    it("falls back to header-byte hashing when validators are unreadable", async () => {
        let payload = 5;
        fetchImpl = vi.fn(async (url, opts) => {
            const range = /bytes=(\d+)-(\d+)/.exec(new Headers(opts.headers).get("range"));
            const off = +range[1];
            const end = +range[2];
            return makeResp(bytes(end - off + 1, off === 0 ? payload : 1), 206, {
                "cache-control": "public, max-age=0",
            });
        });
        const src = new CachedPmtilesSource(ARCHIVE);
        await src.getBytes(1000, 8);
        const meta = await src._meta();
        payload = 77; // header bytes changed -> fingerprint changes
        meta.fetchedAt = Date.now() - 25 * 3600 * 1000; // beyond grace: hard revalidate
        const callsBefore = fetchImpl.mock.calls.length;
        const second = await src.getBytes(1000, 8);
        expect(new Uint8Array(second.data).length).toBe(8);
        // probe (0-126) plus a tile refetch after fingerprint invalidation
        const ranges = fetchImpl.mock.calls.slice(callsBefore).map((c) => new Headers(c[1].headers).get("range"));
        expect(ranges).toContain("bytes=0-126");
        expect(ranges).toContain("bytes=1000-1007");
    });

    it("evicts least-recently-used entries past the memory cap", async () => {
        const src = new CachedPmtilesSource(ARCHIVE);
        const big = 512 * 1024;
        for (let i = 0; i < 110; i++) {
            await src.getBytes(i * big + 4096, 8); // distinct keys
        }
        expect(src.mem.map.size).toBeLessThanOrEqual(400);
        expect(src.mem.bytes).toBeLessThanOrEqual(48 * 1024 * 1024);
    });

    it("shares one source instance per archive URL", () => {
        expect(getCachedPmtilesSource(ARCHIVE)).toBe(getCachedPmtilesSource(ARCHIVE));
        expect(getCachedPmtilesSource("https://other.example/a.pmtiles")).not.toBe(getCachedPmtilesSource(ARCHIVE));
    });

    it("serves stale data while revalidating inside the grace window", async () => {
        const src = new CachedPmtilesSource(ARCHIVE);
        await src._meta();
        const key = `${ARCHIVE}|100|50`;
        await src.getBytes(100, 50);
        const entry = src.mem.get(key);
        const meta = await src._meta();
        meta.maxAge = 0;
        meta.fetchedAt = Date.now() - 5000; // expired, inside grace
        const before = fetchImpl.mock.calls.length;
        const res = await src.getBytes(100, 50);
        expect(new Uint8Array(res.data).length).toBe(50);
        await new Promise((r) => setTimeout(r, 0)); // background probe lands
        const ranges = fetchImpl.mock.calls.slice(before).map((c) => new Headers(c[1].headers).get("range"));
        expect(ranges.length).toBeGreaterThan(0);
        expect(ranges.every((r) => r === "bytes=0-126")).toBe(true);
        void entry;
    });
});
