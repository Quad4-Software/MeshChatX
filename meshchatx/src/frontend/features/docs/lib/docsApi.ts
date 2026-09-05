// SPDX-License-Identifier: 0BSD

import type { DocContentResponse, DocsStatus, MeshChatXDocsListResponse, SearchResultItem } from "./types.js";

/**
 * Fetch status of docs extraction and available versions.
 */
export async function fetchDocsStatus(): Promise<DocsStatus> {
    const response = await window.api.get("/api/v1/docs/status");
    return (response.data || {}) as DocsStatus;
}

/**
 * Fetch MeshChatX docs manifest and sections.
 */
export async function fetchMeshChatXDocsList(lang: string): Promise<MeshChatXDocsListResponse> {
    const response = await window.api.get("/api/v1/meshchatx-docs/list", {
        params: { lang },
    });
    return (response.data || {}) as MeshChatXDocsListResponse;
}

/**
 * Fetch document rendered html and markdown content.
 */
export async function fetchDocContent(path: string): Promise<DocContentResponse> {
    const response = await window.api.get("/api/v1/meshchatx-docs/content", {
        params: { path },
    });
    return (response.data || {}) as DocContentResponse;
}

/**
 * Search documentation by query and language.
 */
export async function searchDocs(q: string, lang: string): Promise<SearchResultItem[]> {
    const response = await window.api.get("/api/v1/docs/search", {
        params: { q, lang },
    });
    const data = response.data as { results?: SearchResultItem[] } | undefined;
    return Array.isArray(data?.results) ? data.results : [];
}

/**
 * Switch Reticulum docs version.
 */
export async function switchDocsVersion(version: string): Promise<void> {
    await window.api.post("/api/v1/docs/switch", { version });
}

/**
 * Delete a Reticulum docs version.
 */
export async function deleteDocsVersion(version: string): Promise<void> {
    await window.api.delete(`/api/v1/docs/version/${encodeURIComponent(version)}`);
}

/**
 * Upload a documentation ZIP file.
 */
export async function uploadDocsZip(version: string, file: File): Promise<void> {
    const formData = new FormData();
    formData.append("file", file);
    await window.api.post(`/api/v1/docs/upload?version=${encodeURIComponent(String(version).trim())}`, formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
    });
}
