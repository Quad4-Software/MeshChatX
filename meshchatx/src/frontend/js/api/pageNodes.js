// @ts-check

/**
 * Endpoint wrappers for /api/v1/page-nodes.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function remove(nodeId, ...rest) {
    return window.api.delete(apiPath(`/page-nodes/${nodeId}`), ...rest);
}
export function deleteFiles(nodeId, fileName, ...rest) {
    return window.api.delete(apiPath(`/page-nodes/${nodeId}/files/${fileName}`), ...rest);
}
export function deletePages(nodeId, pageName, ...rest) {
    return window.api.delete(apiPath(`/page-nodes/${nodeId}/pages/${pageName}`), ...rest);
}
export function listPageNodes(...rest) {
    return window.api.get(apiPath("/page-nodes"), ...rest);
}
export function getPages(nodeId, ...rest) {
    return window.api.get(apiPath(`/page-nodes/${nodeId}/pages`), ...rest);
}
export function getPages2(nodeId, pageName, ...rest) {
    return window.api.get(apiPath(`/page-nodes/${nodeId}/pages/${pageName}`), ...rest);
}
export function updateAnnounceSettings(nodeId, data, ...rest) {
    return window.api.patch(apiPath(`/page-nodes/${nodeId}/announce-settings`), data, ...rest);
}
export function createPageNodes(data, ...rest) {
    return window.api.post(apiPath("/page-nodes"), data, ...rest);
}
export function createFiles(nodeId, data, ...rest) {
    return window.api.post(apiPath(`/page-nodes/${nodeId}/files`), data, ...rest);
}
export function startPageNodes(nodeId, data, ...rest) {
    return window.api.post(apiPath(`/page-nodes/${nodeId}/start`), data, ...rest);
}
export function announcePageNodes(nodeId, data, ...rest) {
    return window.api.post(apiPath(`/page-nodes/${nodeId}/announce`), data, ...rest);
}
export function startPageNodes2(nodeId, data, ...rest) {
    return window.api.post(apiPath(`/page-nodes/${nodeId}/start`), data, ...rest);
}
export function stopPageNodes(nodeId, data, ...rest) {
    return window.api.post(apiPath(`/page-nodes/${nodeId}/stop`), data, ...rest);
}
export function createPages(nodeId, data, ...rest) {
    return window.api.post(apiPath(`/page-nodes/${nodeId}/pages`), data, ...rest);
}
export function createFiles2(nodeId, data, ...rest) {
    return window.api.post(apiPath(`/page-nodes/${nodeId}/files`), data, ...rest);
}
export function createPages2(nodeId, data, ...rest) {
    return window.api.post(apiPath(`/page-nodes/${nodeId}/pages`), data, ...rest);
}
export function updateRename(nodeId, data, ...rest) {
    return window.api.put(apiPath(`/page-nodes/${nodeId}/rename`), data, ...rest);
}
