// SPDX-License-Identifier: 0BSD

/**
 * In-memory Cache Storage double for shell runtime tests.
 */

function requestKey(request) {
    if (typeof request === "string") {
        return request;
    }
    if (request && typeof request.url === "string") {
        return request.url;
    }
    return String(request);
}

export class MemoryCache {
    constructor() {
        this.map = new Map();
    }

    async match(request) {
        const key = requestKey(request);
        const hit = this.map.get(key);
        return hit ? hit.clone() : undefined;
    }

    async put(request, response) {
        this.map.set(requestKey(request), response.clone());
    }

    async keys() {
        return [...this.map.keys()].map((url) => ({ url }));
    }

    urls() {
        return [...this.map.keys()];
    }
}

export class MemoryCacheStorage {
    constructor() {
        this.stores = new Map();
    }

    async open(name) {
        if (!this.stores.has(name)) {
            this.stores.set(name, new MemoryCache());
        }
        return this.stores.get(name);
    }

    async keys() {
        return [...this.stores.keys()];
    }

    async delete(name) {
        return this.stores.delete(name);
    }

    async match(request) {
        for (const cache of this.stores.values()) {
            const hit = await cache.match(request);
            if (hit) {
                return hit;
            }
        }
        return undefined;
    }

    allUrls() {
        const urls = [];
        for (const cache of this.stores.values()) {
            urls.push(...cache.urls());
        }
        return urls;
    }
}

export function okResponse(body, init = {}) {
    return new Response(body, {
        status: 200,
        statusText: "OK",
        headers: { "content-type": "text/plain", ...(init.headers || {}) },
        ...init,
    });
}

export function makeRequest(url, init = {}) {
    const headers = new Headers(init.headers || {});
    return {
        url,
        method: init.method || "GET",
        mode: init.mode || "cors",
        destination: init.destination || "",
        headers,
    };
}
