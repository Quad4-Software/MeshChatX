// @ts-check

/**
 * Endpoint wrappers for /api/v1/sideband-plugins.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listSidebandPlugins(...rest) {
    return window.api.get(apiPath("/sideband-plugins"), ...rest);
}
export function postConfig(data, ...rest) {
    return window.api.post(apiPath("/sideband-plugins/config"), data, ...rest);
}
export function reloadSidebandPlugins(data, ...rest) {
    return window.api.post(apiPath("/sideband-plugins/reload"), data, ...rest);
}
