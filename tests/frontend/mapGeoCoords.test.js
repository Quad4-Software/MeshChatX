import { describe, expect, it, beforeEach } from "vitest";
import {
    formatCoordinate,
    normalizeCoordinateFormat,
    parseCoordinateQuery,
    looksLikeAdvancedCoordinate,
    resetGeoCoordsToastGate,
    shouldWarnGeoWasmFallback,
    COORD_FORMATS,
} from "../../meshchatx/src/frontend/js/mapGeoCoords.js";

describe("mapGeoCoords", () => {
    beforeEach(() => {
        resetGeoCoordsToastGate();
        globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ = false;
        delete globalThis.meshchatxGeoFormat;
        delete globalThis.meshchatxGeoParse;
        delete globalThis.meshchatxGeoLatLonToGrid;
    });

    it("lists supported formats", () => {
        expect(COORD_FORMATS).toContain("wgs84");
        expect(COORD_FORMATS).toContain("utm");
        expect(COORD_FORMATS).toContain("mgrs");
        expect(COORD_FORMATS).toContain("olc");
    });

    it("normalizes unknown formats to wgs84", () => {
        expect(normalizeCoordinateFormat("UTM")).toBe("utm");
        expect(normalizeCoordinateFormat("nope")).toBe("wgs84");
        expect(normalizeCoordinateFormat("")).toBe("wgs84");
        expect(normalizeCoordinateFormat(null)).toBe("wgs84");
    });

    it("formats WGS84 without WASM using lon,lat argument order", () => {
        // API is formatCoordinate(lon, lat, format). Display text is "lat, lon".
        const res = formatCoordinate(36.817223, -1.286386, "wgs84");
        expect(res.ok).toBe(true);
        expect(res.text).toBe("-1.286386, 36.817223");
        expect(res.lat).toBeCloseTo(-1.286386, 5);
        expect(res.lon).toBeCloseTo(36.817223, 5);
    });

    it("parses WGS84 without WASM as lat,lon text", () => {
        const res = parseCoordinateQuery("-1.286386, 36.817223");
        expect(res.ok).toBe(true);
        expect(res.kind).toBe("wgs84");
        expect(res.lat).toBeCloseTo(-1.286386, 5);
        expect(res.lon).toBeCloseTo(36.817223, 5);
    });

    it("oracle: WGS84 format text round-trips through parse", () => {
        const lon = 5.892;
        const lat = 52.658;
        const formatted = formatCoordinate(lon, lat, "wgs84");
        expect(formatted.ok).toBe(true);
        const parsed = parseCoordinateQuery(formatted.text);
        expect(parsed.ok).toBe(true);
        expect(parsed.lat).toBeCloseTo(lat, 5);
        expect(parsed.lon).toBeCloseTo(lon, 5);
    });

    it("oracle: reject out-of-range WGS84", () => {
        expect(parseCoordinateQuery("91, 0").ok).toBe(false);
        expect(parseCoordinateQuery("0, 181").ok).toBe(false);
        expect(parseCoordinateQuery("").error).toBe("empty");
    });

    it("falls back when UTM requested without WASM", () => {
        const res = formatCoordinate(5.892, 52.658, "utm");
        expect(res.ok).toBe(false);
        expect(res.fallback).toBe(true);
        expect(res.error).toBe("geo_wasm_unavailable");
    });

    it("returns geo_wasm_unavailable for Plus Code paste without WASM", () => {
        const res = parseCoordinateQuery("6GCRPR78+CV");
        expect(res.ok).toBe(false);
        expect(res.error).toBe("geo_wasm_unavailable");
    });

    it("does not block place-name search when WASM is missing", () => {
        const res = parseCoordinateQuery("test search");
        expect(res.ok).toBe(false);
        expect(res.error).toBe("parse_failed");
    });

    it("oracle: looksLikeAdvancedCoordinate accept/reject matrix", () => {
        const accept = [
            "6GCRPR78+CV",
            "PR78+CV",
            "UTM 32N 458126 5411198",
            "32N 458126 5411198",
            "32N 458126E 5411198N",
            "UPS N 2000000 2000000",
            "31U DQ 48251 11958",
            "31UDQ4825111958",
        ];
        const reject = ["test search", "Berlin", "hello world", "12 Main Street", "42", "hello+world", "C++ tutorial"];
        for (const raw of accept) {
            expect(looksLikeAdvancedCoordinate(raw), `accept ${raw}`).toBe(true);
        }
        for (const raw of reject) {
            expect(looksLikeAdvancedCoordinate(raw), `reject ${raw}`).toBe(false);
        }
    });

    it("does not treat arbitrary plus strings as advanced coords without WASM", () => {
        const res = parseCoordinateQuery("C++ tutorial");
        expect(res.ok).toBe(false);
        expect(res.error).toBe("parse_failed");
    });

    it("shouldWarnGeoWasmFallback only once until reset", () => {
        expect(shouldWarnGeoWasmFallback()).toBe(true);
        expect(shouldWarnGeoWasmFallback()).toBe(false);
        resetGeoCoordsToastGate();
        expect(shouldWarnGeoWasmFallback()).toBe(true);
    });

    it("uses mocked WASM parse when ready", () => {
        globalThis.meshchatxGeoFormat = () => "{}";
        globalThis.meshchatxGeoParse = () => JSON.stringify({ ok: true, lat: -1.286, lon: 36.817, kind: "olc" });
        globalThis.meshchatxGeoLatLonToGrid = () => "{}";
        const res = parseCoordinateQuery("6GCRPR78+CV");
        expect(res.ok).toBe(true);
        expect(res.kind).toBe("olc");
        expect(res.lat).toBeCloseTo(-1.286, 3);
        expect(res.lon).toBeCloseTo(36.817, 3);
    });
});
