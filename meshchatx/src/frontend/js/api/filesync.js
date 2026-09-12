// @ts-check

/**
 * Endpoint wrappers for /api/v1/filesync.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteEntry(...rest) {
    return window.api.delete(apiPath("/filesync/entry"), ...rest);
}
export function getAcl(...rest) {
    return window.api.get(apiPath("/filesync/acl"), ...rest);
}
export function getContent(...rest) {
    return window.api.get(apiPath("/filesync/content"), ...rest);
}
export function listPeers(...rest) {
    return window.api.get(apiPath("/filesync/peers"), ...rest);
}
export function getSharedDirectorySuggestion(...rest) {
    return window.api.get(apiPath("/filesync/shared-directory-suggestion"), ...rest);
}
export function getStatus(...rest) {
    return window.api.get(apiPath("/filesync/status"), ...rest);
}
export function getTree(...rest) {
    return window.api.get(apiPath("/filesync/tree"), ...rest);
}
export function updateSettings(data, ...rest) {
    return window.api.patch(apiPath("/filesync/settings"), data, ...rest);
}
export function postAcl(data, ...rest) {
    return window.api.post(apiPath("/filesync/acl"), data, ...rest);
}
export function announceFilesync(data, ...rest) {
    return window.api.post(apiPath("/filesync/announce"), data, ...rest);
}
export function browseFilesync(data, ...rest) {
    return window.api.post(apiPath("/filesync/browse"), data, ...rest);
}
export function connectFilesync(data, ...rest) {
    return window.api.post(apiPath("/filesync/connect"), data, ...rest);
}
export function createDirectories(data, ...rest) {
    return window.api.post(apiPath("/filesync/directories"), data, ...rest);
}
export function disconnectFilesync(data, ...rest) {
    return window.api.post(apiPath("/filesync/disconnect"), data, ...rest);
}
export function downloadFilesync(data, ...rest) {
    return window.api.post(apiPath("/filesync/download"), data, ...rest);
}
export function mkdirFilesync(data, ...rest) {
    return window.api.post(apiPath("/filesync/mkdir"), data, ...rest);
}
export function startFilesync(data, ...rest) {
    return window.api.post(apiPath("/filesync/start"), data, ...rest);
}
export function stopFilesync(data, ...rest) {
    return window.api.post(apiPath("/filesync/stop"), data, ...rest);
}
export function uploadFilesync(data, ...rest) {
    return window.api.post(apiPath("/filesync/upload"), data, ...rest);
}
