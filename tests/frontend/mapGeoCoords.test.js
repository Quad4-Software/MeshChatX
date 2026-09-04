import { describe, expect, it, beforeEach } from "vitest";
import {
    formatCoordinate,
    normalizeCoordinateFormat,
    parseCoordinateQuery,
    resetGeoCoordsToastGate,
    COORD_FORMATS,
} from "../../meshchatx/src/frontend/js/mapGeoCoords.js";

describe("mapGeoCoords", () => {
    beforeEach(() => {
        resetGeoCoordsToastGate();
        globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ = false;
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

    it("formats WGS84 without WASM", () => {
        const res = formatCoordinate(36.817223, -1.286386, "wgs84");
        expect(res.ok).toBe(true);
        expect(res.text).toContain("-1.286386");
        expect(res.text).toContain("36.817223");
    });

    it("parses WGS84 without WASM", () => {
        const res = parseCoordinateQuery("-1.286386, 36.817223");
        expect(res.ok).toBe(true);
        expect(res.kind).toBe("wgs84");
        expect(res.lat).toBeCloseTo(-1.286386, 5);
        expect(res.lon).toBeCloseTo(36.817223, 5);
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
});
