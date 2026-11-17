// @ts-check

/**
 * Endpoint wrappers for /api/v1/update.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function getUpdateStatus(...rest) {
    return window.api.get(apiPath("/update/status"), ...rest);
}
export function getUpdateProgress(...rest) {
    return window.api.get(apiPath("/update/progress"), ...rest);
}
export function getPendingUpdate(...rest) {
    return window.api.get(apiPath("/update/pending"), ...rest);
}
export function checkUpdate(data, ...rest) {
    return window.api.post(apiPath("/update/check"), data || {}, ...rest);
}
export function downloadUpdate(data, ...rest) {
    return window.api.post(apiPath("/update/download"), data || {}, ...rest);
}
export function updateSettings(patch, ...rest) {
    return window.api.post(apiPath("/update/settings"), patch, ...rest);
}
export function applyUpdateFile(file, ...rest) {
    const form = new FormData();
    form.append("file", file);
    return window.api.post(apiPath("/update/apply-file"), form, ...rest);
}
export function applyUpdatePath(path, channel, ...rest) {
    return window.api.post(apiPath("/update/apply-file"), { path, channel: channel || null }, ...rest);
}
export function discardUpdate(...rest) {
    return window.api.post(apiPath("/update/discard"), {}, ...rest);
}
