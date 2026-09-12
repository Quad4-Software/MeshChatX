// @ts-check

/**
 * Endpoint wrappers for /api/v1/server.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getSecurity(...rest) {
    return window.api.get(apiPath("/server/security"), ...rest);
}
export function updateSecurity(data, ...rest) {
    return window.api.patch(apiPath("/server/security"), data, ...rest);
}
