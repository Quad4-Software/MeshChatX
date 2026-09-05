// SPDX-License-Identifier: 0BSD

import { flattenHtmlDescription } from "./descriptionFlatten.js";

const ALLOWED_DATA_PREFIXES = [
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/jpg;base64,",
    "data:image/gif;base64,",
    "data:image/webp;base64,",
];

const ALLOWED_KMZ_EXT = /\.(kml|png|jpe?g|gif|webp)$/i;

export class KmlSanitizeError extends Error {
    declare code: any;
    declare name: string;
    constructor(code, message?) {
        super(message || code);
        this.name = "KmlSanitizeError";
        this.code = code;
    }
}

export function isRemoteHref(href) {
    const h = String(href || "").trim();
    if (!h) {
        return false;
    }
    const lower = h.toLowerCase();
    if (lower.startsWith("//")) {
        return true;
    }
    return /^(https?:|file:|ftp:|javascript:|vbscript:)/i.test(h);
}

export function isAllowedDataImageHref(href) {
    const h = String(href || "")
        .trim()
        .toLowerCase();
    if (!h.startsWith("data:")) {
        return false;
    }
    return ALLOWED_DATA_PREFIXES.some((p) => h.startsWith(p));
}

function looksLikeDtd(text) {
    const head = String(text || "")
        .slice(0, 4096)
        .toUpperCase();
    return head.includes("<!DOCTYPE") || head.includes("<!ENTITY");
}

function dropTagBlocks(text, blockRe, emptyRe) {
    let out = String(text);
    let n = 0;
    out = out.replace(blockRe, () => {
        n += 1;
        return "";
    });
    out = out.replace(emptyRe, () => {
        n += 1;
        return "";
    });
    return { text: out, count: n };
}

function rewriteHrefs(text, { zipLocalOk }) {
    const stripped: string[] = [];
    const out = String(text).replace(/<href>\s*([^<]+?)\s*<\/href>/gi, (full, inner) => {
        const raw = String(inner).trim();
        if (isAllowedDataImageHref(raw)) {
            return `<href>${raw}</href>`;
        }
        if (isRemoteHref(raw) || raw.toLowerCase().startsWith("data:")) {
            stripped.push("remote_href");
            return "";
        }
        if (!zipLocalOk) {
            stripped.push("remote_href");
            return "";
        }
        return full;
    });
    return { text: out, stripped };
}

function rewriteHrefAttrs(text, { zipLocalOk }) {
    const stripped: string[] = [];
    const out = String(text).replace(/(\s(?:xlink:)?href\s*=\s*)(["'])([^"']+)\2/gi, (full, _prefix, _quote, inner) => {
        const raw = String(inner).trim();
        if (isAllowedDataImageHref(raw)) {
            return full;
        }
        if (isRemoteHref(raw) || raw.toLowerCase().startsWith("data:") || !zipLocalOk) {
            stripped.push("remote_href");
            return "";
        }
        return full;
    });
    return { text: out, stripped };
}

function unwrapDescriptionInner(inner) {
    const trimmed = String(inner).trim();
    const cdata = trimmed.match(/^<!\[CDATA\[([\s\S]*?)\]\]>$/);
    if (cdata) {
        return cdata[1];
    }
    return String(inner);
}

function escapeXmlText(value) {
    return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function looksLikeHtml(value) {
    return /<[a-z][\s\S]*>/i.test(value);
}

function stripDescriptionHtml(text) {
    const stripped: string[] = [];
    const out = String(text).replace(/<description\b[^>]*>([\s\S]*?)<\/description>/gi, (full, inner) => {
        const content = unwrapDescriptionInner(inner);
        if (!looksLikeHtml(content) && !looksLikeHtml(inner)) {
            return full;
        }
        stripped.push("html_description");
        const plain = flattenHtmlDescription(content);
        return `<description>${escapeXmlText(plain)}</description>`;
    });
    return { text: out, stripped };
}

/**
 * @param {string} text
 * @param {{ zipLocalOk?: boolean }} [opts]
 * @returns {{ text: string, stripped: string[] }}
 */
export function sanitizeKmlText(text, opts: any = {}) {
    const zipLocalOk = Boolean(opts.zipLocalOk);
    if (looksLikeDtd(text)) {
        throw new KmlSanitizeError("dtd_forbidden");
    }
    const stripped: string[] = [];
    let out = String(text);
    const net = dropTagBlocks(out, /<NetworkLink\b[^>]*>[\s\S]*?<\/NetworkLink\s*>/gi, /<NetworkLink\b[^>]*\/>/gi);
    out = net.text;
    if (net.count) {
        stripped.push("network_link");
    }
    const netc = dropTagBlocks(
        out,
        /<NetworkLinkControl\b[^>]*>[\s\S]*?<\/NetworkLinkControl\s*>/gi,
        /<NetworkLinkControl\b[^>]*\/>/gi
    );
    out = netc.text;
    if (netc.count) {
        stripped.push("network_link");
    }
    const overlayBlocks = [
        /<GroundOverlay\b[^>]*>[\s\S]*?<\/GroundOverlay\s*>/gi,
        /<PhotoOverlay\b[^>]*>[\s\S]*?<\/PhotoOverlay\s*>/gi,
        /<ScreenOverlay\b[^>]*>[\s\S]*?<\/ScreenOverlay\s*>/gi,
    ];
    for (const blockRe of overlayBlocks) {
        out = out.replace(blockRe, (block) => {
            const hrefs = [...block.matchAll(/<href>\s*([^<]+?)\s*<\/href>/gi)].map((m) => m[1].trim());
            const remote = hrefs.some(
                (h) => isRemoteHref(h) || (h.toLowerCase().startsWith("data:") && !isAllowedDataImageHref(h))
            );
            const relative = hrefs.some((h) => h && !isAllowedDataImageHref(h) && !isRemoteHref(h));
            if (remote || (!zipLocalOk && relative)) {
                stripped.push("remote_overlay");
                return "";
            }
            return block;
        });
    }
    const desc = stripDescriptionHtml(out);
    out = desc.text;
    stripped.push(...desc.stripped);
    const hrefs = rewriteHrefs(out, { zipLocalOk });
    out = hrefs.text;
    stripped.push(...hrefs.stripped);
    const attrs = rewriteHrefAttrs(out, { zipLocalOk });
    out = attrs.text;
    stripped.push(...attrs.stripped);
    const hasPlacemark = /<placemark\b/i.test(out);
    if (!hasPlacemark && stripped.includes("network_link")) {
        throw new KmlSanitizeError("remote_content");
    }
    return { text: out, stripped };
}

export function kmzEntryAllowed(name) {
    const n = String(name || "").replace(/\\/g, "/");
    if (n.split("/").includes("..")) {
        return false;
    }
    return ALLOWED_KMZ_EXT.test(n);
}
