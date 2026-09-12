// @ts-check

/**
 * Endpoint wrappers for /api/v1/map.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteDataPublished(mapId, ...rest) {
    return window.api.delete(apiPath(`/map/data/published/${mapId}`), ...rest);
}
export function deleteDrawings(id, ...rest) {
    return window.api.delete(apiPath(`/map/drawings/${id}`), ...rest);
}
export function deleteExport(exportId, ...rest) {
    return window.api.delete(apiPath(`/map/export/${exportId}`), ...rest);
}
export function deleteMbtiles(filename, ...rest) {
    return window.api.delete(apiPath(`/map/mbtiles/${filename}`), ...rest);
}
export function deleteOverlays(id, ...rest) {
    return window.api.delete(apiPath(`/map/overlays/${id}`), ...rest);
}
export function getDataHeard(...rest) {
    return window.api.get(apiPath("/map/data/heard"), ...rest);
}
export function getDataPublished(...rest) {
    return window.api.get(apiPath("/map/data/published"), ...rest);
}
export function getDataStatus(...rest) {
    return window.api.get(apiPath("/map/data/status"), ...rest);
}
export function listDrawings(...rest) {
    return window.api.get(apiPath("/map/drawings"), ...rest);
}
export function getExport(exportId, ...rest) {
    return window.api.get(apiPath(`/map/export/${exportId}`), ...rest);
}
export function listMbtiles(...rest) {
    return window.api.get(apiPath("/map/mbtiles"), ...rest);
}
export function getOffline(...rest) {
    return window.api.get(apiPath("/map/offline"), ...rest);
}
export function listOverlays(...rest) {
    return window.api.get(apiPath("/map/overlays"), ...rest);
}
export function getOverlaysJobs(jobId, ...rest) {
    return window.api.get(apiPath(`/map/overlays/jobs/${jobId}`), ...rest);
}
export function updateDataConfig(data, ...rest) {
    return window.api.patch(apiPath("/map/data/config"), data, ...rest);
}
export function updateOverlays(id, data, ...rest) {
    return window.api.patch(apiPath(`/map/overlays/${id}`), data, ...rest);
}
export function postDataAddOverlay(data, ...rest) {
    return window.api.post(apiPath("/map/data/add-overlay"), data, ...rest);
}
export function announceData(data, ...rest) {
    return window.api.post(apiPath("/map/data/announce"), data, ...rest);
}
export function postDataCatalog(data, ...rest) {
    return window.api.post(apiPath("/map/data/catalog"), data, ...rest);
}
export function publishData(data, ...rest) {
    return window.api.post(apiPath("/map/data/publish"), data, ...rest);
}
export function createDrawings(data, ...rest) {
    return window.api.post(apiPath("/map/drawings"), data, ...rest);
}
export function exportMap(data, ...rest) {
    return window.api.post(apiPath("/map/export"), data, ...rest);
}
export function postMbtilesActive(data, ...rest) {
    return window.api.post(apiPath("/map/mbtiles/active"), data, ...rest);
}
export function restoreStarterMbtiles(data, ...rest) {
    return window.api.post(apiPath("/map/mbtiles/restore-starter"), data, ...rest);
}
export function postOffline(data, ...rest) {
    return window.api.post(apiPath("/map/offline"), data, ...rest);
}
export function createOverlays(data, ...rest) {
    return window.api.post(apiPath("/map/overlays"), data, ...rest);
}
export function refreshOverlays(id, data, ...rest) {
    return window.api.post(apiPath(`/map/overlays/${id}/refresh`), data, ...rest);
}
