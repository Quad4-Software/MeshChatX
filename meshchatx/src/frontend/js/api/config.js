// @ts-check

/**
 * Endpoint wrappers for /api/v1/config.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getConfig(...rest) {
    return window.api.get(apiPath("/config"), ...rest);
}
export function updateConfig(data, ...rest) {
    return window.api.patch(apiPath("/config"), data, ...rest);
}
