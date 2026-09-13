// SPDX-License-Identifier: 0BSD

import LinkUtils from "../../../js/LinkUtils.js";
import { DEFAULT_PAGE_PATH } from "./constants.js";
import type { NomadNavigateEvent, NomadNode } from "./types.js";

export function cleanNomadUrl(rawUrl: string): string {
    return (rawUrl || "").trim().replace(/^nomadnet:\/\//i, "");
}

export function parseNomadUrl(rawUrl: string): { destinationHash: string | null; pagePath: string | null } {
    const cleaned = cleanNomadUrl(rawUrl);
    if (!cleaned) {
        return { destinationHash: null, pagePath: null };
    }

    if (cleaned.includes(":/page/")) {
        const parts = cleaned.split(":/page/");
        const hash = parts[0].trim();
        const path = parts[1] ? `/page/${parts[1].trim()}` : DEFAULT_PAGE_PATH;
        return { destinationHash: hash || null, pagePath: path };
    }

    if (cleaned.startsWith("/page/")) {
        return { destinationHash: null, pagePath: cleaned };
    }

    if (/^[0-9a-fA-F]{32}$/.test(cleaned)) {
        return { destinationHash: cleaned, pagePath: DEFAULT_PAGE_PATH };
    }

    if (cleaned.includes(":")) {
        const parts = cleaned.split(":");
        const hash = parts[0].trim();
        const rest = parts.slice(1).join(":").trim();
        const path = rest.startsWith("/page/") ? rest : rest ? `/page/${rest.replace(/^\/+/, "")}` : DEFAULT_PAGE_PATH;
        return { destinationHash: hash || null, pagePath: path };
    }

    return { destinationHash: null, pagePath: null };
}

export function buildNomadUrl(destinationHash: string, pagePath: string): string {
    const cleanHash = (destinationHash || "").trim();
    const cleanPath = (pagePath || "").trim();
    if (!cleanHash) {
        return cleanPath;
    }
    return `${cleanHash}:${cleanPath}`;
}

export function resolveRelativeNomadPath(currentPath: string | null, targetPath: string): string {
    if (!targetPath) {
        return DEFAULT_PAGE_PATH;
    }
    if (targetPath.startsWith("/page/")) {
        return targetPath;
    }
    if (targetPath.startsWith("/")) {
        return `/page${targetPath}`;
    }

    const cur = currentPath && currentPath.startsWith("/page/") ? currentPath : DEFAULT_PAGE_PATH;
    const segments = cur.replace(/^\/page\//, "").split("/");
    segments.pop();

    const targetSegments = targetPath.split("/");
    for (const segment of targetSegments) {
        if (segment === ".") {
            continue;
        }
        if (segment === "..") {
            if (segments.length > 0) {
                segments.pop();
            }
        } else if (segment) {
            segments.push(segment);
        }
    }

    return `/page/${segments.join("/")}`;
}

export function encodeNomadFormQuery(fields: Record<string, string>, fieldSpec?: string): string {
    if (!fields || typeof fields !== "object") {
        return "";
    }
    if (fieldSpec) {
        const order = fieldSpec
            .split("|")
            .map((f) => f.trim())
            .filter(Boolean);
        const parts: string[] = [];
        for (const key of order) {
            const val = fields[key] ?? "";
            parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(val)}`);
        }
        return parts.join("|");
    }
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(fields)) {
        params.set(k, v);
    }
    return params.toString();
}

export interface NomadNavigateDeps {
    nodes: Record<string, NomadNode>;
    selectedNode: NomadNode | null;
    nodePagePath: string | null;
    relativePagePath: string;
    isPrivate: boolean;
    pushHistory: (combinedPath: string) => void;
    selectNode: (node: NomadNode) => void;
    loadPage: (destinationHash: string, pagePath: string) => void;
    onNavigate?: (hash: string, path?: string, isPrivate?: boolean) => void;
}

/** Apply a crash-tab navigate event: external http links, hash urls, or page-relative paths. */
export function navigateNomadPageEvent(e: NomadNavigateEvent, deps: NomadNavigateDeps): void {
    if (!e.url) {
        return;
    }
    if (LinkUtils.httpUrlHrefOrNull(e.url)) {
        window.open(e.url, "_blank");
        return;
    }
    const { destinationHash: dHash, pagePath: pPath } = parseNomadUrl(e.url);
    if (dHash) {
        const targetPath = pPath || DEFAULT_PAGE_PATH;
        if (deps.nodePagePath) deps.pushHistory(deps.nodePagePath);
        deps.selectNode(deps.nodes[dHash] || { destination_hash: dHash, display_name: dHash.substring(0, 16) });
        deps.loadPage(dHash, targetPath);
        deps.onNavigate?.(dHash, targetPath, deps.isPrivate);
        return;
    }
    const selectedHash = deps.selectedNode?.destination_hash;
    if (!selectedHash || !pPath) {
        return;
    }
    const resolved = resolveRelativeNomadPath(deps.relativePagePath || "/", pPath);
    const hasFields = e.fields && Object.keys(e.fields).length > 0;
    const target = hasFields ? `${resolved}?${encodeNomadFormQuery(e.fields as Record<string, string>)}` : resolved;
    if (deps.nodePagePath) deps.pushHistory(deps.nodePagePath);
    deps.loadPage(selectedHash, target);
}
