import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import fc from "fast-check";
import {
    CachedPmtilesSource,
    resetCachedPmtilesSourcesForTests,
} from "../../meshchatx/src/frontend/js/pmtilesCacheSource.js";

const ARCHIVE = "https://tiles.example/planet.pmtiles";
const ARCHIVE_SIZE = 1_000_000;

// Canonical archive model: byte at position p is p % 256.
function archiveByte(p) {
    return p % 256;
}

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

function installFakeCacheApi() {
    const store = new Map();
    const cache = {
        match: vi.fn(async (url) => {
            const data = store.get(String(url));
            if (!data) return undefined;
            return new Response(data.slice(0), { status: 200 });
        }),
        put: vi.fn(async (url, response) => {
            store.set(String(url), await response.arrayBuffer());
        }),
        delete: vi.fn(async (url) => store.delete(String(url))),
    };
    vi.stubGlobal("caches", { open: vi.fn(async () => cache) });
    return { cache, store };
}

let fetchImpl;

function installStaticArchiveFetch() {
    // A static archive: every range response serves canonical model bytes.
    fetchImpl = vi.fn(async (url, opts) => {
        const range = /bytes=(\d+)-(\d+)/.exec(new Headers(opts.headers).get("range"));
        const off = +range[1];
        const end = +range[2];
        return makeResp(bytes(end - off + 1, off & 0xff), 206, {
            "content-range": `bytes ${off}-${end}/${ARCHIVE_SIZE}`,
            "cache-control": "public, max-age=3600",
            "last-modified": "Wed, 01 Jan 2025 00:00:00 GMT",
        });
    });
    vi.stubGlobal("fetch", (...args) => fetchImpl(...args));
}

beforeEach(() => {
    resetCachedPmtilesSourcesForTests();
});
afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

// Generate non-overlapping-ish valid range reads inside the archive.
const rangeRead = fc
    .record({
        offset: fc.integer({ min: 0, max: ARCHIVE_SIZE - 2 }),
        length: fc.integer({ min: 1, max: 4096 }),
    })
    .map(({ offset, length }) => ({
        offset,
        length: Math.min(length, ARCHIVE_SIZE - offset),
    }));

describe("CachedPmtilesSource property tests", () => {
    it("any read returns exactly the canonical archive bytes", async () => {
        installFakeCacheApi();
        installStaticArchiveFetch();
        await fc.assert(
            fc.asyncProperty(rangeRead, async ({ offset, length }) => {
                resetCachedPmtilesSourcesForTests();
                const src = new CachedPmtilesSource(ARCHIVE);
                const result = await src.getBytes(offset, length);
                const data = new Uint8Array(result.data);
                expect(data.length).toBe(length);
                for (let i = 0; i < data.length; i++) {
                    if (data[i] !== archiveByte(offset + i)) {
                        throw new Error(`byte ${offset + i}: got ${data[i]}, expected ${archiveByte(offset + i)}`);
                    }
                }
            }),
            { numRuns: 40 }
        );
    });

    it("arbitrary read sequences never return inconsistent bytes", async () => {
        installFakeCacheApi();
        installStaticArchiveFetch();
        await fc.assert(
            fc.asyncProperty(fc.array(rangeRead, { minLength: 2, maxLength: 12 }), async (reads) => {
                resetCachedPmtilesSourcesForTests();
                const src = new CachedPmtilesSource(ARCHIVE);
                for (const { offset, length } of reads) {
                    const result = await src.getBytes(offset, length);
                    const data = new Uint8Array(result.data);
                    expect(data.length).toBe(length);
                    for (let i = 0; i < data.length; i++) {
                        if (data[i] !== archiveByte(offset + i)) {
                            throw new Error(
                                `corruption at pos ${offset + i}: got ${data[i]}, expected ${archiveByte(offset + i)}`
                            );
                        }
                    }
                }
            }),
            { numRuns: 25 }
        );
    });

    it("re-reading any range yields byte-identical results (no cache poisoning)", async () => {
        installFakeCacheApi();
        installStaticArchiveFetch();
        await fc.assert(
            fc.asyncProperty(rangeRead, fc.integer({ min: 2, max: 5 }), async ({ offset, length }, repeats) => {
                resetCachedPmtilesSourcesForTests();
                const src = new CachedPmtilesSource(ARCHIVE);
                const first = new Uint8Array((await src.getBytes(offset, length)).data).slice(0);
                for (let n = 0; n < repeats; n++) {
                    const again = new Uint8Array((await src.getBytes(offset, length)).data);
                    expect(again).toEqual(first);
                }
            }),
            { numRuns: 30 }
        );
    });

    it("overlapping reads of any shape agree in their intersection", async () => {
        installFakeCacheApi();
        installStaticArchiveFetch();
        await fc.assert(
            fc.asyncProperty(rangeRead, rangeRead, async (a, b) => {
                resetCachedPmtilesSourcesForTests();
                const src = new CachedPmtilesSource(ARCHIVE);
                const ra = new Uint8Array((await src.getBytes(a.offset, a.length)).data);
                const rb = new Uint8Array((await src.getBytes(b.offset, b.length)).data);
                const start = Math.max(a.offset, b.offset);
                const end = Math.min(a.offset + a.length, b.offset + b.length);
                for (let p = start; p < end; p++) {
                    const va = ra[p - a.offset];
                    const vb = rb[p - b.offset];
                    expect(va).toBe(vb);
                }
            }),
            { numRuns: 30 }
        );
    });
});
