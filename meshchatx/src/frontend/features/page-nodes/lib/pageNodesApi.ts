// SPDX-License-Identifier: 0BSD

import { PAGE_NODES_API_BASE } from "./constants.js";
import type { AnnounceSettingsForm, PageContentResponse, PageNode, PageNodeStartResponse } from "./types.js";

declare const window: {
    api: {
        get: (url: string) => Promise<{ data: unknown }>;
        post: (url: string, data?: unknown, config?: unknown) => Promise<{ data: unknown }>;
        put: (url: string, data?: unknown) => Promise<{ data: unknown }>;
        patch: (url: string, data?: unknown) => Promise<{ data: unknown }>;
        delete: (url: string) => Promise<{ data: unknown }>;
    };
};

/** Fetches list of all hosted page nodes */
export async function fetchPageNodes(): Promise<PageNode[]> {
    const response = await window.api.get(PAGE_NODES_API_BASE);
    return response.data as PageNode[];
}

/** Creates a new page node */
export async function createPageNode(name: string): Promise<PageNode> {
    const response = await window.api.post(PAGE_NODES_API_BASE, { name });
    return response.data as PageNode;
}

/** Deletes a page node by its unique identifier */
export async function deletePageNode(nodeId: string): Promise<void> {
    await window.api.delete(`${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}`);
}

/** Starts a page node destination on the mesh */
export async function startPageNode(nodeId: string): Promise<PageNodeStartResponse> {
    const response = await window.api.post(`${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/start`);
    return response.data as PageNodeStartResponse;
}

/** Stops an active page node destination */
export async function stopPageNode(nodeId: string): Promise<void> {
    await window.api.post(`${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/stop`);
}

/** Sends an immediate announce for a running page node */
export async function announcePageNode(nodeId: string): Promise<void> {
    await window.api.post(`${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/announce`);
}

/** Renames a page node */
export async function renamePageNode(nodeId: string, name: string): Promise<void> {
    await window.api.put(`${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/rename`, { name });
}

/** Updates periodic announce and execution settings for a page node */
export async function updateAnnounceSettings(nodeId: string, settings: AnnounceSettingsForm): Promise<PageNode> {
    const response = await window.api.patch(`${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/announce-settings`, {
        announce_enabled: settings.announce_enabled,
        announce_interval_seconds: settings.announce_interval_seconds,
        executable_pages_enabled: settings.executable_pages_enabled,
    });
    return response.data as PageNode;
}

/** Creates an empty page file on a node */
export async function createPage(nodeId: string, name: string): Promise<void> {
    await window.api.post(`${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/pages`, {
        name,
        content: "",
    });
}

/** Loads page content and metadata for editing */
export async function fetchPage(nodeId: string, pageName: string): Promise<PageContentResponse> {
    const response = await window.api.get(
        `${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/pages/${encodeURIComponent(pageName)}`
    );
    let body = response.data;
    if (typeof body === "string") {
        try {
            body = JSON.parse(body);
        } catch {
            body = {};
        }
    }
    const typed = body as Partial<PageContentResponse>;
    return {
        name: pageName,
        content: typed.content ?? "",
        executable: typed.executable === true,
    };
}

/** Saves updated content and executable flag for a page */
export async function savePage(nodeId: string, name: string, content: string, executable: boolean): Promise<void> {
    await window.api.post(`${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/pages`, {
        name,
        content,
        executable,
    });
}

/** Deletes a page file from a node */
export async function deletePage(nodeId: string, pageName: string): Promise<void> {
    await window.api.delete(
        `${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/pages/${encodeURIComponent(pageName)}`
    );
}

/** Uploads a static file asset to a page node */
export async function uploadFile(nodeId: string, file: File): Promise<void> {
    const formData = new FormData();
    formData.append("file", file);
    await window.api.post(`${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/files`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
    });
}

/** Deletes a static file asset from a page node */
export async function deleteFile(nodeId: string, fileName: string): Promise<void> {
    await window.api.delete(
        `${PAGE_NODES_API_BASE}/${encodeURIComponent(nodeId)}/files/${encodeURIComponent(fileName)}`
    );
}
