// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    buildMeshchatMapUri,
    buildWebHashMapUrl,
    findMapUriInContent,
    mapLinkKindFromMessage,
    parseMeshchatMapUri,
} from "@/js/mapLinkUtils.js";

describe("mapLinkUtils", () => {
    it("builds and parses meshchatx map URIs", () => {
        const uri = buildMeshchatMapUri({
            lat: 1.5,
            lon: -2.25,
            zoom: 7,
            layers: "discovered",
            label: "Test",
        });
        expect(uri.startsWith("meshchatx://map?")).toBe(true);
        const p = parseMeshchatMapUri(uri);
        expect(p).not.toBeNull();
        expect(p.lat).toBeCloseTo(1.5);
        expect(p.lon).toBeCloseTo(-2.25);
        expect(p.zoom).toBe(7);
        expect(p.layers).toBe("discovered");
        expect(p.label).toBe("Test");
    });

    it("accepts meshchat:// alias", () => {
        const p = parseMeshchatMapUri("meshchat://map?lat=10&lon=20&z=5");
        expect(p).not.toBeNull();
        expect(p.zoom).toBe(5);
    });

    it("reads z or zoom query", () => {
        expect(parseMeshchatMapUri("meshchatx://map?lat=0&lon=0&zoom=12").zoom).toBe(12);
        expect(parseMeshchatMapUri("meshchatx://map?lat=0&lon=0&z=9").zoom).toBe(9);
    });

    it("finds first map URI in text", () => {
        const text = "See meshchatx://map?lat=1&lon=2&z=3 end";
        expect(findMapUriInContent(text)).toBe("meshchatx://map?lat=1&lon=2&z=3");
    });

    it("classifies ping vs view from message", () => {
        expect(mapLinkKindFromMessage("MeshChatX map ping: meshchatx://map?lat=0&lon=0&z=3", null)).toBe("ping");
        expect(mapLinkKindFromMessage("  MeshChatX map ping: meshchatx://map?lat=0&lon=0&z=3", null)).toBe("ping");
        expect(mapLinkKindFromMessage("<script>MeshChatX map ping:</script>", null)).toBe("view");
        expect(mapLinkKindFromMessage("hello", { label: "Ping" })).toBe("ping");
        expect(mapLinkKindFromMessage("hello", { label: "Here" })).toBe("view");
    });

    it("buildWebHashMapUrl includes hash route", () => {
        const u = buildWebHashMapUrl({ lat: 3, lon: 4, zoom: 8, layers: "discovered" });
        expect(u).toContain("#/map?");
        expect(u).toContain("lat=3");
        expect(u).toContain("lon=4");
        expect(u).toContain("zoom=8");
        expect(u).toContain("layers=discovered");
    });
});
