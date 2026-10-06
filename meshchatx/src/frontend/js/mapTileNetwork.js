import TileJSON from "ol/source/TileJSON";

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export const TILE_FETCH_TIMEOUT_MS = 8000;
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
    let base = normalizeHttpBaseUrl(nominatimApiUrl);
    // Scheme-less hosts or //host paths would resolve relative to the app origin.
    if (base && !base.includes("://")) {
        base = `https://${base.replace(/^\/+/, "")}`;
    }
    const enc = encodeURIComponent(searchQuery);
    return `${base}/search?format=json&q=${enc}&limit=${limit}&addressdetails=1`;
}

export function lonLatToTileXY(lon, lat, zoom) {
    const z = Math.max(0, Math.floor(Number(zoom) || 0));
    const n = 2 ** z;
    let x = Math.floor(((Number(lon) + 180) / 360) * n);
    x = ((x % n) + n) % n;
    const latClamped = Math.max(-85.05112878, Math.min(85.05112878, Number(lat)));
    const latRad = (latClamped * Math.PI) / 180;
    let y = Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n);
    y = Math.max(0, Math.min(n - 1, y));
    return { z, x, y, n };
}

export function neighborTileCoords(lon, lat, zoom, ring = 1) {
    const { z, x, y, n } = lonLatToTileXY(lon, lat, zoom);
    const out = [];
    const r = Math.max(0, Math.floor(ring));
    for (let dx = -r; dx <= r; dx++) {
        for (let dy = -r; dy <= r; dy++) {
            const xx = (((x + dx) % n) + n) % n;
            const yy = y + dy;
            if (yy < 0 || yy >= n) {
                continue;
            }
            out.push({ z, x: xx, y: yy });
        }
    }
    return out;
}

export function resolveTileJsonTileUrls(doc, docUrl) {
    // TileJSON allows relative tile URL templates; resolve them against the
    // document URL so OpenLayers fetches the tile host instead of the app origin.
    if (!doc || typeof doc !== "object" || !Array.isArray(doc.tiles)) {
        return doc;
    }
    // OpenLayers ignores scheme:tms. Flip the y template to {-y} (grid max
    // minus y), which is the standard-XYZ equivalent of a TMS row order.
    const isTms = doc.scheme === "tms";
    const tiles = doc.tiles.map((t) => {
        // OpenLayers only expands {z}/{x}/{y}/{-y}/{a-c}; Leaflet style
        // {s} and {r} placeholders would stay literal in request URLs.
        let template = String(t).replaceAll("{s}", "{a-c}").replaceAll("{r}", "");
        if (isTms) {
            template = template.replaceAll("{y}", "{-y}");
        }
        try {
            // URL percent-encodes { } in paths; restore template placeholders.
            return new URL(template, docUrl).href.replaceAll("%7B", "{").replaceAll("%7D", "}");
        } catch {
            return template;
        }
    });
    return { ...doc, tiles };
}

export class ResolvedTileJSON extends TileJSON {
    constructor(options) {
        const docUrl = options && options.url ? String(options.url) : "";
        super(options);
        this.docUrl_ = docUrl;
    }

    handleTileJSONResponse(doc) {
        super.handleTileJSONResponse(resolveTileJsonTileUrls(doc, this.docUrl_));
    }
}

export function expandTileUrl(template, z, x, y) {
    if (
        typeof template !== "string" ||
        !template.includes("{z}") ||
        !template.includes("{x}") ||
        !template.includes("{y}")
    ) {
        return "";
    }
    return template
        .replaceAll("{z}", String(z))
        .replaceAll("{x}", String(x))
        .replaceAll("{y}", String(y))
        .replaceAll("{r}", "");
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
