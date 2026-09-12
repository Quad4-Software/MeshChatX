// @ts-check

/**
 * Endpoint wrappers for /api/v1/plugins.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function remove(pluginId, ...rest) {
    return window.api.delete(apiPath(`/plugins/${pluginId}`), ...rest);
}
export function listPlugins(...rest) {
    return window.api.get(apiPath("/plugins"), ...rest);
}
export function disablePlugins(pluginId, data, ...rest) {
    return window.api.post(apiPath(`/plugins/${pluginId}/disable`), data, ...rest);
}
export function enablePlugins(pluginId, data, ...rest) {
    return window.api.post(apiPath(`/plugins/${pluginId}/enable`), data, ...rest);
}
export function installPlugins(data, ...rest) {
    return window.api.post(apiPath("/plugins/install"), data, ...rest);
}
export function previewPlugins(data, ...rest) {
    return window.api.post(apiPath("/plugins/preview"), data, ...rest);
}
export function createTrustedPublishers(data, ...rest) {
    return window.api.post(apiPath("/plugins/trusted-publishers"), data, ...rest);
}
