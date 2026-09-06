// SPDX-License-Identifier: 0BSD

/**
 * Maintenance, stickers, folders, and RNS reload API calls used from settings.
 */

import type { ApiClient } from "../apiClient.js";

export type MessageAgeFilterMode = "days" | "date";

export type MessageAgeFilterOpts = {
    mode: MessageAgeFilterMode;
    days?: number;
    beforeDate?: string;
};

export type MessageAgeFilterParams = {
    older_than_days?: number;
    before?: string;
};

export async function clearMessages(api: Pick<ApiClient, "delete">): Promise<void> {
    await api.delete("/api/v1/maintenance/messages");
}

export async function previewDuplicateMessages(api: Pick<ApiClient, "get">): Promise<{ count: number }> {
    const response = await api.get<{ count?: number }>("/api/v1/maintenance/messages/duplicates");
    return { count: Number(response?.data?.count) || 0 };
}

export async function clearDuplicateMessages(api: Pick<ApiClient, "delete">): Promise<{ deleted: number }> {
    const response = await api.delete<{ deleted?: number }>("/api/v1/maintenance/messages/duplicates");
    return { deleted: Number(response?.data?.deleted) || 0 };
}

/** Build query params for age-based message purge/export. */
export function buildMessageAgeFilterParams(
    opts: MessageAgeFilterOpts | null | undefined
): MessageAgeFilterParams | null {
    if (!opts || typeof opts !== "object") return null;
    if (opts.mode === "date") {
        const before = typeof opts.beforeDate === "string" ? opts.beforeDate.trim() : "";
        if (!/^\d{4}-\d{2}-\d{2}$/.test(before)) return null;
        return { before };
    }
    const days = Number(opts.days);
    if (!Number.isFinite(days) || days < 1 || days > 10000) return null;
    return { older_than_days: Math.floor(days) };
}

export async function previewMessageAgePurge(
    api: Pick<ApiClient, "get">,
    params: MessageAgeFilterParams
): Promise<{ count: number; cutoff: number | undefined }> {
    const response = await api.get<{ count?: number; cutoff?: number }>("/api/v1/maintenance/messages/purge-preview", {
        params,
    });
    return {
        count: Number(response?.data?.count) || 0,
        cutoff: response?.data?.cutoff,
    };
}

export async function purgeMessagesByAge(
    api: Pick<ApiClient, "delete">,
    params: MessageAgeFilterParams
): Promise<{ deleted: number; cutoff: unknown }> {
    const response = await api.delete<{ deleted?: number; cutoff?: unknown }>("/api/v1/maintenance/messages", {
        params,
    });
    return {
        deleted: Number(response?.data?.deleted) || 0,
        cutoff: response?.data?.cutoff,
    };
}

export async function exportMessagesBundle(
    api: Pick<ApiClient, "post">,
    params?: MessageAgeFilterParams | null
): Promise<unknown> {
    const body = params && typeof params === "object" ? { ...params } : {};
    const response = await api.post("/api/v1/maintenance/messages/export", body);
    return response?.data;
}

export async function clearAnnounces(api: Pick<ApiClient, "delete">): Promise<void> {
    await api.delete("/api/v1/maintenance/announces");
}

export async function clearNomadnetFavorites(api: Pick<ApiClient, "delete">): Promise<void> {
    await api.delete("/api/v1/maintenance/favourites", {
        params: { aspect: "nomadnetwork.node" },
    });
}

export async function clearLxmfIcons(api: Pick<ApiClient, "delete">): Promise<void> {
    await api.delete("/api/v1/maintenance/lxmf-icons");
}

export async function clearStickers(api: Pick<ApiClient, "delete">): Promise<void> {
    await api.delete("/api/v1/maintenance/stickers");
}

export async function clearGifs(api: Pick<ApiClient, "delete">): Promise<void> {
    await api.delete("/api/v1/maintenance/gifs");
}

export async function clearArchives(api: Pick<ApiClient, "delete">): Promise<void> {
    await api.delete("/api/v1/maintenance/archives");
}

export async function clearReticulumDocs(api: Pick<ApiClient, "delete">): Promise<void> {
    await api.delete("/api/v1/maintenance/docs/reticulum");
}

export async function clearPathTable(api: Pick<ApiClient, "delete">): Promise<unknown> {
    return api.delete("/api/v1/maintenance/path-table");
}

export async function reloadReticulum(api: Pick<ApiClient, "post">): Promise<unknown> {
    return api.post("/api/v1/reticulum/reload");
}

export async function fetchStickerCount(api: Pick<ApiClient, "get">): Promise<number> {
    try {
        const response = await api.get<{ stickers?: unknown[] }>("/api/v1/stickers");
        const list = response.data?.stickers;
        return Array.isArray(list) ? list.length : 0;
    } catch {
        return 0;
    }
}

export async function fetchGifCount(api: Pick<ApiClient, "get">): Promise<number> {
    try {
        const response = await api.get<{ gifs?: unknown[] }>("/api/v1/gifs");
        const list = response.data?.gifs;
        return Array.isArray(list) ? list.length : 0;
    } catch {
        return 0;
    }
}
