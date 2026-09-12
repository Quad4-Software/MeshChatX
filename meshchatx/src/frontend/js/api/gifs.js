// @ts-check

/**
 * Endpoint wrappers for /api/v1/gifs.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listGifs(...rest) {
    return window.api.get(apiPath("/gifs"), ...rest);
}
export function getImage(id, ...rest) {
    return window.api.get(apiPath(`/gifs/${id}/image`), ...rest);
}
export function getExport(...rest) {
    return window.api.get(apiPath("/gifs/export"), ...rest);
}
export function createGifs(data, ...rest) {
    return window.api.post(apiPath("/gifs"), data, ...rest);
}
export function useGifs(id, data, ...rest) {
    return window.api.post(apiPath(`/gifs/${id}/use`), data, ...rest);
}
export function importGifs(data, ...rest) {
    return window.api.post(apiPath("/gifs/import"), data, ...rest);
}
