/**
 * Axios-shaped HTTP helpers backed by fetch (same-origin API calls).
 */

import { fetchCsrfToken, getCsrfToken } from "./csrfToken.js";
import { withRetryableHttp } from "./httpRetry.js";

export function isCancel(error) {
    if (!error) return false;
    return error.name === "AbortError" || error.name === "CanceledError";
}

function buildUrl(path, params) {
    if (!params || typeof params !== "object" || Object.keys(params).length === 0) {
        return path;
    }
    const u = new URL(path, window.location.origin);
    for (const [k, v] of Object.entries(params)) {
        if (v === undefined || v === null) continue;
        if (Array.isArray(v)) {
            for (const item of v) {
                u.searchParams.append(k, String(item));
            }
        } else {
            u.searchParams.set(k, String(v));
        }
    }
    return `${u.pathname}${u.search}${u.hash}`;
}

async function parseErrorBody(response) {
    const ct = response.headers.get("content-type") || "";
    try {
        if (ct.includes("application/json")) {
            const text = await response.text();
            return text ? JSON.parse(text) : null;
        }
        const text = await response.text();
        if (!text) return { message: response.statusText };
        try {
            return JSON.parse(text);
        } catch {
            return { message: text };
        }
    } catch {
        return null;
    }
}

async function readSuccessBody(response, responseType) {
    if (response.status === 204 || response.status === 205) {
        return null;
    }
    if (responseType === "blob") {
        return response.blob();
    }
    if (responseType === "arraybuffer") {
        return response.arrayBuffer();
    }
    const ct = response.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
        const text = await response.text();
        return text ? JSON.parse(text) : null;
    }
    return response.text();
}

/**
 * True when a 403 is a CSRF rejection (not a missing login session).
 * @param {number} status
 * @param {unknown} errData
 * @returns {boolean}
 */
export function isCsrfRejection(status, errData) {
    if (status !== 403) {
        return false;
    }
    const text =
        (errData && typeof errData === "object" && (errData.error || errData.message)) ||
        (typeof errData === "string" ? errData : "");
    return typeof text === "string" && /csrf/i.test(text);
}

/**
 * @param {{ onAuthError?: (err: Error & { response?: { status: number, data: unknown } }) => void }} options
 */
export function createApiClient(options = {}) {
    const { onAuthError } = options;

    async function request(method, path, config = {}, csrfRetry = false) {
        const { params, data, signal, headers = {}, responseType } = config;
        const url = buildUrl(path, params);
        const hdrs = new Headers(headers);
        if (method !== "GET" && method !== "HEAD" && path.startsWith("/api/")) {
            const csrf = getCsrfToken();
            if (csrf) {
                hdrs.set("X-CSRF-Token", csrf);
            }
        }
        const init = { method, signal, headers: hdrs };

        if (data !== undefined && method !== "GET" && method !== "HEAD") {
            if (data instanceof FormData) {
                hdrs.delete("Content-Type");
                hdrs.delete("content-type");
                init.body = data;
            } else if (typeof data === "string" || data instanceof Blob || data instanceof ArrayBuffer) {
                init.body = data;
            } else {
                if (!hdrs.has("Content-Type")) {
                    hdrs.set("Content-Type", "application/json");
                }
                init.body = JSON.stringify(data);
            }
        }

        let response;
        try {
            response = await fetch(url, init);
        } catch (e) {
            if (isCancel(e)) throw e;
            throw e;
        }

        if (!response.ok) {
            const errData = await parseErrorBody(response);
            const err = Object.assign(new Error(`HTTP ${response.status}`), {
                name: "HttpError",
                response: { status: response.status, data: errData },
            });

            const mutating = method !== "GET" && method !== "HEAD" && path.startsWith("/api/");
            if (mutating && !csrfRetry && isCsrfRejection(response.status, errData)) {
                try {
                    await fetchCsrfToken({
                        get(csrfPath) {
                            return request("GET", csrfPath, {});
                        },
                    });
                } catch {
                    // Fall through and surface the original CSRF error.
                    throw err;
                }
                return request(method, path, config, true);
            }

            if (onAuthError && (response.status === 401 || response.status === 403)) {
                if (!isCsrfRejection(response.status, errData)) {
                    onAuthError(err);
                }
            }
            throw err;
        }

        const dataOut = await readSuccessBody(response, responseType);
        return { data: dataOut, status: response.status, headers: response.headers };
    }

    const api = {
        get(path, config) {
            const cfg = config || {};
            return withRetryableHttp(() => request("GET", path, cfg), {
                signal: cfg.signal,
            });
        },
        head(path, config) {
            const cfg = config || {};
            return withRetryableHttp(() => request("HEAD", path, cfg), {
                signal: cfg.signal,
            });
        },
        post(path, data, config = {}) {
            return request("POST", path, { ...config, data });
        },
        patch(path, data, config = {}) {
            return request("PATCH", path, { ...config, data });
        },
        put(path, data, config = {}) {
            return request("PUT", path, { ...config, data });
        },
        delete(path, config = {}) {
            return request("DELETE", path, config || {});
        },
        isCancel,
    };

    return api;
}
