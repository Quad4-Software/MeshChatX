// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    buildMeshchatMapUri,
    buildWebHashMapUrl,
    findMapUriInContent,
    mapLinkKindFromMessage,
    parseMeshchatMapUri,
} from "@/js/mapLinkUtils.js";

const XSS_MARKERS = [
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "javascript:alert(1)",
    "';DROP TABLE t;--",
    "<svg/onload=alert(1)>",
    "\u003cscript\u003e",
];

describe("mapLinkUtils security and XSS-related parsing", () => {
    it("round-trips map URIs with XSS-like label and layers as plain strings", () => {
        for (const marker of XSS_MARKERS) {
            const uri = buildMeshchatMapUri({
                lat: 1,
                lon: 2,
                zoom: 5,
                layers: marker,
                label: marker,
            });
            const p = parseMeshchatMapUri(uri);
            expect(p).not.toBeNull();
            expect(p.layers).toBe(marker);
            expect(p.label).toBe(marker);
        }
    });

    it("findMapUriInContent stops before angle brackets and whitespace", () => {
        expect(findMapUriInContent("x meshchatx://map?lat=1&lon=2&z=3<evil")).toBe("meshchatx://map?lat=1&lon=2&z=3");
        expect(findMapUriInContent("meshchatx://map?lat=1&lon=2 z=3")).toBe("meshchatx://map?lat=1&lon=2");
    });

    it("classifies ping only from line-start prefix or label=ping", () => {
        const uri = "meshchatx://map?lat=0&lon=0&z=3&label=ping";
        expect(mapLinkKindFromMessage("<script>MeshChatX map ping:</script> " + uri, null)).toBe("view");
        expect(mapLinkKindFromMessage("not a ping MeshChatX map ping: " + uri, null)).toBe("view");
        expect(mapLinkKindFromMessage("MeshChatX map ping: " + uri, parseMeshchatMapUri(uri))).toBe("ping");
        expect(mapLinkKindFromMessage("<b>MeshChatX map ping:</b> fake", null)).toBe("view");
        expect(mapLinkKindFromMessage("hello", parseMeshchatMapUri(uri))).toBe("ping");
        expect(mapLinkKindFromMessage("hello", { label: "not-ping" })).toBe("view");
    });

    it("buildWebHashMapUrl encodes dangerous characters in query values", () => {
        const marker = "<script>alert(1)</script>";
        const u = buildWebHashMapUrl({
            lat: 0,
            lon: 0,
            zoom: 4,
            layers: marker,
            label: marker,
        });
        expect(u).not.toContain("<script>");
        expect(/%3[cC]script%3[eE]/i.test(u)).toBe(true);
    });

    it("rejects map URLs with javascript host confusion", () => {
        expect(parseMeshchatMapUri("javascript:meshchatx://map?lat=1&lon=2&z=3")).toBeNull();
        expect(parseMeshchatMapUri("meshchatx://mapper?lat=1&lon=2&z=3")).toBeNull();
    });
});
