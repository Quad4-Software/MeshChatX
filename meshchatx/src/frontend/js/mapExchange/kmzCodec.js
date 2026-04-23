// SPDX-License-Identifier: 0BSD

import JSZip from "jszip";
import { readKmlToFeatures, writeFeaturesToKml } from "./kmlCodec.js";

/**
 * @param {Uint8Array} u8
 * @returns {string}
 */
function uint8ToBase64(u8) {
    const CHUNK = 0x8000;
    let binary = "";
    for (let i = 0; i < u8.length; i += CHUNK) {
        binary += String.fromCharCode.apply(null, u8.subarray(i, i + CHUNK));
    }
    return btoa(binary);
}

/**
 * @param {string} pathInZip
 * @returns {string}
 */
function guessMimeFromPath(pathInZip) {
    const ext = pathInZip.split(".").pop().toLowerCase();
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
    if (ext === "svg") {
        return "image/svg+xml";
    }
    return "application/octet-stream";
}

/**
 * @param {string} mime
 * @returns {string}
 */
function extFromMime(mime) {
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
    if (m.includes("svg")) {
        return "svg";
    }
    return "bin";
}

/**
 * @param {string} kmlPathInZip forward slashes, e.g. "folder/doc.kml"
 * @param {string} href
 * @returns {string|null} resolved path inside zip or null if external / invalid
 */
export function resolveHrefToZipPath(kmlPathInZip, href) {
    const h = String(href).trim();
    if (!h || /^(https?:|data:|file:|\/\/)/i.test(h)) {
        return null;
    }
    const base = kmlPathInZip.includes("/") ? kmlPathInZip.slice(0, kmlPathInZip.lastIndexOf("/") + 1) : "";
    const combined = (base + h).replace(/\\/g, "/");
    const segments = combined.split("/").filter((s) => s.length && s !== ".");
    const out = [];
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

/**
 * @param {import("jszip").default} zip
 * @returns {string|null}
 */
function findKmlEntryName(zip) {
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

/**
 * @param {import("jszip").default} zip
 * @param {string} zipPath
 * @returns {import("jszip").JSZipObject|null}
 */
function zipFileInsensitive(zip, zipPath) {
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

/**
 * Embed zip-local icon paths as data: URIs so blob: URLs are not required (merge-safe).
 * @param {import("jszip").default} zip
 * @param {string} kmlText
 * @param {string} kmlEntryName
 * @returns {Promise<string>}
 */
async function rewriteKmlLocalHrefsToDataUrls(zip, kmlText, kmlEntryName) {
    const hrefRe = /<href>\s*([^<]+?)\s*<\/href>/gi;
    const matches = [...kmlText.matchAll(hrefRe)];
    const rawToData = new Map();
    for (const m of matches) {
        const raw = m[1].trim();
        if (rawToData.has(raw)) {
            continue;
        }
        if (/^(https?:|data:)/i.test(raw)) {
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
        const ab = await entry.async("arraybuffer");
        const mime = guessMimeFromPath(zipPath);
        const b64 = uint8ToBase64(new Uint8Array(ab));
        rawToData.set(raw, `data:${mime};base64,${b64}`);
    }
    return kmlText.replace(hrefRe, (full, inner) => {
        const raw = inner.trim();
        const data = rawToData.get(raw);
        return data ? `<href>${data}</href>` : full;
    });
}

/**
 * @param {ArrayBuffer} arrayBuffer
 * @param {import("ol/proj").ProjectionLike} featureProjection
 * @returns {Promise<import("ol/Feature").default[]>}
 */
export async function readKmzToFeatures(arrayBuffer, featureProjection) {
    const zip = await JSZip.loadAsync(arrayBuffer);
    const kmlName = findKmlEntryName(zip);
    if (!kmlName) {
        throw new Error("KMZ has no KML document");
    }
    const entry = zip.file(kmlName);
    if (!entry) {
        throw new Error("KMZ KML entry missing");
    }
    let kmlText = await entry.async("string");
    kmlText = await rewriteKmlLocalHrefsToDataUrls(zip, kmlText, kmlName);
    return readKmlToFeatures(kmlText, featureProjection);
}

/**
 * @param {import("ol/Feature").default[]} features
 * @param {import("ol/proj").ProjectionLike} featureProjection
 * @returns {Promise<Blob>}
 */
export async function writeFeaturesToKmzBlob(features, featureProjection) {
    let kml = writeFeaturesToKml(features, featureProjection);
    const zip = new JSZip();
    let n = 0;
    const dataUriRe = /<href>\s*(data:([^;]+);base64,([^<\s]+))\s*<\/href>/gi;
    kml = kml.replace(dataUriRe, (full, _dataUri, mime, b64) => {
        const ext = extFromMime(mime);
        const path = `files/mcx-embedded-${n++}.${ext}`;
        let bin;
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
