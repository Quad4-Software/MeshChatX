/**
 * Map coordinate format helpers (WGS84 / UTM / MGRS / Plus Code).
 * Advanced formats require geo-wasm. WGS84 always works without WASM.
 */

import { callGeoWasmJson, isGeoWasmReady, preloadGeoWasm } from "./GeoWasmLoader.js";

export const COORD_FORMATS = Object.freeze(["wgs84", "utm", "mgrs", "olc"]);

let fallbackToastShown = false;

/** Normalize a config/UI format string to a known value. */
export function normalizeCoordinateFormat(format) {
    const f = String(format || "wgs84")
        .toLowerCase()
        .trim();
    return COORD_FORMATS.includes(f) ? f : "wgs84";
}

function normalizeFormat(format) {
    return normalizeCoordinateFormat(format);
}

/** Ensure WASM is loaded when the map needs advanced formats. */
export async function ensureGeoCoordsReady() {
    return preloadGeoWasm();
}

/**
 * Format a WGS84 point for display/copy.
 * @returns {{ text: string, format: string, ok: boolean, error?: string, full?: string, compact?: string }}
 */
export function formatCoordinate(lon, lat, format, options: any = {}) {
    const fmt = normalizeFormat(format);
    const latN = Number(lat);
    const lonN = Number(lon);
    if (!Number.isFinite(latN) || !Number.isFinite(lonN)) {
        return { ok: false, format: fmt, text: "", error: "invalid coordinates" };
    }
    if (fmt === "wgs84") {
        return {
            ok: true,
            format: "wgs84",
            text: `${latN.toFixed(6)}, ${lonN.toFixed(6)}`,
            lat: latN,
            lon: lonN,
        };
    }
    if (!isGeoWasmReady()) {
        return {
            ok: false,
            format: fmt,
            text: `${latN.toFixed(6)}, ${lonN.toFixed(6)}`,
            error: "geo_wasm_unavailable",
            fallback: true,
            lat: latN,
            lon: lonN,
        };
    }
    const payload: any = {
        lat: latN,
        lon: lonN,
        format: fmt,
        hasRef: Boolean(options.hasRef),
        refLat: Number(options.refLat) || 0,
        refLon: Number(options.refLon) || 0,
        codeLen: options.codeLen || 10,
    };
    const res = callGeoWasmJson("meshchatxGeoFormat", payload);
    if (!res || res.ok === false) {
        return {
            ok: false,
            format: fmt,
            text: `${latN.toFixed(6)}, ${lonN.toFixed(6)}`,
            error: res?.error || "format_failed",
            fallback: true,
            lat: latN,
            lon: lonN,
        };
    }
    return res;
}

/**
 * Parse pasted coordinate text into WGS84.
 * @returns {{ ok: boolean, lat?: number, lon?: number, kind?: string, error?: string }}
 */
export function parseCoordinateQuery(text, options: any = {}) {
    const raw = String(text || "").trim();
    if (!raw) {
        return { ok: false, error: "empty" };
    }

    const wgs = tryParseWGS84Local(raw);
    if (wgs) {
        return { ok: true, lat: wgs.lat, lon: wgs.lon, kind: "wgs84" };
    }

    if (!isGeoWasmReady()) {
        if (looksLikeAdvancedCoordinate(raw)) {
            return { ok: false, error: "geo_wasm_unavailable" };
        }
        return { ok: false, error: "parse_failed" };
    }
    const res = callGeoWasmJson("meshchatxGeoParse", {
        text: raw,
        hasRef: Boolean(options.hasRef),
        refLat: Number(options.refLat) || 0,
        refLon: Number(options.refLon) || 0,
    });
    if (!res || res.ok === false) {
        return { ok: false, error: res?.error || "parse_failed" };
    }
    return { ok: true, lat: res.lat, lon: res.lon, kind: res.kind };
}

function tryParseWGS84Local(raw) {
    const cleaned = raw.replace(/,/g, " ");
    const parts = cleaned.trim().split(/\s+/);
    if (parts.length !== 2) return null;
    const lat = Number(parts[0]);
    const lon = Number(parts[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
    return { lat, lon };
}

/** Heuristic: text looks like UTM/MGRS/Plus Code rather than a place name. */
export function looksLikeAdvancedCoordinate(text) {
    const raw = String(text || "").trim();
    if (!raw) return false;
    const compact = raw.replace(/\s+/g, "");
    // Plus Code shape (full or short), not arbitrary strings that happen to contain +.
    if (/^[2-9CFGHJMPQRVWX]{2,8}\+[2-9CFGHJMPQRVWX]{2,}$/i.test(compact)) return true;
    const upper = raw.toUpperCase();
    if (upper.startsWith("UTM") || upper.startsWith("UPS")) return true;
    // Zone+hemi easting northing: 32N 458126 5411198
    if (/^\d{1,2}[A-Z]?\s+[NS]?\s*\d{3,}\s+\d{3,}/i.test(raw)) return true;
    if (/^\d{1,2}[NS]\s+\d{3,}E?\s+\d{3,}N?/i.test(raw)) return true;
    // Compact MGRS-ish (no spaces, digits+letters, length typical of MGRS)
    if (/^[0-9]{1,2}[C-HJ-NP-X][A-Z]{2}[0-9]{2,10}$/i.test(compact)) return true;
    if (/^[ABYZ][A-Z]{2}[0-9]{2,10}$/i.test(compact)) return true;
    return false;
}

/** One-shot toast helper for callers when advanced formats need WASM. */
export function shouldWarnGeoWasmFallback() {
    if (fallbackToastShown || isGeoWasmReady()) {
        return false;
    }
    fallbackToastShown = true;
    return true;
}

/** Reset toast gate (tests). */
export function resetGeoCoordsToastGate() {
    fallbackToastShown = false;
}
