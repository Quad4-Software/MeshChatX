// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import JSZip from "jszip";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { fromLonLat } from "ol/proj";
import { readGeoJsonToFeatures, writeFeaturesToGeoJson } from "@/js/mapExchange/geoJsonCodec.js";
import { readKmlToFeatures, writeFeaturesToKml } from "@/js/mapExchange/kmlCodec.js";
import { readKmzToFeatures, writeFeaturesToKmzBlob, resolveHrefToZipPath } from "@/js/mapExchange/kmzCodec.js";
import { readGpxToFeatures, writeFeaturesToGpx } from "@/js/mapExchange/gpxCodec.js";
import { getDrawFeatureMetadataPayload } from "@/js/mapExchange/metadataUtils.js";
import { MCX_ICON_DATA_URL, MCX_STROKE_COLOR } from "@/js/mapExchange/constants.js";

const TINY_PNG =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

function dataUrlToUint8(dataUrl) {
    const base64 = String(dataUrl).split(",")[1] || "";
    const binary = atob(base64);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        out[i] = binary.charCodeAt(i);
    }
    return out;
}

describe("mapExchange GeoJSON", () => {
    it("reads point with mcx_icon_data_url and round-trips properties", () => {
        const gj = {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    properties: { [MCX_ICON_DATA_URL]: TINY_PNG, mcx_icon_scale: 0.5 },
                    geometry: { type: "Point", coordinates: [-122, 37] },
                },
            ],
        };
        const features = readGeoJsonToFeatures(JSON.stringify(gj), "EPSG:3857");
        expect(features.length).toBe(1);
        const out = writeFeaturesToGeoJson(features, "EPSG:3857");
        const parsed = JSON.parse(out);
        expect(parsed.features[0].properties[MCX_ICON_DATA_URL]).toContain("data:image/png");
    });

    it("reads line with mcx stroke properties", () => {
        const gj = {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    properties: { [MCX_STROKE_COLOR]: "#ff0000", mcx_stroke_width: 3 },
                    geometry: {
                        type: "LineString",
                        coordinates: [
                            [0, 0],
                            [1, 1],
                        ],
                    },
                },
            ],
        };
        const features = readGeoJsonToFeatures(JSON.stringify(gj), "EPSG:3857");
        expect(features.length).toBe(1);
        expect(features[0].getGeometry().getType()).toBe("LineString");
    });

    it("supports simplestyle marker-color on points", () => {
        const gj = {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    properties: { "marker-color": "#00ff00" },
                    geometry: { type: "Point", coordinates: [10, 20] },
                },
            ],
        };
        const features = readGeoJsonToFeatures(JSON.stringify(gj), "EPSG:3857");
        expect(features.length).toBe(1);
        expect(features[0].getStyle()).not.toBeNull();
    });
});

describe("mapExchange KML", () => {
    it("reads placemark with point geometry and name", () => {
        const kml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>P</name>
<Style><IconStyle><scale>0.5</scale><Icon><href>${TINY_PNG}</href></Icon></IconStyle></Style>
<Point><coordinates>-122.1,37.2,0</coordinates></Point>
</Placemark></Document></kml>`;
        const features = readKmlToFeatures(kml, "EPSG:3857");
        expect(features.length).toBeGreaterThanOrEqual(1);
        const f = features[0];
        expect(f.getGeometry().getType()).toBe("Point");
        expect(String(f.get("name") || f.get("Name") || "")).toContain("P");
        const stRaw = f.getStyle();
        const st = typeof stRaw === "function" ? stRaw(f, 1) : stRaw;
        expect(st && typeof st.getImage === "function" && st.getImage()).toBeTruthy();
    });

    it("exports and re-reads a minimal point KML", () => {
        const kml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>X</name>
<Point><coordinates>5,10,0</coordinates></Point></Placemark></Document></kml>`;
        const features = readKmlToFeatures(kml, "EPSG:3857");
        const out = writeFeaturesToKml(features, "EPSG:3857");
        expect(out.includes("<kml")).toBe(true);
        expect(out.includes("coordinates")).toBe(true);
        const again = readKmlToFeatures(out, "EPSG:3857");
        expect(again.length).toBeGreaterThanOrEqual(1);
    });
});

describe("mapExchange KMZ", () => {
    it("resolves relative href paths inside zip", () => {
        expect(resolveHrefToZipPath("folder/doc.kml", "files/icon.png")).toBe("folder/files/icon.png");
        expect(resolveHrefToZipPath("doc.kml", "files/icon.png")).toBe("files/icon.png");
        expect(resolveHrefToZipPath("doc.kml", "../secret")).toBe(null);
    });

    it("reads placemark with zip-embedded icon", async () => {
        const kml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>KMZ Point</name>
<Style><IconStyle><scale>0.5</scale><Icon><href>files/icon.png</href></Icon></IconStyle></Style>
<Point><coordinates>-122.1,37.2,0</coordinates></Point>
</Placemark></Document></kml>`;
        const zip = new JSZip();
        zip.file("doc.kml", kml);
        zip.file("files/icon.png", dataUrlToUint8(TINY_PNG));
        const buf = await zip.generateAsync({ type: "arraybuffer" });
        const features = await readKmzToFeatures(buf, "EPSG:3857");
        expect(features.length).toBeGreaterThanOrEqual(1);
        const f = features[0];
        expect(f.getGeometry().getType()).toBe("Point");
        expect(String(f.get("name") || "")).toContain("KMZ");
        expect(String(f.get(MCX_ICON_DATA_URL) || "")).toContain("data:image/png");
    });

    it("exports KMZ with embedded data-URI icon and reads it back", async () => {
        const kml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>Round</name>
<Style><IconStyle><Icon><href>${TINY_PNG}</href></Icon></IconStyle></Style>
<Point><coordinates>10,20,0</coordinates></Point>
</Placemark></Document></kml>`;
        const features = readKmlToFeatures(kml, "EPSG:3857");
        const blob = await writeFeaturesToKmzBlob(features, "EPSG:3857");
        const ab = await blob.arrayBuffer();
        const again = await readKmzToFeatures(ab, "EPSG:3857");
        expect(again.length).toBeGreaterThanOrEqual(1);
        expect(String(again[0].get("name") || "")).toContain("Round");
    });
});

describe("mapExchange GPX", () => {
    it("reads a waypoint and round-trips name and description", () => {
        const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="meshchatx" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="37.2" lon="-122.1"><name>Trailhead</name><desc>Park here</desc></wpt>
</gpx>`;
        const features = readGpxToFeatures(gpx, "EPSG:3857");
        expect(features.length).toBeGreaterThanOrEqual(1);
        expect(String(features[0].get("name") || "")).toContain("Trailhead");
        expect(String(features[0].get("description") || "")).toContain("Park here");
        const out = writeFeaturesToGpx(features, "EPSG:3857");
        expect(out.toLowerCase()).toContain("<gpx");
        const again = readGpxToFeatures(out, "EPSG:3857");
        expect(again.length).toBeGreaterThanOrEqual(1);
        expect(String(again[0].get("description") || again[0].get("desc") || "")).toContain("Park here");
    });

    it("exports edited description property into GPX desc", () => {
        const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="meshchatx" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="1" lon="2"><name>X</name></wpt>
</gpx>`;
        const features = readGpxToFeatures(gpx, "EPSG:3857");
        features[0].set("description", "edited note");
        const out = writeFeaturesToGpx(features, "EPSG:3857");
        const again = readGpxToFeatures(out, "EPSG:3857");
        expect(String(again[0].get("description") || "")).toContain("edited note");
    });
});

describe("mapExchange GeoJSON sanitize", () => {
    it("strips remote icon hrefs on import", () => {
        const gj = {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    properties: {
                        name: "Tracked",
                        href: "https://evil.example/i.png",
                        mcx_icon_href: "https://tracker.example/pixel.png",
                    },
                    geometry: { type: "Point", coordinates: [10, 20] },
                },
            ],
        };
        const features = readGeoJsonToFeatures(JSON.stringify(gj), "EPSG:3857");
        expect(features.length).toBe(1);
        expect(features[0].get("href")).toBeUndefined();
        expect(features[0].get("mcx_icon_href")).toBeUndefined();
        const payload = getDrawFeatureMetadataPayload(features[0]);
        expect(payload.iconSrc).toBeNull();
    });
});

describe("mapExchange metadata", () => {
    it("builds overlay payload with extended properties", () => {
        const f = new Feature({
            geometry: new Point(fromLonLat([-122, 37])),
            type: "draw",
        });
        f.set("name", "Site A");
        f.set("description", "Plain text");
        f.set("ref", "Q123");
        const p = getDrawFeatureMetadataPayload(f);
        expect(p).not.toBeNull();
        expect(p.name).toBe("Site A");
        expect(p.description).toBe("Plain text");
        expect(p.extended.some((r) => r.key === "ref" && r.value === "Q123")).toBe(true);
    });

    it("returns geometry_type when no other metadata", () => {
        const f = new Feature({
            geometry: new Point(fromLonLat([-122, 37])),
            type: "draw",
        });
        const p = getDrawFeatureMetadataPayload(f);
        expect(p).not.toBeNull();
        expect(p.extended.some((r) => r.key === "geometry_type" && r.value === "Point")).toBe(true);
    });

    it("keeps URL lines in description instead of inventing keyed fields", () => {
        const f = new Feature({
            geometry: new Point(fromLonLat([-122, 37])),
            type: "draw",
        });
        f.set("name", "Link");
        f.set("description", "See https://example.com:8080/path");
        const p = getDrawFeatureMetadataPayload(f);
        expect(p.description).toContain("https://example.com:8080/path");
        expect(p.extended.every((r) => !/https?/i.test(r.key))).toBe(true);
    });
});
