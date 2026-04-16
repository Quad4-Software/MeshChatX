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
