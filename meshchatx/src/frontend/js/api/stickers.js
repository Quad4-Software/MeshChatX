// @ts-check

/**
 * Endpoint wrappers for /api/v1/stickers.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listStickers(...rest) {
    return window.api.get(apiPath("/stickers"), ...rest);
}
export function getImage(id, ...rest) {
    return window.api.get(apiPath(`/stickers/${id}/image`), ...rest);
}
export function getExport(...rest) {
    return window.api.get(apiPath("/stickers/export"), ...rest);
}
export function createStickers(data, ...rest) {
    return window.api.post(apiPath("/stickers"), data, ...rest);
}
export function importStickers(data, ...rest) {
    return window.api.post(apiPath("/stickers/import"), data, ...rest);
}
