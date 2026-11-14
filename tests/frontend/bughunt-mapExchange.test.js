// SPDX-License-Identifier: 0BSD
// Bug-hunt: mapExchange codec crash / sanitizer-gap checks.
import { describe, expect, it } from "vitest";
import { readGpxToFeatures } from "../../meshchatx/src/frontend/js/mapExchange/gpxCodec.js";
import { readKmlToFeatures } from "../../meshchatx/src/frontend/js/mapExchange/kmlCodec.js";
import { readGeoJsonToFeatures } from "../../meshchatx/src/frontend/js/mapExchange/geoJsonCodec.js";
import { readKmzToFeatures, resolveHrefToZipPath } from "../../meshchatx/src/frontend/js/mapExchange/kmzCodec.js";
import { sanitizeKmlText } from "../../meshchatx/src/frontend/js/mapExchange/kmlSanitize.js";
import JSZip from "jszip";

const PROJ = "EPSG:3857";

function throwsOrFeatures(fn) {
    try {
        return { ok: true, features: fn() };
    } catch (e) {
        return { ok: false, error: e };
    }
}

describe("bughunt: mapExchange malformed inputs", () => {
    it("GPX: garbage / truncated / huge inputs do not crash the process", () => {
        const inputs = [
            "",
            "not xml at all",
            "<gpx>",
            "<gpx><trk><trkseg><trkpt lat='abc' lon='1'/></trkseg></trk></gpx>",
            "<gpx>" + "<trkpt lat='1' lon='2'/>".repeat(20000) + "</gpx>",
            "\x00\x01\x02binary",
            "<gpx xmlns='http://www.topografix.com/GPX/1/1'><wpt lat='91' lon='181'><name>" + "x".repeat(100000) + "</name></wpt></gpx>",
        ];
        for (const [i, text] of inputs.entries()) {
            const r = throwsOrFeatures(() => readGpxToFeatures(text, PROJ));
            // Either features or a thrown Error is fine; a hang/crash is not.
            expect(r.ok === false ? r.error instanceof Error : Array.isArray(r.features)).toBe(true);
        }
    });

    it("KML: malformed XML / DTD / entity payloads handled", () => {
        const inputs = [
            "",
            "<kml",
            "<kml><Document><Placemark><Point><coordinates>1,2,3</coordinates></Point></Placemark></Document></kml>",
            "<!DOCTYPE kml [<!ENTITY a 'AAAA'>]><kml><Document><name>&a;</name></Document></kml>",
            "<!--" + "x".repeat(5000) + "--><!DOCTYPE kml [<!ENTITY a 'b'>]><kml/>",
            "<kml><NetworkLink><Link><href>http://evil.example/x.kml</href></Link></NetworkLink></kml>",
        ];
        for (const text of inputs) {
            const r = throwsOrFeatures(() => readKmlToFeatures(text, PROJ));
            expect(r.ok === false ? r.error instanceof Error : Array.isArray(r.features)).toBe(true);
        }
    });

    it("GeoJSON: malformed JSON / wrong shapes do not crash", () => {
        const inputs = [
            "",
            "{",
            "null",
            "42",
            '"string"',
            "[]",
            '{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[1,2]},"properties":{}}]}',
            '{"type":"Feature","geometry":{"type":"Point","coordinates":"abc"},"properties":{}}',
            '{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[0,0],[1,1]]]}}',
            "x".repeat(200000),
        ];
        for (const text of inputs) {
            const r = throwsOrFeatures(() => readGeoJsonToFeatures(text, PROJ));
            expect(r.ok === false ? r.error instanceof Error : Array.isArray(r.features)).toBe(true);
        }
    });

    it("KMZ: non-zip / truncated / hostile entry names", async () => {
        const bad = [
            new ArrayBuffer(0),
            new TextEncoder().encode("not a zip").buffer,
            new Uint8Array([0x50, 0x4b, 0x03, 0x04]).buffer,
        ];
        for (const buf of bad) {
            await expect(readKmzToFeatures(buf, PROJ)).rejects.toThrow();
        }
        // Zip with path traversal entry name (backslash form survives JSZip
        // round-trip; readKmzToFeatures normalizes \\ -> / before checking).
        const zip = new JSZip();
        zip.file("..\\evil.kml", "<kml/>");
        const buf = await zip.generateAsync({ type: "arraybuffer" });
        await expect(readKmzToFeatures(buf, PROJ)).rejects.toThrow();
        // Zip with no .kml entry.
        const zip2 = new JSZip();
        zip2.file("readme.txt", "hi");
        const buf2 = await zip2.generateAsync({ type: "arraybuffer" });
        await expect(readKmzToFeatures(buf2, PROJ)).rejects.toThrow();
    });

    it("resolveHrefToZipPath keeps resolution inside the zip namespace", () => {
        // "../.." from a/b/ lands at the zip root — still inside the archive,
        // looked up via zip.file() only. True escapes (popping past root)
        // return null.
        expect(resolveHrefToZipPath("a/b/doc.kml", "../../etc/passwd")).toBe("etc/passwd");
        expect(resolveHrefToZipPath("a/b/doc.kml", "../../../etc/passwd")).toBeNull();
        expect(resolveHrefToZipPath("a/b/doc.kml", "..\\..\\..\\win.ini")).toBeNull();
        expect(resolveHrefToZipPath("doc.kml", "icons/x.png")).toBe("icons/x.png");
        expect(resolveHrefToZipPath("a/doc.kml", "../shared/x.png")).toBe("shared/x.png");
        expect(resolveHrefToZipPath("a/doc.kml", "http://evil/x.png")).toBeNull();
        expect(resolveHrefToZipPath("a/doc.kml", "data:image/png;base64,xx")).toBeNull();
    });

    it("sanitizeKmlText: DTD hidden behind >4096-char comment prefix is NOT rejected", () => {
        // looksLikeDtd only scans the first 4096 code points. A legal XML
        // comment may precede the DOCTYPE, so padding pushes it out of the
        // window and the explicit dtd_forbidden guarantee is bypassed.
        const kml =
            "<!--" +
            "x".repeat(5000) +
            "--><!DOCTYPE kml [<!ENTITY a 'b'>]><kml><Document/></kml>";
        let threw = false;
        try {
            sanitizeKmlText(kml);
        } catch (e) {
            threw = true;
        }
        // BUG: should throw KmlSanitizeError("dtd_forbidden") like the
        // in-window control does.
        expect(threw, "DTD after 5KB comment prefix was not rejected").toBe(true);
    });

    it("end-to-end: padded DTD reaches the KML parser and expands entities", () => {
        const pad = "<!--" + "x".repeat(5000) + "-->";
        const kml =
            pad +
            "<!DOCTYPE kml [<!ENTITY a 'EXPANDED-TEXT'>]><kml xmlns='http://www.opengis.net/kml/2.2'><Document>" +
            "<Placemark><name>&a;</name><Point><coordinates>1,2</coordinates></Point></Placemark></Document></kml>";
        // sanitizeKmlText lets it through; whether the XML parser then expands
        // the entity is up to the DOMParser — the sanitizer's explicit
        // dtd_forbidden contract is already broken before that.
        const r = throwsOrFeatures(() => readKmlToFeatures(kml, PROJ));
        if (r.ok) {
            const name = r.features[0] && r.features[0].get("name");
            console.log("parsed feature name:", JSON.stringify(name));
        } else {
            console.log("parser threw:", r.error && r.error.message);
        }
        // Document the outcome; the sanitizeKmlText-level assertion above is
        // the hard failure.
        expect(true).toBe(true);
    });
});
