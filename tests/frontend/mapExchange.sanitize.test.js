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

    it("rejects kmz with svg entry", async () => {
        const kml = `<?xml version="1.0"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><Point><coordinates>1,2,0</coordinates></Point></Placemark>
</Document></kml>`;
        const zip = new JSZip();
        zip.file("doc.kml", kml);
        zip.file("icon.svg", "<svg></svg>");
        const buf = await zip.generateAsync({ type: "arraybuffer" });
        await expect(readKmzToFeatures(buf, "EPSG:3857")).rejects.toMatchObject({ code: "unsafe_kmz_entry" });
    });
});
