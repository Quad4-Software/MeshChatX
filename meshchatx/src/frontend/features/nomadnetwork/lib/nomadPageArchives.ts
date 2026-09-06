// SPDX-License-Identifier: 0BSD

import type { NomadPageArchive } from "./types.js";
import {
    createArchiveAddPayload,
    createArchivesGetPayload,
    createArchiveLoadPayload,
    sendNomadWs,
} from "./nomadPageDownloads.js";

interface ApiClient {
    get: (url: string, config?: Record<string, unknown>) => Promise<{ data?: any }>;
}

/** Request archives list over WS. Reply arrives as nomadnet.page.archives. */
export function requestPageArchives(destinationHash: string, pagePath: string): boolean {
    if (!destinationHash || !pagePath) {
        return false;
    }
    return sendNomadWs(createArchivesGetPayload(destinationHash, pagePath));
}

/** Ask the backend to load an archived page (reply is nomadnet.page.download). */
export function requestArchiveLoad(archiveId: string | number, downloadId: number): boolean {
    if (archiveId == null || downloadId == null) {
        return false;
    }
    return sendNomadWs(createArchiveLoadPayload(archiveId, downloadId));
}

/** Persist the current page as a manual archive. Reply is nomadnet.page.archive.added. */
export function requestManualArchive(destinationHash: string, pagePath: string, content: string): boolean {
    if (!destinationHash || !pagePath || !content) {
        return false;
    }
    return sendNomadWs(createArchiveAddPayload(destinationHash, pagePath, content));
}

/**
 * HTTP fallback for a single archive body (Archives page handoff / tests).
 * Browser list + manual add must use WS so path filtering matches Vue.
 */
export async function fetchArchiveContent(
    api: ApiClient,
    archiveId: string | number
): Promise<{ content: string; hash: string; created_at: string; page_path?: string } | null> {
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
                page_path: typeof data.page_path === "string" ? data.page_path : undefined,
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

export type { NomadPageArchive };
