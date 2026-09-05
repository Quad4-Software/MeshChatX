/**
 * Maintenance, stickers, folders, and RNS reload API calls used from settings.
 */

/**
 * @param {{ delete: (path: string, config?: object) => Promise<unknown> }} api
 */
export async function clearMessages(api) {
    await api.delete("/api/v1/maintenance/messages");
}

/**
 * @param {{ get: (path: string) => Promise<{ data?: { count?: number } }> }} api
 */
export async function previewDuplicateMessages(api) {
    const response = await api.get("/api/v1/maintenance/messages/duplicates");
    return { count: Number(response?.data?.count) || 0 };
}

/**
 * @param {{ delete: (path: string) => Promise<{ data?: { deleted?: number } }> }} api
 */
export async function clearDuplicateMessages(api) {
    const response = await api.delete("/api/v1/maintenance/messages/duplicates");
    return { deleted: Number(response?.data?.deleted) || 0 };
}

/**
 * Build query params for age-based message purge/export.
 * @param {{ mode: "days"|"date", days?: number, beforeDate?: string }} opts
 * @returns {{ older_than_days?: number, before?: string }|null}
 */
export function buildMessageAgeFilterParams(opts) {
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

/**
 * @param {{ get: (path: string, config?: object) => Promise<{ data?: { count?: number, cutoff?: number } }> }} api
 * @param {{ older_than_days?: number, before?: string }} params
 */
export async function previewMessageAgePurge(api, params) {
    const response = await api.get("/api/v1/maintenance/messages/purge-preview", { params });
    return {
        count: Number(response?.data?.count) || 0,
        cutoff: response?.data?.cutoff,
    };
}

/**
 * @param {{ delete: (path: string, config?: object) => Promise<{ data?: { deleted?: number } }> }} api
 * @param {{ older_than_days?: number, before?: string }} params
 */
export async function purgeMessagesByAge(api, params) {
    const response = await api.delete("/api/v1/maintenance/messages", { params });
    return {
        deleted: Number(response?.data?.deleted) || 0,
        cutoff: response?.data?.cutoff,
    };
}

/**
 * @param {{ post: (path: string, data?: object, config?: object) => Promise<{ data?: object }> }} api
 * @param {{ older_than_days?: number, before?: string }|null|undefined} [params]
 */
export async function exportMessagesBundle(api, params) {
    const body = params && typeof params === "object" ? { ...params } : {};
    const response = await api.post("/api/v1/maintenance/messages/export", body);
    return response?.data;
}

/**
 * @param {{ delete: (path: string) => Promise<unknown> }} api
 */
export async function clearAnnounces(api) {
    await api.delete("/api/v1/maintenance/announces");
}

/**
 * @param {{ delete: (path: string, config?: object) => Promise<unknown> }} api
 */
export async function clearNomadnetFavorites(api) {
    await api.delete("/api/v1/maintenance/favourites", {
        params: { aspect: "nomadnetwork.node" },
    });
}

/**
 * @param {{ delete: (path: string) => Promise<unknown> }} api
 */
export async function clearLxmfIcons(api) {
    await api.delete("/api/v1/maintenance/lxmf-icons");
}

/**
 * @param {{ delete: (path: string) => Promise<unknown> }} api
 */
export async function clearStickers(api) {
    await api.delete("/api/v1/maintenance/stickers");
}

/**
 * @param {{ delete: (path: string) => Promise<unknown> }} api
 */
export async function clearGifs(api) {
    await api.delete("/api/v1/maintenance/gifs");
}

/**
 * @param {{ delete: (path: string) => Promise<unknown> }} api
 */
export async function clearArchives(api) {
    await api.delete("/api/v1/maintenance/archives");
}

/**
 * @param {{ delete: (path: string) => Promise<unknown> }} api
 */
export async function clearReticulumDocs(api) {
    await api.delete("/api/v1/maintenance/docs/reticulum");
}

/**
 * @param {{ delete: (path: string) => Promise<{ data?: { dropped?: number } }> }} api
 */
export async function clearPathTable(api) {
    return api.delete("/api/v1/maintenance/path-table");
}

/**
 * @param {{ post: (path: string) => Promise<unknown> }} api
 */
export async function reloadReticulum(api) {
    return api.post("/api/v1/reticulum/reload");
}

/**
 * @param {{ get: (path: string) => Promise<{ data?: { stickers?: unknown[] } }> }} api
 * @returns {Promise<number>}
 */
export async function fetchStickerCount(api) {
    try {
        const response = await api.get("/api/v1/stickers");
        const list = response.data?.stickers;
        return Array.isArray(list) ? list.length : 0;
    } catch {
        return 0;
    }
}

/**
 * @param {{ get: (path: string) => Promise<{ data?: { gifs?: unknown[] } }> }} api
 * @returns {Promise<number>}
 */
export async function fetchGifCount(api) {
    try {
        const response = await api.get("/api/v1/gifs");
        const list = response.data?.gifs;
        return Array.isArray(list) ? list.length : 0;
    } catch {
        return 0;
    }
}
