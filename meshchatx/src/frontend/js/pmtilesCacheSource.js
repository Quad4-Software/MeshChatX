// SPDX-License-Identifier: 0BSD
/**
 * Caching pmtiles Source for remote archives fetched via HTTP range requests.
 *
 * Layers, cheap to expensive:
 *  1. In-memory LRU of raw ArrayBuffer ranges (hot tile/directory bytes).
 *  2. The Cache API for persistence across reloads, keyed by archive URL plus
 *     a fingerprint so a changed archive invalidates old entries.
 *  3. Conditional range revalidation: the server is cross-origin without
 *     Access-Control-Expose-Headers, so ETag is unreadable. Last-Modified and
 *     Cache-Control are CORS-safelisted and readable, so entries carry a
 *     Last-Modified validator used with If-Range plus a hash of the first
 *     127 header bytes as fallback change detection.
 *  4. In-flight dedupe so concurrent identical ranges cost one request, and
 *     abort of the shared request once every waiter has cancelled.
 *
 * The archive fingerprint prefers the response ETag when readable
 * (same-origin deployments), then Last-Modified, then a fast hash of the
 * first 127 PMTiles header bytes (magic, root directory offset/length and
 * tile counts all change when the archive is rebuilt).
 */
const CACHE_NAME = "meshchatx-pmtiles-v1";
const INDEX_KEY = "__index__";
const MEM_CAP_ENTRIES = 400;
const MEM_CAP_BYTES = 48 * 1024 * 1024;
const PERSIST_CAP_BYTES = 256 * 1024 * 1024;
const REVALIDATE_LEN = 127;
const DEFAULT_MAX_AGE_MS = 3600 * 1000;
const STALE_GRACE_MS = 24 * 3600 * 1000;

function supportsCacheApi() {
    return typeof caches !== "undefined" && typeof caches.open === "function";
}

function storageKey(url, offset, length) {
    return `${url}|${offset}|${length}`;
}

function fastHash(data) {
    const v = new DataView(data.buffer ? data : new Uint8Array(data).buffer);
    let h = 0x811c9dc5;
    const n = v.byteLength;
    for (let i = 0; i < n; i++) {
        h ^= v.getUint8(i);
        h = Math.imul(h, 0x01000193);
    }
    return (h >>> 0).toString(16);
}

function parseMaxAge(cacheControl) {
    if (!cacheControl) return null;
    const m = /max-age\s*=\s*(\d+)/i.exec(cacheControl);
    return m ? parseInt(m[1], 10) * 1000 : null;
}

class MemLru {
    constructor() {
        this.map = new Map();
        this.bytes = 0;
    }
    get(key) {
        const e = this.map.get(key);
        if (!e) return null;
        this.map.delete(key);
        this.map.set(key, e);
        return e;
    }
    set(key, data) {
        const e = this.map.get(key);
        if (e) this.bytes -= e.data.byteLength;
        this.map.delete(key);
        this.map.set(key, { data });
        this.bytes += data.byteLength;
        while (this.map.size > MEM_CAP_ENTRIES || this.bytes > MEM_CAP_BYTES) {
            const oldest = this.map.keys().next().value;
            if (oldest === undefined) break;
            this.bytes -= this.map.get(oldest).data.byteLength;
            this.map.delete(oldest);
        }
    }
    clear() {
        this.map.clear();
        this.bytes = 0;
    }
}

export class CachedPmtilesSource {
    /**
     * @param {string} url remote archive URL
     * @param {Headers} [customHeaders] extra headers for every request
     */
    constructor(url, customHeaders = new Headers()) {
        this.url = url;
        this.customHeaders = customHeaders;
        this.mem = new MemLru();
        this.inflight = new Map();
        /** @type {Promise<{etag:string|null,lastModified:string|null,maxAge:number,fingerprint:string,fetchedAt:number}|null>} */
        this.metaPromise = null;
        this._cache = null;
        this._indexPromise = null;
    }

    getKey() {
        return this.url;
    }

    async _openCache() {
        if (!supportsCacheApi()) return null;
        if (!this._cache) {
            this._cache = caches.open(CACHE_NAME).catch(() => null);
        }
        return this._cache;
    }

    _cacheUrl(key) {
        return `https://pmtiles-cache.invalid/${encodeURIComponent(this.url)}/${encodeURIComponent(key)}`;
    }

    async _readIndex() {
        if (!this._indexPromise) {
            this._indexPromise = (async () => {
                const cache = await this._openCache();
                if (!cache) return {};
                try {
                    const resp = await cache.match(this._cacheUrl(INDEX_KEY));
                    if (!resp) return {};
                    return await resp.json();
                } catch {
                    return {};
                }
            })();
        }
        return this._indexPromise;
    }

    async _writeIndex(index) {
        const cache = await this._openCache();
        if (!cache) return;
        try {
            await cache.put(
                this._cacheUrl(INDEX_KEY),
                new Response(JSON.stringify(index), { headers: { "content-type": "application/json" } })
            );
        } catch {
            /* quota or opaque errors are non-fatal for a cache */
        }
    }

    async _persistGet(key, fingerprint) {
        const index = await this._readIndex();
        const ent = index[key];
        if (!ent || ent.fp !== fingerprint) return null;
        const cache = await this._openCache();
        if (!cache) return null;
        try {
            const resp = await cache.match(this._cacheUrl(`${ent.fp}/${key}`));
            if (!resp || !resp.ok) return null;
            const data = await resp.arrayBuffer();
            index[key].t = Date.now();
            void this._writeIndex(index);
            return data;
        } catch {
            return null;
        }
    }

    async _persistSet(key, fingerprint, data) {
        const index = await this._readIndex();
        const cache = await this._openCache();
        if (!cache) return;
        try {
            await cache.put(this._cacheUrl(`${fingerprint}/${key}`), new Response(data.slice(0)));
            index[key] = { fp: fingerprint, t: Date.now(), size: data.byteLength };
            let total = 0;
            for (const k of Object.keys(index)) total += index[k].size || 0;
            while (total > PERSIST_CAP_BYTES) {
                let oldestKey = null;
                let oldestT = Infinity;
                for (const k of Object.keys(index)) {
                    if (index[k].t < oldestT) {
                        oldestT = index[k].t;
                        oldestKey = k;
                    }
                }
                if (!oldestKey) break;
                try {
                    await cache.delete(this._cacheUrl(`${index[oldestKey].fp}/${oldestKey}`));
                } catch {
                    /* non-fatal */
                }
                total -= index[oldestKey].size || 0;
                delete index[oldestKey];
            }
            void this._writeIndex(index);
        } catch {
            /* non-fatal */
        }
    }

    async _persistInvalidate(fp) {
        const index = await this._readIndex();
        const cache = await this._openCache();
        if (cache) {
            const doomed = Object.keys(index).filter((k) => index[k].fp !== fp);
            for (const k of doomed) {
                try {
                    await cache.delete(this._cacheUrl(`${index[k].fp}/${k}`));
                } catch {
                    /* non-fatal */
                }
                delete index[k];
            }
            void this._writeIndex(index);
        }
        this.mem.clear();
    }

    async _fetchRange(offset, length, signal, extraHeaders) {
        const headers = new Headers(this.customHeaders);
        headers.set("range", `bytes=${offset}-${offset + length - 1}`);
        if (extraHeaders) {
            for (const [k, v] of Object.entries(extraHeaders)) headers.set(k, v);
        }
        const resp = await fetch(this.url, { signal, headers });
        if (resp.status === 200) {
            const cl = resp.headers.get("Content-Length");
            if (!cl || +cl > length) {
                resp.body?.cancel();
                throw new Error("Server does not support byte serving");
            }
        }
        if (resp.status >= 300 && resp.status !== 304) {
            throw new Error(`Bad response code: ${resp.status}`);
        }
        const data = await resp.arrayBuffer();
        return {
            data,
            etag: resp.headers.get("etag"),
            lastModified: resp.headers.get("last-modified"),
            cacheControl: resp.headers.get("cache-control"),
            expires: resp.headers.get("expires"),
            status: resp.status,
        };
    }

    /**
     * Archive metadata: ETag if readable, else Last-Modified, else a hash of
     * the first 127 header bytes. Refreshes when Cache-Control says stale.
     */
    async _meta() {
        if (!this.metaPromise) {
            this.metaPromise = this._loadMeta().catch(() => {
                this.metaPromise = null;
                return null;
            });
        }
        return this.metaPromise;
    }

    async _loadMeta() {
        const resp = await this._fetchRange(0, REVALIDATE_LEN, undefined, undefined);
        return {
            etag: resp.etag && !resp.etag.startsWith("W/") ? resp.etag : null,
            lastModified: resp.lastModified,
            maxAge: parseMaxAge(resp.cacheControl) ?? DEFAULT_MAX_AGE_MS,
            fingerprint: resp.etag && !resp.etag.startsWith("W/") ? resp.etag : fastHash(resp.data),
            fetchedAt: Date.now(),
        };
    }

    /**
     * Cheap change probe: one 127-byte range request. If-Range with the stored
     * Last-Modified makes an unchanged archive return 206 with the bytes. A
     * changed one returns the full entity (200), which is aborted. ETag,
     * Last-Modified and finally a hash of the probe bytes cover servers that
     * ignore If-Range. Returns {changed, newFp}.
     */
    async _revalidate(meta) {
        try {
            const headers = new Headers(this.customHeaders);
            headers.set("range", `bytes=0-${REVALIDATE_LEN - 1}`);
            if (meta.lastModified) headers.set("if-range", meta.lastModified);
            const resp = await fetch(this.url, { headers });
            meta.fetchedAt = Date.now();
            if (resp.status === 200) {
                resp.body?.cancel();
                return { changed: true, newFp: `changed:${Date.now()}` };
            }
            if (resp.status !== 206 && resp.status !== 304) return { changed: false };
            const rEtag = resp.headers.get("etag");
            const rLm = resp.headers.get("last-modified");
            const data = resp.status === 206 ? await resp.arrayBuffer() : null;
            if (rEtag && meta.etag && rEtag !== meta.etag) {
                return { changed: true, newFp: rEtag };
            }
            if (rLm && meta.lastModified && rLm !== meta.lastModified) {
                return { changed: true, newFp: (rEtag && !rEtag.startsWith("W/")) || `lm:${rLm}` };
            }
            if (!meta.etag && data) {
                const newFp = fastHash(data);
                if (newFp !== meta.fingerprint) return { changed: true, newFp };
            }
            if (rEtag && !rEtag.startsWith("W/")) {
                meta.etag = rEtag;
                meta.fingerprint = rEtag;
            }
            if (rLm) meta.lastModified = rLm;
            const maxAge = parseMaxAge(resp.headers.get("cache-control"));
            if (maxAge !== null) meta.maxAge = maxAge;
            return { changed: false };
        } catch {
            return { changed: false }; // probe failed: keep serving stale
        }
    }

    /**
     * Revalidate when stale. Within the grace window the probe runs in the
     * background so the first paint never waits. Beyond it the caller must
     * await before serving. Returns true if cached entries may be served.
     */
    async _freshen(meta, miss) {
        if (!meta) return;
        const age = Date.now() - meta.fetchedAt;
        if (age < meta.maxAge) return;
        const apply = async () => {
            const r = await this._revalidate(meta);
            if (r.changed) {
                meta.fingerprint = r.newFp;
                meta.fetchedAt = Date.now();
                await this._persistInvalidate(r.newFp);
            }
        };
        if (miss || age > meta.maxAge + STALE_GRACE_MS) {
            await apply();
        } else {
            meta.fetchedAt = Date.now(); // revalidate at most once per window
            void apply();
        }
    }

    /**
     * Fetch one range and persist under the current fingerprint.
     */
    _fetchAndStore(key, offset, length, signal, meta) {
        return this._fetchRange(offset, length, signal).then(async (resp) => {
            if (resp.etag && !resp.etag.startsWith("W/") && meta) {
                meta.etag = resp.etag;
                meta.fingerprint = resp.etag;
            }
            if (meta && resp.lastModified && !meta.lastModified) {
                meta.lastModified = resp.lastModified;
            }
            this.mem.set(key, resp.data);
            void this._persistSet(key, meta ? meta.fingerprint : "nofp", resp.data);
            return resp;
        });
    }

    /**
     * pmtiles Source contract. Returns the byte range plus optional validator
     * hints, deduping in-flight requests and serving from cache when fresh.
     */
    // eslint-disable-next-line no-unused-vars -- pmtiles Source contract
    async getBytes(offset, length, passedSignal, etag) {
        const key = storageKey(this.url, offset, length);
        const meta = await this._meta();
        const fp = () => (meta ? meta.fingerprint : "nofp");
        const hit = this.mem.get(key);
        if (hit && hit.fp === fp()) {
            await this._freshen(meta, false);
            // _freshen may have invalidated. Re-check before serving.
            const still = this.mem.get(key);
            if (still && still.fp === fp()) {
                return { data: still.data.slice(0) };
            }
        }
        if (!this.mem.get(key) || this.mem.get(key).fp !== fp()) {
            await this._freshen(meta, true);
            const persisted = await this._persistGet(key, fp());
            if (persisted) {
                this.mem.set(key, persisted);
                this.mem.get(key).fp = fp();
                // Callers may transfer the returned buffer into a worker
                // (MapLibre tile decode). A detached cached copy would make
                // later hits throw on slice, so hand out a copy.
                return { data: persisted.slice(0) };
            }
        }
        let flight = this.inflight.get(key);
        if (!flight) {
            const controller = new AbortController();
            const waiters = new Set();
            const promise = this._fetchAndStore(key, offset, length, controller.signal, meta)
                .then((resp) => ({
                    data: resp.data,
                    cacheControl: resp.cacheControl,
                    expires: resp.expires,
                    etag: resp.etag,
                }))
                .finally(() => {
                    this.inflight.delete(key);
                });
            flight = { promise, controller, waiters };
            this.inflight.set(key, flight);
        }
        const waiter = { signal: passedSignal };
        flight.waiters.add(waiter);
        const onAbort = () => {
            flight.waiters.delete(waiter);
            if (flight.waiters.size === 0) {
                flight.controller.abort();
                this.inflight.delete(key);
            }
        };
        if (passedSignal) {
            if (passedSignal.aborted) {
                onAbort();
                throw new DOMException("Aborted", "AbortError");
            }
            passedSignal.addEventListener("abort", onAbort, { once: true });
        }
        try {
            const resp = await flight.promise;
            if (this.mem.get(key)) this.mem.get(key).fp = fp();
            // Return a copy: consumers can transfer the buffer into a worker,
            // which would detach the copy held in the LRU.
            return {
                data: resp.data.slice(0),
                cacheControl: resp.cacheControl,
                expires: resp.expires,
                etag: resp.etag,
            };
        } finally {
            if (passedSignal) passedSignal.removeEventListener("abort", onAbort);
            flight.waiters.delete(waiter);
        }
    }
}

/** One shared source per archive URL so header/directory and tile caches are shared. */
const sources = new Map();

export function getCachedPmtilesSource(url) {
    let src = sources.get(url);
    if (!src) {
        src = new CachedPmtilesSource(url);
        sources.set(url, src);
    }
    return src;
}

/** Test hook: drop all shared sources and their caches. */
export function resetCachedPmtilesSourcesForTests() {
    sources.clear();
}
