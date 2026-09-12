// @ts-check

/**
 * Endpoint wrappers for /api/v1/sticker-packs.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteX(id, ...rest) {
    return window.api.delete(apiPath(`/sticker-packs/${id}?with_stickers=true`), ...rest);
}
export function listStickerPacks(...rest) {
    return window.api.get(apiPath("/sticker-packs"), ...rest);
}
export function getExport(id, ...rest) {
    return window.api.get(apiPath(`/sticker-packs/${id}/export`), ...rest);
}
export function createStickerPacks(data, ...rest) {
    return window.api.post(apiPath("/sticker-packs"), data, ...rest);
}
export function installStickerPacks(data, ...rest) {
    return window.api.post(apiPath("/sticker-packs/install"), data, ...rest);
}
