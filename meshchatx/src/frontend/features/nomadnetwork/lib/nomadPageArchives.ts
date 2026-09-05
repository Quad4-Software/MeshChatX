// SPDX-License-Identifier: 0BSD

import type { NomadPageArchive } from "./types.js";

interface ApiClient {
    get: (url: string, config?: Record<string, unknown>) => Promise<{ data?: any }>;
    post: (url: string, body?: unknown, config?: Record<string, unknown>) => Promise<{ data?: any }>;
}

export async function fetchPageArchives(
    api: ApiClient,
    destinationHash: string,
    pagePath: string
): Promise<NomadPageArchive[]> {
    if (!api || !destinationHash || !pagePath) {
        return [];
    }
    try {
        const res = await api.get("/api/v1/nomadnet/archives", {
            params: {
                destination_hash: destinationHash,
                path: pagePath,
            },
        });
        const items = res.data?.archives || res.data || [];
        return Array.isArray(items) ? items : [];
    } catch {
        return [];
    }
}

export async function createManualArchive(
    api: ApiClient,
    destinationHash: string,
    pagePath: string,
    content: string
): Promise<NomadPageArchive | null> {
    if (!api || !destinationHash || !pagePath || !content) {
        return null;
    }
    try {
        const res = await api.post("/api/v1/nomadnet/archives", {
            destination_hash: destinationHash,
            path: pagePath,
            content,
        });
        return res.data?.archive || res.data || null;
    } catch {
        return null;
    }
}

export async function fetchArchiveContent(
    api: ApiClient,
    archiveId: string | number
): Promise<{ content: string; hash: string; created_at: string } | null> {
    if (!api || !archiveId) {
        return null;
    }
    try {
        const res = await api.get(`/api/v1/nomadnet/archives/${encodeURIComponent(String(archiveId))}`);
        const data = res.data?.archive || res.data;
        if (data && typeof data === "object") {
            return {
                content: typeof data.content === "string" ? data.content : "",
                hash: typeof data.hash === "string" ? data.hash : "",
                created_at: typeof data.created_at === "string" ? data.created_at : "",
            };
        }
        if (typeof data === "string") {
            return {
                content: data,
                hash: "",
                created_at: "",
            };
        }
        return null;
    } catch {
        return null;
    }
}
