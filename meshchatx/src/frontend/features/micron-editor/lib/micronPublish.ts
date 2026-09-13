// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import LinkUtils from "../../../js/LinkUtils.js";
import { t } from "../../../js/i18n.js";
import { NOMAD_DESTINATION_HASH, PAGE_EXTENSIONS } from "./constants.js";
import type { MicronTab, PageNodeItem } from "./types.js";

/** Page extensions allowed when publishing site files. */
export const ALLOWED_PAGE_EXTENSIONS = [".mu", ".md", ".txt", ".html"];

export interface PublishSiteEntry {
    tabId: number;
    tabName: string;
    content: string;
    include: boolean;
    filename: string;
}

export interface PublishSitePage {
    name: string;
    content: string;
    label: string;
}

export interface PublishSitePayload {
    nodeId: string | null;
    newServerName: string;
    pages: PublishSitePage[];
    generateIndex: boolean;
}

/**
 * Extract simple page name strings from API page list.
 */
export function pageNamesFromList(pages: unknown[] | undefined | null): string[] {
    return (pages || [])
        .map((entry) => (typeof entry === "string" ? entry : (entry as { name?: string })?.name))
        .filter((n): n is string => Boolean(n));
}

/**
 * Strip file extension from tab name for publish base name.
 */
export function tabNameToPageBase(tab: MicronTab): string {
    const name = (tab.name || "").trim().replace(/\s+/g, "_");
    const lower = name.toLowerCase();
    for (const ext of PAGE_EXTENSIONS) {
        if (lower.endsWith(ext)) {
            return name.slice(0, -ext.length);
        }
    }
    return name;
}

/**
 * Ensure base publish name has an extension, inheriting from tab or defaulting to .mu.
 */
export function pageBaseWithExtension(base: string, tab?: MicronTab): string {
    const trimmed = String(base || "").trim();
    if (!trimmed) {
        return trimmed;
    }
    const lower = trimmed.toLowerCase();
    for (const ext of PAGE_EXTENSIONS) {
        if (lower.endsWith(ext)) {
            return trimmed;
        }
    }
    const tabName = (tab?.name || "").trim();
    const tabLower = tabName.toLowerCase();
    for (const ext of PAGE_EXTENSIONS) {
        if (tabLower.endsWith(ext)) {
            return `${trimmed}${ext}`;
        }
    }
    return trimmed;
}

/**
 * Detect default auto-generated tab names.
 */
export function isUnsetMicronTabName(name: string | undefined | null): boolean {
    const trimmed = (name || "").trim();
    if (!trimmed) {
        return true;
    }
    const newTabLabel = t("tools.micron_editor.new_tab");
    if (trimmed === newTabLabel) {
        return true;
    }
    const numberedPrefix = `${newTabLabel} `;
    if (!trimmed.startsWith(numberedPrefix)) {
        return false;
    }
    return /^\d+$/.test(trimmed.slice(numberedPrefix.length));
}

/**
 * Resolve publish file base name with prompts when necessary.
 */
export async function resolvePublishPageBase(
    tab: MicronTab,
    existingPages: unknown[],
    serverName: string
): Promise<string | null> {
    const pageNames = pageNamesFromList(existingPages);
    const hasIndex = pageNames.includes("index.mu");
    if (!hasIndex) {
        return "index";
    }
    if (!isUnsetMicronTabName(tab.name)) {
        const base = tabNameToPageBase(tab);
        return base || null;
    }
    const entered = await DialogUtils.prompt(t("tools.micron_editor.publish_prompt_name", { server: serverName }));
    if (entered === null || !String(entered).trim()) {
        return null;
    }
    let base = String(entered).trim().replace(/\s+/g, "_");
    const lower = base.toLowerCase();
    for (const ext of PAGE_EXTENSIONS) {
        if (lower.endsWith(ext)) {
            return base;
        }
    }
    return base || null;
}

/**
 * Ensure a mesh server page node is running before publishing.
 */
export async function ensureNodeRunning(node: PageNodeItem): Promise<PageNodeItem> {
    if (node?.running && node.destination_hash) {
        return node;
    }
    if (!node?.node_id) {
        throw new Error("missing_node");
    }
    const startRes = await window.api.post(`/api/v1/page-nodes/${node.node_id}/start`);
    const destinationHash =
        (startRes.data as { destination_hash?: string })?.destination_hash || node.destination_hash || "";
    return {
        ...node,
        running: true,
        destination_hash: destinationHash,
    };
}

/**
 * Normalize nomad page path for destination navigation.
 */
export function nomadPagePathForName(pageName: string | undefined | null): string {
    const name = String(pageName || "index.mu").trim();
    if (!name) {
        return "/page/index.mu";
    }
    if (name.startsWith("/page/")) {
        return name;
    }
    if (name.startsWith("/")) {
        return name;
    }
    return `/page/${name}`;
}

/**
 * Fetch available page nodes from the API.
 */
export async function fetchPageNodesList(): Promise<PageNodeItem[]> {
    const response = await window.api.get("/api/v1/page-nodes");
    return Array.isArray(response.data) ? response.data : [];
}

/**
 * Fetch pages for a specific page node.
 */
export async function fetchNodePagesList(nodeId: string): Promise<unknown[]> {
    const response = await window.api.get(`/api/v1/page-nodes/${nodeId}/pages`);
    const data = response.data as { pages?: unknown[] } | undefined;
    return data?.pages ?? [];
}

/**
 * Sanitize a publish page filename: underscores for whitespace, word/dot/dash
 * chars only, no dot runs, no leading dots.
 */
export function sanitizePublishFilename(value: unknown): string {
    return String(value || "")
        .replace(/\s+/g, "_")
        .replace(/[^\w.-]/g, "")
        .replace(/\.{2,}/g, ".")
        .replace(/^\.+/, "");
}

/**
 * Default publish filename for a tab: sanitized tab name, keeping an existing
 * allowed extension or appending .mu.
 */
export function defaultPublishFilename(tab: MicronTab, index: number): string {
    const raw = String(tab?.name || "").trim();
    const cleaned = sanitizePublishFilename(raw.replace(/\s+/g, "_"));
    const lower = cleaned.toLowerCase();
    for (const ext of ALLOWED_PAGE_EXTENSIONS) {
        if (lower.endsWith(ext)) {
            return cleaned;
        }
    }
    const base = cleaned || `page_${index + 1}`;
    return `${base}.mu`;
}

/**
 * Make filenames unique within one publish batch. Sanitizing can collapse
 * distinct tab names onto the same filename ("My: Page" and "My Page" both
 * become "My_Page"), so collisions get a -2, -3, ... suffix before the
 * extension.
 */
export function dedupePublishFilenames(names: Array<string | null | undefined>): string[] {
    const used = new Set<string>();
    return (names || []).map((raw) => {
        const name = String(raw || "");
        if (!name || !used.has(name)) {
            used.add(name);
            return name;
        }
        const dot = name.lastIndexOf(".");
        const stem = dot > 0 ? name.slice(0, dot) : name;
        const ext = dot > 0 ? name.slice(dot) : "";
        for (let i = 2; ; i++) {
            const candidate = `${stem}-${i}${ext}`;
            if (!used.has(candidate)) {
                used.add(candidate);
                return candidate;
            }
        }
    });
}

/**
 * Build initial publish-site entries from editor tabs.
 */
export function buildPublishSiteEntries(tabs: MicronTab[]): PublishSiteEntry[] {
    const filenames = dedupePublishFilenames((tabs || []).map((tab, index) => defaultPublishFilename(tab, index)));
    return (tabs || []).map((tab, index) => ({
        tabId: tab.id,
        tabName: tab.name || "",
        content: tab.content,
        include: true,
        filename: filenames[index],
    }));
}

/**
 * Build a micron index page linking each published page on the node.
 */
export function buildSiteIndexPage(destinationHash: string, pages: PublishSitePage[]): string {
    const lines = [`>Links`, ""];
    for (const page of pages || []) {
        const label = String(page.label || page.name || "")
            .replace(/[`[\]]/g, "")
            .trim();
        const pageName = String(page.name || "").trim();
        if (!pageName) {
            continue;
        }
        lines.push(`[${label || pageName}\`${destinationHash}:/page/${pageName}]`);
    }
    lines.push("");
    return lines.join("\n");
}

/**
 * Open external http url or navigate to nomad destination.
 */
export function openNomadDestinationUrl(
    destination: string,
    onNavigate: (params: { destinationHash: string; path: string }) => void
): void {
    const raw = String(destination || "")
        .trim()
        .replace(/^nomadnetwork:\/\//i, "")
        .replace(/^lxmf:\/\//i, "");
    if (!raw) {
        return;
    }
    const httpHref = LinkUtils.httpUrlHrefOrNull(raw);
    if (httpHref) {
        window.open(httpHref, "_blank", "noopener,noreferrer");
        return;
    }
    const [hash, ...pathParts] = raw.split(":");
    if (!NOMAD_DESTINATION_HASH.test(hash)) {
        return;
    }
    const pathPart = pathParts.join(":") || "/page/index.mu";
    const pagePath = pathPart.split("`")[0].split("?")[0];
    onNavigate({ destinationHash: hash, path: pagePath });
}
