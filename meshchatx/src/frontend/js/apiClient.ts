/**
 * Axios-shaped HTTP helpers backed by fetch (same-origin API calls).
 */

import { fetchCsrfToken, getCsrfToken } from "./csrfToken.js";
import {
    isDemoReadonlyRejection,
    mergeAndSaveDemoUiPrefs,
    mergeConfigWithDemoUiPrefs,
    partialHasDemoUiPrefs,
} from "./demoUiPrefs.js";
import GlobalState from "./GlobalState.js";
import { withRetryableHttp } from "./httpRetry.js";

export type ApiRequestConfig = {
    params?: Record<string, unknown>;
    data?: unknown;
    signal?: AbortSignal;
    headers?: Record<string, string>;
    responseType?: "json" | "blob" | "arraybuffer" | "text";
};

export type ApiResponse<T = unknown> = {
    data: T;
    status: number;
    headers: Headers;
};

export type ApiClient = {
    get: <T = any>(path: string, config?: ApiRequestConfig) => Promise<ApiResponse<T>>;
    head: <T = any>(path: string, config?: ApiRequestConfig) => Promise<ApiResponse<T>>;
    post: <T = any>(path: string, data?: unknown, config?: ApiRequestConfig) => Promise<ApiResponse<T>>;
    patch: <T = any>(path: string, data?: unknown, config?: ApiRequestConfig) => Promise<ApiResponse<T>>;
    put: <T = any>(path: string, data?: unknown, config?: ApiRequestConfig) => Promise<ApiResponse<T>>;
    delete: <T = any>(path: string, config?: ApiRequestConfig) => Promise<ApiResponse<T>>;
    isCancel: (error: unknown) => boolean;
};

export type CreateApiClientOptions = {
    onAuthError?: (err: Error & { response?: { status: number; data: unknown } }) => void;
};

export type DemoConfigPatchResponse = {
    data: { config: Record<string, unknown> };
    status: number;
    headers: Headers;
};

export function isCancel(error: unknown): boolean {
    if (!error) return false;
    return (error as { name?: string }).name === "AbortError" || (error as { name?: string }).name === "CanceledError";
}

function buildUrl(path: string, params?: Record<string, unknown>): string {
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

function apiPathname(path: string): string {
    try {
        return new URL(path, window.location.origin).pathname;
    } catch {
        return path;
    }
}

async function parseErrorBody(response: Response): Promise<unknown> {
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

async function readSuccessBody(response: Response, responseType?: ApiRequestConfig["responseType"]): Promise<unknown> {
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

/** True when a 403 is a CSRF rejection (not a missing login session). */
export function isCsrfRejection(status: number, errData: unknown): boolean {
    if (status !== 403) {
        return false;
    }
    const text =
        (errData &&
            typeof errData === "object" &&
            ((errData as { error?: unknown; message?: unknown }).error ||
                (errData as { message?: unknown }).message)) ||
        (typeof errData === "string" ? errData : "");
    return typeof text === "string" && /csrf/i.test(text);
}

function applyDemoConfigGetOverlay(dataOut: unknown): unknown {
    if (!GlobalState.demoMode || !dataOut || typeof dataOut !== "object") {
        return dataOut;
    }
    const config = (dataOut as { config?: unknown }).config;
    if (!config || typeof config !== "object") {
        return dataOut;
    }
    return {
        ...dataOut,
        config: mergeConfigWithDemoUiPrefs(config as Record<string, unknown>),
    };
}

/** Serve UI-only config writes from localStorage in demo mode. */
function tryDemoConfigPatch(data: unknown): DemoConfigPatchResponse | null {
    if (!GlobalState.demoMode) {
        return null;
    }
    if (!partialHasDemoUiPrefs(data)) {
        return null;
    }
    const saved = mergeAndSaveDemoUiPrefs(data);
    const base = GlobalState.config && typeof GlobalState.config === "object" ? { ...GlobalState.config } : {};
    return {
        data: { config: { ...base, ...saved } },
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
    };
}

export function createApiClient(options: CreateApiClientOptions = {}): ApiClient {
    const { onAuthError } = options;

    async function request<T = any>(
        method: string,
        path: string,
        config: ApiRequestConfig = {},
        csrfRetry = false
    ): Promise<ApiResponse<T>> {
        const { params, data, signal, headers = {}, responseType } = config;
        const pathname = apiPathname(path);

        if (method === "PATCH" && pathname === "/api/v1/config") {
            const demoResponse = tryDemoConfigPatch(data);
            if (demoResponse) {
                return demoResponse as unknown as ApiResponse<T>;
            }
        }

        const url = buildUrl(path, params);
        const hdrs = new Headers(headers);
        if (method !== "GET" && method !== "HEAD" && path.startsWith("/api/")) {
            const csrf = getCsrfToken();
            if (csrf) {
                hdrs.set("X-CSRF-Token", csrf);
            }
        }
        const init: RequestInit = { method, signal, headers: hdrs };

        if (data !== undefined && method !== "GET" && method !== "HEAD") {
            if (data instanceof FormData) {
                hdrs.delete("Content-Type");
                hdrs.delete("content-type");
                init.body = data;
            } else if (typeof data === "string" || data instanceof Blob || data instanceof ArrayBuffer) {
                init.body = data as BodyInit;
            } else {
                if (!hdrs.has("Content-Type")) {
                    hdrs.set("Content-Type", "application/json");
                }
                init.body = JSON.stringify(data);
            }
        }

        let response: Response;
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
                        get(csrfPath: string) {
                            return request("GET", csrfPath, {});
                        },
                    });
                } catch {
                    // Fall through and surface the original CSRF error.
                    throw err;
                }
                return request(method, path, config, true);
            }

            // Demo read-only 403s are not auth failures. Config UI prefs are
            // handled above; other mutations surface as normal errors.
            if (
                onAuthError &&
                (response.status === 401 || response.status === 403) &&
                !isCsrfRejection(response.status, errData) &&
                !isDemoReadonlyRejection(errData)
            ) {
                onAuthError(err);
            }
            throw err;
        }

        let dataOut = await readSuccessBody(response, responseType);
        if (method === "GET" && pathname === "/api/v1/config") {
            dataOut = applyDemoConfigGetOverlay(dataOut);
        }
        return { data: dataOut as T, status: response.status, headers: response.headers };
    }

    const api: ApiClient = {
        get<T = any>(path: string, config?: ApiRequestConfig) {
            const cfg = config || {};
            return withRetryableHttp(() => request<T>("GET", path, cfg), {
                signal: cfg.signal,
            });
        },
        head<T = any>(path: string, config?: ApiRequestConfig) {
            const cfg = config || {};
            return withRetryableHttp(() => request<T>("HEAD", path, cfg), {
                signal: cfg.signal,
            });
        },
        post<T = any>(path: string, data?: unknown, config = {}) {
            return request<T>("POST", path, { ...config, data });
        },
        patch<T = any>(path: string, data?: unknown, config = {}) {
            return request<T>("PATCH", path, { ...config, data });
        },
        put<T = any>(path: string, data?: unknown, config = {}) {
            return request<T>("PUT", path, { ...config, data });
        },
        delete<T = any>(path: string, config = {}) {
            return request<T>("DELETE", path, config || {});
        },
        isCancel,
    };

    return api;
}
