const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export const TILE_FETCH_TIMEOUT_MS = 22000;
export const TILE_FETCH_RETRIES = 2;
export const TILE_FETCH_RETRY_BASE_DELAY_MS = 450;

export const NOMINATIM_FETCH_TIMEOUT_MS = 16000;
export const NOMINATIM_FETCH_RETRIES = 1;
export const NOMINATIM_FETCH_RETRY_BASE_DELAY_MS = 500;

export function normalizeHttpBaseUrl(url) {
    if (!url || typeof url !== "string") return "";
    return url.endsWith("/") ? url.slice(0, -1) : url;
}

export function buildNominatimSearchUrl(nominatimApiUrl, searchQuery, limit = 10) {
    const base = normalizeHttpBaseUrl(nominatimApiUrl);
    const enc = encodeURIComponent(searchQuery);
    return `${base}/search?format=json&q=${enc}&limit=${limit}&addressdetails=1`;
}

export async function fetchWithTimeout(resource, init = {}, timeoutMs = TILE_FETCH_TIMEOUT_MS) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);
    try {
        return await fetch(resource, { ...init, signal: controller.signal });
    } finally {
        clearTimeout(id);
    }
}

export async function fetchTileBlobWithRetry(url, init = {}, options = {}) {
    const timeoutMs = options.timeoutMs ?? TILE_FETCH_TIMEOUT_MS;
    const retries = options.retries ?? TILE_FETCH_RETRIES;
    const baseDelay = options.retryBaseDelayMs ?? TILE_FETCH_RETRY_BASE_DELAY_MS;
    let lastErr;
    for (let attempt = 0; attempt <= retries; attempt++) {
        if (attempt > 0) await delay(baseDelay * attempt);
        try {
            const response = await fetchWithTimeout(url, init, timeoutMs);
            if (!response.ok) {
                return { ok: false, status: response.status, error: new Error(`HTTP ${response.status}`) };
            }
            const blob = await response.blob();
            return { ok: true, blob };
        } catch (e) {
            lastErr = e;
        }
    }
    return { ok: false, error: lastErr };
}

export async function fetchJsonWithRetry(url, init = {}, options = {}) {
    const timeoutMs = options.timeoutMs ?? NOMINATIM_FETCH_TIMEOUT_MS;
    const retries = options.retries ?? NOMINATIM_FETCH_RETRIES;
    const baseDelay = options.retryBaseDelayMs ?? NOMINATIM_FETCH_RETRY_BASE_DELAY_MS;
    let lastErr;
    for (let attempt = 0; attempt <= retries; attempt++) {
        if (attempt > 0) await delay(baseDelay * attempt);
        try {
            const response = await fetchWithTimeout(url, init, timeoutMs);
            if (!response.ok) {
                return { ok: false, status: response.status, error: new Error(`HTTP ${response.status}`) };
            }
            return { ok: true, response };
        } catch (e) {
            lastErr = e;
        }
    }
    return { ok: false, error: lastErr };
}
