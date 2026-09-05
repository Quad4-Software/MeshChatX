// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import LinkUtils from "../../../js/LinkUtils.js";
import { t } from "../../../js/i18n.js";
import { NOMAD_DESTINATION_HASH, PAGE_EXTENSIONS } from "./constants.js";
import type { MicronTab, PageNodeItem } from "./types.js";

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
