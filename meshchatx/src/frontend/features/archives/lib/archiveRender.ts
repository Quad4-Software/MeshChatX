// SPDX-License-Identifier: 0BSD

import MicronParser from "../../../js/MicronParser.js";
import { isolateNomadLinksInHtml, renderNomadPageByPath } from "../../../js/NomadPageRenderer.js";
import Utils from "../../../js/Utils.js";
import type { ArchiveItem, NomadRenderOptions } from "./types.js";

/** Shorten destination hash for badge display */
export function shortHash(hash?: string | null): string {
    return (hash || "").substring(0, 12);
}

/** Format date string as relative time */
export function formatArchiveDate(dateStr?: string | null): string {
    return Utils.formatTimeAgo(dateStr);
}

/** Sanitize text for safe insertion into HTML */
export function escapeHtml(value?: unknown): string {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/** Highlight query terms within snippet text */
export function highlightMatch(snippet: string, searchQuery: string): string {
    const safe = escapeHtml(snippet);
    const q = (searchQuery || "").trim();
    if (!q || q.length < 2) {
        return safe;
    }
    const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    try {
        const re = new RegExp(`(${escaped})`, "ig");
        return safe.replace(re, '<mark class="bg-sem-accent/30 text-inherit rounded-sm px-0.5">$1</mark>');
    } catch {
        return safe;
    }
}

/** Compute CSS classes for rendering Nomad content by page extension */
export function pathViewerClasses(pagePath?: string | null): string[] {
    if (!pagePath) {
        return ["wrap-break-word", "whitespace-pre-wrap", "text-gray-100"];
    }
    const pl = (pagePath || "").split("`")[0].toLowerCase();
    const isRich = pl.endsWith(".mu") || pl.endsWith(".md") || pl.endsWith(".html");
    const isHtml = pl.endsWith(".html");
    const isMd = pl.endsWith(".md");
    const classes = ["wrap-break-word"];
    if (isRich) {
        classes.push("nomad-page-rich");
    } else {
        classes.push("whitespace-pre-wrap");
    }
    if (isHtml) {
        classes.push("nomad-page-html-host");
    } else {
        classes.push("text-gray-100");
    }
    if (isMd) {
        classes.push("nomad-markdown-host");
    }
    return classes;
}

/** Compute CSS classes for archive card preview */
export function previewClasses(archive?: Pick<ArchiveItem, "page_path"> | null): string[] {
    return pathViewerClasses(archive?.page_path);
}

/** Render content by file extension and Nomad parsing options */
export function renderContentByPath(
    pagePath: string | undefined,
    content: string | undefined,
    destinationHash: string | undefined,
    renderOptions: NomadRenderOptions,
    wasmActive: boolean
): string {
    const pathPart = (pagePath || "").split("`")[0];
    const pl = pathPart.toLowerCase();
    const hasKnownExt = /\.(mu|md|txt|html)$/.test(pl);
    const micronOpts = {
        useWasm: wasmActive,
    };
    const dest = destinationHash || null;
    if (!hasKnownExt && String(content).includes("`")) {
        let out = new MicronParser().convertMicronToHtml(content, {}, micronOpts);
        if (dest) {
            out = isolateNomadLinksInHtml(out, dest);
        }
        return out;
    }
    if (!hasKnownExt) {
        let out = new MicronParser().convertMicronToHtml(content, {}, micronOpts);
        if (dest) {
            out = isolateNomadLinksInHtml(out, dest);
        }
        return out;
    }
    return renderNomadPageByPath(pathPart, content, {}, MicronParser, {
        ...renderOptions,
        nomadDestinationHash: dest || renderOptions.nomadDestinationHash,
    });
}

/** Render preview snippet HTML safely */
export function renderPreviewHtml(
    pagePath: string | undefined,
    content: string | undefined,
    destinationHash: string | undefined,
    renderOptions: NomadRenderOptions,
    wasmActive: boolean
): string {
    if (!content) {
        return "";
    }
    try {
        return renderContentByPath(pagePath, content, destinationHash, renderOptions, wasmActive);
    } catch {
        return escapeHtml(content).replace(/\n/g, "<br>");
    }
}

/** Render full archive content with error fallback */
export function renderFullContent(
    archive: ArchiveItem | null | undefined,
    renderOptions: NomadRenderOptions,
    wasmActive: boolean
): string {
    if (!archive?.content) {
        return "";
    }
    try {
        return renderContentByPath(
            archive.page_path,
            archive.content,
            archive.destination_hash,
            renderOptions,
            wasmActive
        );
    } catch (e) {
        console.error("Archive render failed", e);
        return escapeHtml(archive.content);
    }
}

/** Compute and cache HTML snippet for card preview */
export function cardPreviewHtml(
    archive: ArchiveItem,
    searchQuery: string,
    cache: Record<string, string>,
    wasmActive: boolean,
    renderOptions: NomadRenderOptions
): string {
    const cacheKey = `${archive.id}:${archive.hash || ""}:${wasmActive ? "w" : "j"}`;
    if (cache[cacheKey]) {
        return cache[cacheKey];
    }
    const source = archive.preview || archive.snippet || "";
    if (!source) {
        return "";
    }
    let html = renderPreviewHtml(archive.page_path, source, archive.destination_hash, renderOptions, wasmActive);
    if (searchQuery && archive.snippet && !archive.preview) {
        html = highlightMatch(archive.snippet, searchQuery);
    }
    cache[cacheKey] = html;
    return html;
}
