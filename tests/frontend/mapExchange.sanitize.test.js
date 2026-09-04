// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import JSZip from "jszip";
import {
    isAllowedDataImageHref,
    isRemoteHref,
    kmzEntryAllowed,
    KmlSanitizeError,
    sanitizeKmlText,
} from "@/js/mapExchange/kmlSanitize.js";
import { readKmlToFeatures } from "@/js/mapExchange/kmlCodec.js";
import { readKmzToFeatures } from "@/js/mapExchange/kmzCodec.js";
import { getDrawFeatureMetadataPayload } from "@/js/mapExchange/metadataUtils.js";

const TINY_PNG =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

describe("kmlSanitize oracle", () => {
    it("classifies remote hrefs as remote", () => {
        expect(isRemoteHref("https://evil.example/i.png")).toBe(true);
        expect(isRemoteHref("http://evil.example/x")).toBe(true);
        expect(isRemoteHref("//cdn.example/x.png")).toBe(true);
        expect(isRemoteHref("file:///tmp/x")).toBe(true);
        expect(isRemoteHref("javascript:alert(1)")).toBe(true);
        expect(isRemoteHref("vbscript:msgbox(1)")).toBe(true);
        expect(isRemoteHref("files/icon.png")).toBe(false);
        expect(isRemoteHref(TINY_PNG)).toBe(false);
    });

    it("allows only raster data image hrefs", () => {
        expect(isAllowedDataImageHref(TINY_PNG)).toBe(true);
        expect(isAllowedDataImageHref("data:text/html;base64,PHNjcmlwdD4=")).toBe(false);
        expect(isAllowedDataImageHref("data:image/svg+xml;base64,PHN2Zz4=")).toBe(false);
    });

    it("rejects svg and html kmz entries", () => {
        expect(kmzEntryAllowed("files/icon.png")).toBe(true);
        expect(kmzEntryAllowed("doc.kml")).toBe(true);
        expect(kmzEntryAllowed("icon.svg")).toBe(false);
        expect(kmzEntryAllowed("page.html")).toBe(false);
        expect(kmzEntryAllowed("../evil.kml")).toBe(false);
    });

    it("strips remote icon href and keeps placemark", () => {
        const kml = `<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>P</name>
<Style><IconStyle><Icon><href>https://evil.example/i.png</href></Icon></IconStyle></Style>
<Point><coordinates>1,2,0</coordinates></Point>
</Placemark></Document></kml>`;
        const out = sanitizeKmlText(kml);
        expect(out.stripped).toContain("remote_href");
        expect(out.text.includes("https://evil.example")).toBe(false);
        expect(out.text.toLowerCase()).toContain("placemark");
        const features = readKmlToFeatures(kml, "EPSG:3857");
        expect(features.length).toBeGreaterThanOrEqual(1);
    });

    it("rejects network-link-only kml", () => {
        const kml = `<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<NetworkLink><Link><href>https://evil.example/layer.kml</href></Link></NetworkLink>
</Document></kml>`;
        expect(() => sanitizeKmlText(kml)).toThrow(KmlSanitizeError);
        try {
            sanitizeKmlText(kml);
        } catch (e) {
            expect(e.code).toBe("remote_content");
        }
    });

    it("rejects dtd kml", () => {
        const kml = `<?xml version="1.0"?>
<!DOCTYPE kml [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>x</name><Point><coordinates>1,2,0</coordinates></Point></Placemark>
</Document></kml>`;
        expect(() => sanitizeKmlText(kml)).toThrow(KmlSanitizeError);
        try {
            sanitizeKmlText(kml);
        } catch (e) {
            expect(e.code).toBe("dtd_forbidden");
        }
    });

    it("keeps kmz zip-local png icons", async () => {
        const kml = `<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>Z</name>
<Style><IconStyle><Icon><href>files/icon.png</href></Icon></IconStyle></Style>
<Point><coordinates>1,2,0</coordinates></Point>
</Placemark></Document></kml>`;
        const zip = new JSZip();
        zip.file("doc.kml", kml);
        const png = Uint8Array.from(
            atob("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="),
            (c) => c.charCodeAt(0)
        );
        zip.file("files/icon.png", png);
        const buf = await zip.generateAsync({ type: "arraybuffer" });
        const features = await readKmzToFeatures(buf, "EPSG:3857");
        expect(features.length).toBeGreaterThanOrEqual(1);
    });

    it("strips xlink:href remote icons and vbscript hrefs", () => {
        const kml = `<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:xlink="http://www.w3.org/1999/xlink"><Document>
<Placemark><name>P</name>
<Icon xlink:href="https://evil.example/i.png"/>
<Icon><href>vbscript:msgbox(1)</href></Icon>
<Point><coordinates>1,2,0</coordinates></Point>
</Placemark></Document></kml>`;
        const out = sanitizeKmlText(kml);
        expect(out.text.toLowerCase()).not.toContain("evil.example");
        expect(out.text.toLowerCase()).not.toContain("vbscript:");
        expect(out.stripped).toContain("remote_href");
    });

    it("flattens CDATA HTML descriptions without leaving a CDATA closer", () => {
        const kml = `<?xml version="1.0" encoding="utf-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>Leaking Tanks</name>
<description><![CDATA[<h2>Hostile</h2></br><script>alert(1)</script>]]></description>
<Point><coordinates>-117.99,33.78,0</coordinates></Point>
</Placemark></Document></kml>`;
        const out = sanitizeKmlText(kml);
        expect(out.stripped).toContain("html_description");
        expect(out.text).not.toMatch(/\]\]>/);
        expect(out.text.toLowerCase()).not.toContain("<script");
        expect(out.text.toLowerCase()).not.toContain("<h2");
        expect(out.text.toLowerCase()).not.toContain("alert(1)");
        const parsed = new DOMParser().parseFromString(out.text, "application/xml");
        expect(parsed.getElementsByTagName("parsererror").length).toBe(0);
        const features = readKmlToFeatures(kml, "EPSG:3857");
        expect(features.length).toBe(1);
        expect(String(features[0].get("name") || "")).toContain("Leaking");
    });

    it("flattens ArcGIS table balloons into keyed lines and drops Null cells", () => {
        const kml = `<?xml version="1.0" encoding="utf-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>Vandalism</name>
<description><![CDATA[<html><body><table>
<tr><td>AttackType</td><td>Vandalism</td></tr>
<tr><td>Enemy Wounded</td><td>&lt;Null&gt;</td></tr>
<tr><td>Notes</td><td>Memorial defaced</td></tr>
</table><script>function changeImage(){}</script></body></html>]]></description>
<Point><coordinates>-94.2,36.3,0</coordinates></Point>
</Placemark></Document></kml>`;
        const features = readKmlToFeatures(kml, "EPSG:3857");
        expect(features.length).toBe(1);
        const desc = String(features[0].get("description") || "");
        expect(desc).toContain("AttackType: Vandalism");
        expect(desc).toContain("Notes: Memorial defaced");
        expect(desc.toLowerCase()).not.toContain("enemy wounded");
        expect(desc.toLowerCase()).not.toContain("changeimage");
        const payload = getDrawFeatureMetadataPayload(features[0]);
        expect(payload.extended.some((r) => r.key === "AttackType" && r.value === "Vandalism")).toBe(true);
        expect(payload.extended.some((r) => /null/i.test(r.value))).toBe(false);
    });

    it("skips unreferenced svg kmz entry and keeps placemarks", async () => {
        const kml = `<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>Keep</name><Point><coordinates>1,2,0</coordinates></Point></Placemark>
</Document></kml>`;
        const zip = new JSZip();
        zip.file("doc.kml", kml);
        zip.file("icon.svg", "<svg></svg>");
        const buf = await zip.generateAsync({ type: "arraybuffer" });
        const features = await readKmzToFeatures(buf, "EPSG:3857");
        expect(features.length).toBeGreaterThanOrEqual(1);
    });

    it("imports ArcGIS-style kmz with unused xsl sidecar", async () => {
        const kml = `<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Style id="s"><IconStyle><Icon><href>Layer0_Symbol.png</href></Icon></IconStyle></Style>
<Placemark><name>ArcGIS Point</name>
<styleUrl>#s</styleUrl>
<Point><coordinates>1,2,0</coordinates></Point>
</Placemark></Document></kml>`;
        const zip = new JSZip();
        zip.file("doc.kml", kml);
        zip.file(
            "F2E8A9CB2E0A446C9BCA87742DD683E5.xsl",
            "<?xml version='1.0'?><xsl:stylesheet xmlns:xsl='http://www.w3.org/1999/XSL/Transform' version='1.0'/>"
        );
        const png = Uint8Array.from(
            atob("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="),
            (c) => c.charCodeAt(0)
        );
        zip.file("Layer0_Symbol.png", png);
        const buf = await zip.generateAsync({ type: "arraybuffer" });
        const features = await readKmzToFeatures(buf, "EPSG:3857");
        expect(features.length).toBeGreaterThanOrEqual(1);
        expect(String(features[0].get("name") || "")).toContain("ArcGIS");
    });
});
