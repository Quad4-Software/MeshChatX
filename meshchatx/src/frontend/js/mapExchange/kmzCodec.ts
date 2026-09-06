// SPDX-License-Identifier: 0BSD

import type Feature from "ol/Feature";
import type { ProjectionLike } from "ol/proj";
import type JSZipType from "jszip";
import JSZip from "jszip";
import { readKmlToFeatures, writeFeaturesToKml } from "./kmlCodec.js";
import {
    KmlSanitizeError,
    isAllowedDataImageHref,
    isRemoteHref,
    kmzEntryAllowed,
    sanitizeKmlText,
} from "./kmlSanitize.js";

function uint8ToBase64(u8: Uint8Array): string {
    const CHUNK = 0x8000;
    let binary = "";
    for (let i = 0; i < u8.length; i += CHUNK) {
        binary += String.fromCharCode.apply(null, u8.subarray(i, i + CHUNK) as unknown as number[]);
    }
    return btoa(binary);
}

function guessMimeFromPath(pathInZip: string): string {
    const ext = pathInZip.split(".").pop()?.toLowerCase() || "";
    if (ext === "png") {
        return "image/png";
    }
    if (ext === "jpg" || ext === "jpeg") {
        return "image/jpeg";
    }
    if (ext === "gif") {
        return "image/gif";
    }
    if (ext === "webp") {
        return "image/webp";
    }
    return "application/octet-stream";
}

function extFromMime(mime: string): string {
    const m = String(mime || "").toLowerCase();
    if (m.includes("png")) {
        return "png";
    }
    if (m.includes("jpeg") || m.includes("jpg")) {
        return "jpg";
    }
    if (m.includes("gif")) {
        return "gif";
    }
    if (m.includes("webp")) {
        return "webp";
    }
    return "bin";
}

function isRemoteOrUnsafeHref(raw: string): boolean {
    const h = String(raw || "").trim();
    if (!h) {
        return true;
    }
    if (isAllowedDataImageHref(h)) {
        return false;
    }
    return isRemoteHref(h) || h.toLowerCase().startsWith("data:");
}

/** Resolve href relative to kmlPathInZip. Returns zip path or null if external / invalid. */
export function resolveHrefToZipPath(kmlPathInZip: string, href: string): string | null {
    const h = String(href).trim();
    if (!h || isRemoteHref(h) || h.toLowerCase().startsWith("data:")) {
        return null;
    }
    const base = kmlPathInZip.includes("/") ? kmlPathInZip.slice(0, kmlPathInZip.lastIndexOf("/") + 1) : "";
    const combined = (base + h).replace(/\\/g, "/");
    const segments = combined.split("/").filter((s) => s.length && s !== ".");
    const out: string[] = [];
    for (const s of segments) {
        if (s === "..") {
            if (!out.length) {
                return null;
            }
            out.pop();
        } else {
            out.push(s);
        }
    }
    return out.join("/");
}

function findKmlEntryName(zip: JSZipType): string | null {
    const names = Object.keys(zip.files).filter((n) => !zip.files[n].dir);
    const doc = names.find((n) => n.replace(/\\/g, "/").toLowerCase() === "doc.kml");
    if (doc) {
        return doc.replace(/\\/g, "/");
    }
    const kmls = names.map((n) => n.replace(/\\/g, "/")).filter((n) => n.toLowerCase().endsWith(".kml"));
    if (!kmls.length) {
        return null;
    }
    kmls.sort((a, b) => a.length - b.length);
    return kmls[0];
}

function zipFileInsensitive(zip: JSZipType, zipPath: string): JSZipType.JSZipObject | null {
    const norm = zipPath.replace(/\\/g, "/");
    let f = zip.file(norm);
    if (f) {
        return f;
    }
    const want = norm.toLowerCase();
    const keys = Object.keys(zip.files);
    const hit = keys.find((k) => !zip.files[k].dir && k.replace(/\\/g, "/").toLowerCase() === want);
    return hit ? zip.file(hit) : null;
}

/** Embed zip-local icon paths as data: URIs so blob: URLs are not required (merge-safe). */
async function rewriteKmlLocalHrefsToDataUrls(zip: JSZipType, kmlText: string, kmlEntryName: string): Promise<string> {
    const hrefRe = /<href>\s*([^<]+?)\s*<\/href>/gi;
    const matches = [...kmlText.matchAll(hrefRe)];
    const rawToData = new Map<string, string>();
    for (const m of matches) {
        const raw = m[1].trim();
        if (rawToData.has(raw)) {
            continue;
        }
        if (isRemoteOrUnsafeHref(raw)) {
            continue;
        }
        const zipPath = resolveHrefToZipPath(kmlEntryName, raw);
        if (!zipPath) {
            continue;
        }
        const entry = zipFileInsensitive(zip, zipPath);
        if (!entry) {
            continue;
        }
        if (!kmzEntryAllowed(zipPath)) {
            continue;
        }
        const ab = await entry.async("arraybuffer");
        const mime = guessMimeFromPath(zipPath);
        if (!mime.startsWith("image/") || mime.includes("svg")) {
            continue;
        }
        const b64 = uint8ToBase64(new Uint8Array(ab));
        rawToData.set(raw, `data:${mime};base64,${b64}`);
    }
    return kmlText.replace(hrefRe, (_full, inner) => {
        const raw = String(inner).trim();
        if (isAllowedDataImageHref(raw)) {
            return `<href>${raw}</href>`;
        }
        const data = rawToData.get(raw);
        return data ? `<href>${data}</href>` : "";
    });
}

export async function readKmzToFeatures(
    arrayBuffer: ArrayBuffer,
    featureProjection: ProjectionLike
): Promise<Feature[]> {
    const zip = await JSZip.loadAsync(arrayBuffer);
    const names = Object.keys(zip.files).filter((n) => !zip.files[n].dir);
    for (const n of names) {
        const name = n.replace(/\\/g, "/");
        if (name.split("/").includes("..")) {
            throw new KmlSanitizeError("path_traversal");
        }
        if (!kmzEntryAllowed(name)) {
            // ArcGIS KMZ exports include unused .xsl balloon stylesheets.
            continue;
        }
    }
    const kmlName = findKmlEntryName(zip);
    if (!kmlName) {
        throw new KmlSanitizeError("kmz_missing_kml");
    }
    const entry = zip.file(kmlName);
    if (!entry) {
        throw new KmlSanitizeError("kmz_missing_kml");
    }
    let kmlText = await entry.async("string");
    const sanitized = sanitizeKmlText(kmlText, { zipLocalOk: true });
    kmlText = await rewriteKmlLocalHrefsToDataUrls(zip, sanitized.text, kmlName);
    return readKmlToFeatures(kmlText, featureProjection);
}

export async function writeFeaturesToKmzBlob(features: Feature[], featureProjection: ProjectionLike): Promise<Blob> {
    let kml = writeFeaturesToKml(features, featureProjection);
    const zip = new JSZip();
    let n = 0;
    const dataUriRe = /<href>\s*(data:([^;]+);base64,([^<\s]+))\s*<\/href>/gi;
    kml = kml.replace(dataUriRe, (full, _dataUri, mime, b64) => {
        const ext = extFromMime(mime);
        if (ext === "bin") {
            return "";
        }
        const path = `files/mcx-embedded-${n++}.${ext}`;
        let bin: Uint8Array;
        try {
            const binary = atob(String(b64).trim());
            bin = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bin[i] = binary.charCodeAt(i);
            }
        } catch {
            return full;
        }
        zip.file(path, bin);
        return `<href>${path}</href>`;
    });
    zip.file("doc.kml", kml);
    return zip.generateAsync({ type: "blob", compression: "DEFLATE" });
}
